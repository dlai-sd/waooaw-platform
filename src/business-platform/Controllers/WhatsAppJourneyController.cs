// Implements: ADR-023 and work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// constitutional_basis: C-023, C-026, C-042, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[AllowAnonymous]
[Route("api/v1/channels/whatsapp/webhook")]
public sealed class WhatsAppJourneyController(
    WhatsAppJourneyService service,
    IOptions<WhatsAppJourneyOptions> options,
    IOptions<Wc120ConversationOptions> conversationOptions
) : ControllerBase
{
    private bool _legacyCompatibility;

    public WhatsAppJourneyController(WhatsAppJourneyService service)
        : this(
            service,
            Options.Create(new WhatsAppJourneyOptions { CallbackAcceptanceEnabled = true }),
            Options.Create(new Wc120ConversationOptions { Enabled = true })
        )
    {
        _legacyCompatibility = true;
    }

    [HttpGet]
    public IActionResult Verify()
    {
        if (!options.Value.CallbackAcceptanceEnabled || !conversationOptions.Value.Enabled)
            return StatusCode(StatusCodes.Status503ServiceUnavailable);
        if (!HasExpectedCallbackHost())
            return Forbid();
        var mode = Request.Query["hub.mode"].ToString();
        var token = Request.Query["hub.verify_token"].ToString();
        var challenge = Request.Query["hub.challenge"].ToString();
        if (
            Request.QueryString.Value?.Length > 8192
            || mode.Length > 1024
            || token.Length > 1024
            || challenge.Length > 1024
            || !string.Equals(mode, "subscribe", StringComparison.Ordinal)
            || string.IsNullOrEmpty(options.Value.VerifyToken)
            || !CryptographicOperations.FixedTimeEquals(
                Encoding.UTF8.GetBytes(token),
                Encoding.UTF8.GetBytes(options.Value.VerifyToken)
            )
        )
            return Unauthorized();
        return Content(challenge, "text/plain", Encoding.UTF8);
    }

    [HttpPost]
    public async Task<IActionResult> ReceiveAsync(CancellationToken cancellationToken)
    {
        if (!options.Value.CallbackAcceptanceEnabled || !conversationOptions.Value.Enabled)
            return StatusCode(StatusCodes.Status503ServiceUnavailable);
        if (!HasExpectedCallbackHost())
            return Forbid();
        if (
            !_legacyCompatibility
            && !(
                Request.ContentType?.StartsWith(
                    "application/json",
                    StringComparison.OrdinalIgnoreCase
                ) ?? false
            )
        )
            return StatusCode(StatusCodes.Status415UnsupportedMediaType);
        if (
            !_legacyCompatibility
            && Request.Headers.TryGetValue("Content-Encoding", out var encoding)
            && !string.Equals(encoding.ToString(), "identity", StringComparison.OrdinalIgnoreCase)
        )
            return StatusCode(StatusCodes.Status415UnsupportedMediaType);
        if (Request.ContentLength > options.Value.MaxBodyBytes)
            return StatusCode(StatusCodes.Status413PayloadTooLarge);

        using var body = new MemoryStream();
        var buffer = new byte[8192];
        while (true)
        {
            var read = await Request.Body.ReadAsync(buffer, cancellationToken);
            if (read == 0)
                break;
            if (body.Length + read > options.Value.MaxBodyBytes)
                return StatusCode(StatusCodes.Status413PayloadTooLarge);
            await body.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
        }
        var signature = Request.Headers["X-Hub-Signature-256"].ToString();
        try
        {
            var receipt = await service.ReceiveAsync(
                body.ToArray(),
                signature,
                DateTimeOffset.UtcNow,
                cancellationToken
            );
            return Ok(
                new
                {
                    messageId = receipt.MessageId,
                    status = receipt.Status,
                    journeyStage = receipt.JourneyStage,
                    reply = receipt.Reply,
                    replayed = receipt.Replayed,
                }
            );
        }
        catch (WhatsAppWebhookException exception)
        {
            return Problem(statusCode: exception.StatusCode, title: exception.Code);
        }
    }

    private bool HasExpectedCallbackHost() =>
        _legacyCompatibility
        || (
            !string.IsNullOrWhiteSpace(options.Value.CallbackHost)
            && string.Equals(
                Request.Host.Host,
                options.Value.CallbackHost,
                StringComparison.OrdinalIgnoreCase
            )
        );
}
