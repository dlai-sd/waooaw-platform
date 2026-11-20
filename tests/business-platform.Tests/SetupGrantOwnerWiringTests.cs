// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
// constitutional_basis: C-023, C-059, C-063, C-076
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Spend;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>The owner's setup-grant wiring, exercised with fakes and no database.</summary>
public sealed class SetupGrantOwnerWiringTests
{
    private sealed class FakeAccounts : IPlatformAccountGateway
    {
        public string DrawStatus { get; set; } = SetupGrantDrawReceipt.Reserved;
        public bool Unavailable { get; set; }
        public List<(
            string Call,
            Guid Tenant,
            Guid Actor,
            Guid Relationship,
            long Paise,
            Guid Key
        )> Calls { get; } = [];
        public List<string> Components { get; } = [];

        public Task<SetupGrantDrawReceipt> ReserveSetupGrantAsync(
            Guid tenantId,
            Guid actorId,
            Guid relationshipId,
            string agentType,
            string agentVersion,
            string componentId,
            long maximumPaise,
            Guid invocationId,
            Guid ownerEvidenceId,
            Guid idempotencyKey,
            CancellationToken ct
        )
        {
            if (Unavailable)
                throw new OfferingUsageOwnerUnavailableException("down");
            Calls.Add(("reserve", tenantId, actorId, relationshipId, maximumPaise, idempotencyKey));
            Components.Add($"{agentType}/{agentVersion}/{componentId}");
            var reserved = DrawStatus == SetupGrantDrawReceipt.Reserved;
            return Task.FromResult(
                new SetupGrantDrawReceipt(
                    DrawStatus,
                    Guid.NewGuid(),
                    reserved ? Guid.NewGuid() : null,
                    reserved ? maximumPaise : 0,
                    false
                )
            );
        }

        public Task<WalletReservationOutcome> SettleAccountAsync(
            Guid tenantId,
            Guid actorId,
            Guid reservationId,
            long actualPaise,
            Guid evidenceId,
            Guid idempotencyKey,
            CancellationToken ct
        )
        {
            Calls.Add(("settle", tenantId, actorId, Guid.Empty, actualPaise, idempotencyKey));
            return Task.FromResult(
                new WalletReservationOutcome(
                    reservationId,
                    Guid.NewGuid(),
                    "SETTLED",
                    actualPaise,
                    actualPaise,
                    0,
                    false,
                    false
                )
            );
        }

        public Task<WalletReservationOutcome> ReleaseAccountAsync(
            Guid tenantId,
            Guid actorId,
            Guid reservationId,
            Guid nonDispatchEvidenceId,
            Guid idempotencyKey,
            CancellationToken ct
        )
        {
            Calls.Add(("release", tenantId, actorId, Guid.Empty, 0, idempotencyKey));
            return Task.FromResult(
                new WalletReservationOutcome(
                    reservationId,
                    Guid.NewGuid(),
                    "RELEASED",
                    0,
                    null,
                    0,
                    false,
                    false
                )
            );
        }

        public Task<PlatformAccountReceipt> ReserveAccountAsync(
            PlatformAccountReserveRequest request,
            CancellationToken ct
        ) => throw new NotSupportedException();

        public Task<SetupGrantReceipt> OpenSetupGrantAsync(
            Guid tenantId,
            Guid actorId,
            Guid relationshipId,
            string agentType,
            string agentVersion,
            Guid idempotencyKey,
            CancellationToken ct
        ) => throw new NotSupportedException();
    }

    private static readonly InferenceCaller Caller = new(
        Guid.NewGuid(),
        Guid.NewGuid(),
        Guid.NewGuid(),
        "OWNER",
        Guid.NewGuid(),
        Guid.NewGuid(),
        Guid.NewGuid()
    );

    private static OfferingUsageIdentity Identity() =>
        new(
            Caller.TenantId,
            Caller.RelationshipId,
            Caller.ActorId,
            Guid.NewGuid(),
            "DMA",
            "1.0.0",
            "skill-1",
            "1",
            Guid.NewGuid(),
            Guid.NewGuid(),
            "llm_cloud",
            Guid.NewGuid(),
            "digest",
            Guid.NewGuid()
        );

    [Fact]
    public async Task AReservedDrawBecomesASetupGrantReceiptForTheCallerRelationshipWithAWholePaiseCeiling()
    {
        var accounts = new FakeAccounts();
        var identity = Identity();

        var receipt = await SetupGrantOwnerWiring.ReserveAsync(
            accounts,
            Caller,
            identity,
            12.2m,
            CancellationToken.None
        );

        var call = Assert.Single(accounts.Calls);
        Assert.Equal(
            ("reserve", Caller.TenantId, Caller.ActorId, Caller.RelationshipId, 13L),
            (call.Call, call.Tenant, call.Actor, call.Relationship, call.Paise)
        );
        Assert.Equal(identity.IdempotencyKey, call.Key);
        Assert.Equal("DMA/1.0.0/llm_cloud", Assert.Single(accounts.Components));
        Assert.Equal("RESERVED", receipt.State);
        Assert.Equal(13, receipt.ReservedMarkedUpPaise);
        Assert.Equal(SpendAccountClass.SetupGrant.ToStorage(), receipt.CatalogueThreadId);
        Assert.False(receipt.Replayed);
    }

    [Fact]
    public async Task ASubPaiseCostStillReservesOnePaise()
    {
        var accounts = new FakeAccounts();

        await SetupGrantOwnerWiring.ReserveAsync(
            accounts,
            Caller,
            Identity(),
            0.01m,
            CancellationToken.None
        );

        Assert.Equal(1, Assert.Single(accounts.Calls).Paise);
    }

    [Fact]
    public async Task ExhaustionRefusesWithTheSetupGrantCodeAndAnUnavailableOwnerFailsClosed()
    {
        var exhausted = await Assert.ThrowsAsync<SpendRefusedException>(() =>
            SetupGrantOwnerWiring.ReserveAsync(
                new FakeAccounts { DrawStatus = SetupGrantDrawReceipt.Exhausted },
                Caller,
                Identity(),
                5m,
                CancellationToken.None
            )
        );
        var unavailable = await Assert.ThrowsAsync<SpendRefusedException>(() =>
            SetupGrantOwnerWiring.ReserveAsync(
                new FakeAccounts { Unavailable = true },
                Caller,
                Identity(),
                5m,
                CancellationToken.None
            )
        );
        var withoutGateway = await Assert.ThrowsAsync<SpendRefusedException>(() =>
            SetupGrantOwnerWiring.ReserveAsync(null, Caller, Identity(), 5m, CancellationToken.None)
        );

        Assert.Equal(SetupGrantReservationGate.ExhaustedCode, exhausted.Code);
        Assert.Equal(SpendRefusalCodes.CommercialUnavailable, unavailable.Code);
        Assert.Equal(SpendRefusalCodes.CommercialUnavailable, withoutGateway.Code);
    }

    [Fact]
    public async Task SettlementUsesAStableKeyDifferentFromTheReleaseKeyAndReleaseSendsNoCost()
    {
        var accounts = new FakeAccounts();
        var reservation = Guid.NewGuid();

        await SetupGrantOwnerWiring.SettleAsync(
            accounts,
            Caller,
            reservation,
            false,
            7.4m,
            Guid.NewGuid(),
            CancellationToken.None
        );
        await SetupGrantOwnerWiring.SettleAsync(
            accounts,
            Caller,
            reservation,
            true,
            7.4m,
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(new[] { "settle", "release" }, accounts.Calls.Select(call => call.Call));
        Assert.Equal(8, accounts.Calls[0].Paise);
        Assert.Equal(
            SetupGrantOwnerWiring.IdempotencyKey(reservation, false),
            accounts.Calls[0].Key
        );
        Assert.Equal(
            SetupGrantOwnerWiring.IdempotencyKey(reservation, true),
            accounts.Calls[1].Key
        );
        Assert.NotEqual(accounts.Calls[0].Key, accounts.Calls[1].Key);
        Assert.Equal(
            SetupGrantOwnerWiring.IdempotencyKey(reservation, false),
            SetupGrantOwnerWiring.IdempotencyKey(reservation, false)
        );
        Assert.All(
            accounts.Calls,
            call => Assert.Equal((Caller.TenantId, Caller.ActorId), (call.Tenant, call.Actor))
        );
    }

    [Fact]
    public async Task SettlingWithoutAGatewayFailsClosed()
    {
        var refusal = await Assert.ThrowsAsync<SpendRefusedException>(() =>
            SetupGrantOwnerWiring.SettleAsync(
                null,
                Caller,
                Guid.NewGuid(),
                false,
                1m,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(SpendRefusalCodes.CommercialUnavailable, refusal.Code);
    }
}
