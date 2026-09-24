// Implements: GOAL-005-D03 relationship admission constitutional boundary
// constitutional_basis: C-003, C-023, C-059, C-063

using System.Text.Json;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

public sealed class RelationshipAdmissionEvaluator : IClaimEvaluator
{
    private const string ActionType = "ADMIT_EMPLOYMENT_RELATIONSHIP";

    public string ClaimId => "C-003; C-023; C-059; C-063";

    public Task<EvaluationResult> EvaluateAsync(
        EvaluationContext context,
        CancellationToken cancellationToken = default
    )
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!string.Equals(context.ActionType, ActionType, StringComparison.Ordinal))
            return Result(EvaluationVerdict.Allow, "Outside relationship admission scope.");
        if (
            context.ApprovalType != ApprovalType.CustomerExplicit
            || context.DcmCategory != DcmCategory.DeterministicRequired
            || !Guid.TryParse(context.TenantId, out _)
            || !Guid.TryParse(context.ContractId, out _)
            || context.DecisionSpaceVersion < 1
        )
        {
            return Result(
                EvaluationVerdict.Deny,
                "Relationship admission requires explicit customer approval and deterministic verification."
            );
        }

        try
        {
            using var document = JsonDocument.Parse(context.ActionParameters);
            var root = document.RootElement;
            if (
                !RequiredGuid(root, "evaluation_intent_id")
                || !RequiredGuid(root, "initiating_participant_id")
                || !RequiredGuid(root, "agent_instance_id")
                || !RequiredString(root, "professional_type")
                || !string.Equals(
                    StringValue(root, "target_state"),
                    "DISCOVERED",
                    StringComparison.Ordinal
                )
            )
            {
                return Result(EvaluationVerdict.Deny, "Relationship admission envelope is incomplete.");
            }

            var intent = StringValue(root, "acquisition_intent");
            if (intent is not null && intent is not ("HIRE" or "TRIAL"))
                return Result(EvaluationVerdict.Deny, "Acquisition intent is unsupported.");
            if (
                intent is not null
                && (!RequiredGuid(root, "professional_admission_id")
                    || !RequiredString(root, "professional_version")
                    || !RequiredString(root, "disclosure_revision")
                    || !RequiredString(root, "terms_version"))
            )
            {
                return Result(
                    EvaluationVerdict.Deny,
                    "Acquisition admission lacks its governed professional or disclosure binding."
                );
            }

            return Result(
                EvaluationVerdict.Allow,
                "Relationship admission has explicit customer and governed catalog evidence."
            );
        }
        catch (JsonException)
        {
            return Result(EvaluationVerdict.Deny, "Relationship admission envelope is malformed.");
        }
    }

    private Task<EvaluationResult> Result(EvaluationVerdict verdict, string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, verdict, reason));

    private static bool RequiredGuid(JsonElement root, string name) =>
        Guid.TryParse(StringValue(root, name), out _);

    private static bool RequiredString(JsonElement root, string name) =>
        !string.IsNullOrWhiteSpace(StringValue(root, name));

    private static string? StringValue(JsonElement root, string name) =>
        root.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;
}