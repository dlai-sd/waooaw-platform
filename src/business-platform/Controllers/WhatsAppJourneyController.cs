// Implements: ADR-023 and work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §25.2 WC120-P2
// Implements: work-contracts/WC-121-demo-whatsapp-provider-enablement-work-component.md §5 WC121-C09-S09
// constitutional_basis: C-023, C-026, C-042, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http.Extensions;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Microsoft.Net.Http.Headers;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[AllowAnonymous]
[Route("api/v1/channels/whatsapp/webhook")]
public sealed class WhatsAppJourneyController(
    WhatsAppJourneyService service,
    IOptions<WhatsAppJourneyOptions> options,
    IOptions<Wc120ConversationOptions> conversationOptions,
    IWhatsAppCapabilityGate? capabilityGate = null,
    WhatsAppTenantExecutionScope? tenantExecution = null,
    IWhatsAppWebhookCredentials? webhookCredentials = null
) : ControllerBase
{
    private bool _legacyCompatibility;

    public WhatsAppJourneyController(WhatsAppJourneyService service)
        : this(
            service,
            Options.Create(
                new WhatsAppJourneyOptions
                {
                    VerificationEnabled = true,
                    CallbackAcceptanceEnabled = true,
                }
            ),
            Options.Create(new Wc120ConversationOptions { Enabled = true })
        )
    {
        _legacyCompatibility = true;
    }

    [HttpGet]
    public async Task<IActionResult> VerifyAsync(CancellationToken cancellationToken)
    {
        var preflight = VerifyCore(null, requireToken: false);
        if (preflight is not ContentResult)
            return preflight;
        try
        {
            var expected = webhookCredentials is null
                ? options.Value.VerifyToken
                : await webhookCredentials.ReadVerifyTokenAsync(cancellationToken);
            return VerifyCore(expected, requireToken: true);
        }
        catch (WhatsAppCapabilityUnavailableException)
        {
            return Problem(
                statusCode: StatusCodes.Status503ServiceUnavailable,
                title: "WHATSAPP_VERIFICATION_UNAVAILABLE"
            );
        }
    }

    [NonAction]
    public IActionResult Verify() => VerifyCore(options.Value.VerifyToken, requireToken: true);

    private IActionResult VerifyCore(string? expected, bool requireToken)
    {
        if (!options.Value.VerificationEnabled)
            return StatusCode(StatusCodes.Status503ServiceUnavailable);
        if (!HasExpectedCallbackHost())
            return Forbid();
        var target =
            HttpContext.Features.Get<IHttpRequestFeature>()?.RawTarget
            ?? Request.GetEncodedPathAndQuery();
        var mode = Request.Query["hub.mode"].ToString();
        var token = Request.Query["hub.verify_token"].ToString();
        var challenge = Request.Query["hub.challenge"].ToString();
        if (
            Encoding.UTF8.GetByteCount(target) > 8192
            || Request.Query.Count != 3
            || Request.Query.Keys.Any(key =>
                key != "hub.mode" && key != "hub.verify_token" && key != "hub.challenge"
            )
            || !HasOneBoundedParameter("hub.mode")
            || !HasOneBoundedParameter("hub.verify_token")
            || !HasOneBoundedParameter("hub.challenge")
            || !string.Equals(mode, "subscribe", StringComparison.Ordinal)
            || (
                requireToken
                && (
                    string.IsNullOrEmpty(expected)
                    || !CryptographicOperations.FixedTimeEquals(
                        Encoding.UTF8.GetBytes(token),
                        Encoding.UTF8.GetBytes(expected)
                    )
                )
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
        if (capabilityGate is not null)
        {
            var state = capabilityGate.Evaluate(DateTimeOffset.UtcNow);
            if (state.State != "ACTIVE")
                return Problem(
                    statusCode: StatusCodes.Status503ServiceUnavailable,
                    title: "WHATSAPP_CAPABILITY_INACTIVE"
                );
        }
        if (!HasExpectedCallbackHost())
            return Forbid();
        if (
            !_legacyCompatibility
            && (
                !MediaTypeHeaderValue.TryParse(Request.ContentType, out var mediaType)
                || !string.Equals(
                    mediaType.MediaType.Value,
                    "application/json",
                    StringComparison.OrdinalIgnoreCase
                )
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
            using var tenant = tenantExecution?.Begin();
            var receipt = await service.ReceiveAsync(
                body.ToArray(),
                signature,
                DateTimeOffset.UtcNow,
                cancellationToken
            );
            if (!_legacyCompatibility && webhookCredentials is not null)
                return Ok(new { status = "ACCEPTED" });
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
        catch (WhatsAppCapabilityUnavailableException)
        {
            return Problem(
                statusCode: StatusCodes.Status503ServiceUnavailable,
                title: "WHATSAPP_CAPABILITY_INACTIVE"
            );
        }
    }

    private bool HasOneBoundedParameter(string name) =>
        Request.Query.TryGetValue(name, out var values)
        && values.Count == 1
        && values[0] is { Length: > 0 } value
        && Encoding.UTF8.GetByteCount(value) <= 1024;

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
