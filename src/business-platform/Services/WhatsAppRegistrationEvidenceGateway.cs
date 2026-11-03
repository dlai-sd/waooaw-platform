// Implements: ADR-023 Phone Identity Service step 3b
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
    Task<Guid> RecordProvisionalAsync(
        Guid tenantId,
        string admissionId,
        string bindingDigest,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    ) =>
        throw new NotSupportedException(
            "Provisional onboarding evidence must be explicitly supported."
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
    ILogger<WhatsAppRegistrationEvidenceGateway> logger
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
        await RecordCoreAsync(tenantId, messageId, phoneHmac, occurredAt, false, cancellationToken);
    }

    public Task<Guid> RecordProvisionalAsync(
        Guid tenantId,
        string admissionId,
        string bindingDigest,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    ) => RecordCoreAsync(tenantId, admissionId, bindingDigest, occurredAt, true, cancellationToken);

    private async Task<Guid> RecordCoreAsync(
        Guid tenantId,
        string messageId,
        string phoneHmac,
        DateTimeOffset occurredAt,
        bool provisional,
        CancellationToken cancellationToken
    )
    {
        var endpoint =
            configuration["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException(
                "ConstitutionalEngine:GrpcUrl is not configured."
            );
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(Timeout);
        using var channel = GrpcChannel.ForAddress(endpoint);
        var client = new ConstitutionalService.ConstitutionalServiceClient(channel);
        var actionId = DeterministicActionId(messageId, phoneHmac);
        try
        {
            var evidence = await client.RecordEvidenceAsync(
                new RecordEvidenceRequest
                {
                    ActionInstanceId = actionId.ToString("D"),
                    ContractId = tenantId.ToString("D"),
                    ProfessionalId = "PHONE_IDENTITY",
                    ActionType = provisional
                        ? "WHATSAPP_PROVISIONAL_ONBOARDING"
                        : "WHATSAPP_AUTO_REGISTRATION",
                    State = EvidenceState.Approved,
                    ProposedContent = provisional
                        ? JsonSerializer.Serialize(
                            new
                            {
                                bindingDigest = phoneHmac,
                                authenticationAssurance = "AAL1_CHANNEL",
                                consentScope = "USER_INITIATED_SERVICE",
                                createsFullAccount = false,
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
                },
                new Metadata { { "x-tenant-id", tenantId.ToString("D") } },
                cancellationToken: timeout.Token
            );
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
