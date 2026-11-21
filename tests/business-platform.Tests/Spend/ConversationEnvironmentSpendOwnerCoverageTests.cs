// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-05
// Constitutional basis: C-023, C-059, C-063, C-088
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Spend;
using Waooaw.BusinessPlatform.Tests.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ConversationEnvironmentSpendOwnerValidationTests
{
    private static readonly string Digest = new('a', 64);

    private static Task<EnvironmentSpendPermit> ReserveAsync(
        ConversationStoreDbContext? db,
        string environment = "dev",
        string ownerKind = "MODEL",
        Guid? attemptId = null,
        Guid? reference = null,
        long paise = 100,
        long limit = 1_000,
        string? digest = null
    ) =>
        new ConversationEnvironmentSpendOwner().ReserveAsync(
            db!,
            environment,
            ownerKind,
            attemptId ?? Guid.NewGuid(),
            Guid.NewGuid(),
            "activation",
            digest ?? Digest,
            reference ?? Guid.NewGuid(),
            paise,
            limit,
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );

    public static TheoryData<string, string, Guid, Guid, long, long, string> InvalidIdentities =>
        new()
        {
            { "", "MODEL", Guid.NewGuid(), Guid.NewGuid(), 1, 1, "a" },
            { new string('e', 33), "MODEL", Guid.NewGuid(), Guid.NewGuid(), 1, 1, "a" },
            { "dev", "OTHER", Guid.NewGuid(), Guid.NewGuid(), 1, 1, "a" },
            { "dev", "MODEL", Guid.Empty, Guid.NewGuid(), 1, 1, "a" },
            { "dev", "MODEL", Guid.NewGuid(), Guid.Empty, 1, 1, "a" },
            { "dev", "MODEL", Guid.NewGuid(), Guid.NewGuid(), -1, 1, "a" },
            { "dev", "MODEL", Guid.NewGuid(), Guid.NewGuid(), 1, -1, "a" },
            { "dev", "MODEL", Guid.NewGuid(), Guid.NewGuid(), 1, 1, "short" },
            { "dev", "MODEL", Guid.NewGuid(), Guid.NewGuid(), 1, 1, "B" },
            { "dev", "MODEL", Guid.NewGuid(), Guid.NewGuid(), 1, 1, "z" },
        };

    [Theory]
    [MemberData(nameof(InvalidIdentities))]
    public async Task An_invalid_identity_is_refused_before_any_database_work(
        string environment,
        string ownerKind,
        Guid attemptId,
        Guid reference,
        long paise,
        long limit,
        string digestKind
    )
    {
        var digest = digestKind switch
        {
            "short" => "abc",
            "B" => new string('A', 64),
            "z" => new string('z', 64),
            _ => Digest,
        };

        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            ReserveAsync(null, environment, ownerKind, attemptId, reference, paise, limit, digest)
        );

        Assert.Equal("ENVIRONMENT_SPEND_IDENTITY_INVALID", failure.ReasonCode);
    }

    [Fact]
    public async Task A_store_that_is_not_relational_grants_a_permit_without_spend_tracking()
    {
        await using var db = new ConversationStoreDbContext(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
                .Options
        );
        var attempt = Guid.NewGuid();
        var reference = Guid.NewGuid();

        var permit = await ReserveAsync(
            db,
            attemptId: attempt,
            reference: reference,
            digest: "sha256:" + Digest
        );
        await new ConversationEnvironmentSpendOwner().SettleAsync(
            db,
            "dev",
            "MODEL",
            attempt,
            reference,
            50,
            false,
            Guid.NewGuid(),
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );

        Assert.Equal(
            new EnvironmentSpendPermit("dev", "MODEL", attempt, reference, 100, 100, 1_000),
            permit
        );
    }
}

[Collection(Wc136PostgresFixture.CollectionName)]
public sealed class ConversationEnvironmentSpendOwnerCoverageTests(Wc136PostgresFixture fixture)
{
    private static readonly string Digest = new('b', 64);

    private sealed record Request(
        string Environment,
        Guid AttemptId,
        Guid Tenant,
        string Activation,
        string Digest,
        Guid Reference,
        long Paise
    )
    {
        public static Request For(string environment, long paise = 1_000) =>
            new(
                environment,
                Guid.NewGuid(),
                Guid.NewGuid(),
                "activation",
                ConversationEnvironmentSpendOwnerCoverageTests.Digest,
                Guid.NewGuid(),
                paise
            );
    }

    private async Task<EnvironmentSpendPermit> ReserveAsync(
        ConversationEnvironmentSpendOwner owner,
        Request request,
        long limit = 1_000_000,
        TaskCompletionSource? inserted = null,
        Task? commitGate = null,
        SpendAccountPin? pin = null
    )
    {
        await using var db = fixture.AdminConversations.CreateDbContext();
        await using var transaction = await db.Database.BeginTransactionAsync();
        var permit = await owner.ReserveAsync(
            db,
            request.Environment,
            "MODEL",
            request.AttemptId,
            request.Tenant,
            request.Activation,
            request.Digest,
            request.Reference,
            request.Paise,
            limit,
            DateTimeOffset.UtcNow,
            CancellationToken.None,
            pin
        );
        inserted?.TrySetResult();
        if (commitGate is not null)
            await commitGate;
        await transaction.CommitAsync();
        return permit;
    }

    private async Task SettleAsync(
        ConversationEnvironmentSpendOwner owner,
        EnvironmentSpendPermit permit,
        long actual,
        bool release,
        Guid? reference = null,
        Guid? attemptId = null
    )
    {
        await using var db = fixture.AdminConversations.CreateDbContext();
        await using var transaction = await db.Database.BeginTransactionAsync();
        await owner.SettleAsync(
            db,
            permit.Environment,
            permit.OwnerKind,
            attemptId ?? permit.AttemptId,
            reference ?? permit.ReservationReference,
            actual,
            release,
            Guid.NewGuid(),
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        await transaction.CommitAsync();
    }

    private static ConversationEnvironmentSpendOwner LeaseOwner(
        IEnvironmentSpendLeaseStore store
    ) =>
        new(
            new EnvironmentSpendOptions
            {
                Mode = EnvironmentSpendOptions.LeasesMode,
                LeaseSizeInr = 25,
                LeaseSeconds = 120,
            },
            new EnvironmentSpendLeaseService(
                store,
                new EnvironmentSpendOptions
                {
                    Mode = EnvironmentSpendOptions.LeasesMode,
                    LeaseSizeInr = 25,
                    LeaseSeconds = 120,
                }
            )
        );

    private Task<long> CountAttemptsAsync(string environment) =>
        fixture.ScalarAsync<long>(
            $"SELECT count(*) FROM business.environment_spend_attempts WHERE environment='{environment}'"
        );

    [Fact]
    public async Task An_inactive_authority_refuses_with_reconciliation_required()
    {
        var environment = await fixture.NewEnvironmentAsync(active: false);

        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            ReserveAsync(new ConversationEnvironmentSpendOwner(), Request.For(environment))
        );

        Assert.Equal("ENVIRONMENT_SPEND_RECONCILIATION_REQUIRED", failure.ReasonCode);
        Assert.Equal(0, await CountAttemptsAsync(environment));
    }

    [Fact]
    public async Task Repeating_a_reservation_returns_the_same_permit_without_a_second_row()
    {
        var environment = await fixture.NewEnvironmentAsync(10_000);
        var owner = new ConversationEnvironmentSpendOwner();
        var request = Request.For(environment, 2_500);

        var first = await ReserveAsync(owner, request);
        var second = await ReserveAsync(owner, request);

        Assert.Equal(first.ReservedPaise, second.ReservedPaise);
        Assert.Equal(request.Reference, second.ReservationReference);
        Assert.Equal(2_500, second.ExposurePaise);
        Assert.Equal(1, await CountAttemptsAsync(environment));
    }

    [Fact]
    public async Task A_replay_that_differs_from_the_original_is_a_state_conflict()
    {
        var environment = await fixture.NewEnvironmentAsync(100_000);
        var owner = new ConversationEnvironmentSpendOwner();
        var original = Request.For(environment, 2_000);
        await ReserveAsync(owner, original);

        foreach (
            var changed in new[]
            {
                original with
                {
                    Tenant = Guid.NewGuid(),
                },
                original with
                {
                    Activation = "other-activation",
                },
                original with
                {
                    Digest = new string('c', 64),
                },
                original with
                {
                    Reference = Guid.NewGuid(),
                },
                original with
                {
                    Paise = 2_001,
                },
            }
        )
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ReserveAsync(owner, changed)
            );

        Assert.Equal(1, await CountAttemptsAsync(environment));
    }

    [Fact]
    public async Task A_concurrent_duplicate_on_the_lease_path_replays_the_winner()
    {
        var environment = await fixture.NewEnvironmentAsync(100_000);
        var owner = LeaseOwner(new PostgresEnvironmentSpendLeaseStore(fixture.AdminConversations));
        var request = Request.For(environment, 1_000);
        var inserted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);

        var winner = ReserveAsync(owner, request, inserted: inserted, commitGate: release.Task);
        await inserted.Task;
        var loser = ReserveAsync(owner, request);
        await Task.Delay(750);
        Assert.False(loser.IsCompleted);
        release.SetResult();

        var winnerPermit = await winner;
        var loserPermit = await loser;

        Assert.Equal(winnerPermit.ReservationReference, loserPermit.ReservationReference);
        Assert.Equal(1_000, loserPermit.ReservedPaise);
        Assert.Equal(1, await CountAttemptsAsync(environment));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task A_pinned_account_is_stored_with_the_attempt_on_both_admission_paths(
        bool leases
    )
    {
        var environment = await fixture.NewEnvironmentAsync(100_000);
        var owner = leases
            ? LeaseOwner(new PostgresEnvironmentSpendLeaseStore(fixture.AdminConversations))
            : new ConversationEnvironmentSpendOwner();
        var wallet = Guid.NewGuid();
        var request = Request.For(environment, 1_000);

        await ReserveAsync(
            owner,
            request,
            pin: new SpendAccountPin(SpendAccountClass.Acquisition, wallet)
        );

        Assert.Equal(
            "ACQUISITION",
            await fixture.ScalarAsync<string>(
                $"SELECT account_class FROM business.environment_spend_attempts WHERE attempt_id='{request.AttemptId}'"
            )
        );
        Assert.Equal(
            wallet,
            await fixture.ScalarAsync<Guid>(
                $"SELECT pinned_wallet_account_id FROM business.environment_spend_attempts WHERE attempt_id='{request.AttemptId}'"
            )
        );
    }

    [Fact]
    public async Task The_platform_floor_is_counted_but_not_refused_by_the_ceiling()
    {
        var environment = await fixture.NewEnvironmentAsync(500);
        var owner = LeaseOwner(new PostgresEnvironmentSpendLeaseStore(fixture.AdminConversations));
        var floor = new SpendAccountPin(SpendAccountClass.PlatformFloor);

        var permit = await ReserveAsync(
            owner,
            Request.For(environment, 900),
            limit: 500,
            pin: floor
        );
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            ReserveAsync(owner, Request.For(environment, 900), limit: 500)
        );

        Assert.Equal(900, permit.ExposurePaise);
        Assert.Equal(500, permit.MaximumPaise);
        Assert.Equal(1, await CountAttemptsAsync(environment));
    }

    [Fact]
    public async Task A_lease_that_is_not_live_twice_refuses_with_lease_unavailable()
    {
        var environment = await fixture.NewEnvironmentAsync(100_000);
        var store = new PhantomLeaseStore();
        var owner = LeaseOwner(store);

        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            ReserveAsync(owner, Request.For(environment, 1_000))
        );

        Assert.Equal("ENVIRONMENT_SPEND_LEASE_UNAVAILABLE", failure.ReasonCode);
        Assert.Equal(2, store.Grants);
        Assert.Equal(0, await CountAttemptsAsync(environment));
    }

    [Fact]
    public async Task Settling_twice_the_same_way_is_idempotent_and_changing_the_outcome_conflicts()
    {
        var environment = await fixture.NewEnvironmentAsync(100_000);
        var owner = new ConversationEnvironmentSpendOwner();
        var permit = await ReserveAsync(owner, Request.For(environment, 2_000));

        await SettleAsync(owner, permit, 1_500, release: false);
        await SettleAsync(owner, permit, 1_500, release: false);

        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            SettleAsync(owner, permit, 1_400, release: false)
        );
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            SettleAsync(owner, permit, 0, release: true)
        );
        Assert.Equal(
            "SETTLED",
            await fixture.ScalarAsync<string>(
                $"SELECT state FROM business.environment_spend_attempts WHERE attempt_id='{permit.AttemptId}'"
            )
        );
    }

    [Fact]
    public async Task A_release_is_idempotent_and_records_zero_actual_spend()
    {
        var environment = await fixture.NewEnvironmentAsync(100_000);
        var owner = new ConversationEnvironmentSpendOwner();
        var permit = await ReserveAsync(owner, Request.For(environment, 2_000));

        await SettleAsync(owner, permit, 999, release: true);
        await SettleAsync(owner, permit, 123, release: true);

        Assert.Equal(
            0L,
            await fixture.ScalarAsync<long>(
                $"SELECT actual_paise FROM business.environment_spend_attempts WHERE attempt_id='{permit.AttemptId}'"
            )
        );
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            SettleAsync(owner, permit, 10, release: false)
        );
    }

    [Fact]
    public async Task Settling_above_the_reservation_marks_an_overrun()
    {
        var environment = await fixture.NewEnvironmentAsync(100_000);
        var owner = new ConversationEnvironmentSpendOwner();
        var permit = await ReserveAsync(owner, Request.For(environment, 1_000));

        await SettleAsync(owner, permit, 1_200, release: false);

        Assert.True(
            await fixture.ScalarAsync<bool>(
                $"SELECT overrun FROM business.environment_spend_attempts WHERE attempt_id='{permit.AttemptId}'"
            )
        );
    }

    [Fact]
    public async Task Settling_with_the_wrong_reference_or_an_unknown_attempt_is_refused()
    {
        var environment = await fixture.NewEnvironmentAsync(100_000);
        var owner = new ConversationEnvironmentSpendOwner();
        var permit = await ReserveAsync(owner, Request.For(environment, 1_000));

        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            SettleAsync(owner, permit, 10, false, reference: Guid.NewGuid())
        );
        await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
            SettleAsync(owner, permit, 10, false, attemptId: Guid.NewGuid())
        );
        Assert.Equal(
            "RESERVED",
            await fixture.ScalarAsync<string>(
                $"SELECT state FROM business.environment_spend_attempts WHERE attempt_id='{permit.AttemptId}'"
            )
        );
    }

    [Fact]
    public async Task Settling_in_lease_mode_does_not_take_the_environment_lock()
    {
        var environment = await fixture.NewEnvironmentAsync(100_000);
        var owner = LeaseOwner(new PostgresEnvironmentSpendLeaseStore(fixture.AdminConversations));
        var permit = await ReserveAsync(owner, Request.For(environment, 1_000));

        await SettleAsync(owner, permit, 800, release: false);

        Assert.Equal(
            800L,
            await fixture.ScalarAsync<long>(
                $"SELECT actual_paise FROM business.environment_spend_attempts WHERE attempt_id='{permit.AttemptId}'"
            )
        );
    }

    private sealed class PhantomLeaseStore : IEnvironmentSpendLeaseStore
    {
        public int Grants { get; private set; }

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
            Grants++;
            return Task.FromResult<EnvironmentSpendLease?>(
                new(Guid.NewGuid(), environment, leaseSizePaise, now + duration)
            );
        }

        public Task CloseAsync(Guid leaseId, CancellationToken ct) => Task.CompletedTask;
    }
}
