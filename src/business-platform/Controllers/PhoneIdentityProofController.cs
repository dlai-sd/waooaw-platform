// Implements: architecture/reference/components/identity-boundary.md §7.2
// constitutional_basis: C-023, C-026, C-042, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed class PhoneIdentityAdapterOptions
{
    public const int MinimumKeyLength = 32;
    public string SigningKey { get; set; } = string.Empty;
    public string Audience { get; set; } = string.Empty;
}

[ApiController]
[AllowAnonymous]
[Route("internal/identity/whatsapp-proofs")]
public sealed class PhoneIdentityProofController(
    WhatsAppJourneyService journeyService,
    IOptions<PhoneIdentityAdapterOptions> options) : ControllerBase
{
    private readonly byte[] _signingKey = RequireKey(options.Value.SigningKey);
    private readonly string _audience = RequireAudience(options.Value.Audience);

    [HttpPost]
    public async Task<IActionResult> ReceiveAsync(CancellationToken cancellationToken)
    {
        using var reader = new StreamReader(Request.Body, Encoding.UTF8);
        var rawBody = await reader.ReadToEndAsync(cancellationToken);
        var suppliedSignature = Request.Headers["X-WAOOAW-Phone-Signature"].ToString();
        if (!IsValidSignature(rawBody, suppliedSignature))
            return Problem(statusCode: 403, title: "PHONE_IDENTITY_SIGNATURE_INVALID");

        VerifiedPhoneIdentityProof? proof;
        try
        {
            proof = JsonSerializer.Deserialize<VerifiedPhoneIdentityProof>(
                rawBody, new JsonSerializerOptions(JsonSerializerDefaults.Web));
        }
        catch (JsonException)
        {
            return Problem(statusCode: 400, title: "PHONE_IDENTITY_PROOF_INVALID");
        }

        if (proof is null)
            return Problem(statusCode: 400, title: "PHONE_IDENTITY_PROOF_INVALID");
        if (!string.Equals(proof.Audience, _audience, StringComparison.Ordinal)
            || !string.Equals(proof.AuthenticationAssurance, "AAL1_CHANNEL", StringComparison.Ordinal))
            return Problem(statusCode: 403, title: "PHONE_IDENTITY_PROOF_INVALID");
        var now = DateTimeOffset.UtcNow;
        if (proof.VerifiedAt < proof.SentAt
            || proof.VerifiedAt > now.AddSeconds(30)
            || proof.ExpiresAt <= now
            || proof.ExpiresAt <= proof.VerifiedAt
            || proof.ExpiresAt - proof.VerifiedAt > TimeSpan.FromMinutes(5))
            return Problem(statusCode: 400, title: "PHONE_IDENTITY_PROOF_INVALID");

        try
        {
            var receipt = await journeyService.ReceiveVerifiedAsync(proof, cancellationToken);
            return Ok(new
            {
                messageId = receipt.MessageId,
                status = receipt.Status,
                journeyStage = receipt.JourneyStage,
                reply = receipt.Reply,
                replayed = receipt.Replayed,
            });
        }
        catch (WhatsAppWebhookException exception)
        {
            return Problem(statusCode: exception.StatusCode, title: exception.Code);
        }
    }

    private bool IsValidSignature(string rawBody, string suppliedSignature)
    {
        if (!suppliedSignature.StartsWith("sha256=", StringComparison.OrdinalIgnoreCase))
            return false;
        try
        {
            var supplied = Convert.FromHexString(suppliedSignature[7..]);
            var expected = HMACSHA256.HashData(_signingKey, Encoding.UTF8.GetBytes(rawBody));
            return supplied.Length == expected.Length
                && CryptographicOperations.FixedTimeEquals(supplied, expected);
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static byte[] RequireKey(string value) =>
        value.Length >= PhoneIdentityAdapterOptions.MinimumKeyLength
            ? Encoding.UTF8.GetBytes(value)
            : throw new InvalidOperationException(
                $"PhoneIdentity:SigningKey must contain at least {PhoneIdentityAdapterOptions.MinimumKeyLength} characters.");

    private static string RequireAudience(string value) =>
        !string.IsNullOrWhiteSpace(value)
            ? value
            : throw new InvalidOperationException("PhoneIdentity:Audience is required.");
}
