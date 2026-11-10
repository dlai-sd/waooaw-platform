using System.Text.Json;
using Grpc.Core;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Services;
using Waooaw.ConstitutionalEngine.Grpc;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WhatsAppRegistrationEvidenceGatewayTests
{
    [Theory]
    [InlineData("registration", "PHONE_IDENTITY", "WHATSAPP_AUTO_REGISTRATION")]
    [InlineData("admission", "WHATSAPP_GUEST_SESSION", "WHATSAPP_GUEST_SESSION_ADMISSION")]
    [InlineData(
        "consent",
        "WHATSAPP_GUEST_SERVICE_CONSENT",
        "WHATSAPP_GUEST_SERVICE_CONSENT"
    )]
    public async Task RecordsExactConstitutionalEvidence(
        string operation,
        string professionalId,
        string actionType
    )
    {
        var tenantId = Guid.NewGuid();
        var evidenceId = Guid.NewGuid();
        RecordEvidenceRequest? captured = null;
        Metadata? capturedMetadata = null;
        var gateway = Gateway(
            (request, metadata, _) =>
            {
                captured = request;
                capturedMetadata = metadata;
                return Task.FromResult(
                    new RecordEvidenceResponse { EvidenceRecordId = evidenceId.ToString("D") }
                );
            }
        );

        var result = operation switch
        {
            "admission" => await gateway.RecordGuestAdmissionAsync(
                tenantId,
                "admission-1",
                new string('a', 64),
                DateTimeOffset.UtcNow,
                CancellationToken.None
            ),
            "consent" => await gateway.RecordGuestConsentAsync(
                tenantId,
                "message-1",
                new string('b', 64),
                "notice-1",
                DateTimeOffset.UtcNow,
                CancellationToken.None
            ),
            _ => await RecordAsync(gateway, tenantId),
        };

        Assert.Equal(operation == "registration" ? Guid.Empty : evidenceId, result);
        Assert.Equal(professionalId, captured!.ProfessionalId);
        Assert.Equal(actionType, captured.ActionType);
        Assert.Equal(EvidenceState.Approved, captured.State);
        Assert.Equal(tenantId.ToString("D"), captured.ContractId);
        Assert.Equal(
            tenantId.ToString("D"),
            capturedMetadata!.Single(value => value.Key == "x-tenant-id").Value
        );
        using var proposed = JsonDocument.Parse(captured.ProposedContent);
        if (operation == "registration")
            Assert.Equal(new string('c', 64), proposed.RootElement.GetProperty("phoneHmac").GetString());
        else
            Assert.False(proposed.RootElement.GetProperty("marketingConsent").GetBoolean());
    }

    [Theory]
    [InlineData("")]
    [InlineData("00000000-0000-0000-0000-000000000000")]
    public async Task RejectsInvalidEvidenceIdentity(string evidenceRecordId)
    {
        var gateway = Gateway(
            (_, _, _) =>
                Task.FromResult(
                    new RecordEvidenceResponse { EvidenceRecordId = evidenceRecordId }
                )
        );

        await Assert.ThrowsAsync<InvalidOperationException>(
            () =>
                gateway.RecordGuestAdmissionAsync(
                    Guid.NewGuid(),
                    "admission-1",
                    new string('a', 64),
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
        );
    }

    [Fact]
    public async Task PreservesRecorderFailure()
    {
        var gateway = Gateway(
            (_, _, _) => throw new RpcException(new Status(StatusCode.Unavailable, "offline"))
        );

        await Assert.ThrowsAsync<RpcException>(
            () =>
                gateway.RecordGuestConsentAsync(
                    Guid.NewGuid(),
                    "message-1",
                    new string('b', 64),
                    "notice-1",
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
        );
    }

    [Fact]
    public async Task RequiresConfiguredConstitutionalEndpoint()
    {
        var gateway = new WhatsAppRegistrationEvidenceGateway(
            new ConfigurationBuilder().Build(),
            NullLogger<WhatsAppRegistrationEvidenceGateway>.Instance
        );

        await Assert.ThrowsAsync<InvalidOperationException>(
            () =>
                gateway.RecordAsync(
                    Guid.NewGuid(),
                    "message-1",
                    new string('c', 64),
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
        );
    }

    [Fact]
    public async Task InterfaceDefaultsDenyUnsupportedGuestEvidence()
    {
        IWhatsAppRegistrationEvidenceGateway gateway = new RegistrationOnlyGateway();

        await Assert.ThrowsAsync<NotSupportedException>(
            () =>
                gateway.RecordGuestAdmissionAsync(
                    Guid.NewGuid(),
                    "admission-1",
                    new string('a', 64),
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
        );
        await Assert.ThrowsAsync<NotSupportedException>(
            () =>
                gateway.RecordGuestConsentAsync(
                    Guid.NewGuid(),
                    "message-1",
                    new string('a', 64),
                    "notice-1",
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
        );
    }

    private static WhatsAppRegistrationEvidenceGateway Gateway(
        Func<
            RecordEvidenceRequest,
            Metadata,
            CancellationToken,
            Task<RecordEvidenceResponse>
        > recorder
    ) =>
        new(
            new ConfigurationBuilder().Build(),
            NullLogger<WhatsAppRegistrationEvidenceGateway>.Instance,
            recorder
        );

    private static async Task<Guid> RecordAsync(
        IWhatsAppRegistrationEvidenceGateway gateway,
        Guid tenantId
    )
    {
        await gateway.RecordAsync(
            tenantId,
            "message-1",
            new string('c', 64),
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        return Guid.Empty;
    }

    private sealed class RegistrationOnlyGateway : IWhatsAppRegistrationEvidenceGateway
    {
        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken cancellationToken
        ) => Task.CompletedTask;
    }
}
