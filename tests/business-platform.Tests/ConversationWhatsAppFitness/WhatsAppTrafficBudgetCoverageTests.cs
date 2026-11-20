// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-04
// Constitutional basis: C-023, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppTrafficBudgetCoverageTests
{
    private static readonly DateTimeOffset Now = new(2026, 11, 6, 10, 0, 0, TimeSpan.Zero);
    private static readonly string Binding = new('a', 64);

    private static ConversationFitnessDbFactory NewStore() => new(Guid.NewGuid().ToString("N"));

    private static WhatsAppTrafficBudget Budget(
        ConversationFitnessDbFactory store,
        FakeGate gate
    ) => new(store, gate, new FixedClock(Now));

    private static string AuthorityDigest(WhatsAppActivationAuthority authority) =>
        Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
        );

    private static async Task<string> Failure(Func<Task> action) =>
        (await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(action)).ReasonCode;

    private static async Task SeedAsync(ConversationFitnessDbFactory store, params object[] rows)
    {
        await using var db = store.CreateDbContext();
        db.AddRange(rows);
        await db.SaveChangesAsync();
    }

    private static WhatsAppGuestTrafficEvent InboundEvent(
        FakeGate gate,
        string providerMessageId,
        string eventType,
        string? notice,
        string binding
    )
    {
        var authority = gate.Authority(Now);
        return new()
        {
            TenantId = gate.TenantId,
            ActivationDigest = WhatsAppGuestTrafficEventIdentity.Activation(
                authority.ActivationReference
            ),
            AuthorityDigest = AuthorityDigest(authority),
            EventId = WhatsAppGuestTrafficEventIdentity.Inbound(providerMessageId),
            BindingDigest = binding,
            EventType = eventType,
            InboundNotice = notice,
            ReservedAt = Now,
        };
    }

    [Theory]
    [InlineData("NONE", WhatsAppGuestTrafficNotice.None)]
    [InlineData("GLOBAL_RATE_LIMIT", WhatsAppGuestTrafficNotice.GlobalRateLimit)]
    [InlineData("ACTIVATION_LIMIT", WhatsAppGuestTrafficNotice.ActivationLimit)]
    public async Task A_replayed_relationship_inbound_returns_the_notice_it_was_given(
        string stored,
        WhatsAppGuestTrafficNotice expected
    )
    {
        var store = NewStore();
        var gate = new FakeGate();
        await SeedAsync(store, InboundEvent(gate, "wamid.1", "INBOUND", stored, Binding));

        var notice = await Budget(store, gate)
            .ReserveRelationshipInboundAsync(gate.TenantId, Binding, "wamid.1", default);

        Assert.Equal(expected, notice);
    }

    [Theory]
    [InlineData("INBOUND", "UNKNOWN", "INBOUND_BUDGET_REPLAY_UNRESOLVED")]
    [InlineData("INBOUND", null, "INBOUND_BUDGET_REPLAY_UNRESOLVED")]
    [InlineData("OUTBOUND", "NONE", "INBOUND_BUDGET_EVENT_CONFLICT")]
    public async Task A_replayed_relationship_inbound_that_cannot_be_trusted_fails_closed(
        string eventType,
        string? stored,
        string reason
    )
    {
        var store = NewStore();
        var gate = new FakeGate();
        await SeedAsync(store, InboundEvent(gate, "wamid.2", eventType, stored, Binding));

        Assert.Equal(
            reason,
            await Failure(() =>
                Budget(store, gate)
                    .ReserveRelationshipInboundAsync(gate.TenantId, Binding, "wamid.2", default)
            )
        );
    }

    [Fact]
    public async Task A_replay_from_another_recipient_binding_is_an_event_conflict()
    {
        var store = NewStore();
        var gate = new FakeGate();
        await SeedAsync(store, InboundEvent(gate, "wamid.3", "INBOUND", "NONE", Binding));

        Assert.Equal(
            "INBOUND_BUDGET_EVENT_CONFLICT",
            await Failure(() =>
                Budget(store, gate)
                    .ReserveRelationshipInboundAsync(
                        gate.TenantId,
                        new string('b', 64),
                        "wamid.3",
                        default
                    )
            )
        );
    }

    [Theory]
    [InlineData(2)]
    [InlineData(3)]
    public async Task An_activation_that_changes_while_inbound_is_reserved_is_refused(
        int changesOnCall
    )
    {
        var store = NewStore();
        var gate = new FakeGate { ChangeAuthorityOnCall = changesOnCall };

        Assert.Equal(
            "ACTIVATION_RECORD_CHANGED",
            await Failure(() =>
                Budget(store, gate)
                    .ReserveRelationshipInboundAsync(gate.TenantId, Binding, "wamid.4", default)
            )
        );
    }

    [Fact]
    public async Task A_fresh_relationship_inbound_that_reaches_the_activation_limit_is_refused()
    {
        var store = NewStore();
        var gate = new FakeGate { MaximumMessages = 1 };
        var budget = Budget(store, gate);

        Assert.Equal(
            WhatsAppGuestTrafficNotice.ActivationLimit,
            await budget.ReserveRelationshipInboundAsync(gate.TenantId, Binding, "wamid.5", default)
        );
        Assert.Equal(
            "TRAFFIC_BUDGET_EXHAUSTED",
            await Failure(() =>
                budget.ReserveRelationshipInboundAsync(gate.TenantId, Binding, "wamid.6", default)
            )
        );
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(true, true)]
    public async Task A_registration_verification_needs_its_allowance_and_a_challenge(
        bool allowed,
        bool emptyChallenge
    )
    {
        var gate = new FakeGate { AllowRegistrationVerification = allowed };

        Assert.Equal(
            "REGISTRATION_VERIFICATION_DENIED",
            await Failure(() =>
                Budget(NewStore(), gate)
                    .ReserveAsync(emptyChallenge ? Guid.Empty : Guid.NewGuid(), default)
            )
        );
    }

    [Fact]
    public async Task A_challenge_that_is_already_reserved_cannot_be_reserved_again()
    {
        var store = NewStore();
        var gate = new FakeGate { AllowRegistrationVerification = true };
        var authority = gate.Authority(Now);
        var challenge = Guid.NewGuid();
        await SeedAsync(
            store,
            new WhatsAppTrafficReservation
            {
                TenantId = gate.TenantId,
                ActivationDigest = Convert.ToHexStringLower(
                    SHA256.HashData(Encoding.UTF8.GetBytes(authority.ActivationReference))
                ),
                AuthorityDigest = AuthorityDigest(authority),
                OutboxId = challenge,
                AttemptNumber = 1,
                ReservedCostInr = 0,
                ReservedAt = Now,
            }
        );

        Assert.Equal(
            "VERIFICATION_ALREADY_RESERVED",
            await Failure(() => Budget(store, gate).ReserveAsync(challenge, default))
        );
    }

    [Fact]
    public async Task A_reservation_made_under_another_authority_record_is_refused()
    {
        var store = NewStore();
        var gate = new FakeGate { AllowRegistrationVerification = true };
        await SeedAsync(
            store,
            new WhatsAppTrafficReservation
            {
                TenantId = gate.TenantId,
                ActivationDigest = Convert.ToHexStringLower(
                    SHA256.HashData(Encoding.UTF8.GetBytes(gate.Authority(Now).ActivationReference))
                ),
                AuthorityDigest = new string('f', 64),
                OutboxId = Guid.NewGuid(),
                AttemptNumber = 1,
                ReservedCostInr = 0,
                ReservedAt = Now,
            }
        );

        Assert.Equal(
            "ACTIVATION_RECORD_CHANGED",
            await Failure(() => Budget(store, gate).ReserveAsync(Guid.NewGuid(), default))
        );
    }

    [Theory]
    [InlineData("0.005")]
    [InlineData("-1")]
    public async Task A_message_cost_that_is_not_whole_paise_cannot_be_priced(string cost)
    {
        var gate = new FakeGate
        {
            AllowRegistrationVerification = true,
            MaximumCostPerMessageInr = decimal.Parse(
                cost,
                System.Globalization.CultureInfo.InvariantCulture
            ),
        };

        Assert.Equal(
            "ENVIRONMENT_SPEND_COST_UNVERIFIABLE",
            await Failure(() => Budget(NewStore(), gate).ReserveAsync(Guid.NewGuid(), default))
        );
    }

    private sealed class FixedClock(DateTimeOffset now) : TimeProvider
    {
        public override DateTimeOffset GetUtcNow() => now;
    }

    private sealed class FakeGate : IWhatsAppCapabilityGate
    {
        private int _calls;

        public Guid TenantId { get; } = Guid.NewGuid();

        public int MaximumMessages { get; init; } = 100;

        public decimal MaximumCostPerMessageInr { get; init; }

        public bool AllowRegistrationVerification { get; init; }

        public int ChangeAuthorityOnCall { get; init; }

        public WhatsAppActivationAuthority Authority(DateTimeOffset now) =>
            new()
            {
                ActivationReference = "FA:budget-coverage",
                TenantId = TenantId,
                Environment = "demo",
                StartsAt = now.AddMinutes(-1),
                ExpiresAt = now.AddMinutes(1),
                MaximumMessages = MaximumMessages,
                MaximumMessagesPerMinute = 100,
                MaximumSpendInr = 500,
                MaximumCostPerMessageInr = MaximumCostPerMessageInr,
                AllowProvisionalOnboarding = true,
                AllowPublicAdmission = true,
                AllowRegistrationVerification = AllowRegistrationVerification,
            };

        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now)
        {
            _calls++;
            var authority = Authority(now);
            return _calls == ChangeAuthorityOnCall
                ? authority with
                {
                    MaximumSpendInr = authority.MaximumSpendInr + 1,
                }
                : authority;
        }

        public void RequireRecipient(
            Guid tenantId,
            string recipientBindingDigest,
            DateTimeOffset now
        )
        {
            if (tenantId != TenantId)
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        }
    }
}
