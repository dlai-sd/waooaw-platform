// Implements: ADR-023 and architecture/reference/components/identity-boundary.md §7.2
// constitutional_basis: C-023, C-026, C-042, C-059, C-063

using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

var builder = WebApplication.CreateBuilder(args);
var options = PhoneIdentityOptions.FromConfiguration(builder.Configuration);
builder.Services.AddSingleton(options);
builder.Services.AddHttpClient("BusinessPlatform", client =>
{
    client.BaseAddress = new Uri(options.BusinessPlatformBaseUrl);
    client.Timeout = TimeSpan.FromSeconds(15);
});
builder.Services.AddSingleton<PhoneIdentityVerifier>();

var app = builder.Build();
app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));
app.MapGet("/webhooks/meta", (HttpRequest request, PhoneIdentityOptions configured) =>
{
    var mode = request.Query["hub.mode"].ToString();
    var challenge = request.Query["hub.challenge"].ToString();
    var token = request.Query["hub.verify_token"].ToString();
    return mode == "subscribe"
        && CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(token), Encoding.UTF8.GetBytes(configured.VerifyToken))
        ? Results.Text(challenge)
        : Results.StatusCode(StatusCodes.Status403Forbidden);
});

app.MapPost("/webhooks/meta", async (
    HttpRequest request,
    PhoneIdentityVerifier verifier,
    IHttpClientFactory httpClientFactory,
    CancellationToken cancellationToken) =>
{
    using var reader = new StreamReader(request.Body, Encoding.UTF8);
    var rawBody = await reader.ReadToEndAsync(cancellationToken);
    var signature = request.Headers["X-Hub-Signature-256"].ToString();

    PhoneIdentityProof proof;
    try
    {
        proof = verifier.Verify(rawBody, signature, DateTimeOffset.UtcNow);
    }
    catch (PhoneIdentityVerificationException exception)
    {
        return Results.Problem(statusCode: exception.StatusCode, title: exception.Code);
    }

    var proofJson = JsonSerializer.Serialize(proof, PhoneIdentityJson.Options);
    using var message = new HttpRequestMessage(HttpMethod.Post, "/internal/identity/whatsapp-proofs")
    {
        Content = new StringContent(proofJson, Encoding.UTF8, "application/json"),
    };
    message.Headers.Add("X-WAOOAW-Phone-Signature", verifier.SignProof(proofJson));

    try
    {
        using var response = await httpClientFactory.CreateClient("BusinessPlatform")
            .SendAsync(message, cancellationToken);
        var responseBody = await response.Content.ReadAsStringAsync(cancellationToken);
        return Results.Content(responseBody, response.Content.Headers.ContentType?.MediaType ?? "application/json",
            statusCode: (int)response.StatusCode);
    }
    catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException)
    {
        return Results.Problem(statusCode: StatusCodes.Status503ServiceUnavailable,
            title: "PHONE_IDENTITY_DEPENDENCY_UNAVAILABLE");
    }
});

app.Run();

public sealed record PhoneIdentityOptions(
    string WebhookSecret,
    string VerifyToken,
    string PhoneHashKey,
    string InternalSigningKey,
    string InternalAudience,
    string BusinessPlatformBaseUrl)
{
    public static PhoneIdentityOptions FromConfiguration(IConfiguration configuration)
    {
        var options = new PhoneIdentityOptions(
            configuration["PhoneIdentity:WebhookSecret"] ?? string.Empty,
            configuration["PhoneIdentity:VerifyToken"] ?? string.Empty,
            configuration["PhoneIdentity:PhoneHashKey"] ?? string.Empty,
            configuration["PhoneIdentity:InternalSigningKey"] ?? string.Empty,
            configuration["PhoneIdentity:InternalAudience"] ?? string.Empty,
            configuration["PhoneIdentity:BusinessPlatformBaseUrl"] ?? string.Empty);
        if (options.WebhookSecret.Length < 32 || options.VerifyToken.Length < 16
            || options.PhoneHashKey.Length < 32 || options.InternalSigningKey.Length < 32)
            throw new InvalidOperationException("Phone Identity keys and verification token are missing or too short.");
        if (string.IsNullOrWhiteSpace(options.InternalAudience)
            || !Uri.TryCreate(options.BusinessPlatformBaseUrl, UriKind.Absolute, out _))
            throw new InvalidOperationException("Phone Identity audience and Business Platform URL are required.");
        return options;
    }
}

public sealed record PhoneIdentityProof(
    string MessageId,
    string PhoneSubjectHash,
    string Text,
    string? RiskTier,
    string Audience,
    string AuthenticationAssurance,
    DateTimeOffset SentAt,
    DateTimeOffset VerifiedAt,
    DateTimeOffset ExpiresAt,
    Guid CorrelationId);

public sealed class PhoneIdentityVerificationException(int statusCode, string code) : Exception(code)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
}

public sealed partial class PhoneIdentityVerifier(PhoneIdentityOptions options)
{
    private readonly byte[] _webhookSecret = Encoding.UTF8.GetBytes(options.WebhookSecret);
    private readonly byte[] _phoneHashKey = Encoding.UTF8.GetBytes(options.PhoneHashKey);
    private readonly byte[] _internalSigningKey = Encoding.UTF8.GetBytes(options.InternalSigningKey);
    private readonly ConcurrentDictionary<string, DateTimeOffset> _recentMessages = new(StringComparer.Ordinal);

    public PhoneIdentityProof Verify(string rawBody, string signatureHeader, DateTimeOffset receivedAt)
    {
        VerifySignature(rawBody, signatureHeader);
        MetaInbound inbound;
        try
        {
            inbound = JsonSerializer.Deserialize<MetaInbound>(rawBody, PhoneIdentityJson.Options)
                ?? throw new JsonException();
        }
        catch (JsonException)
        {
            throw new PhoneIdentityVerificationException(400, "WHATSAPP_PAYLOAD_INVALID");
        }

        if (string.IsNullOrWhiteSpace(inbound.MessageId) || string.IsNullOrWhiteSpace(inbound.Text)
            || !E164().IsMatch(inbound.From))
            throw new PhoneIdentityVerificationException(400, "WHATSAPP_PAYLOAD_INVALID");

        DateTimeOffset sentAt;
        try
        {
            sentAt = DateTimeOffset.FromUnixTimeSeconds(inbound.Timestamp);
        }
        catch (ArgumentOutOfRangeException)
        {
            throw new PhoneIdentityVerificationException(400, "WHATSAPP_TIMESTAMP_INVALID");
        }
        if (sentAt > receivedAt.AddSeconds(30)
            || receivedAt - sentAt > TimeSpan.FromMinutes(5))
            throw new PhoneIdentityVerificationException(409, "WHATSAPP_REPLAY_WINDOW_EXCEEDED");

        foreach (var expired in _recentMessages.Where(value => value.Value <= receivedAt).Select(value => value.Key))
            _recentMessages.TryRemove(expired, out _);
        if (!_recentMessages.TryAdd(inbound.MessageId, receivedAt.AddHours(24)))
            throw new PhoneIdentityVerificationException(409, "WHATSAPP_MESSAGE_REPLAYED");

        return new PhoneIdentityProof(
            inbound.MessageId,
            HmacHex(_phoneHashKey, inbound.From),
            inbound.Text,
            inbound.RiskTier,
            options.InternalAudience,
            "AAL1_CHANNEL",
            sentAt,
            receivedAt,
            receivedAt.AddMinutes(5),
            Guid.NewGuid());
    }

    public string SignProof(string proofJson) =>
        $"sha256={HmacHex(_internalSigningKey, proofJson)}";

    private void VerifySignature(string rawBody, string signatureHeader)
    {
        if (!signatureHeader.StartsWith("sha256=", StringComparison.OrdinalIgnoreCase))
            throw new PhoneIdentityVerificationException(403, "WHATSAPP_SIGNATURE_INVALID");
        try
        {
            var supplied = Convert.FromHexString(signatureHeader[7..]);
            var expected = HMACSHA256.HashData(_webhookSecret, Encoding.UTF8.GetBytes(rawBody));
            if (supplied.Length != expected.Length
                || !CryptographicOperations.FixedTimeEquals(supplied, expected))
                throw new PhoneIdentityVerificationException(403, "WHATSAPP_SIGNATURE_INVALID");
        }
        catch (FormatException)
        {
            throw new PhoneIdentityVerificationException(403, "WHATSAPP_SIGNATURE_INVALID");
        }
    }

    private static string HmacHex(byte[] key, string value) =>
        Convert.ToHexStringLower(HMACSHA256.HashData(key, Encoding.UTF8.GetBytes(value)));

    [GeneratedRegex("^\\+[1-9][0-9]{7,14}$", RegexOptions.CultureInvariant)]
    private static partial Regex E164();

    private sealed record MetaInbound(string MessageId, long Timestamp, string From, string Text, string? RiskTier);
}

public static class PhoneIdentityJson
{
    public static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web);
}

public partial class Program;
