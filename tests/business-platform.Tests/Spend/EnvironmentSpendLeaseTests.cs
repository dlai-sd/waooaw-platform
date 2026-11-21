// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-06
// Constitutional basis: C-023, C-059, C-063
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Spend;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Spend;

public sealed class EnvironmentSpendLeaseServiceTests
{
    private static readonly DateTimeOffset Now = new(2026, 11, 20, 9, 0, 0, TimeSpan.Zero);

    [Fact]
    public async Task DrawsInsideOneLeaseNeedNoSecondGrant()
    {
        var store = new FakeStore();
        var service = Service(store);

        var first = await service.TryDrawAsync("demo", 1_000, 100_000, Now, CancellationToken.None);
        var second = await service.TryDrawAsync(
            "demo",
            1_000,
            100_000,
            Now,
            CancellationToken.None
        );

        Assert.NotNull(first);
        Assert.NotNull(second);
        Assert.Equal(first.LeaseId, second.LeaseId);
        Assert.Equal(500, second.RemainingPaise);
        Assert.Single(store.Grants);
        Assert.Empty(store.Closed);
    }

    [Fact]
    public async Task ExhaustedLeaseIsReturnedAndReplaced()
    {
        var store = new FakeStore();
        var service = Service(store);

        var first = await service.TryDrawAsync("demo", 2_000, 100_000, Now, CancellationToken.None);
        var second = await service.TryDrawAsync(
            "demo",
            1_000,
            100_000,
            Now,
            CancellationToken.None
        );

        Assert.NotNull(first);
        Assert.NotNull(second);
        Assert.NotEqual(first.LeaseId, second.LeaseId);
        Assert.Equal(new[] { first.LeaseId }, store.Closed);
        Assert.Equal(2, store.Grants.Count);
    }

    [Fact]
    public async Task ExpiredLeaseIsDroppedAndReplacedWithoutAClientClose()
    {
        var store = new FakeStore();
        var service = Service(store);

        var first = await service.TryDrawAsync("demo", 1_000, 100_000, Now, CancellationToken.None);
        var second = await service.TryDrawAsync(
            "demo",
            1_000,
            100_000,
            Now.AddSeconds(121),
            CancellationToken.None
        );

        Assert.NotNull(first);
        Assert.NotNull(second);
        Assert.NotEqual(first.LeaseId, second.LeaseId);
        Assert.Empty(store.Closed);
        Assert.Equal(2, store.Grants.Count);
    }

    [Fact]
    public async Task GrantSmallerThanTheRequestIsReturnedAndRefused()
    {
        var store = new FakeStore { GrantCapPaise = 500 };
        var service = Service(store);

        var draw = await service.TryDrawAsync("demo", 1_000, 100_000, Now, CancellationToken.None);

        Assert.Null(draw);
        Assert.Single(store.Closed);
    }

    [Fact]
    public async Task NoHeadroomRefusesTheDraw()
    {
        var store = new FakeStore { GrantCapPaise = 0 };
        var service = Service(store);

        var draw = await service.TryDrawAsync("demo", 1_000, 100_000, Now, CancellationToken.None);

        Assert.Null(draw);
        Assert.Empty(store.Closed);
    }

    [Fact]
    public async Task InvalidatedLeaseIsNotReused()
    {
        var store = new FakeStore();
        var service = Service(store);
        var first = await service.TryDrawAsync("demo", 1_000, 100_000, Now, CancellationToken.None);
        Assert.NotNull(first);

        await service.InvalidateAsync("demo", first.LeaseId, CancellationToken.None);
        var second = await service.TryDrawAsync(
            "demo",
            1_000,
            100_000,
            Now,
            CancellationToken.None
        );

        Assert.NotNull(second);
        Assert.NotEqual(first.LeaseId, second.LeaseId);
    }

    [Fact]
    public async Task EnvironmentsHoldIndependentLeases()
    {
        var store = new FakeStore();
        var service = Service(store);

        var first = await service.TryDrawAsync("demo", 1_000, 100_000, Now, CancellationToken.None);
        var second = await service.TryDrawAsync("uat", 1_000, 100_000, Now, CancellationToken.None);

        Assert.NotNull(first);
        Assert.NotNull(second);
        Assert.NotEqual(first.LeaseId, second.LeaseId);
        Assert.Equal(
            new[] { "demo", "uat" },
            store.Grants.Select(grant => grant.Environment).ToArray()
        );
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    [InlineData(2_501)]
    public async Task AmountsOutsideTheLeaseSizeAreRejected(long amount)
    {
        var service = Service(new FakeStore());

        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() =>
            service.TryDrawAsync("demo", amount, 100_000, Now, CancellationToken.None)
        );
    }

    [Fact]
    public async Task ConcurrentDrawsNeverOverdrawOneLease()
    {
        var store = new FakeStore();
        var service = Service(store);

        var draws = await Task.WhenAll(
            Enumerable
                .Range(0, 50)
                .Select(_ =>
                    service.TryDrawAsync("demo", 100, 100_000, Now, CancellationToken.None)
                )
        );

        Assert.All(draws, draw => Assert.NotNull(draw));
        Assert.Equal(2, store.Grants.Count);
        Assert.All(store.Grants, grant => Assert.Equal(2_500, grant.GrantedPaise));
    }

    private static EnvironmentSpendLeaseService Service(FakeStore store) =>
        new(
            store,
            new EnvironmentSpendOptions
            {
                Mode = EnvironmentSpendOptions.LeasesMode,
                LeaseSizeInr = 25,
                LeaseSeconds = 120,
            }
        );

    private sealed class FakeStore : IEnvironmentSpendLeaseStore
    {
        public long GrantCapPaise { get; init; } = long.MaxValue;
        public List<EnvironmentSpendLease> Grants { get; } = [];
        public List<Guid> Closed { get; } = [];

        public Task<EnvironmentSpendLease?> GrantAsync(
            string environment,
            string holder,
            long leaseSizePaise,
            long maximumPaise,
            TimeSpan duration,
            DateTimeOffset now,
            CancellationToken ct
        )
        {
            var granted = Math.Min(Math.Min(leaseSizePaise, maximumPaise), GrantCapPaise);
            if (granted <= 0)
                return Task.FromResult<EnvironmentSpendLease?>(null);
            var lease = new EnvironmentSpendLease(
                Guid.NewGuid(),
                environment,
                granted,
                now.Add(duration)
            );
            lock (Grants)
                Grants.Add(lease);
            return Task.FromResult<EnvironmentSpendLease?>(lease);
        }

        public Task CloseAsync(Guid leaseId, CancellationToken ct)
        {
            lock (Closed)
                Closed.Add(leaseId);
            return Task.CompletedTask;
        }
    }
}

public sealed class EnvironmentSpendLeasePostgresTests(EnvironmentSpendPostgresFixture fixture)
    : IClassFixture<EnvironmentSpendPostgresFixture>
{
    [Fact]
    public async Task ConcurrentLeasedReservationsNeverExceedTheCeiling()
    {
        var environment = await fixture.NewEnvironmentAsync();
        var owner = fixture.LeaseOwner(LeaseOptions(), out _);

        var outcomes = await Task.WhenAll(
            Enumerable
                .Range(0, 50)
                .Select(async _ =>
                {
                    try
                    {
                        await fixture.ReserveAsync(
                            owner,
                            environment,
                            400,
                            10_000,
                            new SpendAccountPin(SpendAccountClass.Subscription)
                        );
                        return (string?)null;
                    }
                    catch (WhatsAppCapabilityUnavailableException refusal)
                    {
                        return refusal.ReasonCode;
                    }
                })
        );

        var accepted = outcomes.Count(code => code is null);
        Assert.InRange(accepted, 1, 25);
        Assert.All(
            outcomes.Where(code => code is not null),
            code =>
                Assert.Contains(
                    code!,
                    new[] { "COMBINED_DAILY_COST_EXHAUSTED", "ENVIRONMENT_SPEND_LEASE_UNAVAILABLE" }
                )
        );
        Assert.Equal(
            accepted,
            await fixture.ScalarAsync<long>(
                $"SELECT count(*) FROM business.environment_spend_attempts WHERE environment='{environment}'"
            )
        );
        Assert.InRange(await fixture.ExposureAsync(environment), 1, 10_000);
    }

    [Fact]
    public async Task ExpiredLeaseReturnsItsUnusedHeadroom()
    {
        var environment = await fixture.NewEnvironmentAsync();
        var owner = fixture.LeaseOwner(LeaseOptions(seconds: 5), out _);
        var start = DateTimeOffset.UtcNow;

        await fixture.ReserveAsync(
            owner,
            environment,
            400,
            2_500,
            new SpendAccountPin(SpendAccountClass.Subscription),
            start
        );
        Assert.Equal(2_500, await fixture.ExposureAsync(environment, start));

        var later = start.AddSeconds(10);
        await fixture.ReserveAsync(
            owner,
            environment,
            400,
            2_500,
            new SpendAccountPin(SpendAccountClass.Subscription),
            later
        );

        Assert.Equal(
            "EXPIRED",
            await fixture.ScalarAsync<string>(
                $"""
                SELECT state FROM business.environment_spend_leases
                WHERE environment='{environment}' ORDER BY granted_at LIMIT 1
                """
            )
        );
        Assert.Equal(
            400L,
            await fixture.ScalarAsync<long>(
                $"""
                SELECT consumed_paise FROM business.environment_spend_leases
                WHERE environment='{environment}' ORDER BY granted_at LIMIT 1
                """
            )
        );
        Assert.Equal(2_500, await fixture.ExposureAsync(environment, later));
    }

    [Fact]
    public async Task ReturnedLeaseKeepsReservedAndSettledSpendCounted()
    {
        var environment = await fixture.NewEnvironmentAsync();
        var owner = fixture.LeaseOwner(LeaseOptions(), out var leases);
        var permit = await fixture.ReserveAsync(
            owner,
            environment,
            400,
            2_500,
            new SpendAccountPin(SpendAccountClass.Subscription)
        );

        await new PostgresEnvironmentSpendLeaseStore(fixture.Conversations).CloseAsync(
            Guid.Parse(
                await fixture.ScalarAsync<string>(
                    $"SELECT lease_id::text FROM business.environment_spend_leases WHERE environment='{environment}'"
                )
            ),
            CancellationToken.None
        );

        Assert.Equal(400, await fixture.ExposureAsync(environment));
        await fixture.SettleAsync(owner, permit, 300, release: false);
        Assert.Equal(300, await fixture.ExposureAsync(environment));
        Assert.Equal(2_500, leases.LeaseSizePaise);
    }

    [Fact]
    public async Task UnresolvedAttemptStaysCountedWhenItsLeaseIsReturned()
    {
        var environment = await fixture.NewEnvironmentAsync();
        var owner = fixture.LeaseOwner(LeaseOptions(), out _);
        await fixture.ReserveAsync(
            owner,
            environment,
            400,
            2_500,
            new SpendAccountPin(SpendAccountClass.Subscription)
        );
        await fixture.ExecuteAsync(
            $"""
            INSERT INTO business.environment_spend_attempts
                (environment,owner_kind,attempt_id,original_tenant_id,activation_digest,
                 request_digest,reservation_reference,reserved_paise,state,reserved_at,lease_id)
            SELECT '{environment}','MODEL',gen_random_uuid(),gen_random_uuid(),'activation',
                repeat('c',64),gen_random_uuid(),700,'RECONCILIATION_REQUIRED',clock_timestamp(),lease_id
            FROM business.environment_spend_leases WHERE environment='{environment}'
            """
        );

        await fixture.ExecuteAsync(
            $"""
            UPDATE business.environment_spend_leases SET state='RETURNED'
            WHERE environment='{environment}'
            """
        );

        Assert.Equal(1_100, await fixture.ExposureAsync(environment));
    }

    [Fact]
    public async Task LeaseSizeNeverExceedsRemainingHeadroom()
    {
        var environment = await fixture.NewEnvironmentAsync();
        var owner = fixture.LeaseOwner(LeaseOptions(), out _);
        var pin = new SpendAccountPin(SpendAccountClass.Subscription);

        await fixture.ReserveAsync(owner, environment, 600, 1_000, pin);
        Assert.Equal(1_000, await fixture.ExposureAsync(environment));
        var refused = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            fixture.ReserveAsync(owner, environment, 600, 1_000, pin)
        );

        Assert.Equal("COMBINED_DAILY_COST_EXHAUSTED", refused.ReasonCode);
        Assert.InRange(await fixture.ExposureAsync(environment), 1, 1_000);
    }

    [Fact]
    public async Task GlobalLockModeKeepsTheDirectCeilingCheck()
    {
        var environment = await fixture.NewEnvironmentAsync();
        var owner = new ConversationEnvironmentSpendOwner(new EnvironmentSpendOptions());
        var pin = new SpendAccountPin(SpendAccountClass.Subscription);

        await fixture.ReserveAsync(owner, environment, 6_000, 10_000, pin);
        var refused = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            fixture.ReserveAsync(owner, environment, 5_000, 10_000, pin)
        );

        Assert.Equal("COMBINED_DAILY_COST_EXHAUSTED", refused.ReasonCode);
        Assert.Equal(6_000, await fixture.ExposureAsync(environment));
        Assert.Equal(
            0L,
            await fixture.ScalarAsync<long>(
                $"SELECT count(*) FROM business.environment_spend_leases WHERE environment='{environment}'"
            )
        );
    }

    [Fact]
    public async Task OversizedReservationUsesTheDirectPathInLeaseMode()
    {
        var environment = await fixture.NewEnvironmentAsync();
        var owner = fixture.LeaseOwner(LeaseOptions(), out _);

        await fixture.ReserveAsync(
            owner,
            environment,
            4_000,
            10_000,
            new SpendAccountPin(SpendAccountClass.Subscription)
        );

        Assert.Equal(4_000, await fixture.ExposureAsync(environment));
        Assert.Equal(
            0L,
            await fixture.ScalarAsync<long>(
                $"SELECT count(*) FROM business.environment_spend_leases WHERE environment='{environment}'"
            )
        );
    }

    private static EnvironmentSpendOptions LeaseOptions(int seconds = 120) =>
        new()
        {
            Mode = EnvironmentSpendOptions.LeasesMode,
            LeaseSizeInr = 25,
            LeaseSeconds = seconds,
        };
}
