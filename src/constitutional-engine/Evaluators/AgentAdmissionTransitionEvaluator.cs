// Implements: WC-079 AA-05, AA-09
// constitutional_basis: C-003, C-023, C-059, C-063, C-065

using System.Text.Json;
using System.Text.RegularExpressions;

namespace Waooaw.ConstitutionalEngine.Evaluators;

public sealed partial class AgentAdmissionTransitionEvaluator : IClaimEvaluator
{
    private static readonly IReadOnlyDictionary<string, string[]> Authorities =
        new Dictionary<string, string[]>(StringComparer.Ordinal)
        {
            ["AGENT_ADMISSION_SUBMIT"] = ["OWNER_DELEGATE"],
            ["AGENT_ADMISSION_APPROVE"] = ["FOUNDER", "ADMISSION_APPROVER"],
            ["AGENT_ADMISSION_REJECT"] = ["FOUNDER", "ADMISSION_APPROVER"],
            ["AGENT_ADMISSION_ACTIVATE"] = ["PLATFORM_ACTIVATION_AUTHORITY"],
            ["AGENT_ADMISSION_SUSPEND"] = ["CONSTITUTIONAL_AUTHORITY", "OPERATIONS_AUTHORITY"],
            ["AGENT_ADMISSION_SUPERSEDE"] = ["LIFECYCLE_AUTHORITY"],
            ["AGENT_ADMISSION_RETIRE"] = ["LIFECYCLE_AUTHORITY"],
        };

    public string ClaimId => "C-003; C-023; C-059; C-065";

    public Task<EvaluationResult> EvaluateAsync(
        EvaluationContext context,
        CancellationToken cancellationToken = default)
    {
        if (!context.ActionType.StartsWith("AGENT_ADMISSION_", StringComparison.Ordinal))
            return Allow("Outside WC-079 admission transition scope.");
        if (!Authorities.TryGetValue(context.ActionType, out var authorities))
            return Deny("Unknown admission transition is denied.");

        try
        {
            using var document = JsonDocument.Parse(context.ActionParameters);
            var root = document.RootElement;
            var actor = RequiredString(root, "actor_subject_id");
            var authority = RequiredString(root, "actor_authority").ToUpperInvariant();
            var submitter = OptionalString(root, "submitter_subject_id");
            var contentDigest = RequiredString(root, "AdmissionContentDigest");
            var evidenceDigest = RequiredString(root, "EvidenceSetDigest");
            var policyVersion = RequiredString(root, "PolicyVersion");
            if (!DigestPattern().IsMatch(contentDigest) || !DigestPattern().IsMatch(evidenceDigest)
                || string.IsNullOrWhiteSpace(policyVersion) || !authorities.Contains(authority, StringComparer.Ordinal))
                return Deny("Admission transition authority or immutable binding is invalid.");
            if (context.ActionType != "AGENT_ADMISSION_SUBMIT"
                && submitter is not null
                && string.Equals(actor, submitter, StringComparison.OrdinalIgnoreCase))
                return Deny("Admission submitter cannot perform an independent lifecycle transition.");
            return Allow("Admission transition is within the actor's licensed Decision Space.");
        }
        catch (JsonException)
        {
            return Deny("Admission transition envelope is malformed.");
        }
        catch (InvalidOperationException)
        {
            return Deny("Admission transition envelope is incomplete.");
        }
    }

    private Task<EvaluationResult> Allow(string reason) => Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));
    private Task<EvaluationResult> Deny(string reason) => Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
    private static string RequiredString(JsonElement root, string name) =>
        root.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(value.GetString())
            ? value.GetString()!
            : throw new InvalidOperationException($"Required admission field {name} is absent.");
    private static string? OptionalString(JsonElement root, string name) =>
        root.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    [GeneratedRegex("^sha256:[0-9a-f]{64}$", RegexOptions.CultureInvariant)]
    private static partial Regex DigestPattern();
}