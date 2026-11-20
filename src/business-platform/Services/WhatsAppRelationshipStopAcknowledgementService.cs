// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-03
// Constitutional basis: C-001, C-023, C-026, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>
/// What the signed safety route resolved once the stop had committed: the relationship that was stopped and the
/// destination the contact has already verified. It carries no message text and no personal data beyond that.
/// </summary>
public sealed record WhatsAppSafetyAcknowledgementTarget(
    Guid RelationshipTenantId,
    Guid RelationshipId,
    bool Emergency,
    string? ContactDestination
);

/// <summary>
/// Queues the fixed STOP or Emergency Stop acknowledgement for a relationship-bound recipient. It runs only after
/// the stop evidence, fence and halt have committed and can never delay, fail or undo the stop: every failure is
/// logged by reason code and swallowed.
/// </summary>
public sealed class WhatsAppRelationshipStopAcknowledgementService(
    IGuestConversation interactions,
    WhatsAppOutboxService outbox,
    IWhatsAppCapabilityGate capability,
    IOptions<Wc120ConversationOptions> conversationOptions,
    IOptionsMonitor<ProtocolOptions> protocolOptions,
    TimeProvider clock,
    ILogger<WhatsAppRelationshipStopAcknowledgementService> logger
)
{
    /// <summary>Returns the acknowledgement text when one was queued, otherwise null.</summary>
    public async Task<string?> TryAcknowledgeAsync(
        WhatsAppSafetyAcknowledgementTarget target,
        VerifiedPhoneIdentityProof proof,
        CancellationToken ct
    )
    {
        if (!WhatsAppStopAcknowledgementPolicy.IsActive(protocolOptions))
            return null;
        var kind = target.Emergency ? "EMERGENCY_STOP" : "STOP";
        var text = WhatsAppStopAcknowledgementPolicy.RelationshipText(target.Emergency);
        try
        {
            var now = clock.GetUtcNow();
            var authority = capability.RequireActive(now);
            var destination = proof.ProtectedDestination ?? target.ContactDestination;
            if (string.IsNullOrWhiteSpace(destination))
                throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");
            var participantId = ParticipantId(authority.TenantId, target.RelationshipId, proof);
            var submission = await interactions.SendGuestFixedNoticeAsync(
                authority.TenantId,
                participantId,
                MessageKey(authority.TenantId, target.RelationshipId, proof, kind),
                text,
                ct
            );
            await outbox.QueueRelationshipStopAcknowledgementAsync(
                authority.TenantId,
                target.RelationshipTenantId,
                target.RelationshipId,
                participantId,
                proof.PhoneSubjectHash,
                destination,
                target.Emergency,
                submission.Value,
                now,
                ct
            );
            logger.LogInformation("protocol_stop_acknowledged channel=WHATSAPP kind={Kind}", kind);
            return text;
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            // The stop is already committed; a failed acknowledgement is reported, never retried into the stop.
            logger.LogWarning(
                "protocol_stop_acknowledgement_failed channel=WHATSAPP kind={Kind} reason={Reason}",
                kind,
                exception is WhatsAppCapabilityUnavailableException unavailable
                    ? unavailable.ReasonCode
                    : exception.GetType().Name
            );
            return null;
        }
    }

    private Guid ParticipantId(
        Guid tenantId,
        Guid relationshipId,
        VerifiedPhoneIdentityProof proof
    ) =>
        Derive(
            $"WC136:relationship-stop-ack:{conversationOptions.Value.Environment}:{tenantId:D}:{relationshipId:D}:{proof.PhoneSubjectHash}"
        );

    // Built from the relationship and the stop message, so a replay of the same message queues nothing new.
    private Guid MessageKey(
        Guid tenantId,
        Guid relationshipId,
        VerifiedPhoneIdentityProof proof,
        string kind
    ) =>
        Derive(
            $"WC136:relationship-stop-ack-message:{conversationOptions.Value.Environment}:{tenantId:D}:{relationshipId:D}:{kind}:{proof.MessageId}"
        );

    private static Guid Derive(string value) =>
        new(SHA256.HashData(Encoding.UTF8.GetBytes(value)).AsSpan(0, 16));
}
