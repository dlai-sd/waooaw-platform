// Implements: WC-084 Customer Portal Solution Contract section 4.5
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class CustomerAlertControllerTests
{
    [Fact]
    public async Task ListIsTenantBoundAndServerOrdered()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.CustomerAlerts.AddRange(
                Alert(tenantId, DateTimeOffset.UtcNow.AddMinutes(-1), "LOW"),
                Alert(tenantId, DateTimeOffset.UtcNow, "HIGH"),
                Alert(Guid.NewGuid(), DateTimeOffset.UtcNow.AddMinutes(1), "CRITICAL"));
            await db.SaveChangesAsync();
        }
        var controller = Controller(factory, tenantId);

        var result = Assert.IsType<OkObjectResult>(await controller.ListAsync(null, 20));
        var items = JsonSerializer.SerializeToElement(result.Value).GetProperty("items").EnumerateArray().ToArray();

        Assert.Equal(2, items.Length);
        Assert.Equal("HIGH", items[0].GetProperty("severity").GetString());
        Assert.Equal("LOW", items[1].GetProperty("severity").GetString());
    }

    [Fact]
    public async Task MutationsReplayConflictAndNeverDowngradeAcknowledgedState()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid();
        var alert = Alert(tenantId, DateTimeOffset.UtcNow, "HIGH");
        await using (var db = factory.CreateDbContext())
        {
            db.CustomerAlerts.Add(alert);
            await db.SaveChangesAsync();
        }
        var controller = Controller(factory, tenantId);
        var acknowledgeKey = Guid.NewGuid().ToString();
        var request = new CustomerAlertMutationRequest("1.0.0", "alert-1");

        var acknowledged = Assert.IsType<OkObjectResult>(await controller.AcknowledgeAsync(
            alert.AlertId, request, acknowledgeKey, CancellationToken.None));
        Assert.Equal("ACKNOWLEDGED", JsonSerializer.SerializeToElement(acknowledged.Value).GetProperty("readState").GetString());
        Assert.IsType<OkObjectResult>(await controller.AcknowledgeAsync(
            alert.AlertId, request, acknowledgeKey, CancellationToken.None));

        var conflict = Assert.IsType<ObjectResult>(await controller.AcknowledgeAsync(
            alert.AlertId, request with { ExpectedAlertVersion = "alert-99" }, acknowledgeKey, CancellationToken.None));
        Assert.Equal(409, conflict.StatusCode);

        var read = Assert.IsType<OkObjectResult>(await controller.MarkReadAsync(
            alert.AlertId, new CustomerAlertMutationRequest("1.0.0", "alert-2"),
            Guid.NewGuid().ToString(), CancellationToken.None));
        Assert.Equal("ACKNOWLEDGED", JsonSerializer.SerializeToElement(read.Value).GetProperty("readState").GetString());
    }

    [Fact]
    public async Task MutationDoesNotRevealCrossTenantAlert()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var alert = Alert(Guid.NewGuid(), DateTimeOffset.UtcNow, "LOW");
        await using (var db = factory.CreateDbContext())
        {
            db.CustomerAlerts.Add(alert);
            await db.SaveChangesAsync();
        }

        var result = await Controller(factory, Guid.NewGuid()).MarkReadAsync(
            alert.AlertId, new CustomerAlertMutationRequest("1.0.0", "alert-1"),
            Guid.NewGuid().ToString(), CancellationToken.None);

        Assert.IsType<NotFoundResult>(result);
    }

    private static NotificationsController Controller(InMemoryEmploymentRelationshipFactory factory, Guid tenantId)
    {
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim(ClaimTypes.NameIdentifier, "customer-subject")], "Test")),
        };
        context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        return new NotificationsController(new CustomerAlertService(factory))
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
    }

    private static CustomerAlert Alert(Guid tenantId, DateTimeOffset occurredAt, string severity) => new()
    {
        TenantId = tenantId,
        AlertType = severity == "HIGH" ? "ACTIONABLE" : "INFORMATIONAL",
        Severity = severity,
        Source = "SYSTEM",
        OccurredAt = occurredAt,
        DestinationSurface = "ALERTS",
        AvailableAction = severity == "HIGH" ? "ACKNOWLEDGE" : "NONE",
    };
}