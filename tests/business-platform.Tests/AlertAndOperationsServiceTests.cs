// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R005, WC171-R006, WC171-R007, WC171-R008, WC171-R009
// Constitutional basis: C-001, C-005, C-007, C-023, C-049, C-059, C-063, C-076
// IB: IB-171

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.Extensions.Options;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Alerts;
using Waooaw.BusinessPlatform.Services.Operations;
using Waooaw.BusinessPlatform.Services.RealWork;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AlertPolicyServiceTests
{
    private static readonly Guid Tenant = Guid.NewGuid();
    private static readonly Guid Relationship = Guid.NewGuid();

    private sealed class FakeAllowance(AllowanceOutcome outcome) : IProactiveAllowance
    {
        public int Calls { get; private set; }

        public Task<AllowanceOutcome> ConsumeAsync(
            Guid tenantId,
            Guid? relationshipId,
            string idempotencyKey,
            CancellationToken cancellationToken
        )
        {
            Calls++;
            return Task.FromResult(outcome);
        }
    }

    private sealed class FakeSender(bool sends) : IAlertWhatsAppSender
    {
        public bool Available => true;
        public List<AlertSendRequest> Sent { get; } = [];

        public Task<bool> SendAsync(AlertSendRequest request, CancellationToken cancellationToken)
        {
            Sent.Add(request);
            return Task.FromResult(sends);
        }
    }

    private static (
        AlertPolicyService Service,
        InMemoryEmploymentRelationshipFactory Factory
    ) Create(
        bool gateOpen = false,
        IProactiveAllowance? allowance = null,
        IAlertWhatsAppSender? sender = null,
        DateTimeOffset? now = null
    )
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var clock = new Mock<TimeProvider>();
        clock
            .Setup(value => value.GetUtcNow())
            .Returns(now ?? new DateTimeOffset(2026, 11, 25, 6, 30, 0, TimeSpan.Zero));
        return (
            new AlertPolicyService(
                factory,
                Options.Create(new AlertDeliveryOptions { ProactiveWhatsAppEnabled = gateOpen }),
                allowance ?? new UnavailableProactiveAllowance(),
                sender ?? new ClosedAlertWhatsAppSender(),
                clock.Object
            ),
            factory
        );
    }

    private static AlertEvent Event(
        string source = AlertSources.AgentDeclared,
        string severity = "WARNING",
        string category = "PACE_BELOW_TARGET",
        string signal = "PACE",
        string period = "2026-11"
    ) => new(source, Tenant, Relationship, signal, severity, period, "Behind pace.", category);

    [Fact]
    public async Task AnAlertIsWrittenOnceToThePortalAndTheClosedGateSaysWhyNoMessageWasSent()
    {
        var (service, factory) = Create();

        var outcome = await service.RaiseAsync(Event(), true, false, default);

        Assert.False(outcome.Folded);
        Assert.Equal(AlertClasses.AtRisk, outcome.AlertClass);
        Assert.Equal(WhatsAppDecisions.GateClosed, outcome.WhatsAppDecision);
        await using var db = factory.CreateDbContext();
        var alert = Assert.Single(db.CustomerAlerts);
        Assert.Equal("MEDIUM", alert.Severity);
        Assert.Equal(WhatsAppDecisions.GateClosed, alert.WhatsAppDecision);
        Assert.Equal("PACE_BELOW_TARGET", alert.Category);
        var delivery = Assert.Single(db.AlertDeliveries);
        Assert.Equal(("portal", "DELIVERED"), (delivery.Channel, delivery.Outcome));
    }

    [Fact]
    public async Task ASecondEventForTheSameProblemIsFoldedIntoTheFirstAndNeverASecondMessage()
    {
        var (service, factory) = Create();
        var first = await service.RaiseAsync(Event(), true, false, default);

        var second = await service.RaiseAsync(Event(), true, false, default);

        Assert.True(second.Folded);
        Assert.Equal(first.AlertId, second.AlertId);
        await using var db = factory.CreateDbContext();
        Assert.Single(db.CustomerAlerts);
    }

    [Fact]
    public async Task OnlyAMoreMaterialClassEscalatesAndOnlyOnce()
    {
        var (service, factory) = Create();
        await service.RaiseAsync(
            Event(AlertSources.BillingThreshold, "MEDIUM", "BUDGET"),
            true,
            false,
            default
        );

        var escalated = await service.RaiseAsync(
            Event(AlertSources.SpendDiscrepancy, "HIGH", "BUDGET"),
            true,
            false,
            default
        );
        var again = await service.RaiseAsync(
            Event(AlertSources.SpendDiscrepancy, "HIGH", "BUDGET"),
            true,
            false,
            default
        );
        var lower = await service.RaiseAsync(
            Event(AlertSources.BillingThreshold, "LOW", "BUDGET"),
            true,
            false,
            default
        );

        Assert.True(escalated.Escalated);
        Assert.Equal(AlertClasses.ActionRequired, escalated.AlertClass);
        Assert.True(again.Folded);
        Assert.True(lower.Folded);
        await using var db = factory.CreateDbContext();
        Assert.Equal(2, db.CustomerAlerts.Count());
    }

    [Fact]
    public async Task AnOperationsAlertIsPagedToOperatorsNeverWrittenToACustomerInbox()
    {
        var (service, _) = Create();

        await Assert.ThrowsAsync<ArgumentException>(() =>
            service.RaiseAsync(Event(AlertSources.Operations, "HIGH"), true, false, default)
        );
    }

    [Fact]
    public async Task AnOpenGateConsumesTheAllowanceOnSendAndRecordsTheWhatsAppDelivery()
    {
        var allowance = new FakeAllowance(AllowanceOutcome.Consumed);
        var sender = new FakeSender(true);
        var (service, factory) = Create(true, allowance, sender);

        var outcome = await service.RaiseAsync(Event(), true, false, default);

        Assert.Equal(WhatsAppDecisions.Send, outcome.WhatsAppDecision);
        Assert.Equal(1, allowance.Calls);
        Assert.True(Assert.Single(sender.Sent).SandboxOnly);
        await using var db = factory.CreateDbContext();
        Assert.Contains(
            db.AlertDeliveries,
            value => value.Channel == "whatsapp_text" && value.Outcome == "DELIVERED"
        );
    }

    [Theory]
    [InlineData(AllowanceOutcome.Exhausted, WhatsAppDecisions.AllowanceExhausted)]
    [InlineData(AllowanceOutcome.Unavailable, WhatsAppDecisions.AllowanceUnavailable)]
    public async Task AnExhaustedOrUnreadableAllowanceFallsBackToThePortalAndSaysSo(
        AllowanceOutcome allowanceOutcome,
        string expected
    )
    {
        var sender = new FakeSender(true);
        var (service, _) = Create(true, new FakeAllowance(allowanceOutcome), sender);

        var outcome = await service.RaiseAsync(Event(), true, false, default);

        Assert.Equal(expected, outcome.WhatsAppDecision);
        Assert.Empty(sender.Sent);
    }

    [Fact]
    public async Task AFloorAlertIsUncountedAndSentEvenInQuietHoursWithoutTouchingTheAllowance()
    {
        var allowance = new FakeAllowance(AllowanceOutcome.Exhausted);
        var sender = new FakeSender(true);
        var (service, _) = Create(
            true,
            allowance,
            sender,
            new DateTimeOffset(2026, 11, 24, 20, 30, 0, TimeSpan.Zero)
        );

        var outcome = await service.RaiseAsync(
            Event(AlertSources.EmergencyStop, "CRITICAL", "EMERGENCY_STOP", "STOP"),
            true,
            false,
            default
        );

        Assert.Equal(WhatsAppDecisions.SendUncounted, outcome.WhatsAppDecision);
        Assert.Equal(0, allowance.Calls);
        Assert.Single(sender.Sent);
    }

    [Fact]
    public async Task ASenderThatCannotSendLeavesAFailedRecordAndThePortalAlert()
    {
        var (service, factory) = Create(
            true,
            new FakeAllowance(AllowanceOutcome.Consumed),
            new FakeSender(false)
        );

        var outcome = await service.RaiseAsync(Event(), true, false, default);

        Assert.Equal(WhatsAppDecisions.SenderUnavailable, outcome.WhatsAppDecision);
        await using var db = factory.CreateDbContext();
        Assert.Contains(
            db.AlertDeliveries,
            value => value.Channel == "whatsapp_text" && value.Outcome == "FAILED"
        );
        Assert.Single(db.CustomerAlerts);
    }

    [Fact]
    public async Task AMutedCategorySuppressesTheMessageButNotThePortalAlert()
    {
        var sender = new FakeSender(true);
        var (service, factory) = Create(true, new FakeAllowance(AllowanceOutcome.Consumed), sender);
        await using (var db = factory.CreateDbContext())
        {
            db.AlertCategoryMutes.Add(
                new AlertCategoryMute
                {
                    TenantId = Tenant,
                    Category = "PACE_BELOW_TARGET",
                    Muted = true,
                }
            );
            await db.SaveChangesAsync();
        }

        var outcome = await service.RaiseAsync(Event(), true, false, default);

        Assert.Equal(WhatsAppDecisions.Muted, outcome.WhatsAppDecision);
        Assert.Empty(sender.Sent);
        await using var check = factory.CreateDbContext();
        Assert.Single(check.CustomerAlerts);
    }
}

public sealed class AlertControlsTests
{
    private static readonly Guid Tenant = Guid.NewGuid();
    private static readonly DateTimeOffset Now = new(2026, 11, 25, 12, 0, 0, TimeSpan.Zero);

    private static async Task<(
        AlertControlsController Controller,
        InMemoryEmploymentRelationshipFactory Factory
    )> Create(params CustomerAlert[] alerts)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        await using (var db = factory.CreateDbContext())
        {
            db.CustomerAlerts.AddRange(alerts);
            await db.SaveChangesAsync();
        }
        var clock = new Mock<TimeProvider>();
        clock.Setup(value => value.GetUtcNow()).Returns(Now);
        var controller = new AlertControlsController(
            new CustomerAlertService(factory),
            clock.Object
        )
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = Tenant.ToString(
            "D"
        );
        controller.HttpContext.User = new ClaimsPrincipal(
            new ClaimsIdentity([new Claim("sub", "customer-1")], "test")
        );
        return (controller, factory);
    }

    private static CustomerAlert Alert(
        string alertClass,
        string category,
        Guid? relationship = null,
        DateTimeOffset? snoozedUntil = null
    ) =>
        new()
        {
            TenantId = Tenant,
            AlertClass = alertClass,
            Category = category,
            RelationshipId = relationship,
            SnoozedUntil = snoozedUntil,
            OccurredAt = Now,
        };

    private static JsonElement Json(object? value) => JsonSerializer.SerializeToElement(value);

    [Fact]
    public async Task TheInboxFiltersToOneAgentAndHidesASnoozedAlertExceptAFloorAlert()
    {
        var mine = Guid.NewGuid();
        var (controller, _) = await Create(
            Alert(AlertClasses.AtRisk, "PACE", mine),
            Alert(AlertClasses.AtRisk, "BUDGET", Guid.NewGuid()),
            Alert(AlertClasses.AtRisk, "HIDDEN", mine, Now.AddHours(5)),
            Alert(AlertClasses.Floor, "EMERGENCY_STOP", mine, Now.AddHours(5))
        );

        var all = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(null, false, 50, default)
        );
        var filtered = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(mine, false, 50, default)
        );
        var withSnoozed = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(mine, true, 50, default)
        );

        Assert.Equal(3, Json(all.Value).GetProperty("items").GetArrayLength());
        Assert.Equal(2, Json(filtered.Value).GetProperty("items").GetArrayLength());
        Assert.Equal(3, Json(withSnoozed.Value).GetProperty("items").GetArrayLength());
    }

    [Fact]
    public async Task AnInvalidLimitOrNoTenantIsRefused()
    {
        var (controller, _) = await Create();
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(await controller.ListAsync(null, false, 0, default))
                .StatusCode
        );

        controller.HttpContext.Items.Clear();
        Assert.IsType<UnauthorizedResult>(await controller.ListAsync(null, false, 50, default));
        Assert.IsType<UnauthorizedResult>(await controller.ListCategoriesAsync(default));
    }

    [Fact]
    public async Task ARoutineAlertCanBeSnoozedButFloorAndActionRequiredAlertsCannot()
    {
        var routine = Alert(AlertClasses.AtRisk, "PACE");
        var floor = Alert(AlertClasses.Floor, "EMERGENCY_STOP");
        var needsYou = Alert(AlertClasses.ActionRequired, "DECISION");
        var (controller, factory) = await Create(routine, floor, needsYou);
        var request = (Guid id, string version = "alert-1") =>
            new AlertSnoozeRequest("1.0.0", version, Now.AddHours(24));

        Assert.IsType<OkObjectResult>(
            await controller.SnoozeAsync(routine.AlertId, request(routine.AlertId), default)
        );
        Assert.IsType<ConflictObjectResult>(
            await controller.SnoozeAsync(floor.AlertId, request(floor.AlertId), default)
        );
        Assert.IsType<ConflictObjectResult>(
            await controller.SnoozeAsync(needsYou.AlertId, request(needsYou.AlertId), default)
        );
        await using var db = factory.CreateDbContext();
        Assert.NotNull(
            db.CustomerAlerts.Single(value => value.AlertId == routine.AlertId).SnoozedUntil
        );
        Assert.Null(db.CustomerAlerts.Single(value => value.AlertId == floor.AlertId).SnoozedUntil);
    }

    [Fact]
    public async Task ASnoozeNeedsTheCurrentVersionAWindowOfThirtyDaysAndAKnownAlert()
    {
        var routine = Alert(AlertClasses.AtRisk, "PACE");
        var (controller, _) = await Create(routine);

        Assert.IsType<ObjectResult>(
            await controller.SnoozeAsync(
                routine.AlertId,
                new AlertSnoozeRequest("1.0.0", "alert-9", Now.AddHours(1)),
                default
            )
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await controller.SnoozeAsync(
                        routine.AlertId,
                        new AlertSnoozeRequest("1.0.0", "alert-1", Now.AddDays(31)),
                        default
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await controller.SnoozeAsync(
                        routine.AlertId,
                        new AlertSnoozeRequest("2", "alert-1", Now.AddHours(1)),
                        default
                    )
                )
                .StatusCode
        );
        Assert.IsType<NotFoundResult>(
            await controller.SnoozeAsync(
                Guid.NewGuid(),
                new AlertSnoozeRequest("1.0.0", "alert-1", Now.AddHours(1)),
                default
            )
        );
    }

    [Fact]
    public async Task ARoutineCategoryCanBeMutedAndUnmutedButAFloorCategoryCanNeverBeMuted()
    {
        var (controller, _) = await Create();

        Assert.IsType<OkObjectResult>(
            await controller.SetCategoryAsync(
                "PACE_BELOW_TARGET",
                new AlertCategoryMuteRequest("1.0.0", true),
                default
            )
        );
        var listed = Assert.IsType<OkObjectResult>(await controller.ListCategoriesAsync(default));
        Assert.True(Json(listed.Value).GetProperty("items")[0].GetProperty("muted").GetBoolean());
        Assert.Contains(
            "EMERGENCY_STOP",
            Json(listed.Value)
                .GetProperty("floorCategories")
                .EnumerateArray()
                .Select(value => value.GetString())
        );
        Assert.IsType<OkObjectResult>(
            await controller.SetCategoryAsync(
                "PACE_BELOW_TARGET",
                new AlertCategoryMuteRequest("1.0.0", false),
                default
            )
        );
        Assert.IsType<ConflictObjectResult>(
            await controller.SetCategoryAsync(
                "EMERGENCY_STOP",
                new AlertCategoryMuteRequest("1.0.0", true),
                default
            )
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await controller.SetCategoryAsync(
                        "bad category",
                        new AlertCategoryMuteRequest("1.0.0", true),
                        default
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await controller.SetCategoryAsync(
                        "PACE",
                        new AlertCategoryMuteRequest("9", true),
                        default
                    )
                )
                .StatusCode
        );
    }
}

public sealed class OperationsConsoleTests
{
    private static readonly Guid Tenant = Guid.NewGuid();
    private static readonly Guid Relationship = Guid.NewGuid();
    private static readonly DateTimeOffset Now = new(2026, 11, 25, 12, 0, 0, TimeSpan.Zero);

    private sealed record Harness(
        OperationsController Controller,
        OperationsConsoleService Console,
        OperatorPageService Pages,
        InMemoryConversationStoreFactory Conversations,
        InMemoryEmploymentRelationshipFactory Relationships
    );

    private static Harness Create(string[] roles, bool stepUp = true, bool whatsAppActive = true)
    {
        var conversations = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        var relationships = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var options = Options.Create(new Wc120ConversationOptions { Environment = "demo" });
        var gate = new Mock<IWhatsAppCapabilityGate>();
        if (whatsAppActive)
            gate.Setup(value => value.RequireActive(It.IsAny<DateTimeOffset>()))
                .Returns(
                    new WhatsAppActivationAuthority { TenantId = Tenant, Environment = "demo" }
                );
        else
            gate.Setup(value => value.RequireActive(It.IsAny<DateTimeOffset>()))
                .Throws(new WhatsAppCapabilityUnavailableException("NOT_ENABLED"));
        var clock = new Mock<TimeProvider>();
        clock.Setup(value => value.GetUtcNow()).Returns(Now);
        var execution = new WhatsAppTenantExecutionScope(gate.Object, clock.Object);
        var health = new Mock<HealthCheckService>();
        health
            .Setup(value =>
                value.CheckHealthAsync(
                    It.IsAny<Func<HealthCheckRegistration, bool>?>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(
                new HealthReport(
                    new Dictionary<string, HealthReportEntry>
                    {
                        ["identity-schema"] = new(
                            HealthStatus.Healthy,
                            null,
                            TimeSpan.Zero,
                            null,
                            null
                        ),
                    },
                    TimeSpan.Zero
                )
            );
        var console = new OperationsConsoleService(
            conversations,
            relationships,
            new ConversationOperationsService(conversations, options),
            execution,
            health.Object,
            options
        );
        var pages = new OperatorPageService(relationships, clock.Object);
        var controller = new OperationsController(
            console,
            pages,
            new RealWorkTimelineService(
                new InMemoryRealWorkLedger(),
                new RealWorkDecisionService(
                    new InMemoryRealWorkLedger(),
                    new RealWorkArtifactService(new InMemoryRealWorkLedger(), TimeProvider.System),
                    Mock.Of<IRelationshipConstitutionalGateway>(),
                    TimeProvider.System
                ),
                TimeProvider.System
            ),
            new UnavailableSpendChainReader(),
            clock.Object
        )
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        var claims = roles.Select(role => new Claim(ClaimTypes.Role, role)).ToList();
        claims.Add(new Claim("sub", "founder-subject"));
        if (stepUp)
        {
            claims.Add(new Claim("auth_time", Now.ToUnixTimeSeconds().ToString()));
            claims.Add(new Claim("acr", "2"));
            claims.Add(new Claim("amr", "mfa"));
        }
        controller.HttpContext.User = new ClaimsPrincipal(new ClaimsIdentity(claims, "test"));
        return new Harness(controller, console, pages, conversations, relationships);
    }

    private static async Task<Guid> Block(
        Harness harness,
        string reason = "PROVIDER_REJECTED",
        string state = "BLOCKED"
    )
    {
        var row = new ConversationOutboxRecord
        {
            Environment = "demo",
            TenantId = Tenant,
            RelationshipId = Relationship,
            Purpose = "GUEST_DISCOVERY",
            State = state,
            BlockedReason = reason,
            AttemptNumber = 3,
            UpdatedAt = Now.AddMinutes(-42),
        };
        await using var db = harness.Conversations.CreateDbContext();
        db.ConversationOutbox.Add(row);
        await db.SaveChangesAsync();
        return row.OutboxId;
    }

    private static JsonElement Json(object? value) =>
        JsonSerializer.SerializeToElement(
            value,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );

    [Fact]
    public async Task ACustomerOrAnUnrelatedStaffRoleReadsNothing()
    {
        var harness = Create(["pricing_admin"]);

        Assert.Equal(
            403,
            Assert.IsType<ObjectResult>(await harness.Controller.OverviewAsync(default)).StatusCode
        );
        Assert.Equal(
            403,
            Assert
                .IsType<ObjectResult>(await harness.Controller.ListBlockedAsync(default))
                .StatusCode
        );
        Assert.Equal(
            403,
            Assert.IsType<ObjectResult>(await harness.Controller.ListPagesAsync(default)).StatusCode
        );
        Assert.Equal(
            403,
            Assert
                .IsType<ObjectResult>(harness.Controller.GetWorkTimeline(Relationship, Tenant))
                .StatusCode
        );
        Assert.Equal(
            403,
            Assert
                .IsType<ObjectResult>(
                    await harness.Controller.GetSpendChainAsync(Relationship, Tenant, default)
                )
                .StatusCode
        );
    }

    [Fact]
    public async Task TheOverviewCountsBlockedMessagesAndReportsServiceHealthAndPageOutcomes()
    {
        var harness = Create(["operations_authority"]);
        await Block(harness);
        await harness.Pages.RecordAsync("DEAD_LETTER_AGE_BREACH", false, default);

        var overview = Json(
            Assert.IsType<OkObjectResult>(await harness.Controller.OverviewAsync(default)).Value
        );

        Assert.Equal("ACTIVE", overview.GetProperty("whatsApp").GetString());
        Assert.Equal(1, overview.GetProperty("blockedMessages").GetInt32());
        Assert.Equal(
            "operator_page",
            overview.GetProperty("deliveries")[0].GetProperty("channel").GetString()
        );
        Assert.Equal(
            "identity-schema",
            overview.GetProperty("services")[0].GetProperty("name").GetString()
        );
    }

    [Fact]
    public async Task AnInactiveWhatsAppIsReportedNotShownAsAHealthyEmptyQueue()
    {
        var harness = Create(["founder"], whatsAppActive: false);

        var overview = Json(
            Assert.IsType<OkObjectResult>(await harness.Controller.OverviewAsync(default)).Value
        );
        var blocked = Assert.IsType<ObjectResult>(
            await harness.Controller.ListBlockedAsync(default)
        );

        Assert.Equal("INACTIVE", overview.GetProperty("whatsApp").GetString());
        Assert.Equal("NOT_ENABLED", overview.GetProperty("whatsAppReason").GetString());
        Assert.Equal(503, blocked.StatusCode);
    }

    [Fact]
    public async Task TheBlockedListCarriesNoRecipientOrBodyAndLeavesOnceClosed()
    {
        var harness = Create(["operations_authority", "founder"]);
        var outbox = await Block(harness);

        var listed = Json(
            Assert.IsType<OkObjectResult>(await harness.Controller.ListBlockedAsync(default)).Value
        );
        var item = listed.GetProperty("items")[0];
        Assert.Equal(outbox, item.GetProperty("outboxId").GetGuid());
        Assert.False(item.TryGetProperty("recipient", out _));
        Assert.False(item.TryGetProperty("protectedRecipientDestination", out _));
        Assert.Equal(42, item.GetProperty("ageMinutes").GetDouble());

        var closed = await harness.Controller.ResolveBlockedAsync(
            outbox,
            new BlockedMessageResolveRequest(
                "1.0.0",
                "CLOSE_WITH_REASON",
                "Recipient is not on WhatsApp"
            ),
            Guid.NewGuid().ToString(),
            default
        );
        Assert.Equal(201, Assert.IsType<ObjectResult>(closed).StatusCode);

        Assert.Equal(
            0,
            Json(
                    Assert
                        .IsType<OkObjectResult>(await harness.Controller.ListBlockedAsync(default))
                        .Value
                )
                .GetProperty("items")
                .GetArrayLength()
        );
        var overview = Json(
            Assert.IsType<OkObjectResult>(await harness.Controller.OverviewAsync(default)).Value
        );
        Assert.Equal(0, overview.GetProperty("blockedMessages").GetInt32());
        await using var db = harness.Conversations.CreateDbContext();
        var row = Assert.Single(db.ConversationOutbox);
        Assert.Equal("BLOCKED", row.State);
        Assert.Equal("PROVIDER_REJECTED", row.BlockedReason);
    }

    [Fact]
    public async Task ARetryRequeuesTheSameMessageAndAReplayOfTheSameKeyChangesNothingMore()
    {
        var harness = Create(["founder"]);
        var outbox = await Block(harness);
        var key = Guid.NewGuid().ToString();
        var request = new BlockedMessageResolveRequest("1.0.0", "RETRY", "Template approved now");

        var first = await harness.Controller.ResolveBlockedAsync(outbox, request, key, default);
        var replay = await harness.Controller.ResolveBlockedAsync(outbox, request, key, default);

        Assert.Equal(201, Assert.IsType<ObjectResult>(first).StatusCode);
        Assert.IsType<OkObjectResult>(replay);
        await using var db = harness.Conversations.CreateDbContext();
        var row = Assert.Single(db.ConversationOutbox);
        Assert.Equal("PENDING", row.State);
        Assert.Null(row.BlockedReason);
        Assert.Single(db.OutboxResolutions);
    }

    [Fact]
    public async Task AResolutionIsRefusedForTheWrongRoleNoStepUpABadRequestOrAConflict()
    {
        var reader = Create(["operations_authority"]);
        var outbox = await Block(reader);
        var request = new BlockedMessageResolveRequest(
            "1.0.0",
            "CLOSE_WITH_REASON",
            "Recipient is not on WhatsApp"
        );
        var key = Guid.NewGuid().ToString();

        Assert.Equal(
            403,
            Assert
                .IsType<ObjectResult>(
                    await reader.Controller.ResolveBlockedAsync(outbox, request, key, default)
                )
                .StatusCode
        );

        var noStepUp = Create(["founder"], stepUp: false);
        var refused = Assert.IsType<ObjectResult>(
            await noStepUp.Controller.ResolveBlockedAsync(
                await Block(noStepUp),
                request,
                key,
                default
            )
        );
        Assert.Equal(403, refused.StatusCode);
        Assert.Contains("OPERATIONS_STEP_UP_REQUIRED", JsonSerializer.Serialize(refused.Value));

        var founder = Create(["founder"]);
        var id = await Block(founder);
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await founder.Controller.ResolveBlockedAsync(id, request, "not-a-guid", default)
                )
                .StatusCode
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await founder.Controller.ResolveBlockedAsync(
                        id,
                        request with
                        {
                            SchemaVersion = "2",
                        },
                        key,
                        default
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await founder.Controller.ResolveBlockedAsync(
                        id,
                        request with
                        {
                            Reason = "no",
                        },
                        key,
                        default
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await founder.Controller.ResolveBlockedAsync(
                        id,
                        request with
                        {
                            Action = "DELETE",
                        },
                        key,
                        default
                    )
                )
                .StatusCode
        );
        Assert.IsType<NotFoundResult>(
            await founder.Controller.ResolveBlockedAsync(
                Guid.NewGuid(),
                request,
                Guid.NewGuid().ToString(),
                default
            )
        );

        var delivered = await Block(founder, state: "DELIVERED");
        Assert.IsType<ConflictObjectResult>(
            await founder.Controller.ResolveBlockedAsync(
                delivered,
                request,
                Guid.NewGuid().ToString(),
                default
            )
        );

        await founder.Controller.ResolveBlockedAsync(id, request, key, default);
        var other = await Block(founder);
        Assert.IsType<ConflictObjectResult>(
            await founder.Controller.ResolveBlockedAsync(other, request, key, default)
        );
    }

    [Fact]
    public async Task AnAcknowledgedPageIsSuppressedForItsWindowAndTheSignalStaysVisible()
    {
        var harness = Create(["founder"]);

        Assert.False(await harness.Pages.IsAcknowledgedAsync("DEAD_LETTER_AGE_BREACH", default));
        Assert.Equal(
            "EMITTED",
            await harness.Pages.RecordAsync("DEAD_LETTER_AGE_BREACH", false, default)
        );
        Assert.IsType<AcceptedResult>(
            await harness.Controller.AcknowledgePageAsync("DEAD_LETTER_AGE_BREACH", default)
        );
        Assert.True(await harness.Pages.IsAcknowledgedAsync("DEAD_LETTER_AGE_BREACH", default));
        Assert.Equal(
            "SUPPRESSED",
            await harness.Pages.RecordAsync("DEAD_LETTER_AGE_BREACH", true, default)
        );

        var listed = Json(
            Assert.IsType<OkObjectResult>(await harness.Controller.ListPagesAsync(default)).Value
        );
        Assert.Equal(
            new[] { "ACKNOWLEDGED", "EMITTED", "SUPPRESSED" },
            listed
                .GetProperty("items")
                .EnumerateArray()
                .Select(value => value.GetProperty("outcome").GetString() ?? string.Empty)
                .Order()
                .ToArray()
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await harness.Controller.AcknowledgePageAsync("lower", default)
                )
                .StatusCode
        );
        Assert.Equal(
            403,
            Assert
                .IsType<ObjectResult>(
                    await Create(["operations_authority"])
                        .Controller.AcknowledgePageAsync("DEAD_LETTER_AGE_BREACH", default)
                )
                .StatusCode
        );
    }

    [Fact]
    public async Task TheWorkTimelineIsReadForANamedTenantAndTheSpendChainSaysItCannotBeReadYet()
    {
        var harness = Create(["operations_authority"]);

        Assert.IsType<OkObjectResult>(harness.Controller.GetWorkTimeline(Relationship, Tenant));
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(harness.Controller.GetWorkTimeline(Relationship, Guid.Empty))
                .StatusCode
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await harness.Controller.GetSpendChainAsync(Relationship, Guid.Empty, default)
                )
                .StatusCode
        );
        var unavailable = Assert.IsType<ObjectResult>(
            await harness.Controller.GetSpendChainAsync(Relationship, Tenant, default)
        );
        Assert.Equal(503, unavailable.StatusCode);
        Assert.Contains(
            "SPEND_CHAIN_READ_UNAVAILABLE",
            JsonSerializer.Serialize(unavailable.Value)
        );
    }

    [Fact]
    public async Task ADiscrepancyIsResolvedOnlyByTheFounderWithAStepUpAndEvidence()
    {
        var request = new SpendDiscrepancyResolveRequest("1.0.0", Tenant, Guid.NewGuid());
        var founder = Create(["founder"]);

        Assert.Equal(
            403,
            Assert
                .IsType<ObjectResult>(
                    await Create(["operations_authority"])
                        .Controller.ResolveDiscrepancyAsync(
                            Relationship,
                            Guid.NewGuid(),
                            request,
                            default
                        )
                )
                .StatusCode
        );
        Assert.Equal(
            403,
            Assert
                .IsType<ObjectResult>(
                    await Create(["founder"], stepUp: false)
                        .Controller.ResolveDiscrepancyAsync(
                            Relationship,
                            Guid.NewGuid(),
                            request,
                            default
                        )
                )
                .StatusCode
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await founder.Controller.ResolveDiscrepancyAsync(
                        Relationship,
                        Guid.NewGuid(),
                        request with
                        {
                            EvidenceId = Guid.Empty,
                        },
                        default
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            503,
            Assert
                .IsType<ObjectResult>(
                    await founder.Controller.ResolveDiscrepancyAsync(
                        Relationship,
                        Guid.NewGuid(),
                        request,
                        default
                    )
                )
                .StatusCode
        );
    }
}
