// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-041, C-073, C-059

#nullable enable
namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>Verdict returned by a constitutional claim evaluator.</summary>
public enum EvaluationVerdict { Allow, Deny, Escalate }

/// <summary>Result of a single constitutional claim evaluation.</summary>
public sealed record EvaluationResult(
    string ClaimId,
    EvaluationVerdict Verdict,
    string Reason);
