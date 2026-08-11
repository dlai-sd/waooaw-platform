// Implements: ADR-023 and work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// constitutional_basis: C-023, C-026, C-042, C-059, C-063

using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[AllowAnonymous]
[Route("api/v1/whatsapp/webhook")]
public sealed class WhatsAppJourneyController(WhatsAppJourneyService service) : ControllerBase
{
    [HttpPost]
    public async Task<IActionResult> ReceiveAsync(CancellationToken cancellationToken)
    {
        using var reader = new StreamReader(Request.Body, Encoding.UTF8);
        var rawBody = await reader.ReadToEndAsync(cancellationToken);
        var signature = Request.Headers["X-Hub-Signature-256"].ToString();
        try
        {
            var receipt = await service.ReceiveAsync(rawBody, signature, DateTimeOffset.UtcNow, cancellationToken);
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
}