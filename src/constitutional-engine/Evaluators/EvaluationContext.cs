// Implements: architecture/reference/ce-validate-action-evaluators.md §Evaluator Architecture
// constitutional_basis: C-023 (Evidence First), C-059 (Traceability)

#nullable enable

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Immutable evaluation context built exclusively from ValidateActionRequest fields.
/// Contains NO database references — ConstitutionalDbContext does not exist yet (WC012-03).
/// </summary>
public sealed record EvaluationContext(
    string TenantId,
    string AgentId,
    string ActionType,
    string ToolName,
    double EstimatedCostUsd,
    IReadOnlyDictionary<string, string> Parameters);