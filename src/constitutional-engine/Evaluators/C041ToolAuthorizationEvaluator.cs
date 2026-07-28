// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-041, C-059
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): every action type must be explicitly recognised
/// before execution is permitted.  Unlisted action type = DENY (default-deny posture).
///
/// Constitutional basis : C-041 (Tool Authorization — every tool call must be within
///                                the customer's authorised Decision Space)
///                        C-059 (Implementation Traceability)
/// Spec ref             : architecture/reference/ce-validate-action-evaluators.md
/// ADR ref              : ADR-001 (gRPC Constitutional Engine)
///
/// Implementation notes
/// ─────────────────────
/// • This evaluator performs no network or database I/O — all evaluation is in-memory.
/// • KnownActionTypes represents the authorised action vocabulary for the platform.
///   Any action type absent from this set is constitutionally denied (C-041 default-deny).
/// • The set uses OrdinalIgnoreCase comparison so callers may not bypass the check
///   via capitalisation tricks (C-062 defence-in-depth).
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // ── Constitutional constant (C-041) ──────────────────────────────────────
    // C-041: any action type absent from this vocabulary is denied by default.
    // New action types MUST be approved via architecture change and added here
    // before any evaluator call in production can succeed.
    private static readonly IReadOnlySet<string> KnownActionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "MARKETING_POST",
            "CALENDAR_INVITE",
            "TRADE_ORDER",
            "EMERGENCY_STOP",
            "SCOPE_BOUNDARY_CONFIRMATION",
            "AUTHORITY_GRANT",
            "AUTHORITY_REVOKE",
            "EVIDENCE_RECORD",
            "TOOL_CALL",
            "EMAIL_SEND",
            "DOCUMENT_CREATE",
            "DOCUMENT_UPDATE",
            "POLICY_EVALUATE",
            "BUDGET_CHECK",
        };

    // ── IClaimEvaluator ──────────────────────────────────────────────────────

    /// <inheritdoc />
    public string ClaimId => "C-041";

    /// <inheritdoc />
    /// <remarks>
    /// Evaluation logic (C-041):
    ///   1. ActionType absent or whitespace → DENY (cannot authorise an unnamed tool).
    ///   2. ActionType not in <see cref="KnownActionTypes"/> → DENY (default-deny).
    ///   3. ActionType present and recognised → Allow.
    ///
    /// The method is intentionally synchronous internally; it is wrapped in
    /// <see cref="Task.FromResult{T}"/> to satisfy the async interface contract
    /// without spinning up a state machine for a zero-I/O operation.
    /// </remarks>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Guard: cancellation respected even for in-memory evaluation
        ct.ThrowIfCancellationRequested();

        // Rule 1 — ActionType must be present (C-041: cannot authorise an unnamed tool)
        if (string.IsNullOrWhiteSpace(ctx.ActionType))
        {
            return Task.FromResult(
                new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    "C-041: ActionType is absent or whitespace — tool authorisation requires an explicit, named action type."));
        }

        // Rule 2 — Default deny: unlisted action type is constitutionally unauthorised
        if (!KnownActionTypes.Contains(ctx.ActionType))
        {
            return Task.FromResult(
                new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-041: Action type '{ctx.ActionType}' is not in the platform-authorised action vocabulary — default-deny applies. Add the action type to C041ToolAuthorizationEvaluator.KnownActionTypes after architectural approval."));
        }

        // Rule 3 — Action type is recognised → allow (remaining evaluators may still deny)
        return Task.FromResult(
            new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                $"C-041: Action type '{ctx.ActionType}' is in the authorised action vocabulary."));
    }
}