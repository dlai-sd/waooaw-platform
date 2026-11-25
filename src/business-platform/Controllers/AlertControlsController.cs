// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R007
// Constitutional basis: C-005, C-007, C-023, C-026, C-059, C-063
// IB: IB-171

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Alerts;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record AlertSnoozeRequest(
    string SchemaVersion,
    string ExpectedAlertVersion,
    DateTimeOffset Until
);

public sealed record AlertCategoryMuteRequest(string SchemaVersion, bool Muted);

/// <summary>
/// The customer's alert controls (alerts-oversight.openapi.yaml): one inbox across agents with a per-agent filter,
/// snooze, and per-category mute. Floor alerts (Emergency Stop, authority and safety) can be neither snoozed nor muted.
/// </summary>
[ApiController]
[Authorize]
[Route("api/v1/alert-controls")]
public sealed class AlertControlsController(CustomerAlertService alerts, TimeProvider clock)
    : ControllerBase
{
    [HttpGet("alerts")]
    public async Task<IActionResult> ListAsync(
        [FromQuery] Guid? relationshipId,
        [FromQuery] bool includeSnoozed = false,
        [FromQuery] int limit = 50,
        CancellationToken cancellationToken = default
    )
    {
        if (!TryGetTenantId(out var tenantId))
            return Unauthorized();
        if (limit is < 1 or > 100)
            return Problem(statusCode: 400, title: "Invalid alerts query");
        var items = await alerts.ListInboxAsync(
            tenantId,
            relationshipId,
            includeSnoozed,
            limit,
            clock.GetUtcNow(),
            cancellationToken
        );
        return Ok(
            new
            {
                schemaVersion = "1.0.0",
                policyVersion = AlertPolicy.Version,
                items = items.Select(ToResponse).ToArray(),
            }
        );
    }

    [HttpPost("alerts/{alertId:guid}/snooze")]
    public async Task<IActionResult> SnoozeAsync(
        Guid alertId,
        [FromBody] AlertSnoozeRequest request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetTenantId(out var tenantId))
            return Unauthorized();
        if (
            request.SchemaVersion != "1.0.0"
            || string.IsNullOrWhiteSpace(request.ExpectedAlertVersion)
        )
            return Problem(statusCode: 400, title: "Invalid alert snooze");
        try
        {
            return Ok(
                ToResponse(
                    await alerts.SnoozeAsync(
                        tenantId,
                        alertId,
                        request.ExpectedAlertVersion,
                        request.Until,
                        clock.GetUtcNow(),
                        cancellationToken
                    )
                )
            );
        }
        catch (ArgumentOutOfRangeException)
        {
            return Problem(statusCode: 400, title: "Invalid alert snooze");
        }
        catch (KeyNotFoundException)
        {
            return NotFound();
        }
        catch (AlertNotMutableException)
        {
            return Conflict(new { code = "ALERT_CLASS_NOT_MUTABLE" });
        }
        catch (CustomerAlertConflictException)
        {
            return Problem(statusCode: 409, title: "Alert version conflict");
        }
    }

    [HttpGet("categories")]
    public async Task<IActionResult> ListCategoriesAsync(CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId))
            return Unauthorized();
        var mutes = await alerts.ListMutesAsync(tenantId, cancellationToken);
        return Ok(
            new
            {
                schemaVersion = "1.0.0",
                floorCategories = AlertPolicy.FloorCategories.Order().ToArray(),
                items = mutes.Select(value => new
                {
                    category = value.Category,
                    muted = value.Muted,
                    updatedAt = value.UpdatedAt,
                }),
            }
        );
    }

    [HttpPut("categories/{category}")]
    public async Task<IActionResult> SetCategoryAsync(
        string category,
        [FromBody] AlertCategoryMuteRequest request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetTenantId(out var tenantId))
            return Unauthorized();
        if (request.SchemaVersion != "1.0.0")
            return Problem(statusCode: 400, title: "Invalid category mute");
        var actor =
            User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub")
            ?? "unknown";
        try
        {
            var row = await alerts.SetMuteAsync(
                tenantId,
                category,
                request.Muted,
                actor,
                clock.GetUtcNow(),
                cancellationToken
            );
            return Ok(
                new
                {
                    category = row.Category,
                    muted = row.Muted,
                    updatedAt = row.UpdatedAt,
                }
            );
        }
        catch (ArgumentException)
        {
            return Problem(statusCode: 400, title: "Invalid category mute");
        }
        catch (AlertNotMutableException)
        {
            return Conflict(new { code = "ALERT_CLASS_NOT_MUTABLE" });
        }
    }

    private bool TryGetTenantId(out Guid tenantId)
    {
        tenantId = default;
        return HttpContext.Items.TryGetValue(
                TenantIsolationMiddleware.TenantIdItemKey,
                out var value
            )
            && value is string text
            && Guid.TryParse(text, out tenantId);
    }

    private static object ToResponse(CustomerAlert alert) =>
        new
        {
            alertId = alert.AlertId,
            version = CustomerAlertService.Version(alert),
            alertClass = alert.AlertClass,
            category = alert.Category,
            severity = alert.Severity,
            source = alert.Source,
            relationshipId = alert.RelationshipId,
            occurredAt = alert.OccurredAt,
            dueMeaning = alert.DueMeaning,
            readState = alert.ReadState,
            snoozedUntil = alert.SnoozedUntil,
            mutable = AlertPolicy.IsMutable(alert.AlertClass),
            destination = new
            {
                surface = alert.DestinationSurface,
                relationshipId = alert.RelationshipId,
                subjectId = alert.DestinationSubjectId,
            },
            availableAction = alert.AvailableAction,
        };
}
