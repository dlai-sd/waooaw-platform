// Implements: WC-084 Customer Portal Solution Contract section 4.5
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record CustomerAlertMutationRequest(string SchemaVersion, string ExpectedAlertVersion);

[ApiController]
[Authorize]
[Route("api/v1/notifications/alerts")]
public sealed class NotificationsController(CustomerAlertService alerts) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> ListAsync(
        [FromQuery] string? cursor, [FromQuery] int limit = 20,
        CancellationToken cancellationToken = default)
    {
        if (!TryGetTenantId(out var tenantId)) return Unauthorized();
        if (limit is < 1 or > 100) return Problem(statusCode: 400, title: "Invalid alerts query");
        try
        {
            var page = await alerts.ListAsync(tenantId, cursor, limit, cancellationToken);
            return Ok(new { schemaVersion = "1.0.0", producedAt = DateTimeOffset.UtcNow,
                nextCursor = page.NextCursor, items = page.Items.Select(ToResponse).ToArray() });
        }
        catch (ArgumentException exception)
        {
            return Problem(statusCode: 400, title: "Invalid alerts cursor", detail: exception.Message);
        }
    }

    [HttpPost("{alertId:guid}/read")]
    public Task<IActionResult> MarkReadAsync(
        Guid alertId, [FromBody] CustomerAlertMutationRequest request,
        [FromHeader(Name = "Idempotency-Key")] string? idempotencyKey,
        CancellationToken cancellationToken) =>
        MutateAsync(alertId, request, idempotencyKey, "MARK_READ", "READ", cancellationToken);

    [HttpPost("{alertId:guid}/acknowledge")]
    public Task<IActionResult> AcknowledgeAsync(
        Guid alertId, [FromBody] CustomerAlertMutationRequest request,
        [FromHeader(Name = "Idempotency-Key")] string? idempotencyKey,
        CancellationToken cancellationToken) =>
        MutateAsync(alertId, request, idempotencyKey, "ACKNOWLEDGE", "ACKNOWLEDGED", cancellationToken);

    private async Task<IActionResult> MutateAsync(
        Guid alertId, CustomerAlertMutationRequest request, string? idempotencyKey,
        string operation, string targetState, CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId)) return Unauthorized();
        if (request.SchemaVersion != "1.0.0" || string.IsNullOrWhiteSpace(request.ExpectedAlertVersion)
            || !Guid.TryParse(idempotencyKey, out var parsedKey))
            return Problem(statusCode: 400, title: "Invalid alert mutation");
        var actor = User.FindFirstValue(ClaimTypes.NameIdentifier) ?? User.FindFirstValue("sub") ?? "unknown";
        var hash = Convert.ToHexStringLower(SHA256.HashData(
            Encoding.UTF8.GetBytes(JsonSerializer.Serialize(request))));
        try
        {
            return Ok(ToResponse(await alerts.SetReadStateAsync(
                tenantId, alertId, actor, parsedKey, operation, request.ExpectedAlertVersion,
                hash, targetState, cancellationToken)));
        }
        catch (KeyNotFoundException) { return NotFound(); }
        catch (CustomerAlertConflictException)
        {
            return Problem(statusCode: 409, title: "Alert version or idempotency conflict");
        }
    }

    private bool TryGetTenantId(out Guid tenantId)
    {
        tenantId = default;
        return HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var value)
            && value is string text && Guid.TryParse(text, out tenantId);
    }

    private static object ToResponse(CustomerAlert alert) => new
    {
        alertId = alert.AlertId,
        version = CustomerAlertService.Version(alert),
        alertType = alert.AlertType,
        severity = alert.Severity,
        source = alert.Source,
        relationshipId = alert.RelationshipId,
        occurredAt = alert.OccurredAt,
        dueMeaning = alert.DueMeaning,
        readState = alert.ReadState,
        destination = new { surface = alert.DestinationSurface,
            relationshipId = alert.RelationshipId, subjectId = alert.DestinationSubjectId },
        availableAction = alert.AvailableAction,
    };
}