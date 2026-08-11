// Implements: ADR-023 and work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// constitutional_basis: C-023, C-026, C-042, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppJourneyOptions
{
    public string WebhookSecret { get; set; } = string.Empty;
    public string TenantTokenKey { get; set; } = string.Empty;
}

public sealed record WhatsAppJourneyReceipt(
    string MessageId,
    string Status,
    string JourneyStage,
    string Reply,
    bool Replayed,
    string InternalTenantToken);

public sealed class WhatsAppWebhookException(int statusCode, string code) : Exception(code)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
}

public sealed partial class WhatsAppJourneyService
{
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _dbFactory;
    private readonly IWhatsAppRegistrationEvidenceGateway _evidenceGateway;
    private readonly byte[] _webhookSecret;
    private readonly byte[] _tokenKey;

    public WhatsAppJourneyService(
        IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
        IWhatsAppRegistrationEvidenceGateway evidenceGateway,
        IOptions<WhatsAppJourneyOptions> options)
    {
        _dbFactory = dbFactory;
        _evidenceGateway = evidenceGateway;
        _webhookSecret = RequireKey(options.Value.WebhookSecret, nameof(options.Value.WebhookSecret));
        _tokenKey = RequireKey(options.Value.TenantTokenKey, nameof(options.Value.TenantTokenKey));
    }

    public async Task<WhatsAppJourneyReceipt> ReceiveAsync(
        string rawBody,
        string signatureHeader,
        DateTimeOffset receivedAt,
        CancellationToken cancellationToken)
    {
        VerifySignature(rawBody, signatureHeader);
        WhatsAppInbound inbound;
        try
        {
            inbound = JsonSerializer.Deserialize<WhatsAppInbound>(rawBody, new JsonSerializerOptions(JsonSerializerDefaults.Web))
                ?? throw new JsonException();
        }
        catch (JsonException)
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_PAYLOAD_INVALID");
        }
        if (string.IsNullOrWhiteSpace(inbound.MessageId) || string.IsNullOrWhiteSpace(inbound.Text)
            || !E164().IsMatch(inbound.From))
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_PAYLOAD_INVALID");
        }
        DateTimeOffset sentAt;
        try
        {
            sentAt = DateTimeOffset.FromUnixTimeSeconds(inbound.Timestamp);
        }
        catch (ArgumentOutOfRangeException)
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_TIMESTAMP_INVALID");
        }
        if ((receivedAt - sentAt).Duration() > TimeSpan.FromMinutes(5))
        {
            throw new WhatsAppWebhookException(409, "WHATSAPP_REPLAY_WINDOW_EXCEEDED");
        }

        var phoneHmac = HmacHex(_webhookSecret, inbound.From);
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var existingReceipt = await db.WhatsAppMessageReceipts
            .SingleOrDefaultAsync(item => item.MessageId == inbound.MessageId, cancellationToken);
        if (existingReceipt is not null && existingReceipt.ExpiresAt > receivedAt)
        {
            return new(inbound.MessageId, "DUPLICATE", "UNKNOWN",
                "This message was already received.", true, string.Empty);
        }
        if (existingReceipt is not null)
        {
            db.WhatsAppMessageReceipts.Remove(existingReceipt);
            await db.SaveChangesAsync(cancellationToken);
        }

        var contact = await db.WhatsAppJourneyContacts.SingleOrDefaultAsync(
            item => item.PhoneHmac == phoneHmac, cancellationToken);
        if (contact is null)
        {
            contact = new WhatsAppJourneyContact
            {
                TenantId = Guid.NewGuid(),
                PhoneHmac = phoneHmac,
                OptedInAt = receivedAt,
                LastInboundAt = receivedAt,
            };
            await _evidenceGateway.RecordAsync(
                contact.TenantId, inbound.MessageId, phoneHmac, receivedAt, cancellationToken);
            db.WhatsAppJourneyContacts.Add(contact);
        }
        contact.LastInboundAt = receivedAt;

        var riskTier = inbound.RiskTier?.Trim().ToUpperInvariant() ?? "TIER_1_LOW_RISK";
        var confirmation = inbound.Text.Trim().Equals("YES", StringComparison.OrdinalIgnoreCase)
            || inbound.Text.Trim().Equals("CONFIRM", StringComparison.OrdinalIgnoreCase);
        string status;
        string reply;
        if (riskTier == "TIER_4_CONSEQUENTIAL")
        {
            contact.PendingMediumRiskConfirmation = false;
            status = "SECURE_PORTAL_REQUIRED";
            reply = "Contracts, hiring, cancellation, and payment cannot be accepted or initiated in WhatsApp. Review the exact contract and current payment or activation status in the secure portal: /relationships. Payment details are entered only on Razorpay. You may choose Hire, Not now, Cancel, or Exit there.";
        }
        else if (riskTier == "TIER_3_HIGH_RISK")
        {
            status = "PORTAL_STEP_UP_REQUIRED";
            reply = "This high-risk action cannot be authorized by phone identity. Continue in the secure portal.";
        }
        else if (riskTier == "TIER_2_MEDIUM_RISK" && (!contact.PendingMediumRiskConfirmation || !confirmation))
        {
            contact.PendingMediumRiskConfirmation = true;
            status = "CONFIRMATION_REQUIRED";
            reply = "Reply YES to confirm this action. Reply NO or ignore to cancel.";
        }
        else
        {
            contact.PendingMediumRiskConfirmation = false;
            status = "ACCEPTED";
            (contact.JourneyStage, reply) = Present(inbound.Text);
        }

        var (tenantToken, tokenHash, tokenExpiresAt) = IssueTenantToken(contact.TenantId, inbound.From, receivedAt);
        db.WhatsAppMessageReceipts.Add(new WhatsAppMessageReceipt
        {
            MessageId = inbound.MessageId,
            TenantId = contact.TenantId,
            SessionTokenHash = tokenHash,
            SessionExpiresAt = tokenExpiresAt,
            ReceivedAt = receivedAt,
            ExpiresAt = receivedAt.AddHours(24),
        });
        await db.SaveChangesAsync(cancellationToken);
        return new(inbound.MessageId, status, contact.JourneyStage, reply, false, tenantToken);
    }

    private void VerifySignature(string rawBody, string signatureHeader)
    {
        if (!signatureHeader.StartsWith("sha256=", StringComparison.OrdinalIgnoreCase))
            throw new WhatsAppWebhookException(403, "WHATSAPP_SIGNATURE_INVALID");
        byte[] supplied;
        try
        {
            supplied = Convert.FromHexString(signatureHeader[7..]);
        }
        catch (FormatException)
        {
            throw new WhatsAppWebhookException(403, "WHATSAPP_SIGNATURE_INVALID");
        }
        var expected = HMACSHA256.HashData(_webhookSecret, Encoding.UTF8.GetBytes(rawBody));
        if (supplied.Length != expected.Length || !CryptographicOperations.FixedTimeEquals(supplied, expected))
            throw new WhatsAppWebhookException(403, "WHATSAPP_SIGNATURE_INVALID");
    }

    private (string Token, string TokenHash, DateTimeOffset ExpiresAt) IssueTenantToken(
        Guid tenantId,
        string phone,
        DateTimeOffset now)
    {
        const string header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9";
        var expiresAt = now.AddMinutes(30);
        var payload = Base64Url(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new
        {
            sub = tenantId,
            phone,
            iss = "waooaw-phone-identity",
            iat = now.ToUnixTimeSeconds(),
            exp = expiresAt.ToUnixTimeSeconds(),
        })));
        var signingInput = $"{header}.{payload}";
        var token = $"{signingInput}.{Base64Url(HMACSHA256.HashData(_tokenKey, Encoding.UTF8.GetBytes(signingInput)))}";
        return (token, Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(token))), expiresAt);
    }

    private static (string Stage, string Reply) Present(string text)
    {
        var normalized = text.Trim().ToUpperInvariant();
        if (normalized.Contains("TRIAL", StringComparison.Ordinal))
            return ("TRIAL", "Your evaluation plan spans 14 calendar days. It uses local inference and cannot publish, spend, message third parties, or mutate providers.");
        if (normalized.Contains("CONFIG", StringComparison.Ordinal) || normalized.Contains("BUDGET", StringComparison.Ordinal))
            return ("CONFIGURE", "Review goals, measures, skills, budget, cadence, Decision Space, and stop conditions one item at a time.");
        if (normalized.Contains("NAME", StringComparison.Ordinal) || normalized.Contains("LOCATION", StringComparison.Ordinal))
            return ("CONTEXT", "I will confirm this context and ask at most one new decision-relevant question next.");
        if (normalized.Contains("?", StringComparison.Ordinal) || normalized.StartsWith("INTERVIEW", StringComparison.Ordinal))
            return ("INTERVIEW", "Your question is queued for a sourced answer that distinguishes fact, inference, recommendation, and limitation.");
        if (normalized.Contains("SKILL", StringComparison.Ordinal) || normalized.Contains("LIMIT", StringComparison.Ordinal))
            return ("DISCLOSURE", "I can present skills, limitations, authority needs, rights, evidence posture, trial boundaries, and indicative price before trial.");
        return ("DISCOVER", "Tell me the business outcome you need. I will compare lawful suitable professionals and explain why they fit.");
    }

    private static byte[] RequireKey(string value, string name) =>
        value.Length >= 32 ? Encoding.UTF8.GetBytes(value) : throw new InvalidOperationException($"WhatsApp:{name} must contain at least 32 characters.");
    private static string HmacHex(byte[] key, string value) =>
        Convert.ToHexStringLower(HMACSHA256.HashData(key, Encoding.UTF8.GetBytes(value)));
    private static string Base64Url(byte[] value) => Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    [GeneratedRegex("^\\+[1-9][0-9]{7,14}$", RegexOptions.CultureInvariant)]
    private static partial Regex E164();

    private sealed record WhatsAppInbound(string MessageId, long Timestamp, string From, string Text, string? RiskTier);
}