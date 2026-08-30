// Implements: WC-079 AA-03, AA-04, AA-05, AA-06, AA-08, AA-09
// constitutional_basis: C-003, C-005, C-007, C-023, C-026, C-036, C-037, C-059, C-063, C-079

using System.Text.Json;
using System.Data;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record AdmissionValidationResult(AgentAdmissionValidation Validation, bool Replayed);
public sealed record AdmissionMutationResult(AgentAdmission Admission, bool Replayed);
public sealed record AdmissionTransitionIntent(
    int ExpectedStateVersion,
    int Revision,
    string AdmissionContentDigest,
    string EvidenceSetDigest,
    string? ArtifactDigest,
    string PolicyVersion,
    string? ReasonCategory,
    string? SuccessorVersion);
public sealed record OfferableSkill(string SkillId, string SkillVersion, string Capability, string BusinessKpi);
public sealed record OfferableProfessionalVersion(
    string ProfessionalTypeId,
    string ProfessionalVersion,
    string AdmissionContentDigest,
    string DisplayName,
    IReadOnlyList<string> SupportedChannels,
    IReadOnlyList<OfferableSkill> Skills);
public sealed record AdmissionReadinessObservation(
    string AssertionType,
    string SubjectDigest,
    string Environment,
    string Status,
    string SourceAuthority,
    DateTimeOffset ObservedAt,
    DateTimeOffset ValidUntil,
    string PolicyVersion,
    string EvidenceRef);

public sealed class AdmissionNotFoundException : Exception;
public sealed class AdmissionIdempotencyConflictException : Exception;
public sealed class AdmissionStateConflictException : Exception;
public sealed class AdmissionTransitionBlockedException(string reason) : Exception(reason);

public sealed class AgentAdmissionService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    AgentAdmissionValidator validator,
    IRelationshipConstitutionalGateway constitutionalGateway)
{
    private static readonly string[] RequiredReadiness =
        ["RUNTIME", "ENVIRONMENT", "PROVIDER", "BILLING", "ARTIFACT", "CONSTITUTIONAL"];

    public async Task<AdmissionMutationResult> CreateDraftAsync(
        Guid tenantId,
        string professionalType,
        string professionalVersion,
        Guid ownerSubjectId,
        Guid actorSubjectId,
        Guid idempotencyKey,
        CancellationToken cancellationToken)
    {
        var requestHash = AgentAdmissionCanonicalizer.Digest($"CREATE|{professionalType}|{professionalVersion}|{ownerSubjectId:D}");
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var prior = await db.AgentAdmissionIdempotency.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.Operation == "CREATE" && value.IdempotencyKey == idempotencyKey,
            cancellationToken);
        if (prior is not null)
        {
            if (prior.ActorSubjectId != actorSubjectId || prior.MaterialRequestHash != requestHash || prior.Status != "COMPLETED")
                throw new AdmissionIdempotencyConflictException();
            var replayed = await db.AgentAdmissions.SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.AdmissionId == prior.AdmissionId,
                cancellationToken) ?? throw new AdmissionStateConflictException();
            return new(replayed, true);
        }
        var existing = await FindAsync(db, tenantId, professionalType, professionalVersion, cancellationToken);
        if (existing is not null)
            throw new AdmissionStateConflictException();

        var admission = new AgentAdmission
        {
            TenantId = tenantId,
            ProfessionalTypeId = professionalType,
            ProfessionalVersion = professionalVersion,
            OwnerSubjectId = ownerSubjectId,
        };
        db.AgentAdmissions.Add(admission);
        db.AgentAdmissionIdempotency.Add(CompletedIdempotency(
            admission, "CREATE", idempotencyKey, actorSubjectId, null, requestHash, admission.AdmissionId));
        await db.SaveChangesAsync(cancellationToken);
        return new(admission, false);
    }

    public async Task<AdmissionMutationResult> PutRevisionAsync(
        Guid tenantId,
        string professionalType,
        string professionalVersion,
        Guid admissionId,
        int revision,
        int expectedStateVersion,
        string suppliedDigest,
        JsonElement content,
        Guid actorSubjectId,
        Guid idempotencyKey,
        CancellationToken cancellationToken)
    {
        var canonicalJson = AgentAdmissionCanonicalizer.Canonicalize(content);
        var actualDigest = AgentAdmissionCanonicalizer.Digest(content);
        if (!string.Equals(actualDigest, suppliedDigest, StringComparison.Ordinal))
            throw new ArgumentException("Admission content digest does not match canonical content.");

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var admission = await RequireAsync(db, tenantId, professionalType, professionalVersion, admissionId, cancellationToken);
        RequireOwner(admission, actorSubjectId);
        var requestHash = AgentAdmissionCanonicalizer.Digest($"REVISE|{revision}|{expectedStateVersion}|{actualDigest}");
        if (await FindReplayAsync(db, admission, "REVISE", idempotencyKey, actorSubjectId, requestHash, cancellationToken))
            return new(admission, true);
        if (admission.StateVersion != expectedStateVersion || revision != admission.CurrentRevision + 1
            || admission.State is not (AgentAdmissionState.Draft or AgentAdmissionState.RemediationRequired or AgentAdmissionState.Rejected))
            throw new AdmissionStateConflictException();

        var predecessor = await db.AgentAdmissionRevisions.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.AdmissionId == admissionId)
            .OrderByDescending(value => value.Revision)
            .Select(value => (Guid?)value.RevisionId)
            .FirstOrDefaultAsync(cancellationToken);
        db.AgentAdmissionRevisions.Add(new AgentAdmissionRevision
        {
            TenantId = tenantId,
            AdmissionId = admissionId,
            Revision = revision,
            ContractSchemaVersion = content.ValueKind == JsonValueKind.Object
                && content.TryGetProperty("contractSchemaVersion", out var schemaVersion)
                && schemaVersion.ValueKind == JsonValueKind.String
                    ? schemaVersion.GetString() ?? string.Empty
                    : string.Empty,
            AdmissionContentDigest = actualDigest,
            AdmissionContentJson = canonicalJson,
            ActorSubjectId = actorSubjectId,
            PredecessorRevisionId = predecessor,
        });
        admission.State = AgentAdmissionState.Draft;
        admission.StateVersion++;
        admission.CurrentRevision = revision;
        admission.AdmissionContentDigest = actualDigest;
        admission.EvidenceSetDigest = null;
        admission.ArtifactDigest = null;
        admission.PolicyVersion = null;
        admission.UpdatedAt = DateTimeOffset.UtcNow;
        db.AgentAdmissionIdempotency.Add(CompletedIdempotency(
            admission, "REVISE", idempotencyKey, actorSubjectId, actualDigest, requestHash, admission.AdmissionId));
        await SaveOrConflictAsync(db, cancellationToken);
        return new(admission, false);
    }

    public async Task<AdmissionValidationResult> ValidateAsync(
        Guid tenantId,
        string professionalType,
        string professionalVersion,
        Guid admissionId,
        int revision,
        string contentDigest,
        string profile,
        Guid actorSubjectId,
        bool validatorOperator,
        Guid idempotencyKey,
        CancellationToken cancellationToken)
    {
        if (profile != AgentAdmissionValidator.Profile) throw new ArgumentException("Unsupported validator profile.");
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var admission = await RequireAsync(db, tenantId, professionalType, professionalVersion, admissionId, cancellationToken);
        if (!validatorOperator) RequireOwner(admission, actorSubjectId);
        var requestHash = AgentAdmissionCanonicalizer.Digest($"VALIDATE|{revision}|{contentDigest}|{profile}");
        var existing = await db.AgentAdmissionValidations.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.IdempotencyKey == idempotencyKey,
            cancellationToken);
        if (existing is not null)
        {
            if (existing.AdmissionId != admissionId || existing.RequestHash != requestHash)
                throw new AdmissionIdempotencyConflictException();
            return new(existing, true);
        }
        if (admission.State is not (AgentAdmissionState.Draft or AgentAdmissionState.RemediationRequired)
            || admission.CurrentRevision != revision || admission.AdmissionContentDigest != contentDigest)
            throw new AdmissionStateConflictException();

        var storedRevision = await db.AgentAdmissionRevisions.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.AdmissionId == admissionId && value.Revision == revision,
            cancellationToken) ?? throw new AdmissionStateConflictException();
        using var document = JsonDocument.Parse(storedRevision.AdmissionContentJson);
        var findings = validator.Validate(document.RootElement, professionalType, professionalVersion, contentDigest);
        var validation = new AgentAdmissionValidation
        {
            TenantId = tenantId,
            AdmissionId = admissionId,
            Revision = revision,
            ValidatorProfile = profile,
            IdempotencyKey = idempotencyKey,
            RequestHash = requestHash,
            Result = findings.Count == 0 ? "PASS" : "FAIL",
            FindingCount = findings.Count,
        };
        db.AgentAdmissionValidations.Add(validation);
        db.AgentAdmissionFindings.AddRange(findings.Select(finding => new AgentAdmissionFinding
        {
            TenantId = tenantId,
            ValidationId = validation.ValidationId,
            RuleId = finding.RuleId,
            Severity = finding.Severity,
            ContractPath = finding.ContractPath,
            ConstitutionalBasis = finding.ConstitutionalBasis,
            Expected = finding.Expected,
            ObservedCategory = finding.ObservedCategory,
            Remediation = finding.Remediation,
            Blocking = finding.Blocking,
        }));
        admission.State = findings.Count == 0 ? AgentAdmissionState.Validated : AgentAdmissionState.RemediationRequired;
        admission.StateVersion++;
        admission.UpdatedAt = DateTimeOffset.UtcNow;
        await SaveOrConflictAsync(db, cancellationToken);
        return new(validation, false);
    }

    public async Task<IReadOnlyList<AgentAdmissionFinding>> GetFindingsAsync(
        Guid tenantId,
        string professionalType,
        string professionalVersion,
        Guid admissionId,
        Guid validationId,
        Guid actorSubjectId,
        bool reviewer,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var admission = await RequireAsync(db, tenantId, professionalType, professionalVersion, admissionId, cancellationToken);
        if (!reviewer) RequireOwner(admission, actorSubjectId);
        var validationExists = await db.AgentAdmissionValidations.AsNoTracking().AnyAsync(
            value => value.TenantId == tenantId && value.AdmissionId == admissionId && value.ValidationId == validationId,
            cancellationToken);
        if (!validationExists) throw new AdmissionNotFoundException();
        return await db.AgentAdmissionFindings.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.ValidationId == validationId)
            .OrderBy(value => value.RuleId).ThenBy(value => value.ContractPath)
            .ToListAsync(cancellationToken);
    }

    public async Task RecordReadinessAsync(
        Guid tenantId,
        string professionalType,
        string professionalVersion,
        AdmissionReadinessObservation observation,
        CancellationToken cancellationToken)
    {
        if (!RequiredReadiness.Contains(observation.AssertionType, StringComparer.Ordinal)
            || observation.Environment is not ("demo" or "uat" or "prod")
            || observation.Status is not ("PASS" or "FAIL" or "UNKNOWN" or "UNAVAILABLE" or "REVOKED")
            || observation.ValidUntil <= observation.ObservedAt
            || string.IsNullOrWhiteSpace(observation.SourceAuthority)
            || string.IsNullOrWhiteSpace(observation.EvidenceRef))
            throw new ArgumentException("Readiness observation is invalid.");

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var admission = await FindAsync(db, tenantId, professionalType, professionalVersion, cancellationToken)
            ?? throw new AdmissionNotFoundException();
        if (admission.State is not (AgentAdmissionState.Approved or AgentAdmissionState.Active or AgentAdmissionState.Suspended))
            throw new AdmissionTransitionBlockedException("Readiness can bind only an approved admission revision.");
        var expectedDigest = observation.AssertionType == "ARTIFACT"
            ? admission.ArtifactDigest
            : admission.AdmissionContentDigest;
        if (expectedDigest != observation.SubjectDigest || admission.PolicyVersion != observation.PolicyVersion)
            throw new AdmissionTransitionBlockedException("Readiness subject or policy does not match the approved admission.");
        db.AgentAdmissionAssertions.Add(new AgentAdmissionAssertion
        {
            TenantId = tenantId,
            AdmissionId = admission.AdmissionId,
            AssertionType = observation.AssertionType,
            SubjectDigest = observation.SubjectDigest,
            Environment = observation.Environment,
            Status = observation.Status,
            SourceAuthority = observation.SourceAuthority,
            ObservedAt = observation.ObservedAt,
            ValidUntil = observation.ValidUntil,
            PolicyVersion = observation.PolicyVersion,
            EvidenceRef = observation.EvidenceRef,
        });
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task<AdmissionMutationResult> TransitionAsync(
        Guid tenantId,
        string professionalType,
        string professionalVersion,
        string operation,
        AdmissionTransitionIntent intent,
        Guid actorSubjectId,
        string actorAuthority,
        Guid idempotencyKey,
        Guid correlationId,
        string environment,
        CancellationToken cancellationToken)
    {
        await using var lookupDb = await dbFactory.CreateDbContextAsync(cancellationToken);
        var admission = await FindAsync(lookupDb, tenantId, professionalType, professionalVersion, cancellationToken)
            ?? throw new AdmissionNotFoundException();
        if (operation == "SUBMIT") RequireOwner(admission, actorSubjectId);
        var requestHash = TransitionRequestHash(operation, intent, environment);
        if (await FindReplayAsync(lookupDb, admission, operation, idempotencyKey, actorSubjectId, requestHash, cancellationToken))
            return new(admission, true);
        EnsureTransition(admission, operation, intent, actorSubjectId);
        if (operation == "ACTIVATE") await RequireReadinessAsync(lookupDb, admission, intent, environment, cancellationToken);

        var target = TargetState(operation);
        var evidenceId = await constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            admission.AdmissionId,
            professionalType,
            $"AGENT_ADMISSION_{operation}",
            correlationId,
            new
            {
                admission.AdmissionId,
                admission.ProfessionalTypeId,
                admission.ProfessionalVersion,
                fromState = AgentAdmissionStateCodec.ToDatabase(admission.State),
                toState = AgentAdmissionStateCodec.ToDatabase(target),
                intent.Revision,
                intent.AdmissionContentDigest,
                intent.EvidenceSetDigest,
                intent.ArtifactDigest,
                intent.PolicyVersion,
                actor_subject_id = actorSubjectId.ToString("D"),
                actor_authority = actorAuthority,
                submitter_subject_id = admission.SubmitterSubjectId?.ToString("D"),
            },
            cancellationToken);

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        admission = await RequireAsync(db, tenantId, professionalType, professionalVersion, admission.AdmissionId, cancellationToken);
        EnsureTransition(admission, operation, intent, actorSubjectId);
        var from = AgentAdmissionStateCodec.ToDatabase(admission.State);
        var transition = new AgentAdmissionTransition
        {
            TenantId = tenantId,
            AdmissionId = admission.AdmissionId,
            FromState = from,
            ToState = AgentAdmissionStateCodec.ToDatabase(target),
            ActorSubjectId = actorSubjectId,
            ActorAuthority = actorAuthority,
            CorrelationId = correlationId,
            AdmissionContentDigest = intent.AdmissionContentDigest,
            EvidenceSetDigest = intent.EvidenceSetDigest,
            ArtifactDigest = intent.ArtifactDigest,
            PolicyVersion = intent.PolicyVersion,
            CeEvidenceRef = evidenceId,
            ReasonCategory = intent.ReasonCategory,
        };
        db.AgentAdmissionTransitions.Add(transition);
        admission.State = target;
        admission.StateVersion++;
        admission.SubmitterSubjectId ??= operation == "SUBMIT" ? actorSubjectId : null;
        admission.EvidenceSetDigest = intent.EvidenceSetDigest;
        admission.ArtifactDigest = intent.ArtifactDigest;
        admission.PolicyVersion = intent.PolicyVersion;
        admission.SuccessorVersion = intent.SuccessorVersion;
        admission.UpdatedAt = DateTimeOffset.UtcNow;
        db.AgentAdmissionIdempotency.Add(CompletedIdempotency(
            admission, operation, idempotencyKey, actorSubjectId, intent.AdmissionContentDigest, requestHash, transition.TransitionId));
        db.AgentAdmissionOutbox.Add(new AgentAdmissionOutbox
        {
            TenantId = tenantId,
            AdmissionId = admission.AdmissionId,
            TransitionId = transition.TransitionId,
            EventType = $"agent.admission.{operation.ToLowerInvariant()}",
            ScopeHash = AgentAdmissionCanonicalizer.Digest($"{tenantId:D}|{admission.AdmissionId:D}|{transition.TransitionId:D}|{target}"),
            PayloadJson = JsonSerializer.Serialize(new
            {
                admission.AdmissionId,
                admission.ProfessionalTypeId,
                admission.ProfessionalVersion,
                state = AgentAdmissionStateCodec.ToDatabase(target),
                admission.StateVersion,
                transition.TransitionId,
                transition.CeEvidenceRef,
            }),
        });
        await SaveOrConflictAsync(db, cancellationToken);
        return new(admission, false);
    }

    public async Task<IReadOnlyList<OfferableProfessionalVersion>> GetOfferableAsync(
        string environment,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var result = new List<OfferableProfessionalVersion>();
        var connection = db.Database.GetDbConnection();
        if (connection.State != ConnectionState.Open) await connection.OpenAsync(cancellationToken);
        await using var command = connection.CreateCommand();
        command.CommandText = "SELECT projection::text FROM business.get_offerable_professional_versions(@environment)";
        var parameter = command.CreateParameter();
        parameter.ParameterName = "environment";
        parameter.Value = environment;
        command.Parameters.Add(parameter);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            var projection = JsonSerializer.Deserialize<OfferableProfessionalVersion>(reader.GetString(0), new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
            }) ?? throw new InvalidOperationException("Offerable projection is invalid.");
            result.Add(projection);
        }
        return result;
    }

    private static async Task<AgentAdmission?> FindAsync(
        EmploymentRelationshipDbContext db,
        Guid tenantId,
        string professionalType,
        string professionalVersion,
        CancellationToken cancellationToken) => await db.AgentAdmissions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.ProfessionalTypeId == professionalType && value.ProfessionalVersion == professionalVersion,
            cancellationToken);

    private static async Task<AgentAdmission> RequireAsync(
        EmploymentRelationshipDbContext db,
        Guid tenantId,
        string professionalType,
        string professionalVersion,
        Guid admissionId,
        CancellationToken cancellationToken) => await db.AgentAdmissions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.AdmissionId == admissionId
                && value.ProfessionalTypeId == professionalType && value.ProfessionalVersion == professionalVersion,
            cancellationToken) ?? throw new AdmissionNotFoundException();

    private static void RequireOwner(AgentAdmission admission, Guid actorSubjectId)
    {
        if (admission.OwnerSubjectId != actorSubjectId) throw new AdmissionNotFoundException();
    }

    private static async Task<bool> FindReplayAsync(
        EmploymentRelationshipDbContext db,
        AgentAdmission admission,
        string operation,
        Guid idempotencyKey,
        Guid actorSubjectId,
        string requestHash,
        CancellationToken cancellationToken)
    {
        var replay = await db.AgentAdmissionIdempotency.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == admission.TenantId && value.Operation == operation
                && value.IdempotencyKey == idempotencyKey,
            cancellationToken);
        if (replay is null) return false;
        if (replay.AdmissionId != admission.AdmissionId || replay.ActorSubjectId != actorSubjectId
            || replay.MaterialRequestHash != requestHash || replay.Status != "COMPLETED")
            throw new AdmissionIdempotencyConflictException();
        return true;
    }

    private static AgentAdmissionIdempotency CompletedIdempotency(
        AgentAdmission admission,
        string operation,
        Guid key,
        Guid actor,
        string? subjectDigest,
        string requestHash,
        Guid outcome) => new()
        {
            TenantId = admission.TenantId,
            AdmissionId = admission.AdmissionId,
            Operation = operation,
            IdempotencyKey = key,
            ActorSubjectId = actor,
            SubjectDigest = subjectDigest,
            MaterialRequestHash = requestHash,
            OutcomeReference = outcome,
            Status = "COMPLETED",
            CompletedAt = DateTimeOffset.UtcNow,
        };

    private static string TransitionRequestHash(string operation, AdmissionTransitionIntent intent, string environment) =>
        AgentAdmissionCanonicalizer.Digest(JsonSerializer.Serialize(new
        {
            operation,
            environment,
            intent.ExpectedStateVersion,
            intent.Revision,
            intent.AdmissionContentDigest,
            intent.EvidenceSetDigest,
            intent.ArtifactDigest,
            intent.PolicyVersion,
            intent.ReasonCategory,
            intent.SuccessorVersion,
        }));

    private static void EnsureTransition(
        AgentAdmission admission,
        string operation,
        AdmissionTransitionIntent intent,
        Guid actorSubjectId)
    {
        if (admission.StateVersion != intent.ExpectedStateVersion
            || admission.CurrentRevision != intent.Revision
            || admission.AdmissionContentDigest != intent.AdmissionContentDigest)
            throw new AdmissionStateConflictException();
        if (operation is "APPROVE" or "REJECT"
            && (admission.EvidenceSetDigest != intent.EvidenceSetDigest
                || admission.ArtifactDigest != intent.ArtifactDigest
                || admission.PolicyVersion != intent.PolicyVersion))
            throw new AdmissionTransitionBlockedException("Review must bind the exact submitted evidence, artifact, and policy.");
        if (operation == "ACTIVATE"
            && (admission.ArtifactDigest != intent.ArtifactDigest
                || admission.PolicyVersion != intent.PolicyVersion))
            throw new AdmissionTransitionBlockedException("Activation must bind the exact approved artifact and policy.");
        if (operation != "SUBMIT" && admission.SubmitterSubjectId == actorSubjectId)
            throw new AdmissionTransitionBlockedException("Submitter cannot perform an independent lifecycle transition.");
        var allowed = (admission.State, operation) switch
        {
            (AgentAdmissionState.Validated, "SUBMIT") => true,
            (AgentAdmissionState.ReadyForReview, "APPROVE" or "REJECT") => true,
            (AgentAdmissionState.Approved, "ACTIVATE") => true,
            (AgentAdmissionState.Active, "SUSPEND" or "SUPERSEDE" or "RETIRE") => true,
            (AgentAdmissionState.Suspended, "ACTIVATE" or "SUPERSEDE" or "RETIRE") => true,
            _ => false,
        };
        if (!allowed) throw new AdmissionStateConflictException();
        if (operation is "REJECT" or "SUSPEND" && string.IsNullOrWhiteSpace(intent.ReasonCategory))
            throw new ArgumentException("Reason category is required.");
        if (operation == "SUPERSEDE" && string.IsNullOrWhiteSpace(intent.SuccessorVersion))
            throw new ArgumentException("Successor version is required.");
    }

    private static AgentAdmissionState TargetState(string operation) => operation switch
    {
        "SUBMIT" => AgentAdmissionState.ReadyForReview,
        "APPROVE" => AgentAdmissionState.Approved,
        "REJECT" => AgentAdmissionState.Rejected,
        "ACTIVATE" => AgentAdmissionState.Active,
        "SUSPEND" => AgentAdmissionState.Suspended,
        "SUPERSEDE" => AgentAdmissionState.Superseded,
        "RETIRE" => AgentAdmissionState.Retired,
        _ => throw new ArgumentException("Unsupported admission transition."),
    };

    private static async Task RequireReadinessAsync(
        EmploymentRelationshipDbContext db,
        AgentAdmission admission,
        AdmissionTransitionIntent intent,
        string environment,
        CancellationToken cancellationToken)
    {
        var current = await CurrentAssertionsAsync(db, admission, environment, DateTimeOffset.UtcNow, cancellationToken);
        if (!RequiredReadiness.All(type => current.Contains(type)))
            throw new AdmissionTransitionBlockedException("All exact current readiness assertions are required.");
        if (string.IsNullOrWhiteSpace(intent.ArtifactDigest))
            throw new AdmissionTransitionBlockedException("Artifact digest is required for activation.");
    }

    private static async Task<HashSet<string>> CurrentAssertionsAsync(
        EmploymentRelationshipDbContext db,
        AgentAdmission admission,
        string environment,
        DateTimeOffset now,
        CancellationToken cancellationToken)
    {
        var rows = await db.AgentAdmissionAssertions.AsNoTracking()
            .Where(value => value.TenantId == admission.TenantId && value.AdmissionId == admission.AdmissionId
                && value.Environment == environment && value.PolicyVersion == admission.PolicyVersion
                && value.ValidUntil > now)
            .OrderByDescending(value => value.ObservedAt)
            .ToListAsync(cancellationToken);
        return rows.GroupBy(value => value.AssertionType)
            .Select(group => group.First())
            .Where(value => value.Status == "PASS"
                && value.SubjectDigest == (value.AssertionType == "ARTIFACT" ? admission.ArtifactDigest : admission.AdmissionContentDigest))
            .Select(value => value.AssertionType)
            .ToHashSet(StringComparer.Ordinal);
    }

    private static async Task SaveOrConflictAsync(EmploymentRelationshipDbContext db, CancellationToken cancellationToken)
    {
        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateConcurrencyException exception)
        {
            throw new AdmissionStateConflictException() { Source = exception.Source };
        }
    }
}