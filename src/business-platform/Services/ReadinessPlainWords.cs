// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R008
// Constitutional basis: C-042 (Localization), C-049 (Honest Limitation), C-059 (Implementation Traceability)

namespace Waooaw.BusinessPlatform.Services;

/// <summary>What is missing, in words a customer uses, and the one thing to do about it.</summary>
public sealed record PlainReadinessItem(string Missing, string NextStep, bool CustomerCanAct);

/// <summary>
/// Turns the technical reasons the platform reports for a locked workspace into plain words with one next step. The
/// technical reasons stay available to support; the customer is never left at a dead end, so a reason that only the
/// platform can resolve says so and says what happens next.
/// </summary>
public static class ReadinessPlainWords
{
    private static readonly (string Match, PlainReadinessItem Item)[] Rules =
    [
        (
            "must be active before",
            new(
                "Your agent is not active yet.",
                "Finish starting your Trial or Hire from My Agents.",
                true
            )
        ),
        (
            "Onboarding preferences",
            new(
                "Your agent does not know how you like to be updated.",
                "Confirm your preferences.",
                true
            )
        ),
        (
            "induction context",
            new(
                "Your agent still needs to learn about your business.",
                "Continue the induction conversation with your agent.",
                true
            )
        ),
        (
            "Skill must be accepted",
            new(
                "No skill has been switched on for your agent yet.",
                "Accept the skills you want your agent to use.",
                true
            )
        ),
        (
            "goal must be customer-verified",
            new("Your agent has no confirmed goal yet.", "Review and confirm your goals.", true)
        ),
        (
            "every active goal",
            new(
                "A goal is still waiting for your confirmation.",
                "Review and confirm your goals.",
                true
            )
        ),
        (
            "bind a current verified goal",
            new("A skill is waiting for a confirmed goal.", "Review and confirm your goals.", true)
        ),
        (
            "accepted employment contract",
            new(
                "You have not accepted the employment agreement yet.",
                "Review and accept the agreement.",
                true
            )
        ),
        (
            "accepted contract",
            new(
                "You have not accepted the employment agreement yet.",
                "Review and accept the agreement.",
                true
            )
        ),
        (
            "Decision Space",
            new(
                "What your agent may and may not do has not been confirmed.",
                "Confirm your agent's limits when asked.",
                true
            )
        ),
        (
            "authority snapshot",
            new(
                "What your agent may and may not do has not been confirmed.",
                "Confirm your agent's limits when asked.",
                true
            )
        ),
        (
            "lacks current operational authority",
            new(
                "A skill has no confirmed limits yet.",
                "Confirm your agent's limits when asked.",
                true
            )
        ),
        (
            "Commercial readiness",
            new("Your plan's allowance is not ready yet.", "Open Billing to see your plan.", true)
        ),
        (
            "reassessment",
            new(
                "A performance review is waiting for your answer.",
                "Open the review and answer it.",
                true
            )
        ),
        (
            "Professional Runtime readiness",
            new(
                "Your agent's workplace is still being prepared.",
                "Nothing to do now. We are finishing this; check back in a few minutes.",
                false
            )
        ),
        (
            "runtime binding",
            new(
                "Your agent's skills are still being set up on our side.",
                "Nothing to do now. If this stays for more than an hour, tell us in the chat.",
                false
            )
        ),
        (
            "admission",
            new(
                "Your agent's approval is still being set up on our side.",
                "Nothing to do now. If this stays for more than an hour, tell us in the chat.",
                false
            )
        ),
        (
            "artifact",
            new(
                "Your agent's approval is still being set up on our side.",
                "Nothing to do now. If this stays for more than an hour, tell us in the chat.",
                false
            )
        ),
    ];

    private static readonly PlainReadinessItem Fallback = new(
        "Something is still being set up for your agent.",
        "Nothing to do now. Check back in a few minutes.",
        false
    );

    public static PlainReadinessItem Translate(string technicalReason) =>
        Rules
            .Where(rule => technicalReason.Contains(rule.Match, StringComparison.OrdinalIgnoreCase))
            .Select(rule => rule.Item)
            .FirstOrDefault()
        ?? Fallback;

    /// <summary>The distinct plain items, in the order the technical reasons arrived, customer-actionable ones first.</summary>
    public static IReadOnlyList<PlainReadinessItem> Translate(
        IEnumerable<string> technicalReasons
    ) =>
        technicalReasons
            .Select(Translate)
            .DistinctBy(item => item.Missing)
            .OrderByDescending(item => item.CustomerCanAct)
            .ToArray();
}
