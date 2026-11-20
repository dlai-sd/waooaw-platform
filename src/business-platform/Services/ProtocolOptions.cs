// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-02, C1-03
// Constitutional basis: C-023, C-026, C-059, C-063

using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services.Visitor;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>
/// Per-environment switches for protocol behavior (FD17). The visitor endpoint and the simulator follow the
/// protocol policy table regardless of these values; they only gate the WhatsApp delivery exception.
/// </summary>
public sealed class ProtocolOptions
{
    public const string SectionName = "Protocol";

    /// <summary>
    /// Off by default: sending to a stopped recipient on a live number needs a privacy and provider-policy check.
    /// </summary>
    public bool WhatsAppStopAcknowledgementEnabled { get; set; }
}

/// <summary>The single guard for the narrow "acknowledge STOP to a stopped recipient" delivery exception.</summary>
public static class WhatsAppStopAcknowledgementPolicy
{
    public const string GuestPurpose = "WHATSAPP_GUEST_STOP_ACK";
    public const string RelationshipPurpose = "WHATSAPP_RELATIONSHIP_STOP_ACK";

    /// <summary>Base Specification B-5 sentence, sent once when an Emergency Stop has no other confirmation.</summary>
    public const string EmergencyStopConfirmation =
        "Everything has stopped. Nothing will happen until you say so.";

    private const string RecipientStopReferencePrefix = "relationship-stop:";
    private const string EmergencyStopReferencePrefix = "relationship-emergency-stop:";

    public static bool IsActive(IOptionsMonitor<ProtocolOptions>? options)
    {
        var copy = GuestCopyRegistry.Current;
        return options?.CurrentValue.WhatsAppStopAcknowledgementEnabled == true
            && copy.Protocol.AcknowledgesStopOn(VisitorProtocolContent.WhatsAppChannel)
            && !string.IsNullOrWhiteSpace(copy.StopAcknowledged);
    }

    public static string RelationshipReference(
        bool emergency,
        Guid relationshipTenantId,
        Guid relationshipId,
        Guid stopMessageKey
    ) =>
        $"{(emergency ? EmergencyStopReferencePrefix : RecipientStopReferencePrefix)}{relationshipTenantId:D}:{relationshipId:D}:{stopMessageKey:D}";

    /// <summary>The only text a relationship STOP acknowledgement row may carry for the given kind.</summary>
    public static string RelationshipText(bool emergency) =>
        emergency ? EmergencyStopConfirmation : GuestCopyRegistry.Current.StopAcknowledged;

    public static bool TryParseRelationshipReference(
        string? reference,
        out bool emergency,
        out Guid relationshipTenantId,
        out Guid relationshipId
    )
    {
        emergency = false;
        relationshipTenantId = Guid.Empty;
        relationshipId = Guid.Empty;
        if (reference is null)
            return false;
        string rest;
        if (reference.StartsWith(EmergencyStopReferencePrefix, StringComparison.Ordinal))
        {
            emergency = true;
            rest = reference[EmergencyStopReferencePrefix.Length..];
        }
        else if (reference.StartsWith(RecipientStopReferencePrefix, StringComparison.Ordinal))
            rest = reference[RecipientStopReferencePrefix.Length..];
        else
            return false;
        var parts = rest.Split(':');
        return parts.Length == 3
            && Guid.TryParse(parts[0], out relationshipTenantId)
            && relationshipTenantId != Guid.Empty
            && Guid.TryParse(parts[1], out relationshipId)
            && relationshipId != Guid.Empty
            && Guid.TryParse(parts[2], out var messageKey)
            && messageKey != Guid.Empty;
    }
}
