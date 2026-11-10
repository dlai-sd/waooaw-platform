// Implements: WC-134 R005, R008, R012
// Constitutional basis: C-023, C-026, C-059, C-063

using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;
using OpenTelemetry;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed partial class WhatsAppIdentityVerificationDispatcher(
    IHttpClientFactory clients,
    IWhatsAppProviderCredentials credentials,
    IWhatsAppAuthenticationTemplateVerifier templates,
    IWhatsAppRegistrationVerificationBudget budget,
    IWhatsAppCapabilityGate gate,
    WhatsAppTenantExecutionScope tenantExecution,
    IOptionsMonitor<WhatsAppAuthenticationTemplateOptions> options,
    TimeProvider clock
) : IIdentityVerificationDispatcher
{
    public Task DispatchAsync(
        IdentityVerificationPurpose purpose,
        string destination,
        string code,
        CancellationToken ct
    ) => throw new IdentityDeliveryUnavailableException("REGISTRATION_CHALLENGE_REQUIRED");

    public async Task DispatchRegistrationMobileAsync(
        Guid registrationId,
        Guid challengeId,
        DateTimeOffset expiresAt,
        string destination,
        string code,
        CancellationToken ct
    )
    {
        if (
            registrationId == Guid.Empty
            || challengeId == Guid.Empty
            || !Phone().IsMatch(destination)
            || !Code().IsMatch(code)
            || expiresAt <= clock.GetUtcNow()
            || expiresAt > clock.GetUtcNow().AddMinutes(15)
        )
            throw new IdentityDeliveryUnavailableException("REGISTRATION_CHALLENGE_INVALID");
        var authority = gate.RequireActive(clock.GetUtcNow());
        if (!authority.AllowRegistrationVerification)
            throw new IdentityDeliveryUnavailableException("REGISTRATION_VERIFICATION_DENIED");
        var template = await templates.VerifyAsync(ct);
        var protectedValues = await credentials.ReadAsync(ct);
        if (
            protectedValues.Binding.Environment != authority.Environment
            || protectedValues.Binding.RecipientBindingDigest != authority.RecipientBindingDigest
            || protectedValues.Binding.WabaId != template.WabaId
            || protectedValues.Binding.PhoneNumberId != template.PhoneNumberId
            || protectedValues.Binding.BindingVersion != template.BindingVersion
            || !authority.AllowPublicAdmission
                && destination != protectedValues.Binding.RecipientPhoneNumber
        )
            throw new IdentityDeliveryUnavailableException("REGISTRATION_RECIPIENT_DENIED");
        using var tenant = tenantExecution.Begin();
        var reserved = await budget.ReserveAsync(challengeId, ct);
        using var suppression = SuppressInstrumentationScope.Begin();
        using var client = clients.CreateClient("WhatsAppProtected");
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"https://graph.facebook.com/{protectedValues.Binding.ApiVersion}"
                + $"/{protectedValues.Binding.PhoneNumberId}/messages"
        );
        request.Headers.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            protectedValues.AccessToken
        );
        request.Content = JsonContent.Create(
            new
            {
                messaging_product = "whatsapp",
                recipient_type = "individual",
                to = destination.TrimStart('+'),
                type = "template",
                template = new
                {
                    name = template.Name,
                    language = new { code = template.Locale },
                    components = new object[]
                    {
                        new
                        {
                            type = "body",
                            parameters = new[] { new { type = "text", text = code } },
                        },
                        new
                        {
                            type = "button",
                            sub_type = "url",
                            index = "0",
                            parameters = new[] { new { type = "text", text = code } },
                        },
                    },
                },
            }
        );
        var latest = options.CurrentValue;
        if (
            gate.RequireActive(clock.GetUtcNow()) != reserved
            || reserved != authority
            || !latest.Enabled
            || latest.TemplateId != template.TemplateId
            || latest.TemplateName != template.Name
            || latest.Locale != template.Locale
            || latest.ApprovalReference != template.ApprovalReference
            || protectedValues.ValidUntil <= clock.GetUtcNow()
            || expiresAt <= clock.GetUtcNow()
        )
            throw new IdentityDeliveryUnavailableException("REGISTRATION_AUTHORITY_CHANGED");
        try
        {
            using var response = await client.SendAsync(request, ct);
            if (!response.IsSuccessStatusCode)
                throw new IdentityDeliveryUnavailableException("REGISTRATION_PROVIDER_REJECTED");
            using var content = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(ct),
                cancellationToken: ct
            );
            if (
                content.RootElement.ValueKind != JsonValueKind.Object
                || !content.RootElement.TryGetProperty("messages", out var messages)
                || messages.ValueKind != JsonValueKind.Array
                || messages.GetArrayLength() != 1
                || messages[0].ValueKind != JsonValueKind.Object
                || !messages[0].TryGetProperty("id", out var id)
                || id.ValueKind != JsonValueKind.String
                || string.IsNullOrWhiteSpace(id.GetString())
            )
                throw new IdentityDeliveryUnavailableException(
                    "REGISTRATION_PROVIDER_OUTCOME_UNKNOWN"
                );
        }
        catch (JsonException)
        {
            throw new IdentityDeliveryUnavailableException("REGISTRATION_PROVIDER_OUTCOME_UNKNOWN");
        }
        catch (HttpRequestException)
        {
            throw new IdentityDeliveryUnavailableException("REGISTRATION_PROVIDER_OUTCOME_UNKNOWN");
        }
        catch (IOException)
        {
            throw new IdentityDeliveryUnavailableException("REGISTRATION_PROVIDER_OUTCOME_UNKNOWN");
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            throw new IdentityDeliveryUnavailableException("REGISTRATION_PROVIDER_OUTCOME_UNKNOWN");
        }
    }

    [GeneratedRegex("\\A\\+[1-9][0-9]{7,14}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Phone();

    [GeneratedRegex("\\A[0-9]{6}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Code();
}
