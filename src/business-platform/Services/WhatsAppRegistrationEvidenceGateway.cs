// Implements: ADR-023 channel evidence boundary for user-initiated WhatsApp guest discovery
// constitutional_basis: C-023, C-026, C-042, C-059

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Grpc.Core;
using Grpc.Net.Client;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.BusinessPlatform.Services;

public interface IWhatsAppRegistrationEvidenceGateway
{
    Task<Guid> RecordGuestAdmissionAsync(
        Guid tenantId,
        string admissionId,
        string bindingDigest,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    ) =>
        throw new NotSupportedException(
            "WhatsApp guest-session admission evidence must be explicitly supported."
        );

    Task<Guid> RecordGuestConsentAsync(
        Guid tenantId,
        string messageId,
        string bindingDigest,
        string noticeVersion,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    ) =>
        throw new NotSupportedException(
            "WhatsApp guest service-consent evidence must be explicitly supported."
        );

    Task RecordAsync(
        Guid tenantId,
        string messageId,
        string phoneHmac,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    );
}

public sealed class WhatsAppRegistrationEvidenceGateway(
    IConfiguration configuration,
    ILogger<WhatsAppRegistrationEvidenceGateway> logger,
    Func<
        RecordEvidenceRequest,
        Metadata,
        CancellationToken,
        Task<RecordEvidenceResponse>
    >? recorder = null
) : IWhatsAppRegistrationEvidenceGateway
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(5);

    public async Task RecordAsync(
        Guid tenantId,
        string messageId,
        string phoneHmac,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    )
    {
        await RecordCoreAsync(
            tenantId,
            messageId,
            phoneHmac,
            occurredAt,
            guestAdmission: false,
            guestConsent: false,
            noticeVersion: null,
            cancellationToken: cancellationToken
        );
    }

    public Task<Guid> RecordGuestAdmissionAsync(
        Guid tenantId,
        string admissionId,
        string bindingDigest,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    ) =>
        RecordCoreAsync(
            tenantId,
            admissionId,
            bindingDigest,
            occurredAt,
            guestAdmission: true,
            guestConsent: false,
            noticeVersion: null,
            cancellationToken: cancellationToken
        );

    public Task<Guid> RecordGuestConsentAsync(
        Guid tenantId,
        string messageId,
        string bindingDigest,
        string noticeVersion,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    ) =>
        RecordCoreAsync(
            tenantId,
            messageId,
            bindingDigest,
            occurredAt,
            guestAdmission: false,
            guestConsent: true,
            noticeVersion: noticeVersion,
            cancellationToken: cancellationToken
        );

    private async Task<Guid> RecordCoreAsync(
        Guid tenantId,
        string messageId,
        string phoneHmac,
        DateTimeOffset occurredAt,
        bool guestAdmission,
        bool guestConsent,
        string? noticeVersion,
        CancellationToken cancellationToken
    )
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(Timeout);
        var actionId = DeterministicActionId(messageId, phoneHmac);
        var request = new RecordEvidenceRequest
        {
            ActionInstanceId = actionId.ToString("D"),
            ContractId = tenantId.ToString("D"),
            ProfessionalId =
                guestAdmission ? "WHATSAPP_GUEST_SESSION"
                : guestConsent ? "WHATSAPP_GUEST_SERVICE_CONSENT"
                : "PHONE_IDENTITY",
            ActionType =
                guestAdmission ? "WHATSAPP_GUEST_SESSION_ADMISSION"
                : guestConsent ? "WHATSAPP_GUEST_SERVICE_CONSENT"
                : "WHATSAPP_AUTO_REGISTRATION",
            State = EvidenceState.Approved,
            ProposedContent =
                guestAdmission
                    ? JsonSerializer.Serialize(
                        new
                        {
                            bindingDigest = phoneHmac,
                            authenticationAssurance = "AAL1_CHANNEL",
                            guestInitiated = true,
                            serviceScope = "WHATSAPP_GUEST_DISCOVERY",
                            marketingConsent = false,
                            createsCustomerAccount = false,
                            createsMembership = false,
                            createsEmployment = false,
                            occurredAt,
                        }
                    )
                : guestConsent
                    ? JsonSerializer.Serialize(
                        new
                        {
                            bindingDigest = phoneHmac,
                            consentMessageId = messageId,
                            serviceConsent = true,
                            serviceScope = "WHATSAPP_GUEST_DISCOVERY",
                            noticeVersion,
                            marketingConsent = false,
                            createsCustomerAccount = false,
                            createsMembership = false,
                            createsEmployment = false,
                            occurredAt,
                        }
                    )
                : JsonSerializer.Serialize(
                    new
                    {
                        phoneHmac,
                        optedIn = true,
                        onboardingChannel = "WHATSAPP",
                        occurredAt,
                    }
                ),
            DecisionSpaceVersion = 1,
            ConstitutionalBasis = "C-023; C-026; C-042; C-059; ADR-023",
        };
        var metadata = new Metadata { { "x-tenant-id", tenantId.ToString("D") } };
        try
        {
            RecordEvidenceResponse evidence;
            if (recorder is not null)
                evidence = await recorder(request, metadata, timeout.Token);
            else
            {
                var endpoint =
                    configuration["ConstitutionalEngine:GrpcUrl"]
                    ?? throw new InvalidOperationException(
                        "ConstitutionalEngine:GrpcUrl is not configured."
                    );
                using var channel = GrpcChannel.ForAddress(endpoint);
                var client = new ConstitutionalService.ConstitutionalServiceClient(channel);
                evidence = await client.RecordEvidenceAsync(
                    request,
                    metadata,
                    cancellationToken: timeout.Token
                );
            }
            if (
                !Guid.TryParse(evidence.EvidenceRecordId, out var evidenceId)
                || evidenceId == Guid.Empty
            )
                throw new InvalidOperationException(
                    "Constitutional Engine returned an invalid evidence identifier."
                );
            return evidenceId;
        }
        catch (Exception exception)
        {
            logger.LogError(
                exception,
                "WhatsApp registration evidence failed for tenant {TenantId}",
                tenantId
            );
            throw;
        }
    }

    private static Guid DeterministicActionId(string messageId, string phoneHmac)
    {
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes($"{messageId}:{phoneHmac}"));
        return new Guid(digest.AsSpan(0, 16));
    }
}
