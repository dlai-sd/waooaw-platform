// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2 Execution binding and DC-3 Decision steps (WC170-R005, WC170-R006)
// constitutional_basis: C-001, C-005, C-023, C-059, C-063

using System.Text.Json;
using System.Text.RegularExpressions;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Refuses a decision or an execution step that is not bound to one exact locked artifact version. A decision must name
/// the artifact id and its digest; a consequential step must also carry genuine approval and scope-confirmation evidence
/// ids (two different ids) and the LOCKED status the owner read. Anything else is outside this evaluator's scope.
/// </summary>
public sealed partial class ArtifactBindingEvaluator : IClaimEvaluator
{
    public const string ExecuteStep = "REAL_WORK_EXECUTE_STEP";

    private static readonly HashSet<string> Decisions = new(StringComparer.Ordinal)
    {
        "EMPLOYMENT_ACCEPT_ARTIFACT_VERSION",
        "EMPLOYMENT_CONFIRM_SCOPE_BOUNDARY",
    };

    public string ClaimId => "C-001; C-005; C-023; C-059; C-063";

    [GeneratedRegex("^[0-9a-f]{64}$")]
    private static partial Regex DigestPattern();

    public Task<EvaluationResult> EvaluateAsync(
        EvaluationContext context,
        CancellationToken cancellationToken = default
    )
    {
        var decision = Decisions.Contains(context.ActionType);
        if (!decision && context.ActionType != ExecuteStep)
            return Result(EvaluationVerdict.Allow, "Outside artifact binding scope.");
        try
        {
            using var document = JsonDocument.Parse(
                string.IsNullOrEmpty(context.ActionParameters) ? "{}" : context.ActionParameters
            );
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
                return Deny("Artifact binding envelope is malformed.");
            var artifactId = Read(root, "artifactId", "artifact_id");
            var digest = Read(root, "artifactDigest", "artifact_digest");
            if (!IsGuid(artifactId) || digest is null || !DigestPattern().IsMatch(digest))
                return Deny("The step is not bound to one exact artifact id and digest.");
            if (decision)
                return Result(
                    EvaluationVerdict.Allow,
                    "The decision names one exact artifact version."
                );

            var approval = Read(root, "approvalEvidenceId", "approval_evidence_id");
            var scope = Read(root, "scopeEvidenceId", "scope_evidence_id");
            if (
                !string.Equals(
                    Read(root, "artifactStatus", "artifact_status"),
                    "LOCKED",
                    StringComparison.Ordinal
                )
            )
                return Deny("The artifact is not locked.");
            if (
                !IsGuid(approval)
                || !IsGuid(scope)
                || string.Equals(approval, scope, StringComparison.OrdinalIgnoreCase)
            )
                return Deny("Execution needs separate approval and scope-confirmation evidence.");
            return Result(
                EvaluationVerdict.Allow,
                "The step runs under one locked, approved and scope-confirmed artifact."
            );
        }
        catch (JsonException)
        {
            return Deny("Artifact binding envelope is malformed.");
        }
    }

    private static string? Read(JsonElement root, params string[] names)
    {
        foreach (var property in root.EnumerateObject())
            if (
                names.Contains(property.Name, StringComparer.OrdinalIgnoreCase)
                && property.Value.ValueKind == JsonValueKind.String
            )
                return property.Value.GetString();
        return null;
    }

    private static bool IsGuid(string? value) =>
        Guid.TryParse(value, out var parsed) && parsed != Guid.Empty;

    private Task<EvaluationResult> Deny(string reason) => Result(EvaluationVerdict.Deny, reason);

    private Task<EvaluationResult> Result(EvaluationVerdict verdict, string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, verdict, reason));
}
