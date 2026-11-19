// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R003, WC135-R008, WC135-R011
// Constitutional basis: C-009, C-023, C-026, C-048, C-049, C-059, C-063

using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.Visitor;

public static class VisitorMode
{
    public const string Legacy = "LEGACY";
    public const string V2 = "V2";
}

/// <summary>Per-environment switches for the visitor conversation (WC-135).</summary>
public sealed class VisitorConversationOptions
{
    /// <summary>LEGACY keeps today's guest replies; V2 uses the visitor conversation core.</summary>
    public string Mode { get; set; } = VisitorMode.Legacy;

    /// <summary>Content set id used when a tenant has no explicit mapping.</summary>
    public string DefaultContentId { get; set; } = "waooaw-demo";

    /// <summary>Tenant used by the visitor endpoint when no tenant scope is active.</summary>
    public Guid? DefaultTenantId { get; set; }

    /// <summary>Public anonymous WEB and MOBILE exposure. Disabled in the first release.</summary>
    public bool PublicEntryEnabled { get; set; }

    /// <summary>Demo-only simulated customers (SIMULATION channel).</summary>
    public bool SimulatorEnabled { get; set; }

    /// <summary>Shared HMAC secret for simulated customers. Never logged.</summary>
    public string SimulatorSecret { get; set; } = string.Empty;

    public int SimulatorMaxTurnsPerSession { get; set; } = 40;
    public int SimulatorMaxSessionsPerDay { get; set; } = 2_000;

    /// <summary>HMAC key for visitor session tokens (WEB and MOBILE).</summary>
    public string SessionTokenKey { get; set; } = string.Empty;

    /// <summary>Local/test key ring (version to key). Demo and above use the Key Vault phone-subject key versions.</summary>
    public Dictionary<string, string> LocalKeys { get; set; } = [];

    public string LocalCurrentKeyVersion { get; set; } = string.Empty;

    /// <summary>Content set id per tenant; tenants without an entry use <see cref="DefaultContentId"/>.</summary>
    public Dictionary<Guid, string> TenantContentIds { get; set; } = [];

    public int SessionTokenMinutes { get; set; } = 60;

    /// <summary>Portal registration URL; the opaque handoff reference is appended as ?lead=.</summary>
    public string HandoffBaseUrl { get; set; } = "https://cp.demo.waooaw.com/register";

    /// <summary>
    /// Public base of the open endpoint (…/api/v1/visitor/handoffs). When set, the shared link goes through it so a
    /// tap is recorded before the visitor is sent on to <see cref="HandoffBaseUrl"/>.
    /// </summary>
    public string HandoffOpenBaseUrl { get; set; } = string.Empty;

    public int HandoffReferenceMinutes { get; set; } = 60 * 24 * 7;

    /// <summary>Messages per visitor per rolling minute on the endpoint path.</summary>
    public int MessagesPerVisitorPerMinute { get; set; } = 20;

    /// <summary>Messages per tenant per rolling minute on the endpoint path.</summary>
    public int MessagesPerTenantPerMinute { get; set; } = 600;

    /// <summary>Channel rendering limits; verified against Meta documentation before use.</summary>
    public int MaxChoiceButtons { get; set; } = 3;

    public int MaxChoiceLabelLength { get; set; } = 20;
    public int MaxListRows { get; set; } = 10;
    public int MaxInteractiveBodyLength { get; set; } = 1_024;
    public int MaxTextBodyLength { get; set; } = 4_096;

    public bool IsV2 => string.Equals(Mode, VisitorMode.V2, StringComparison.Ordinal);
}

/// <summary>Lead retention (Founder decision O-3): default 90 days within 30 to 365.</summary>
public sealed class VisitorLeadOptions
{
    public const int MinimumRetentionDays = 30;
    public const int MaximumRetentionDays = 365;
    public const int MinimumSimulationRetentionDays = 1;
    public const int MaximumSimulationRetentionDays = 30;

    public int RetentionDays { get; set; } = 90;
    public int SimulationRetentionDays { get; set; } = 7;
    public int PurgeIntervalMinutes { get; set; } = 60;
    public int PurgeBatchSize { get; set; } = 500;

    /// <summary>Per-tenant overrides; each value is validated with the same bounds.</summary>
    public Dictionary<Guid, int> TenantRetentionDays { get; set; } = [];

    public int RetentionDaysFor(Guid tenantId) =>
        TenantRetentionDays.TryGetValue(tenantId, out var days) ? days : RetentionDays;
}

internal sealed class VisitorLeadOptionsValidator : IValidateOptions<VisitorLeadOptions>
{
    public ValidateOptionsResult Validate(string? name, VisitorLeadOptions options)
    {
        var errors = new List<string>();
        if (
            options.RetentionDays
            is < VisitorLeadOptions.MinimumRetentionDays
                or > VisitorLeadOptions.MaximumRetentionDays
        )
            errors.Add(
                $"VisitorLeads:RetentionDays must be between {VisitorLeadOptions.MinimumRetentionDays} and {VisitorLeadOptions.MaximumRetentionDays}."
            );
        foreach (var (tenant, days) in options.TenantRetentionDays)
        {
            if (
                days
                is < VisitorLeadOptions.MinimumRetentionDays
                    or > VisitorLeadOptions.MaximumRetentionDays
            )
                errors.Add(
                    $"VisitorLeads:TenantRetentionDays for {tenant} must be between {VisitorLeadOptions.MinimumRetentionDays} and {VisitorLeadOptions.MaximumRetentionDays}."
                );
        }
        if (
            options.SimulationRetentionDays
            is < VisitorLeadOptions.MinimumSimulationRetentionDays
                or > VisitorLeadOptions.MaximumSimulationRetentionDays
        )
            errors.Add(
                $"VisitorLeads:SimulationRetentionDays must be between {VisitorLeadOptions.MinimumSimulationRetentionDays} and {VisitorLeadOptions.MaximumSimulationRetentionDays}."
            );
        if (options.PurgeIntervalMinutes is < 1 or > 1_440)
            errors.Add("VisitorLeads:PurgeIntervalMinutes must be between 1 and 1440.");
        if (options.PurgeBatchSize is < 1 or > 5_000)
            errors.Add("VisitorLeads:PurgeBatchSize must be between 1 and 5000.");
        return errors.Count == 0
            ? ValidateOptionsResult.Success
            : ValidateOptionsResult.Fail(errors);
    }
}

internal sealed class VisitorConversationOptionsValidator
    : IValidateOptions<VisitorConversationOptions>
{
    public ValidateOptionsResult Validate(string? name, VisitorConversationOptions options)
    {
        var errors = new List<string>();
        if (options.Mode is not (VisitorMode.Legacy or VisitorMode.V2))
            errors.Add("VisitorConversation:Mode must be LEGACY or V2.");
        if (options.SimulatorEnabled && options.SimulatorSecret.Length < 32)
            errors.Add("VisitorConversation:SimulatorSecret must be at least 32 characters.");
        if (options.PublicEntryEnabled && options.SessionTokenKey.Length < 32)
            errors.Add("VisitorConversation:SessionTokenKey must be at least 32 characters.");
        if (options.SessionTokenMinutes is < 5 or > 1_440)
            errors.Add("VisitorConversation:SessionTokenMinutes must be between 5 and 1440.");
        if (options.HandoffReferenceMinutes is < 5 or > 60 * 24 * 30)
            errors.Add("VisitorConversation:HandoffReferenceMinutes must be between 5 and 43200.");
        if (
            !Uri.TryCreate(options.HandoffBaseUrl, UriKind.Absolute, out var handoff)
            || handoff.Scheme != Uri.UriSchemeHttps
        )
            errors.Add("VisitorConversation:HandoffBaseUrl must be an absolute HTTPS URL.");
        if (
            options.HandoffOpenBaseUrl.Length > 0
            && (
                !Uri.TryCreate(options.HandoffOpenBaseUrl, UriKind.Absolute, out var open)
                || open.Scheme != Uri.UriSchemeHttps
            )
        )
            errors.Add(
                "VisitorConversation:HandoffOpenBaseUrl must be empty or an absolute HTTPS URL."
            );
        if (options.MaxChoiceButtons is < 1 or > 3)
            errors.Add("VisitorConversation:MaxChoiceButtons must be between 1 and 3.");
        if (options.MaxChoiceLabelLength is < 4 or > 20)
            errors.Add("VisitorConversation:MaxChoiceLabelLength must be between 4 and 20.");
        if (options.MaxListRows is < 1 or > 10)
            errors.Add("VisitorConversation:MaxListRows must be between 1 and 10.");
        if (options.MessagesPerVisitorPerMinute < 1 || options.MessagesPerTenantPerMinute < 1)
            errors.Add("VisitorConversation message limits must be positive.");
        return errors.Count == 0
            ? ValidateOptionsResult.Success
            : ValidateOptionsResult.Fail(errors);
    }
}
