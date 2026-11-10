// Implements: WC-134 R005, R011, R012
// Constitutional basis: C-023, C-026, C-059, C-063

using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;
using OpenTelemetry;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppAuthenticationTemplateOptions
{
    public bool Enabled { get; set; }
    public string TemplateId { get; set; } = string.Empty;
    public string TemplateName { get; set; } = string.Empty;
    public string Locale { get; set; } = string.Empty;
    public string ApprovalReference { get; set; } = string.Empty;
}

public sealed record VerifiedWhatsAppAuthenticationTemplate(
    string TemplateId,
    string Name,
    string Locale,
    string ApprovalReference,
    string WabaId,
    string PhoneNumberId,
    string BindingVersion
);

public interface IWhatsAppAuthenticationTemplateVerifier
{
    Task<VerifiedWhatsAppAuthenticationTemplate> VerifyAsync(CancellationToken ct);
}

public sealed partial class WhatsAppAuthenticationTemplateVerifier(
    IHttpClientFactory clients,
    IWhatsAppProviderCredentials credentials,
    IOptionsMonitor<WhatsAppAuthenticationTemplateOptions> options,
    TimeProvider clock
) : IWhatsAppAuthenticationTemplateVerifier
{
    public async Task<VerifiedWhatsAppAuthenticationTemplate> VerifyAsync(CancellationToken ct)
    {
        var current = options.CurrentValue;
        if (
            !current.Enabled
            || !Identifier().IsMatch(current.TemplateId)
            || !Name().IsMatch(current.TemplateName)
            || !Locale().IsMatch(current.Locale)
            || !Reference().IsMatch(current.ApprovalReference)
        )
            throw Denied("AUTHENTICATION_TEMPLATE_CONFIGURATION_REQUIRED");

        var protectedValues = await credentials.ReadAsync(ct);
        var expected = new VerifiedWhatsAppAuthenticationTemplate(
            current.TemplateId,
            current.TemplateName,
            current.Locale,
            current.ApprovalReference,
            protectedValues.Binding.WabaId,
            protectedValues.Binding.PhoneNumberId,
            protectedValues.Binding.BindingVersion
        );
        if (protectedValues.ValidUntil <= clock.GetUtcNow())
            throw Denied("PROVIDER_AUTHORITY_EXPIRED");

        using var suppression = SuppressInstrumentationScope.Begin();
        using var client = clients.CreateClient("WhatsAppProtected");
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            $"https://graph.facebook.com/{protectedValues.Binding.ApiVersion}"
                + $"/{protectedValues.Binding.WabaId}/message_templates"
                + $"?name={Uri.EscapeDataString(expected.Name)}"
                + "&fields=id,name,language,status,category,components&limit=100"
        );
        request.Headers.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            protectedValues.AccessToken
        );
        try
        {
            using var response = await client.SendAsync(request, ct);
            if (!response.IsSuccessStatusCode)
                throw Denied("AUTHENTICATION_TEMPLATE_READBACK_UNAVAILABLE");
            using var content = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(ct),
                cancellationToken: ct
            );
            var root = content.RootElement;
            if (
                root.ValueKind != JsonValueKind.Object
                || !root.TryGetProperty("data", out var data)
                || data.ValueKind != JsonValueKind.Array
            )
                throw Denied("AUTHENTICATION_TEMPLATE_READBACK_INVALID");
            var matches = data.EnumerateArray()
                .Where(value =>
                    Is(value, "id", expected.TemplateId)
                    && Is(value, "name", expected.Name)
                    && Is(value, "language", expected.Locale)
                )
                .ToArray();
            if (
                matches.Length != 1
                || !Is(matches[0], "status", "APPROVED")
                || !Is(matches[0], "category", "AUTHENTICATION")
                || !HasApprovedComponents(matches[0])
            )
                throw Denied("AUTHENTICATION_TEMPLATE_APPROVAL_REQUIRED");
            if (
                options.CurrentValue is not { Enabled: true } latest
                || latest.TemplateId != expected.TemplateId
                || latest.TemplateName != expected.Name
                || latest.Locale != expected.Locale
                || latest.ApprovalReference != expected.ApprovalReference
            )
                throw Denied("AUTHENTICATION_TEMPLATE_CONFIGURATION_CHANGED");
            return expected;
        }
        catch (JsonException)
        {
            throw Denied("AUTHENTICATION_TEMPLATE_READBACK_INVALID");
        }
        catch (HttpRequestException)
        {
            throw Denied("AUTHENTICATION_TEMPLATE_READBACK_UNAVAILABLE");
        }
        catch (IOException)
        {
            throw Denied("AUTHENTICATION_TEMPLATE_READBACK_UNAVAILABLE");
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            throw Denied("AUTHENTICATION_TEMPLATE_READBACK_UNAVAILABLE");
        }
    }

    private static bool HasApprovedComponents(JsonElement template)
    {
        if (
            !template.TryGetProperty("components", out var components)
            || components.ValueKind != JsonValueKind.Array
        )
            return false;
        var values = components.EnumerateArray().ToArray();
        if (values.Length != 3)
            return false;
        var bodies = values.Where(value => Is(value, "type", "BODY")).ToArray();
        var footers = values.Where(value => Is(value, "type", "FOOTER")).ToArray();
        var buttonGroups = values.Where(value => Is(value, "type", "BUTTONS")).ToArray();
        if (
            bodies.Length != 1
            || !bodies[0].TryGetProperty("text", out var body)
            || body.ValueKind != JsonValueKind.String
            || !body.GetString()!.Contains("{{1}}", StringComparison.Ordinal)
            || TemplateVariable().Matches(body.GetString()!).Any(match => match.Value != "{{1}}")
            || !body.GetString()!
                .Contains("For your security, do not share this code.", StringComparison.Ordinal)
            || footers.Length != 1
            || !footers[0].TryGetProperty("text", out var footer)
            || footer.ValueKind != JsonValueKind.String
            || !Expiry().IsMatch(footer.GetString()!)
            || buttonGroups.Length != 1
            || !buttonGroups[0].TryGetProperty("buttons", out var buttons)
            || buttons.ValueKind != JsonValueKind.Array
            || buttons.GetArrayLength() != 1
        )
            return false;
        var button = buttons[0];
        return Is(button, "type", "URL")
            && button.TryGetProperty("url", out var url)
            && url.ValueKind == JsonValueKind.String
            && Uri.TryCreate(url.GetString(), UriKind.Absolute, out var address)
            && address.Scheme == "https"
            && address.Host == "www.whatsapp.com"
            && address.IsDefaultPort
            && address.UserInfo.Length == 0
            && address.AbsolutePath == "/otp/code/"
            && address
                .Query.TrimStart('?')
                .Split('&')
                .Contains("otp_type=COPY_CODE", StringComparer.Ordinal);
    }

    private static bool Is(JsonElement value, string name, string expected) =>
        value.ValueKind == JsonValueKind.Object
        && value.TryGetProperty(name, out var property)
        && property.ValueKind == JsonValueKind.String
        && property.GetString() == expected;

    private static IdentityDeliveryUnavailableException Denied(string code) => new(code);

    [GeneratedRegex("\\A[0-9]{1,32}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Identifier();

    [GeneratedRegex("\\A[a-z0-9_]{1,512}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Name();

    [GeneratedRegex("\\Aen(?:_[A-Z]{2})?\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Locale();

    [GeneratedRegex("\\A[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Reference();

    [GeneratedRegex("\\b15 minutes\\b", RegexOptions.CultureInvariant)]
    private static partial Regex Expiry();

    [GeneratedRegex("\\{\\{[0-9]+\\}\\}", RegexOptions.CultureInvariant)]
    private static partial Regex TemplateVariable();
}
