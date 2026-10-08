// Implements: architecture/reference/components/conversational-employment-solution-contract.md §4.1 BP public candidate operations
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public sealed record EmploymentWorkspaceSnapshot(
    Guid TenantId,
    Guid RelationshipId,
    string WorkspaceVersion,
    string ManifestVersion,
    JsonElement Workspace,
    IReadOnlyDictionary<string, JsonElement> Phases,
    JsonElement Readiness,
    IReadOnlyDictionary<string, JsonElement> Plans,
    string? CurrentPlanVersion,
    long DecisionSpaceVersion,
    string WbeSourceVersion
);

public sealed record EmploymentCommandReceipt(
    string SchemaVersion,
    Guid CommandId,
    string State,
    DateTimeOffset AcceptedAt,
    string ReconciliationUri
);

public sealed record EmploymentOwnerStep(
    string Owner,
    string State,
    string? OwnerCommandRef = null,
    string? SourceVersion = null
);

public sealed record EmploymentResultingVersions(
    string WorkspaceVersion,
    string? PlanVersion,
    string ManifestVersion,
    long? DecisionSpaceVersion,
    string? WbeSourceVersion
);

public sealed record EmploymentCommandOutcome(
    string SchemaVersion,
    Guid CommandId,
    string State,
    DateTimeOffset AcceptedAt,
    string ReconciliationUri,
    IReadOnlyList<EmploymentOwnerStep> OwnerSteps,
    IReadOnlyList<string> EvidenceRefs,
    EmploymentResultingVersions ResultingVersions,
    string? Limitation,
    DateTimeOffset UpdatedAt
);

public sealed record EmploymentCommandSubmission(
    EmploymentCommandReceipt Receipt,
    EmploymentCommandOutcome Outcome,
    bool Replayed
);

public sealed class EmploymentProtocolException(string code) : InvalidOperationException(code)
{
    public string Code { get; } = code;
}

public sealed class ConversationalEmploymentService
{
    private static readonly IReadOnlyDictionary<string, HashSet<string>> CommandFields =
        new Dictionary<string, HashSet<string>>(StringComparer.Ordinal)
        {
            ["CONFIRM_INDUCTION_ITEM"] = Fields(),
            ["DEFER_INDUCTION_ITEM"] = Fields("deferredReason", "blockedSkillRefs"),
            ["APPLY_CANDIDATE_PATCH"] = Fields("candidatePatchRef"),
            ["SUBMIT_PLAN_FOR_REVIEW"] = Fields("expectedPlanVersion"),
            ["ACCEPT_PLAN_VERSION"] = Fields(
                "expectedPlanVersion",
                "expectedDecisionSpaceVersion",
                "expectedWbeSourceVersion",
                "acknowledgement"
            ),
            ["ACKNOWLEDGE_MATERIAL_CHANGE"] = Fields(
                "expectedPlanVersion",
                "expectedDecisionSpaceVersion",
                "expectedWbeSourceVersion",
                "acknowledgement"
            ),
            ["RESCHEDULE_WITHIN_TOLERANCE"] = Fields(
                "expectedPlanVersion",
                "requestedCalendarCommitment",
                "acknowledgement"
            ),
            ["REQUEST_REASSESSMENT"] = Fields("expectedPlanVersion"),
            ["ACKNOWLEDGE_CORRECTIVE_PROPOSAL"] = Fields("acknowledgement"),
        };
    private static readonly IReadOnlyDictionary<string, string[]> RequiredOwners = new Dictionary<
        string,
        string[]
    >(StringComparer.Ordinal)
    {
        ["CONFIRM_INDUCTION_ITEM"] = ["DOMAIN_ADAPTER", "CE"],
        ["DEFER_INDUCTION_ITEM"] = ["DOMAIN_ADAPTER", "CE"],
        ["APPLY_CANDIDATE_PATCH"] = ["DOMAIN_ADAPTER", "CE"],
        ["SUBMIT_PLAN_FOR_REVIEW"] = ["DOMAIN_ADAPTER", "CE"],
        ["ACCEPT_PLAN_VERSION"] = ["DOMAIN_ADAPTER", "WBE", "CE"],
        ["ACKNOWLEDGE_MATERIAL_CHANGE"] = ["DOMAIN_ADAPTER", "WBE", "CE"],
        ["RESCHEDULE_WITHIN_TOLERANCE"] = ["DOMAIN_ADAPTER", "CE"],
        ["REQUEST_REASSESSMENT"] = ["DOMAIN_ADAPTER", "CE"],
        ["ACKNOWLEDGE_CORRECTIVE_PROPOSAL"] = ["DOMAIN_ADAPTER", "CE"],
    };

    private readonly Dictionary<
        (Guid TenantId, Guid RelationshipId),
        EmploymentWorkspaceSnapshot
    > _workspaces = new();
    private readonly Dictionary<
        (Guid TenantId, Guid RelationshipId, Guid ActorId, Guid IdempotencyKey),
        (string Digest, Guid CommandId)
    > _idempotency = new();
    private readonly Dictionary<
        (Guid TenantId, Guid RelationshipId, Guid CommandId),
        EmploymentCommandOutcome
    > _commands = new();
    private readonly object _sync = new();
    private readonly IConversationalEmploymentPersistence? _persistence;

    public ConversationalEmploymentService(IConversationalEmploymentPersistence? persistence = null)
    {
        _persistence = persistence;
    }

    public void RegisterWorkspace(EmploymentWorkspaceSnapshot snapshot)
    {
        ValidateWorkspace(snapshot);
        lock (_sync)
        {
            var key = (snapshot.TenantId, snapshot.RelationshipId);
            if (_workspaces.TryGetValue(key, out var current))
            {
                if (
                    string.Equals(
                        current.WorkspaceVersion,
                        snapshot.WorkspaceVersion,
                        StringComparison.Ordinal
                    )
                )
                    throw new EmploymentProtocolException("EMPLOYMENT_VERSION_CONFLICT");
            }
            _persistence?.AppendWorkspace(snapshot);
            _workspaces[key] = snapshot;
        }
    }

    public EmploymentWorkspaceSnapshot? GetWorkspace(Guid tenantId, Guid relationshipId)
    {
        lock (_sync)
        {
            var key = (tenantId, relationshipId);
            var workspace =
                _workspaces.GetValueOrDefault(key)
                ?? _persistence?.LoadWorkspace(tenantId, relationshipId);
            if (workspace is not null)
                _workspaces[key] = workspace;
            return workspace;
        }
    }

    public EmploymentCommandSubmission Submit(
        Guid tenantId,
        Guid relationshipId,
        Guid actorId,
        Guid idempotencyKey,
        JsonElement command
    )
    {
        var kind = ValidateCommand(command);
        var digest = CanonicalDigest(command);
        lock (_sync)
        {
            var workspace =
                _workspaces.GetValueOrDefault((tenantId, relationshipId))
                ?? _persistence?.LoadWorkspace(tenantId, relationshipId);
            if (workspace is null)
                throw new EmploymentProtocolException("EMPLOYMENT_NOT_ACCESSIBLE");
            if (
                !string.Equals(
                    command.GetProperty("expectedWorkspaceVersion").GetString(),
                    workspace.WorkspaceVersion,
                    StringComparison.Ordinal
                )
                || !string.Equals(
                    command.GetProperty("expectedManifestVersion").GetString(),
                    workspace.ManifestVersion,
                    StringComparison.Ordinal
                )
            )
                throw new EmploymentProtocolException("EMPLOYMENT_VERSION_CONFLICT");

            var replayKey = (tenantId, relationshipId, actorId, idempotencyKey);
            if (_idempotency.TryGetValue(replayKey, out var replay))
            {
                if (
                    !CryptographicOperations.FixedTimeEquals(
                        Encoding.ASCII.GetBytes(replay.Digest),
                        Encoding.ASCII.GetBytes(digest)
                    )
                )
                    throw new EmploymentProtocolException("EMPLOYMENT_IDEMPOTENCY_CONFLICT");
                var replayedOutcome = _commands[(tenantId, relationshipId, replay.CommandId)];
                return new EmploymentCommandSubmission(
                    Receipt(replayedOutcome),
                    replayedOutcome,
                    true
                );
            }

            var commandId = Guid.NewGuid();
            var acceptedAt = DateTimeOffset.UtcNow;
            var reconciliationUri =
                $"/api/v1/employment/relationships/{relationshipId}/workspace/employment/commands/{commandId}";
            var ownerSteps = new List<EmploymentOwnerStep>
            {
                new("BP", "COMMITTED", commandId.ToString(), workspace.WorkspaceVersion),
            };
            ownerSteps.AddRange(
                RequiredOwners[kind].Select(owner => new EmploymentOwnerStep(owner, "PENDING"))
            );
            var outcome = new EmploymentCommandOutcome(
                "1.0",
                commandId,
                "ACCEPTED",
                acceptedAt,
                reconciliationUri,
                ownerSteps,
                [$"bp-command-accepted:{commandId}"],
                new EmploymentResultingVersions(
                    workspace.WorkspaceVersion,
                    workspace.CurrentPlanVersion,
                    workspace.ManifestVersion,
                    null,
                    null
                ),
                $"Command {kind} accepted for owner validation; no business success is implied.",
                acceptedAt
            );
            if (_persistence is not null)
            {
                var persisted = _persistence.ReserveCommand(
                    tenantId,
                    relationshipId,
                    actorId,
                    idempotencyKey,
                    kind,
                    digest,
                    workspace.WorkspaceVersion,
                    workspace.ManifestVersion,
                    outcome
                );
                if (
                    !CryptographicOperations.FixedTimeEquals(
                        Encoding.ASCII.GetBytes(persisted.CanonicalDigest),
                        Encoding.ASCII.GetBytes(digest)
                    )
                )
                    throw new EmploymentProtocolException("EMPLOYMENT_IDEMPOTENCY_CONFLICT");
                outcome = persisted.Outcome;
                commandId = outcome.CommandId;
                _commands[(tenantId, relationshipId, commandId)] = outcome;
                _idempotency[replayKey] = (digest, commandId);
                return new EmploymentCommandSubmission(
                    Receipt(outcome),
                    outcome,
                    persisted.Replayed
                );
            }
            _commands[(tenantId, relationshipId, commandId)] = outcome;
            _idempotency[replayKey] = (digest, commandId);
            return new EmploymentCommandSubmission(Receipt(outcome), outcome, false);
        }
    }

    public EmploymentCommandOutcome? GetCommand(Guid tenantId, Guid relationshipId, Guid commandId)
    {
        lock (_sync)
        {
            var key = (tenantId, relationshipId, commandId);
            var outcome =
                _commands.GetValueOrDefault(key)
                ?? _persistence?.LoadCommand(tenantId, relationshipId, commandId);
            if (outcome is not null)
                _commands[key] = outcome;
            return outcome;
        }
    }

    public EmploymentCommandOutcome UpdateOwnerStep(
        Guid tenantId,
        Guid relationshipId,
        Guid commandId,
        string owner,
        string state,
        string? ownerCommandRef,
        string? sourceVersion,
        string evidenceRef
    )
    {
        var allowedStates = new HashSet<string>(StringComparer.Ordinal)
        {
            "PENDING",
            "ACCEPTED",
            "COMMITTED",
            "COMPLETED",
            "FAILED",
            "BLOCKED",
            "UNKNOWN",
        };
        if (
            !allowedStates.Contains(state)
            || string.IsNullOrWhiteSpace(evidenceRef)
            || owner == "BP"
        )
            throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
        lock (_sync)
        {
            var key = (tenantId, relationshipId, commandId);
            if (
                !_commands.TryGetValue(key, out var current)
                && (current = _persistence?.LoadCommand(tenantId, relationshipId, commandId))
                    is null
            )
                throw new EmploymentProtocolException("EMPLOYMENT_NOT_ACCESSIBLE");
            if (current.State is "COMPLETED" or "REJECTED" or "CONFLICT" or "BLOCKED")
                throw new EmploymentProtocolException("EMPLOYMENT_COMMAND_TERMINAL");
            var index = current
                .OwnerSteps.Select((step, position) => (step, position))
                .SingleOrDefault(item => item.step.Owner == owner);
            if (index.step is null)
                throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
            if (
                state == "COMPLETED"
                && (
                    string.IsNullOrWhiteSpace(ownerCommandRef)
                    || string.IsNullOrWhiteSpace(sourceVersion)
                )
            )
                throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
            var steps = current.OwnerSteps.ToArray();
            steps[index.position] = new EmploymentOwnerStep(
                owner,
                state,
                ownerCommandRef,
                sourceVersion
            );
            var commandState = AggregateState(steps);
            var updated = current with
            {
                State = commandState,
                OwnerSteps = steps,
                EvidenceRefs = current.EvidenceRefs.Append(evidenceRef).Distinct().ToArray(),
                Limitation =
                    commandState == "COMPLETED"
                        ? null
                        : $"Owner reconciliation is {commandState.ToLowerInvariant()}.",
                UpdatedAt = DateTimeOffset.UtcNow,
            };
            _persistence?.AppendCommandOutcome(tenantId, relationshipId, updated);
            _commands[key] = updated;
            return updated;
        }
    }

    private static EmploymentCommandReceipt Receipt(EmploymentCommandOutcome outcome) =>
        new(
            outcome.SchemaVersion,
            outcome.CommandId,
            outcome.State,
            outcome.AcceptedAt,
            outcome.ReconciliationUri
        );

    private static string ValidateCommand(JsonElement command)
    {
        if (command.ValueKind != JsonValueKind.Object)
            throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
        if (
            !command.TryGetProperty("schemaVersion", out var schema)
            || schema.GetString() != "1.0"
            || !command.TryGetProperty("kind", out var kindProperty)
            || kindProperty.GetString() is not { } kind
            || !CommandFields.TryGetValue(kind, out var expected)
        )
            throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
        var actual = command
            .EnumerateObject()
            .Select(item => item.Name)
            .ToHashSet(StringComparer.Ordinal);
        if (!actual.SetEquals(expected))
            throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
        foreach (
            var required in new[]
            {
                "subjectRef",
                "expectedWorkspaceVersion",
                "expectedManifestVersion",
            }
        )
        {
            if (
                command.GetProperty(required).ValueKind != JsonValueKind.String
                || string.IsNullOrWhiteSpace(command.GetProperty(required).GetString())
            )
                throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
        }
        foreach (
            var required in expected.Except([
                "schemaVersion",
                "kind",
                "subjectRef",
                "expectedWorkspaceVersion",
                "expectedManifestVersion",
            ])
        )
        {
            var value = command.GetProperty(required);
            var valid = required switch
            {
                "expectedDecisionSpaceVersion" => value.ValueKind == JsonValueKind.Number
                    && value.TryGetInt64(out var version)
                    && version >= 1,
                "candidatePatchRef" => value.ValueKind == JsonValueKind.String
                    && Guid.TryParse(value.GetString(), out _),
                "blockedSkillRefs" => value.ValueKind == JsonValueKind.Array
                    && value.GetArrayLength() > 0
                    && value.EnumerateArray().All(NonEmptyString),
                "requestedCalendarCommitment" => ValidCalendarCommitment(value),
                _ => NonEmptyString(value),
            };
            if (!valid)
                throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
        }
        return kind;
    }

    private static string AggregateState(IReadOnlyList<EmploymentOwnerStep> steps)
    {
        if (steps.Any(step => step.State == "BLOCKED"))
            return "BLOCKED";
        if (steps.Any(step => step.State == "FAILED"))
            return "REJECTED";
        if (steps.Any(step => step.State == "UNKNOWN"))
            return "UNKNOWN";
        var successStates = new HashSet<string>(["COMMITTED", "COMPLETED"], StringComparer.Ordinal);
        return
            steps.All(step => successStates.Contains(step.State))
            && steps.Single(step => step.Owner == "CE").State == "COMPLETED"
            ? "COMPLETED"
            : "PARTIAL";
    }

    private static bool NonEmptyString(JsonElement value) =>
        value.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(value.GetString());

    private static bool ValidCalendarCommitment(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.Object)
            return false;
        var expected = new HashSet<string>(
            [
                "commitmentId",
                "timeZone",
                "localDateTime",
                "utcInstant",
                "utcOffset",
                "fold",
                "tzdbVersion",
                "tolerancePolicy",
            ],
            StringComparer.Ordinal
        );
        var optional = new HashSet<string>(
            ["recurrence", "missedWindowPolicy"],
            StringComparer.Ordinal
        );
        var actual = value
            .EnumerateObject()
            .Select(item => item.Name)
            .ToHashSet(StringComparer.Ordinal);
        if (!expected.IsSubsetOf(actual) || actual.Except(expected).Except(optional).Any())
            return false;
        var tolerancePolicy = value.GetProperty("tolerancePolicy");
        if (
            tolerancePolicy.ValueKind != JsonValueKind.Object
            || !ExactProperties(
                tolerancePolicy,
                new HashSet<string>(["policyRef", "policyVersion"], StringComparer.Ordinal),
                new HashSet<string>()
            )
            || !NonEmptyString(tolerancePolicy.GetProperty("policyRef"))
            || !NonEmptyString(tolerancePolicy.GetProperty("policyVersion"))
        )
            return false;
        return TryGuid(value.GetProperty("commitmentId"), out _)
            && NonEmptyString(value.GetProperty("timeZone"))
            && NonEmptyString(value.GetProperty("localDateTime"))
            && TryDateTimeOffset(value.GetProperty("utcInstant"))
            && NonEmptyString(value.GetProperty("utcOffset"))
            && value.GetProperty("fold").ValueKind == JsonValueKind.Number
            && value.GetProperty("fold").TryGetInt32(out var fold)
            && fold is 0 or 1
            && NonEmptyString(value.GetProperty("tzdbVersion"))
            && ValidCalendarInstant(value, fold);
    }

    private static HashSet<string> Fields(params string[] fields) =>
        new(
            new[]
            {
                "schemaVersion",
                "kind",
                "subjectRef",
                "expectedWorkspaceVersion",
                "expectedManifestVersion",
            }.Concat(fields),
            StringComparer.Ordinal
        );

    private static void ValidateWorkspace(EmploymentWorkspaceSnapshot snapshot)
    {
        var workspace = snapshot.Workspace;
        var requiredWorkspaceFields = new HashSet<string>(
            [
                "schemaVersion",
                "protocolVersion",
                "relationshipId",
                "workspaceVersion",
                "agentType",
                "agentVersion",
                "manifestVersion",
                "readiness",
                "phases",
                "operations",
                "sources",
                "limitations",
                "availableCommands",
                "authoritativeCursor",
                "producedAt",
            ],
            StringComparer.Ordinal
        );
        var optionalWorkspaceFields = new HashSet<string>(
            ["currentPlan", "recommendedNextAction"],
            StringComparer.Ordinal
        );
        if (
            snapshot.Phases.Count != 3
            || !snapshot
                .Phases.Keys.ToHashSet(StringComparer.Ordinal)
                .SetEquals(["INDUCTION", "PLANNING", "OPERATIONS"])
            || workspace.ValueKind != JsonValueKind.Object
            || !ExactProperties(workspace, requiredWorkspaceFields, optionalWorkspaceFields)
            || workspace.GetProperty("schemaVersion").GetString() != "1.0"
            || workspace.GetProperty("protocolVersion").GetString() != "1.0-candidate"
            || !TryGuid(workspace.GetProperty("relationshipId"), out var workspaceRelationshipId)
            || workspaceRelationshipId != snapshot.RelationshipId
            || workspace.GetProperty("workspaceVersion").GetString() != snapshot.WorkspaceVersion
            || workspace.GetProperty("manifestVersion").GetString() != snapshot.ManifestVersion
            || !NonEmptyString(workspace.GetProperty("agentType"))
            || !NonEmptyString(workspace.GetProperty("agentVersion"))
            || !NonEmptyString(workspace.GetProperty("authoritativeCursor"))
            || !TryDateTimeOffset(workspace.GetProperty("producedAt"))
            || !ValidStringArray(workspace.GetProperty("limitations"), 500)
            || !ValidAvailableCommands(workspace.GetProperty("availableCommands"))
            || workspace.GetProperty("sources").ValueKind != JsonValueKind.Array
            || workspace.GetProperty("sources").GetArrayLength() == 0
            || workspace.GetProperty("sources").EnumerateArray().Any(source => !ValidSource(source))
            || !ValidReadiness(workspace.GetProperty("readiness"))
            || workspace.GetProperty("phases").ValueKind != JsonValueKind.Array
            || workspace.GetProperty("phases").GetArrayLength() != 3
            || snapshot.Plans.Any(plan =>
                !ValidPlan(plan.Value)
                || plan.Value.GetProperty("planVersion").GetString() != plan.Key
            )
            || CanonicalDigest(workspace.GetProperty("readiness"))
                != CanonicalDigest(snapshot.Readiness)
            || workspace
                .GetProperty("phases")
                .EnumerateArray()
                .Any(phase =>
                    !phase.TryGetProperty("phase", out var phaseKind)
                    || phaseKind.GetString() is not { } kind
                    || !snapshot.Phases.TryGetValue(kind, out var registered)
                    || CanonicalDigest(phase) != CanonicalDigest(registered)
                    || !ValidPhase(phase)
                )
            || !workspace.TryGetProperty("operations", out var operations)
            || !ValidOperations(operations)
            || (
                snapshot.CurrentPlanVersion is null
                && workspace.TryGetProperty("currentPlan", out var noCurrentPlan)
                && noCurrentPlan.ValueKind != JsonValueKind.Null
            )
            || (
                snapshot.CurrentPlanVersion is not null
                && (
                    !snapshot.Plans.TryGetValue(snapshot.CurrentPlanVersion, out var currentPlan)
                    || !workspace.TryGetProperty("currentPlan", out var workspacePlan)
                    || CanonicalDigest(workspacePlan) != CanonicalDigest(currentPlan)
                )
            )
        )
            throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
    }

    private static bool ValidPlan(JsonElement plan)
    {
        var required = new HashSet<string>(
            [
                "planId",
                "planVersion",
                "state",
                "goalRef",
                "outcomeLabel",
                "accountableOwner",
                "skillRefs",
                "milestones",
                "calendarCommitments",
                "source",
            ],
            StringComparer.Ordinal
        );
        var optional = new HashSet<string>(
            ["priorPlanVersion", "impactSummary"],
            StringComparer.Ordinal
        );
        return plan.ValueKind == JsonValueKind.Object
            && ExactProperties(plan, required, optional)
            && TryGuid(plan.GetProperty("planId"), out _)
            && NonEmptyString(plan.GetProperty("planVersion"))
            && IsAllowedString(
                plan.GetProperty("state"),
                new HashSet<string>(
                    [
                        "DRAFT",
                        "GROOMING",
                        "READY_FOR_REVIEW",
                        "AGREED",
                        "ACTIVE",
                        "BLOCKED",
                        "SUPERSEDED",
                        "CANCELLED",
                        "COMPLETED",
                    ],
                    StringComparer.Ordinal
                )
            )
            && NonEmptyString(plan.GetProperty("goalRef"))
            && NonEmptyString(plan.GetProperty("outcomeLabel"))
            && NonEmptyString(plan.GetProperty("accountableOwner"))
            && plan.GetProperty("skillRefs").ValueKind == JsonValueKind.Array
            && plan.GetProperty("skillRefs").GetArrayLength() > 0
            && plan.GetProperty("skillRefs").EnumerateArray().All(NonEmptyString)
            && plan.GetProperty("milestones").ValueKind == JsonValueKind.Array
            && plan.GetProperty("milestones").EnumerateArray().All(ValidWorkspaceItem)
            && plan.GetProperty("calendarCommitments").ValueKind == JsonValueKind.Array
            && plan.GetProperty("calendarCommitments").EnumerateArray().All(ValidCalendarCommitment)
            && ValidSource(plan.GetProperty("source"));
    }

    private static bool ValidReadiness(JsonElement readiness)
    {
        var required = new HashSet<string>(
            ["induction", "plan", "operations", "performance", "unmetConditions", "sources"],
            StringComparer.Ordinal
        );
        var optional = new HashSet<string>(
            ["eligibleSkillRefs", "lockedSkillRefs"],
            StringComparer.Ordinal
        );
        return readiness.ValueKind == JsonValueKind.Object
            && ExactProperties(readiness, required, optional)
            && IsAllowedString(
                readiness.GetProperty("induction"),
                new HashSet<string>(
                    [
                        "NOT_STARTED",
                        "IN_PROGRESS",
                        "READY_WITH_DEFERRED_ITEMS",
                        "READY",
                        "BLOCKED",
                        "STALE_REASSESSMENT_REQUIRED",
                    ],
                    StringComparer.Ordinal
                )
            )
            && IsAllowedString(
                readiness.GetProperty("plan"),
                new HashSet<string>(
                    [
                        "NO_PLAN",
                        "DRAFT",
                        "GROOMING",
                        "READY_FOR_REVIEW",
                        "AGREED",
                        "BLOCKED",
                        "STALE_REASSESSMENT_REQUIRED",
                    ],
                    StringComparer.Ordinal
                )
            )
            && IsAllowedString(
                readiness.GetProperty("operations"),
                new HashSet<string>(
                    [
                        "LOCKED",
                        "ELIGIBLE",
                        "ACTIVE",
                        "PAUSED",
                        "BLOCKED",
                        "REASSESSMENT_REQUIRED",
                        "TERMINATED",
                    ],
                    StringComparer.Ordinal
                )
            )
            && IsAllowedString(
                readiness.GetProperty("performance"),
                new HashSet<string>(
                    [
                        "NOT_ESTABLISHED",
                        "CURRENT",
                        "DEGRADED",
                        "CORRECTIVE_ACTION_REQUIRED",
                        "BLOCKED",
                        "UNAVAILABLE",
                    ],
                    StringComparer.Ordinal
                )
            )
            && (
                !readiness.TryGetProperty("eligibleSkillRefs", out var eligibleSkillRefs)
                || ValidStringArray(eligibleSkillRefs, 128)
            )
            && (
                !readiness.TryGetProperty("lockedSkillRefs", out var lockedSkillRefs)
                || ValidStringArray(lockedSkillRefs, 128)
            )
            && readiness.GetProperty("unmetConditions").ValueKind == JsonValueKind.Array
            && ValidStringArray(readiness.GetProperty("unmetConditions"), 160)
            && readiness.GetProperty("sources").ValueKind == JsonValueKind.Array
            && readiness.GetProperty("sources").GetArrayLength() > 0
            && readiness.GetProperty("sources").EnumerateArray().All(ValidSource);
    }

    private static bool ValidOperations(JsonElement operations)
    {
        var required = new HashSet<string>(
            [
                "mode",
                "eligibility",
                "eligibleSkillRefs",
                "lockedSkillRefs",
                "permittedOperationClasses",
                "stopReachable",
                "commercialSource",
            ],
            StringComparer.Ordinal
        );
        return operations.ValueKind == JsonValueKind.Object
            && ExactProperties(operations, required, new HashSet<string>())
            && IsAllowedString(
                operations.GetProperty("mode"),
                new HashSet<string>(["TRIAL_ADVISORY", "ACTIVE_BOUNDED"], StringComparer.Ordinal)
            )
            && IsAllowedString(
                operations.GetProperty("eligibility"),
                new HashSet<string>(
                    [
                        "LOCKED",
                        "ELIGIBLE",
                        "ACTIVE",
                        "PAUSED",
                        "BLOCKED",
                        "REASSESSMENT_REQUIRED",
                        "TERMINATED",
                    ],
                    StringComparer.Ordinal
                )
            )
            && operations.GetProperty("stopReachable").ValueKind == JsonValueKind.True
            && ValidStringArray(operations.GetProperty("eligibleSkillRefs"), 128)
            && ValidStringArray(operations.GetProperty("lockedSkillRefs"), 128)
            && ValidEnumArray(
                operations.GetProperty("permittedOperationClasses"),
                new HashSet<string>(
                    ["SIMULATED", "READ_ONLY", "ADVISORY", "CONSEQUENTIAL"],
                    StringComparer.Ordinal
                )
            )
            && (
                operations.GetProperty("mode").GetString() != "TRIAL_ADVISORY"
                || !operations
                    .GetProperty("permittedOperationClasses")
                    .EnumerateArray()
                    .Any(item => item.GetString() == "CONSEQUENTIAL")
            )
            && ValidSource(operations.GetProperty("commercialSource"));
    }

    private static bool ValidSource(JsonElement source)
    {
        var required = new HashSet<string>(
            ["owner", "contractVersion", "sourceVersion", "state", "observedAt"],
            StringComparer.Ordinal
        );
        var optional = new HashSet<string>(["validUntil", "limitation"], StringComparer.Ordinal);
        if (
            source.ValueKind != JsonValueKind.Object
            || !ExactProperties(source, required, optional)
            || !NonEmptyString(source.GetProperty("owner"))
            || !new HashSet<string>(
                ["BP", "PR", "CE", "WBE", "DOMAIN_ADAPTER"],
                StringComparer.Ordinal
            ).Contains(source.GetProperty("owner").GetString()!)
            || !NonEmptyString(source.GetProperty("contractVersion"))
            || !NonEmptyString(source.GetProperty("sourceVersion"))
            || !NonEmptyString(source.GetProperty("state"))
            || !new HashSet<string>(
                ["CURRENT", "STALE", "PARTIAL", "DISPUTED", "UNKNOWN", "UNAVAILABLE", "BLOCKED"],
                StringComparer.Ordinal
            ).Contains(source.GetProperty("state").GetString()!)
            || !TryDateTimeOffset(source.GetProperty("observedAt"), out var observedAt)
        )
            return false;
        if (
            source.TryGetProperty("validUntil", out var validUntil)
            && (
                !TryDateTimeOffset(validUntil, out var parsedValidUntil)
                || parsedValidUntil < observedAt
            )
        )
            return false;
        return !source.TryGetProperty("limitation", out var limitation)
            || (NonEmptyString(limitation) && limitation.GetString()!.Length <= 500);
    }

    private static bool ValidPhase(JsonElement phase)
    {
        var required = new HashSet<string>(
            [
                "phase",
                "status",
                "progress",
                "completedItems",
                "inProgressItems",
                "pendingItems",
                "blockers",
                "assumptions",
                "dependencies",
                "milestones",
                "calendarCommitments",
                "evidenceState",
                "sourceFreshness",
                "limitations",
                "availableCommands",
                "sources",
            ],
            StringComparer.Ordinal
        );
        var optional = new HashSet<string>(
            [
                "currentGoalRef",
                "currentPlanVersion",
                "billingSummary",
                "performanceSummary",
                "recommendedNextAction",
            ],
            StringComparer.Ordinal
        );
        if (
            phase.ValueKind != JsonValueKind.Object
            || !ExactProperties(phase, required, optional)
            || phase.GetProperty("phase").ValueKind != JsonValueKind.String
            || phase.GetProperty("phase").GetString() is not { } phaseKind
            || phase.GetProperty("status").ValueKind != JsonValueKind.String
            || phase.GetProperty("status").GetString() is not { } status
            || phase.GetProperty("evidenceState").ValueKind != JsonValueKind.String
            || phase.GetProperty("evidenceState").GetString() is not { } evidenceState
            || !new HashSet<string>(
                ["INDUCTION", "PLANNING", "OPERATIONS"],
                StringComparer.Ordinal
            ).Contains(phaseKind)
            || !new HashSet<string>(
                [
                    "NOT_STARTED",
                    "IN_PROGRESS",
                    "READY",
                    "ACTIVE",
                    "BLOCKED",
                    "DEGRADED",
                    "COMPLETE",
                ],
                StringComparer.Ordinal
            ).Contains(status)
            || !new HashSet<string>(
                ["CURRENT", "STALE", "PARTIAL", "DISPUTED", "UNKNOWN", "UNAVAILABLE", "BLOCKED"],
                StringComparer.Ordinal
            ).Contains(evidenceState)
            || (phaseKind == "OPERATIONS" && status == "COMPLETE")
            || (
                evidenceState
                    is "STALE"
                        or "PARTIAL"
                        or "DISPUTED"
                        or "UNKNOWN"
                        or "UNAVAILABLE"
                        or "BLOCKED"
                && status is "READY" or "ACTIVE" or "COMPLETE"
            )
            || !TryDateTimeOffset(phase.GetProperty("sourceFreshness"))
            || !ValidProgress(phase.GetProperty("progress"))
            || !ValidStringArray(phase.GetProperty("assumptions"), 500)
            || !ValidStringArray(phase.GetProperty("limitations"), 500)
            || !ValidAvailableCommands(phase.GetProperty("availableCommands"))
            || phase.GetProperty("calendarCommitments").ValueKind != JsonValueKind.Array
            || phase
                .GetProperty("calendarCommitments")
                .EnumerateArray()
                .Any(commitment => !ValidCalendarCommitment(commitment))
            || phase.GetProperty("sources").ValueKind != JsonValueKind.Array
            || phase.GetProperty("sources").GetArrayLength() == 0
            || phase.GetProperty("sources").EnumerateArray().Any(source => !ValidSource(source))
        )
            return false;
        foreach (
            var collection in new[]
            {
                "completedItems",
                "inProgressItems",
                "pendingItems",
                "blockers",
                "dependencies",
                "milestones",
            }
        )
        {
            var items = phase.GetProperty(collection);
            if (
                items.ValueKind != JsonValueKind.Array
                || items.EnumerateArray().Any(item => !ValidWorkspaceItem(item))
            )
                return false;
        }
        return true;
    }

    private static bool ValidWorkspaceItem(JsonElement item)
    {
        var required = new HashSet<string>(
            [
                "itemId",
                "itemVersion",
                "phase",
                "label",
                "mandatory",
                "state",
                "reason",
                "accountableOwner",
                "blockedEffects",
                "source",
                "availableCommands",
            ],
            StringComparer.Ordinal
        );
        var optional = new HashSet<string>(
            ["dueMeaning", "completionReference"],
            StringComparer.Ordinal
        );
        return item.ValueKind == JsonValueKind.Object
            && ExactProperties(item, required, optional)
            && TryGuid(item.GetProperty("itemId"), out _)
            && NonEmptyString(item.GetProperty("itemVersion"))
            && IsAllowedString(
                item.GetProperty("phase"),
                new HashSet<string>(["INDUCTION", "PLANNING", "OPERATIONS"], StringComparer.Ordinal)
            )
            && NonEmptyString(item.GetProperty("label"))
            && IsAllowedString(
                item.GetProperty("state"),
                new HashSet<string>(
                    [
                        "PROPOSED",
                        "READY",
                        "IN_PROGRESS",
                        "WAITING_ON_CUSTOMER",
                        "WAITING_ON_AGENT",
                        "WAITING_ON_PLATFORM",
                        "BLOCKED",
                        "COMPLETED",
                        "DEFERRED",
                        "CANCELLED",
                        "SUPERSEDED",
                        "OUTCOME_UNKNOWN",
                    ],
                    StringComparer.Ordinal
                )
            )
            && NonEmptyString(item.GetProperty("reason"))
            && NonEmptyString(item.GetProperty("accountableOwner"))
            && (
                item.GetProperty("mandatory").ValueKind is JsonValueKind.True or JsonValueKind.False
            )
            && item.GetProperty("blockedEffects").ValueKind == JsonValueKind.Array
            && item.GetProperty("blockedEffects").EnumerateArray().All(ValidBlockedEffect)
            && item.GetProperty("source").ValueKind == JsonValueKind.Object
            && ValidSource(item.GetProperty("source"))
            && ValidAvailableCommands(item.GetProperty("availableCommands"));
    }

    private static bool ValidProgress(JsonElement progress)
    {
        var fields = new HashSet<string>(
            [
                "mandatoryTotal",
                "mandatoryCompleted",
                "optionalTotal",
                "optionalCompleted",
                "blockedCount",
                "deferredCount",
            ],
            StringComparer.Ordinal
        );
        if (
            progress.ValueKind != JsonValueKind.Object
            || !ExactProperties(progress, fields, new HashSet<string>())
        )
            return false;
        var values = fields.ToDictionary(
            field => field,
            field => progress.GetProperty(field).TryGetInt32(out var value) ? value : -1,
            StringComparer.Ordinal
        );
        return values.Values.All(value => value >= 0)
            && values["mandatoryCompleted"] <= values["mandatoryTotal"]
            && values["optionalCompleted"] <= values["optionalTotal"];
    }

    private static bool ValidBlockedEffect(JsonElement effect) =>
        effect.ValueKind == JsonValueKind.Object
        && ExactProperties(
            effect,
            new HashSet<string>(["effectType", "effectRef"], StringComparer.Ordinal),
            new HashSet<string>()
        )
        && new HashSet<string>(
            ["SKILL", "WORK_ITEM", "MILESTONE", "GOAL", "ACTION"],
            StringComparer.Ordinal
        ).Contains(effect.GetProperty("effectType").GetString()!)
        && NonEmptyString(effect.GetProperty("effectRef"));

    private static bool ValidAvailableCommands(JsonElement commands) =>
        commands.ValueKind == JsonValueKind.Array
        && commands
            .EnumerateArray()
            .All(command =>
                command.ValueKind == JsonValueKind.Object
                && ExactProperties(
                    command,
                    new HashSet<string>(
                        ["kind", "subjectRef", "requiresExplicitAcknowledgement"],
                        StringComparer.Ordinal
                    ),
                    new HashSet<string>()
                )
                && command.GetProperty("kind").ValueKind == JsonValueKind.String
                && RequiredOwners.ContainsKey(command.GetProperty("kind").GetString()!)
                && NonEmptyString(command.GetProperty("subjectRef"))
                && (
                    command.GetProperty("requiresExplicitAcknowledgement").ValueKind
                    is JsonValueKind.True
                        or JsonValueKind.False
                )
            );

    private static bool ValidStringArray(JsonElement values, int maxLength) =>
        values.ValueKind == JsonValueKind.Array
        && values
            .EnumerateArray()
            .All(value => NonEmptyString(value) && value.GetString()!.Length <= maxLength);

    private static bool ValidEnumArray(JsonElement values, IReadOnlySet<string> allowed) =>
        values.ValueKind == JsonValueKind.Array
        && values.GetArrayLength()
            == values.EnumerateArray().Select(value => value.GetString()).Distinct().Count()
        && values
            .EnumerateArray()
            .All(value =>
                value.ValueKind == JsonValueKind.String && allowed.Contains(value.GetString()!)
            );

    private static bool IsAllowedString(JsonElement value, IReadOnlySet<string> allowed) =>
        value.ValueKind == JsonValueKind.String && allowed.Contains(value.GetString()!);

    private static bool ExactProperties(
        JsonElement value,
        IReadOnlySet<string> required,
        IReadOnlySet<string> optional
    )
    {
        var actual = value
            .EnumerateObject()
            .Select(property => property.Name)
            .ToHashSet(StringComparer.Ordinal);
        return required.IsSubsetOf(actual) && actual.Except(required).All(optional.Contains);
    }

    private static bool TryGuid(JsonElement value, out Guid parsed)
    {
        parsed = default;
        return value.ValueKind == JsonValueKind.String
            && Guid.TryParse(value.GetString(), out parsed);
    }

    private static bool TryDateTimeOffset(JsonElement value) => TryDateTimeOffset(value, out _);

    private static bool TryDateTimeOffset(JsonElement value, out DateTimeOffset parsed)
    {
        parsed = default;
        return value.ValueKind == JsonValueKind.String
            && DateTimeOffset.TryParse(value.GetString(), out parsed);
    }

    private static bool ValidCalendarInstant(JsonElement value, int fold)
    {
        var utcOffsetText = value.GetProperty("utcOffset").GetString();
        if (utcOffsetText?.StartsWith('+') == true)
            utcOffsetText = utcOffsetText[1..];
        if (
            !DateTime.TryParseExact(
                value.GetProperty("localDateTime").GetString(),
                "yyyy-MM-dd'T'HH:mm:ss",
                CultureInfo.InvariantCulture,
                DateTimeStyles.None,
                out var localDateTime
            )
            || !DateTimeOffset.TryParse(
                value.GetProperty("utcInstant").GetString(),
                CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out var utcInstant
            )
            || !TimeSpan.TryParse(utcOffsetText, CultureInfo.InvariantCulture, out var utcOffset)
            || utcOffset < TimeSpan.FromHours(-14)
            || utcOffset > TimeSpan.FromHours(14)
        )
            return false;
        try
        {
            var timeZone = TimeZoneInfo.FindSystemTimeZoneById(
                value.GetProperty("timeZone").GetString()!
            );
            if (timeZone.IsInvalidTime(localDateTime))
                return false;
            var validOffsets = timeZone.IsAmbiguousTime(localDateTime)
                ? timeZone
                    .GetAmbiguousTimeOffsets(localDateTime)
                    .OrderByDescending(offset => offset)
                    .ToArray()
                : [timeZone.GetUtcOffset(localDateTime)];
            if (fold >= validOffsets.Length || validOffsets[fold] != utcOffset)
                return false;
            return new DateTimeOffset(localDateTime, utcOffset).ToUniversalTime() == utcInstant;
        }
        catch (TimeZoneNotFoundException)
        {
            return false;
        }
        catch (InvalidTimeZoneException)
        {
            return false;
        }
    }

    private static string CanonicalDigest(JsonElement value)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
            WriteCanonical(writer, value);
        return Convert.ToHexStringLower(SHA256.HashData(stream.ToArray()));
    }

    public static string CommandDigest(JsonElement command) => CanonicalDigest(command);

    private static void WriteCanonical(Utf8JsonWriter writer, JsonElement value)
    {
        switch (value.ValueKind)
        {
            case JsonValueKind.Object:
                writer.WriteStartObject();
                foreach (
                    var property in value
                        .EnumerateObject()
                        .OrderBy(item => item.Name, StringComparer.Ordinal)
                )
                {
                    writer.WritePropertyName(property.Name);
                    WriteCanonical(writer, property.Value);
                }
                writer.WriteEndObject();
                break;
            case JsonValueKind.Array:
                writer.WriteStartArray();
                foreach (var item in value.EnumerateArray())
                    WriteCanonical(writer, item);
                writer.WriteEndArray();
                break;
            default:
                value.WriteTo(writer);
                break;
        }
    }
}
