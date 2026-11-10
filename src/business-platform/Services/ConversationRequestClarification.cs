// Implements: WC-134 customer request-boundary clarification.
// constitutional_basis: C-023, C-026, C-059, C-063
namespace Waooaw.BusinessPlatform.Services;

internal enum ConversationRequestBoundary
{
    Unclear,
    OneRequest,
    SeparateRequests,
}

internal static class ConversationRequestClarification
{
    internal const string Question =
        "Should all these messages be combined into one request, or should each message "
        + "be a separate request? Reply to this message with ONE or SEPARATE.";

    internal static ConversationRequestBoundary Interpret(string? response)
    {
        var choice = response?.Trim();
        if (string.Equals(choice, "ONE", StringComparison.OrdinalIgnoreCase))
            return ConversationRequestBoundary.OneRequest;
        if (string.Equals(choice, "SEPARATE", StringComparison.OrdinalIgnoreCase))
            return ConversationRequestBoundary.SeparateRequests;
        return ConversationRequestBoundary.Unclear;
    }
}
