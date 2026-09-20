// Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md §6.3
// constitutional_basis: C-001, C-005, C-007, C-023, C-026, C-059, C-063, C-079

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class OperationalMandateResolver(
    IDbContextFactory<EmploymentRelationshipDbContext> relationshipFactory
) : IOperationalMandateResolver
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public async Task<OperationalMandateReadiness> GetReadinessAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db
            .EmploymentRelationships.AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                cancellationToken
            );
        var participantExists = await db
            .RelationshipParticipants.AsNoTracking()
            .AnyAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ParticipantId == participantId
                    && value.Status == "ACTIVE",
                cancellationToken
            );
        var blocked = new List<string>();
        if (relationship is null || !participantExists)
            return new OperationalMandateReadiness(
                false,
                ["The relationship mandate identity is unavailable."]
            );
        if (!relationship.ProfessionalAdmissionId.HasValue)
            blocked.Add("The active professional admission is unavailable.");
        if (!relationship.AcceptedContractId.HasValue)
            blocked.Add("The accepted contract binding is unavailable.");
        if (!relationship.AuthoritySnapshotId.HasValue)
            blocked.Add("The current Decision Space snapshot is unavailable.");
        if (blocked.Count > 0)
            return new OperationalMandateReadiness(false, blocked);

        var admission = await db
            .AgentAdmissions.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.AdmissionId == relationship.ProfessionalAdmissionId!.Value
                    && value.State == AgentAdmissionState.Active,
                cancellationToken
            );
        if (admission?.AdmissionContentDigest is null || admission.ArtifactDigest is null)
            blocked.Add("The admitted professional artifact coordinates are unavailable.");
        else if (
            !await db
                .AgentAdmissionRevisions.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.AdmissionId == admission.AdmissionId
                        && value.Revision == admission.CurrentRevision,
                    cancellationToken
                )
        )
            blocked.Add("The current admission revision is unavailable.");

        if (
            !await db
                .ContractAcceptances.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == relationshipId
                        && value.ContractId == relationship.AcceptedContractId!.Value,
                    cancellationToken
                )
        )
            blocked.Add("The accepted contract evidence is unavailable.");
        if (
            !await db
                .DecisionSpaceSnapshots.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.SnapshotId == relationship.AuthoritySnapshotId!.Value,
                    cancellationToken
                )
        )
            blocked.Add("The current Decision Space evidence is unavailable.");

        var skills = await db
            .RelationshipSkillConfigurations.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Status == "ACCEPTED"
            )
            .ToListAsync(cancellationToken);
        foreach (var skill in skills)
        {
            if (skill.AuthorityState is not ("GRANTED" or "CONSTRAINED"))
                blocked.Add($"Skill {skill.SkillId} lacks current operational authority.");
            var bindingReady =
                admission is not null
                && await db
                    .AgentSkillRuntimeBindings.AsNoTracking()
                    .AnyAsync(
                        value =>
                            value.TenantId == tenantId
                            && value.AdmissionId == admission.AdmissionId
                            && value.SkillId == skill.SkillId
                            && value.SkillVersion == skill.SkillVersion
                            && value.SupersededAt == null,
                        cancellationToken
                    );
            if (!bindingReady)
                blocked.Add($"Skill {skill.SkillId} lacks an exact active runtime binding.");
        }
        return new OperationalMandateReadiness(blocked.Count == 0, blocked);
    }

    public async Task<OperationalMandateV1> ResolveAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        Guid constitutionalEvidenceId,
        string skillId,
        string operationalPurpose,
        CancellationToken cancellationToken
    )
    {
        await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
        var replay = await db
            .OperationalMandateSnapshots.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.IdempotencyIdentity == idempotencyKey,
                cancellationToken
            );
        if (replay is not null)
        {
            var replayMandate =
                JsonSerializer.Deserialize<OperationalMandateV1>(replay.MandateJson, JsonOptions)
                ?? throw new OperationalMandateUnavailableException();
            if (
                replayMandate.ActorId != participantId
                || !string.Equals(replayMandate.SkillId, skillId, StringComparison.Ordinal)
                || !string.Equals(
                    replayMandate.OperationalPurpose,
                    operationalPurpose,
                    StringComparison.Ordinal
                )
            )
            {
                throw new ConversationIdempotencyConflictException();
            }
            return replayMandate;
        }

        var relationship = await db.EmploymentRelationships.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken
        );
        var participant = await db
            .RelationshipParticipants.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ParticipantId == participantId
                    && value.Status == "ACTIVE",
                cancellationToken
            );
        if (
            relationship is null
            || participant is null
            || relationship.State
                is not (
                    EmploymentRelationshipState.Active
                    or EmploymentRelationshipState.TrialActive
                )
            || relationship.StoppedAt.HasValue
            || !relationship.ProfessionalAdmissionId.HasValue
            || !relationship.AcceptedContractId.HasValue
            || !relationship.AuthoritySnapshotId.HasValue
        )
        {
            throw new OperationalMandateUnavailableException();
        }

        var admission = await db
            .AgentAdmissions.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.AdmissionId == relationship.ProfessionalAdmissionId.Value
                    && value.State == AgentAdmissionState.Active,
                cancellationToken
            );
        if (admission?.AdmissionContentDigest is null || admission.ArtifactDigest is null)
        {
            throw new OperationalMandateUnavailableException();
        }

        var admissionRevision = await db
            .AgentAdmissionRevisions.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.AdmissionId == admission.AdmissionId
                    && value.Revision == admission.CurrentRevision,
                cancellationToken
            );
        var runtimeBinding = await db
            .AgentSkillRuntimeBindings.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.AdmissionId == admission.AdmissionId
                    && value.SkillId == skillId
                    && value.SupersededAt == null,
                cancellationToken
            );
        var skill = await db
            .RelationshipSkillConfigurations.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.SkillId == skillId
                    && value.Status == "ACCEPTED",
                cancellationToken
            );
        if (
            admissionRevision is null
            || runtimeBinding is null
            || skill is null
            || skill.SkillVersion != runtimeBinding.SkillVersion
            || skill.AuthorityState is not ("GRANTED" or "CONSTRAINED")
            || !skill.GoalId.HasValue
        )
        {
            throw new OperationalMandateUnavailableException();
        }

        var goal = await db
            .RelationshipGoals.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.GoalId == skill.GoalId.Value
                    && value.Status == "ACTIVE",
                cancellationToken
            );
        var goalDecision = await db
            .RelationshipGoalDecisions.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.GoalId == skill.GoalId.Value
            )
            .OrderByDescending(value => value.OccurredAt)
            .ThenByDescending(value => value.DecisionId)
            .FirstOrDefaultAsync(cancellationToken);
        var contextRevision = await db
            .ContextConfirmationEvents.AsNoTracking()
            .CountAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.Action == "CONFIRMED",
                cancellationToken
            );
        var configurationRevision = await db
            .RelationshipSkillDecisions.AsNoTracking()
            .CountAsync(
                value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                cancellationToken
            );
        var goalRevision = await db
            .RelationshipGoalDecisions.AsNoTracking()
            .CountAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.GoalId == skill.GoalId,
                cancellationToken
            );
        var decisionSpace = await db
            .DecisionSpaceSnapshots.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.SnapshotId == relationship.AuthoritySnapshotId.Value,
                cancellationToken
            );
        var acceptance = await db
            .ContractAcceptances.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ContractId == relationship.AcceptedContractId.Value,
                cancellationToken
            );
        if (
            goal is null
            || goalDecision?.Decision != "VERIFIED"
            || goalDecision.SkillId != skillId
            || contextRevision == 0
            || configurationRevision == 0
            || goalRevision == 0
            || decisionSpace is null
            || acceptance is null
        )
        {
            throw new OperationalMandateUnavailableException();
        }

        using var document = JsonDocument.Parse(admissionRevision.AdmissionContentJson);
        var root = document.RootElement;
        var identity = root.GetProperty("professionalIdentity");
        var compliance = root.GetProperty("complianceDeclaration");
        var adapter = root.GetProperty("runtimeAdapter");
        var admittedSkill = root.GetProperty("skillManifest")
            .EnumerateArray()
            .SingleOrDefault(value =>
                value.GetProperty("skillId").GetString() == skillId
                && value.GetProperty("skillVersion").GetString() == skill.SkillVersion
            );
        if (admittedSkill.ValueKind == JsonValueKind.Undefined)
        {
            throw new OperationalMandateUnavailableException();
        }

        var mandateId = Guid.NewGuid();
        var deadline = DateTimeOffset.UtcNow.AddMinutes(5);
        deadline = new DateTimeOffset(
            deadline.Year,
            deadline.Month,
            deadline.Day,
            deadline.Hour,
            deadline.Minute,
            deadline.Second,
            TimeSpan.Zero
        );
        var permittedActions = admittedSkill
            .GetProperty("constitutionalActions")
            .EnumerateArray()
            .Select(value => value.GetString()!)
            .ToArray();
        var draft = new OperationalMandateV1(
            "1.0",
            mandateId,
            string.Empty,
            tenantId,
            relationshipId,
            relationship.AgentInstanceId,
            participantId,
            RelationshipRoleCodec.ToDatabase(participant.Role),
            RelationshipStateCodec.ToDatabase(relationship.State),
            relationship.State == EmploymentRelationshipState.TrialActive ? "TRIAL" : "LIVE",
            admission.ProfessionalTypeId,
            runtimeBinding.ReleaseSequence,
            admission.ProfessionalVersion,
            runtimeBinding.SpecificationRevision,
            runtimeBinding.SpecificationDigest,
            admission.CurrentRevision,
            admission.AdmissionContentDigest,
            admission.ArtifactDigest,
            compliance.GetProperty("agentBaseSpec").GetProperty("version").GetString()!,
            compliance.GetProperty("constitutionalDna").GetProperty("version").GetString()!,
            compliance
                .GetProperty("platformAgentContract")
                .GetProperty("schemaVersion")
                .GetString()!,
            adapter.GetProperty("protocolVersion").GetString()!,
            acceptance.ContractHash,
            skill.SkillId,
            skill.SkillVersion,
            runtimeBinding.InputSchemaDigest,
            runtimeBinding.OutputSchemaDigest,
            runtimeBinding.PromptVersion,
            runtimeBinding.PromptDigest,
            contextRevision,
            configurationRevision,
            goalRevision,
            decisionSpace.Version,
            $"decision-space:{decisionSpace.SnapshotId:D}:budget",
            admission.CurrentRevision,
            [
                $"contract-acceptance:{acceptance.AcceptanceId:D}",
                $"goal-decision:{goalDecision.DecisionId:D}",
            ],
            false,
            null,
            operationalPurpose,
            permittedActions,
            ["UNDECLARED_ACTION"],
            deadline,
            idempotencyKey,
            $"ce-decision:{constitutionalEvidenceId:D}",
            $"ce-evidence:{constitutionalEvidenceId:D}",
            null,
            null
        );
        var mandate = draft with { MandateDigest = Digest(draft) };
        var mandateJson = JsonSerializer.Serialize(mandate, JsonOptions);
        db.OperationalMandateSnapshots.Add(
            new OperationalMandateSnapshot
            {
                MandateId = mandateId,
                TenantId = tenantId,
                RelationshipId = relationshipId,
                AgentInstanceId = relationship.AgentInstanceId,
                ActorParticipantId = participantId,
                AdmissionId = admission.AdmissionId,
                RuntimeBindingId = runtimeBinding.BindingId,
                ContractId = acceptance.ContractId,
                DecisionSpaceSnapshotId = decisionSpace.SnapshotId,
                ConstitutionalEvidenceId = constitutionalEvidenceId,
                IdempotencyIdentity = idempotencyKey,
                SkillId = skillId,
                MandateDigest = mandate.MandateDigest,
                MandateJson = mandateJson,
                Deadline = deadline,
            }
        );
        await db.SaveChangesAsync(cancellationToken);
        return mandate;
    }

    private static string Digest(OperationalMandateV1 mandate)
    {
        var canonical = JsonSerializer.Serialize(
            mandate with
            {
                MandateDigest = string.Empty,
            },
            JsonOptions
        );
        var normalized =
            JsonNode.Parse(canonical)?.AsObject()
            ?? throw new OperationalMandateUnavailableException();
        normalized.Remove("mandateDigest");
        normalized["deadline"] = mandate.Deadline.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");
        using var document = JsonDocument.Parse(normalized.ToJsonString());
        var properties = document
            .RootElement.EnumerateObject()
            .OrderBy(property => property.Name, StringComparer.Ordinal);
        var builder = new StringBuilder("{");
        var separator = string.Empty;
        foreach (var property in properties)
        {
            builder
                .Append(separator)
                .Append(JsonSerializer.Serialize(property.Name))
                .Append(':')
                .Append(property.Value.GetRawText());
            separator = ",";
        }
        builder.Append('}');
        return $"sha256:{Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(builder.ToString()))).ToLowerInvariant()}";
    }
}
