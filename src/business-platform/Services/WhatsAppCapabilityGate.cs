// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §25.2 WC120-P2, WC120-P4
// Constitutional basis: C-001, C-023, C-026, C-059, C-063

using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppCapabilityOptions
{
    public bool Configured { get; set; }
    public bool ProviderAvailable { get; set; }
    public bool Revoked { get; set; }
    public string Environment { get; set; } = string.Empty;
    public string ReleaseDigest { get; set; } = string.Empty;
    public string ConfigurationDigest { get; set; } = string.Empty;
    public string CatalogDigest { get; set; } = string.Empty;
    public string RollbackDigest { get; set; } = string.Empty;
    public WhatsAppActivationAuthority? Authority { get; set; }
}

public sealed record WhatsAppActivationAuthority
{
    public string ActivationReference { get; init; } = string.Empty;
    public string ExternalTrafficReference { get; init; } = string.Empty;
    public string ConsentReference { get; init; } = string.Empty;
    public string IncidentOwnerReference { get; init; } = string.Empty;
    public string AlertRouteReference { get; init; } = string.Empty;
    public string Environment { get; init; } = string.Empty;
    public string ReleaseDigest { get; init; } = string.Empty;
    public string ConfigurationDigest { get; init; } = string.Empty;
    public string CatalogDigest { get; init; } = string.Empty;
    public string RollbackDigest { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public string RecipientBindingDigest { get; init; } = string.Empty;
    public DateTimeOffset StartsAt { get; init; }
    public DateTimeOffset ExpiresAt { get; init; }
    public int MaximumMessages { get; init; }
    public int MaximumMessagesPerMinute { get; init; }
    public decimal MaximumSpendInr { get; init; }
    public decimal MaximumCostPerMessageInr { get; init; }
    public bool Revoked { get; init; }
    public bool AllowProvisionalOnboarding { get; init; }
}

public sealed record WhatsAppCapabilityState(string State, string ReasonCode);

public interface IWhatsAppCapabilityGate
{
    WhatsAppCapabilityState Evaluate(DateTimeOffset now);
    WhatsAppActivationAuthority RequireActive(DateTimeOffset now);
    void RequireRecipient(Guid tenantId, string recipientBindingDigest, DateTimeOffset now);
}

public sealed class WhatsAppCapabilityUnavailableException(string reasonCode)
    : Exception(reasonCode)
{
    public string ReasonCode { get; } = reasonCode;
}

public sealed partial class WhatsAppCapabilityGate(
    IOptionsMonitor<WhatsAppCapabilityOptions> options
) : IWhatsAppCapabilityGate
{
    public WhatsAppCapabilityState Evaluate(DateTimeOffset now) =>
        Evaluate(options.CurrentValue, now);

    private static WhatsAppCapabilityState Evaluate(
        WhatsAppCapabilityOptions current,
        DateTimeOffset now
    )
    {
        if (!current.Configured)
            return new("BLOCKED", "CONFIGURATION_MISSING");
        if (
            current.Environment != "demo"
            || !Matches(Digest(), current.ReleaseDigest)
            || !Matches(Digest(), current.ConfigurationDigest)
            || !Matches(Digest(), current.CatalogDigest)
            || !Matches(Digest(), current.RollbackDigest)
            || current.Revoked
        )
            return new("BLOCKED", "CONFIGURATION_DENIED");
        if (!current.ProviderAvailable)
            return new("UNAVAILABLE", "DEPENDENCY_UNAVAILABLE");

        var authority = current.Authority;
        if (authority is null)
            return new("READY_INACTIVE", "ACTIVATION_REQUIRED");
        if (
            authority.Revoked
            || authority.Environment != current.Environment
            || authority.ReleaseDigest != current.ReleaseDigest
            || authority.ConfigurationDigest != current.ConfigurationDigest
            || authority.CatalogDigest != current.CatalogDigest
            || authority.RollbackDigest != current.RollbackDigest
            || !Matches(Reference(), authority.ActivationReference)
            || !Matches(Reference(), authority.ExternalTrafficReference)
            || authority.ExternalTrafficReference == authority.ActivationReference
            || !Matches(Reference(), authority.ConsentReference)
            || !Matches(Reference(), authority.IncidentOwnerReference)
            || !Matches(Reference(), authority.AlertRouteReference)
            || authority.TenantId == Guid.Empty
            || !Matches(BindingDigest(), authority.RecipientBindingDigest)
            || authority.ExpiresAt <= authority.StartsAt
            || authority.MaximumMessages <= 0
            || authority.MaximumMessagesPerMinute <= 0
            || authority.MaximumMessagesPerMinute > authority.MaximumMessages
            || authority.MaximumSpendInr <= 0
            || authority.MaximumSpendInr > 999_999_999_999m
            || decimal.Round(authority.MaximumSpendInr, 6) != authority.MaximumSpendInr
            || authority.MaximumCostPerMessageInr <= 0
            || authority.MaximumCostPerMessageInr > authority.MaximumSpendInr
            || authority.MaximumCostPerMessageInr > 999_999_999_999m
            || decimal.Round(authority.MaximumCostPerMessageInr, 6)
                != authority.MaximumCostPerMessageInr
        )
            return new("BLOCKED", "AUTHORITY_DENIED");
        if (now < authority.StartsAt || now >= authority.ExpiresAt)
            return new("READY_INACTIVE", "WINDOW_CLOSED");
        return new("ACTIVE", "AUTHORIZED");
    }

    public WhatsAppActivationAuthority RequireActive(DateTimeOffset now)
    {
        var current = options.CurrentValue;
        var state = Evaluate(current, now);
        if (state.State != "ACTIVE")
            throw new WhatsAppCapabilityUnavailableException(state.ReasonCode);
        return current.Authority
            ?? throw new WhatsAppCapabilityUnavailableException("AUTHORITY_DENIED");
    }

    public void RequireRecipient(Guid tenantId, string recipientBindingDigest, DateTimeOffset now)
    {
        var authority = RequireActive(now);
        if (
            tenantId != authority.TenantId
            || !string.Equals(
                recipientBindingDigest,
                authority.RecipientBindingDigest,
                StringComparison.Ordinal
            )
        )
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
    }

    [GeneratedRegex("\\Asha256:[a-f0-9]{64}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Digest();

    [GeneratedRegex("\\A[a-f0-9]{64}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex BindingDigest();

    [GeneratedRegex("\\A[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Reference();

    private static bool Matches(Regex pattern, string? value) =>
        value is not null && pattern.IsMatch(value);
}
