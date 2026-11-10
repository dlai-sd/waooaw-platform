// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R008
// Constitutional basis: C-023, C-026, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppGuestTrafficBudgetTests
{
    [Fact]
    public async Task ReplayedInboundRetainsItsOriginalDecisionAfterOtherTraffic()
    {
        var tenantId = Guid.NewGuid();
        var factory = new ConversationFitnessDbFactory(Guid.NewGuid().ToString("N"));
        var now = new DateTimeOffset(2026, 11, 6, 10, 0, 0, TimeSpan.Zero);
        var budget = new WhatsAppGuestTrafficBudget(
            factory,
            new GuestBudgetGate(tenantId, maximumMessagesPerMinute: 4),
            new FixedTimeProvider(now)
        );
        var first = new string('a', 64);
        var second = new string('b', 64);
        Assert.Equal(
            WhatsAppGuestTrafficNotice.None,
            await budget.ReserveInboundAsync(
                tenantId,
                first,
                "first",
                false,
                CancellationToken.None
            )
        );
        await budget.ReserveOutboundAsync(tenantId, first, Guid.NewGuid(), CancellationToken.None);
        Assert.Equal(
            WhatsAppGuestTrafficNotice.GlobalRateLimit,
            await budget.ReserveInboundAsync(
                tenantId,
                second,
                "second",
                false,
                CancellationToken.None
            )
        );
        Assert.Equal(
            WhatsAppGuestTrafficNotice.None,
            await budget.ReserveInboundAsync(
                tenantId,
                first,
                "first",
                false,
                CancellationToken.None
            )
        );
        await budget.ReserveOutboundAsync(tenantId, second, Guid.NewGuid(), CancellationToken.None);
        Assert.Equal(
            WhatsAppGuestTrafficNotice.GlobalRateLimit,
            await budget.ReserveInboundAsync(
                tenantId,
                second,
                "second",
                false,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task LegacyInboundWithUnknownDecisionFailsClosed()
    {
        var tenantId = Guid.NewGuid();
        var factory = new ConversationFitnessDbFactory(Guid.NewGuid().ToString("N"));
        var now = new DateTimeOffset(2026, 11, 6, 10, 0, 0, TimeSpan.Zero);
        var gate = new GuestBudgetGate(tenantId, maximumMessagesPerMinute: 100);
        var authority = gate.RequireActive(now);
        await using (var db = factory.CreateDbContext())
        {
            db.Add(
                new WhatsAppGuestTrafficEvent
                {
                    TenantId = tenantId,
                    ActivationDigest = WhatsAppGuestTrafficEventIdentity.Activation(
                        authority.ActivationReference
                    ),
                    AuthorityDigest = Convert.ToHexStringLower(
                        SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
                    ),
                    EventId = WhatsAppGuestTrafficEventIdentity.Inbound("legacy"),
                    BindingDigest = new string('a', 64),
                    EventType = "INBOUND",
                    ReservedAt = now,
                }
            );
            await db.SaveChangesAsync();
        }
        var budget = new WhatsAppGuestTrafficBudget(factory, gate, new FixedTimeProvider(now));
        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveInboundAsync(
                tenantId,
                new string('a', 64),
                "legacy",
                false,
                CancellationToken.None
            )
        );
        Assert.Equal("GUEST_BUDGET_REPLAY_UNRESOLVED", failure.ReasonCode);
    }

    [Fact]
    public async Task ReusedInboundProviderIdCannotBorrowAnotherSendersReservation()
    {
        var tenantId = Guid.NewGuid();
        var factory = new ConversationFitnessDbFactory(Guid.NewGuid().ToString("N"));
        var now = new DateTimeOffset(2026, 11, 6, 10, 0, 0, TimeSpan.Zero);
        var budget = new WhatsAppGuestTrafficBudget(
            factory,
            new GuestBudgetGate(tenantId, maximumMessagesPerMinute: 100),
            new FixedTimeProvider(now)
        );
        var firstSender = new string('a', 64);
        await budget.ReserveInboundAsync(
            tenantId,
            firstSender,
            "same-provider-id",
            false,
            CancellationToken.None
        );
        Assert.Equal(
            WhatsAppGuestTrafficNotice.None,
            await budget.ReserveInboundAsync(
                tenantId,
                firstSender,
                "same-provider-id",
                false,
                CancellationToken.None
            )
        );
        var conflict = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveInboundAsync(
                tenantId,
                new string('b', 64),
                "same-provider-id",
                false,
                CancellationToken.None
            )
        );
        Assert.Equal("GUEST_BUDGET_EVENT_CONFLICT", conflict.ReasonCode);
        await using var db = factory.CreateDbContext();
        Assert.Single(db.Set<WhatsAppGuestTrafficEvent>());
    }

    [Fact]
    public async Task SharedRollingMinuteCountsRelationshipAndOtpTrafficButNotGuestDispatchTwice()
    {
        var tenantId = Guid.NewGuid();
        var factory = new ConversationFitnessDbFactory(Guid.NewGuid().ToString("N"));
        var now = new DateTimeOffset(2026, 11, 6, 10, 0, 0, TimeSpan.Zero);
        var gate = new GuestBudgetGate(tenantId, maximumMessagesPerMinute: 5, maximumMessages: 10);
        var authority = gate.RequireActive(now);
        var activation = WhatsAppGuestTrafficEventIdentity.Activation(
            authority.ActivationReference
        );
        var authorityDigest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
        );
        var guestOutboxId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.ConversationOutbox.Add(
                new()
                {
                    OutboxId = guestOutboxId,
                    TenantId = tenantId,
                    PortalContextId = Guid.NewGuid(),
                    Purpose = "WHATSAPP_GUEST_DISCOVERY",
                }
            );
            db.Add(
                new WhatsAppGuestTrafficEvent
                {
                    TenantId = tenantId,
                    ActivationDigest = activation,
                    AuthorityDigest = authorityDigest,
                    EventId = WhatsAppGuestTrafficEventIdentity.Outbound(guestOutboxId),
                    BindingDigest = new string('b', 64),
                    EventType = "OUTBOUND",
                    ReservedAt = now,
                }
            );
            foreach (var outboxId in new[] { guestOutboxId, Guid.NewGuid(), Guid.NewGuid() })
                db.Add(
                    new WhatsAppTrafficReservation
                    {
                        TenantId = tenantId,
                        ActivationDigest = activation,
                        AuthorityDigest = authorityDigest,
                        OutboxId = outboxId,
                        AttemptNumber = 1,
                        ReservedAt = now,
                    }
                );
            db.Add(
                new WhatsAppTrafficReservation
                {
                    TenantId = tenantId,
                    ActivationDigest = activation,
                    AuthorityDigest = authorityDigest,
                    OutboxId = Guid.NewGuid(),
                    AttemptNumber = 1,
                    ReservedAt = now.AddMinutes(-1),
                }
            );
            db.Add(
                new WhatsAppTrafficReservation
                {
                    TenantId = Guid.NewGuid(),
                    ActivationDigest = activation,
                    AuthorityDigest = authorityDigest,
                    OutboxId = Guid.NewGuid(),
                    AttemptNumber = 1,
                    ReservedAt = now,
                }
            );
            await db.SaveChangesAsync();
            Assert.Equal(
                3,
                await WhatsAppTrafficBudget.CountGlobalMessagesAsync(
                    db,
                    tenantId,
                    now.AddMinutes(-1),
                    CancellationToken.None
                )
            );
            Assert.Equal(
                4,
                await WhatsAppTrafficBudget.CountActivationMessagesAsync(
                    db,
                    tenantId,
                    activation,
                    CancellationToken.None
                )
            );
        }
        var budget = new WhatsAppGuestTrafficBudget(factory, gate, new FixedTimeProvider(now));
        var receipt = await budget.ReserveInboundAsync(
            tenantId,
            new string('a', 64),
            "shared-rate-final-notice",
            false,
            CancellationToken.None
        );
        Assert.Equal(WhatsAppGuestTrafficNotice.GlobalRateLimit, receipt);
        var denied = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveInboundAsync(
                tenantId,
                new string('c', 64),
                "shared-rate-exhausted",
                false,
                CancellationToken.None
            )
        );
        Assert.Equal("GUEST_GLOBAL_RATE_LIMIT_REACHED", denied.ReasonCode);
    }

    [Fact]
    public async Task ReservesFinalResponseSlotAtTenantWideRollingMinuteLimit()
    {
        var tenantId = Guid.NewGuid();
        var databaseName = Guid.NewGuid().ToString("N");
        var factory = new ConversationFitnessDbFactory(databaseName);
        var clock = new FixedTimeProvider(new DateTimeOffset(2026, 11, 6, 10, 0, 0, TimeSpan.Zero));
        var gate = new GuestBudgetGate(tenantId, maximumMessagesPerMinute: 3);
        var budget = new WhatsAppGuestTrafficBudget(factory, gate, clock);

        var first = await budget.ReserveInboundAsync(
            tenantId,
            new string('a', 64),
            "first-sender-message",
            false,
            CancellationToken.None
        );
        var finalAllowed = await budget.ReserveInboundAsync(
            tenantId,
            new string('b', 64),
            "second-sender-message",
            false,
            CancellationToken.None
        );
        Assert.Equal(WhatsAppGuestTrafficNotice.None, first);
        Assert.Equal(WhatsAppGuestTrafficNotice.GlobalRateLimit, finalAllowed);

        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveInboundAsync(
                tenantId,
                new string('c', 64),
                "third-sender-message",
                false,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task ReservesFinalResponseSlotAtPerGuestMessageLimit()
    {
        var tenantId = Guid.NewGuid();
        var factory = new ConversationFitnessDbFactory(Guid.NewGuid().ToString("N"));
        var clock = new FixedTimeProvider(new DateTimeOffset(2026, 11, 6, 10, 0, 0, TimeSpan.Zero));
        var budget = new WhatsAppGuestTrafficBudget(
            factory,
            new GuestBudgetGate(tenantId, maximumMessagesPerMinute: 100),
            clock
        );
        var bindingDigest = new string('a', 64);
        foreach (var index in Enumerable.Range(0, 4))
        {
            await budget.ReserveInboundAsync(
                tenantId,
                bindingDigest,
                $"inbound-{index}",
                false,
                CancellationToken.None
            );
            await budget.ReserveOutboundAsync(
                tenantId,
                bindingDigest,
                Guid.NewGuid(),
                CancellationToken.None
            );
        }

        var finalAllowed = await budget.ReserveInboundAsync(
            tenantId,
            bindingDigest,
            "inbound-limit-notice",
            false,
            CancellationToken.None
        );
        Assert.Equal(WhatsAppGuestTrafficNotice.GuestMessageLimit, finalAllowed);
        await budget.ReserveOutboundAsync(
            tenantId,
            bindingDigest,
            Guid.NewGuid(),
            CancellationToken.None
        );
        Assert.Equal(
            WhatsAppGuestTrafficNotice.GuestMessageLimit,
            await budget.ReserveInboundAsync(
                tenantId,
                bindingDigest,
                "inbound-limit-notice",
                false,
                CancellationToken.None
            )
        );
        var exhausted = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveInboundAsync(
                tenantId,
                bindingDigest,
                "after-limit",
                false,
                CancellationToken.None
            )
        );
        Assert.Equal("GUEST_MESSAGE_LIMIT_REACHED", exhausted.ReasonCode);
    }

    [Fact]
    public async Task ActivationLimitCountsInboundAndOutboundAndPreservesNoticeOnReplay()
    {
        var tenantId = Guid.NewGuid();
        var factory = new ConversationFitnessDbFactory(Guid.NewGuid().ToString("N"));
        var clock = new FixedTimeProvider(new DateTimeOffset(2026, 11, 6, 10, 0, 0, TimeSpan.Zero));
        var gate = new GuestBudgetGate(tenantId, maximumMessagesPerMinute: 100, maximumMessages: 4);
        var budget = new WhatsAppGuestTrafficBudget(factory, gate, clock);
        var binding = new string('a', 64);
        Assert.Equal(
            WhatsAppGuestTrafficNotice.None,
            await budget.ReserveInboundAsync(
                tenantId,
                binding,
                "first",
                false,
                CancellationToken.None
            )
        );
        await budget.ReserveOutboundAsync(
            tenantId,
            binding,
            Guid.NewGuid(),
            CancellationToken.None
        );
        Assert.Equal(
            WhatsAppGuestTrafficNotice.ActivationLimit,
            await budget.ReserveInboundAsync(
                tenantId,
                binding,
                "last",
                false,
                CancellationToken.None
            )
        );
        await budget.ReserveOutboundAsync(
            tenantId,
            binding,
            Guid.NewGuid(),
            CancellationToken.None
        );
        Assert.Equal(
            WhatsAppGuestTrafficNotice.ActivationLimit,
            await budget.ReserveInboundAsync(
                tenantId,
                binding,
                "last",
                false,
                CancellationToken.None
            )
        );
        var exhausted = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveInboundAsync(tenantId, binding, "next", false, CancellationToken.None)
        );
        Assert.Equal("TRAFFIC_BUDGET_EXHAUSTED", exhausted.ReasonCode);
    }

    [Fact]
    public async Task ActivationLimitCountsLegacyGuestReservationWithoutMatchingTrafficEvent()
    {
        var tenantId = Guid.NewGuid();
        var factory = new ConversationFitnessDbFactory(Guid.NewGuid().ToString("N"));
        var now = new DateTimeOffset(2026, 11, 6, 10, 0, 0, TimeSpan.Zero);
        var gate = new GuestBudgetGate(tenantId, maximumMessagesPerMinute: 100, maximumMessages: 3);
        var authority = gate.RequireActive(now);
        var outboxId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.ConversationOutbox.Add(
                new()
                {
                    OutboxId = outboxId,
                    TenantId = tenantId,
                    PortalContextId = Guid.NewGuid(),
                    Purpose = "WHATSAPP_GUEST_DISCOVERY",
                }
            );
            db.Add(
                new WhatsAppTrafficReservation
                {
                    TenantId = tenantId,
                    ActivationDigest = WhatsAppGuestTrafficEventIdentity.Activation(
                        authority.ActivationReference
                    ),
                    AuthorityDigest = Convert.ToHexStringLower(
                        SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
                    ),
                    OutboxId = outboxId,
                    AttemptNumber = 1,
                    ReservedAt = now,
                }
            );
            await db.SaveChangesAsync();
        }
        var budget = new WhatsAppGuestTrafficBudget(factory, gate, new FixedTimeProvider(now));
        Assert.Equal(
            WhatsAppGuestTrafficNotice.ActivationLimit,
            await budget.ReserveInboundAsync(
                tenantId,
                new string('a', 64),
                "last",
                false,
                CancellationToken.None
            )
        );
    }

    private sealed class GuestBudgetGate(
        Guid tenantId,
        int maximumMessagesPerMinute,
        int maximumMessages = 100
    ) : IWhatsAppCapabilityGate
    {
        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) =>
            new()
            {
                ActivationReference = "FA:guest-rate-test",
                TenantId = tenantId,
                Environment = "demo",
                StartsAt = now.AddMinutes(-1),
                ExpiresAt = now.AddMinutes(1),
                MaximumMessages = maximumMessages,
                MaximumMessagesPerMinute = maximumMessagesPerMinute,
                MaximumSpendInr = 500,
                MaximumCostPerMessageInr = 0,
                AllowProvisionalOnboarding = true,
                AllowPublicAdmission = true,
            };

        public void RequireRecipient(Guid tenant, string binding, DateTimeOffset now)
        {
            if (tenant != tenantId)
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        }
    }

    private sealed class FixedTimeProvider(DateTimeOffset now) : TimeProvider
    {
        public override DateTimeOffset GetUtcNow() => now;
    }
}
