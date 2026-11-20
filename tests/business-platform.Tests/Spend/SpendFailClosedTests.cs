// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-05
// Constitutional basis: C-023, C-059, C-063
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Spend;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Spend;

public sealed class SpendFailClosedTests(EnvironmentSpendPostgresFixture fixture)
    : IClassFixture<EnvironmentSpendPostgresFixture>
{
    [Fact]
    public async Task UnreachableCommercialOwnerRefusesWithoutDispatch()
    {
        var gateway = new FakeGateway(unavailable: true);

        var refusal = await Assert.ThrowsAsync<SpendRefusedException>(() =>
            CommercialReservationGate.ReserveAsync(
                gateway,
                SpendAccountClass.Subscription,
                Identity(),
                10,
                CancellationToken.None
            )
        );

        Assert.Equal(SpendRefusalCodes.CommercialUnavailable, refusal.Code);
        Assert.Equal(503, refusal.StatusCode);
        Assert.IsType<OfferingUsageOwnerUnavailableException>(refusal.InnerException);
        Assert.Equal(1, gateway.ReserveCalls);
    }

    [Fact]
    public async Task UnconfiguredGatewayRefusesMeteredAccountClasses()
    {
        foreach (
            var accountClass in new[]
            {
                SpendAccountClass.Trial,
                SpendAccountClass.Subscription,
                SpendAccountClass.Acquisition,
            }
        )
            await Assert.ThrowsAsync<SpendRefusedException>(() =>
                CommercialReservationGate.ReserveAsync(
                    new UnconfiguredOfferingUsageGateway(),
                    accountClass,
                    Identity(),
                    10,
                    CancellationToken.None
                )
            );
    }

    [Fact]
    public async Task PlatformFloorNeverCallsTheCommercialOwner()
    {
        var gateway = new FakeGateway(unavailable: true);

        var receipt = await CommercialReservationGate.ReserveAsync(
            gateway,
            SpendAccountClass.PlatformFloor,
            Identity(),
            10,
            CancellationToken.None
        );

        Assert.Null(receipt);
        Assert.Equal(0, gateway.ReserveCalls);
    }

    [Fact]
    public async Task ReachableOwnerReceiptIsReturnedUnchanged()
    {
        var gateway = new FakeGateway(unavailable: false);

        var receipt = await CommercialReservationGate.ReserveAsync(
            gateway,
            SpendAccountClass.Subscription,
            Identity(),
            10,
            CancellationToken.None
        );

        Assert.NotNull(receipt);
        Assert.Equal("RESERVED", receipt.State);
        Assert.Equal(1, gateway.ReserveCalls);
    }

    [Fact]
    public async Task UnknownOutcomeKeepsTheReservationCountedUntilReconciled()
    {
        var environment = await fixture.NewEnvironmentAsync();
        var owner = new ConversationEnvironmentSpendOwner();
        await fixture.InsertUnresolvedAttemptAsync(environment, 2_500);

        Assert.Equal(2_500, await fixture.ExposureAsync(environment));
        var fenced = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            fixture.ReserveAsync(
                owner,
                environment,
                100,
                100_000,
                new SpendAccountPin(SpendAccountClass.Subscription)
            )
        );
        Assert.Equal("ENVIRONMENT_SPEND_ADMISSION_FENCED", fenced.ReasonCode);
        Assert.Equal(2_500, await fixture.ExposureAsync(environment));
    }

    [Fact]
    public async Task PlatformFloorSpendIsCountedButNotFenced()
    {
        var environment = await fixture.NewEnvironmentAsync();
        var owner = new ConversationEnvironmentSpendOwner();
        await fixture.InsertUnresolvedAttemptAsync(environment, 1_000);

        await fixture.ReserveAsync(
            owner,
            environment,
            400,
            100_000,
            new SpendAccountPin(SpendAccountClass.PlatformFloor)
        );

        Assert.Equal(1_400, await fixture.ExposureAsync(environment));
        Assert.Equal(
            "PLATFORM_FLOOR",
            await fixture.ScalarAsync<string>(
                $"""
                SELECT account_class FROM business.environment_spend_attempts
                WHERE environment='{environment}' AND reserved_paise=400
                """
            )
        );
    }

    [Fact]
    public async Task PlatformFloorIsNotRefusedByTheCeiling()
    {
        var environment = await fixture.NewEnvironmentAsync(authorityMaximumPaise: 1_000);
        var owner = new ConversationEnvironmentSpendOwner();

        await fixture.ReserveAsync(
            owner,
            environment,
            900,
            1_000,
            new SpendAccountPin(SpendAccountClass.PlatformFloor)
        );
        await fixture.ReserveAsync(
            owner,
            environment,
            900,
            1_000,
            new SpendAccountPin(SpendAccountClass.PlatformFloor)
        );
        var refused = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            fixture.ReserveAsync(
                owner,
                environment,
                100,
                1_000,
                new SpendAccountPin(SpendAccountClass.Subscription)
            )
        );

        Assert.Equal("COMBINED_DAILY_COST_EXHAUSTED", refused.ReasonCode);
        Assert.Equal(1_800, await fixture.ExposureAsync(environment));
    }

    [Fact]
    public void BaseSpecDefaultsToFailClosedFreePath()
    {
        var spec = File.ReadAllText(
            RepositoryPaths.Resolve("architecture/reference/agents/AGENT-BASE-SPEC.md")
        );
        var guide = File.ReadAllText(
            RepositoryPaths.Resolve("architecture/reference/agents/AGENT-AUTHORING-GUIDE.md")
        );

        Assert.Contains("wbe_unavailable:  \"fail_closed_free_path\"", spec);
        Assert.DoesNotContain("wbe_unavailable:  \"continue_silent\"", spec);
        Assert.DoesNotContain("wbe_unavailable: \"continue_silent\"", guide);
    }

    private static OfferingUsageIdentity Identity() =>
        new(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            "marketing",
            "1.0.0",
            "skill",
            "1.0.0",
            Guid.NewGuid(),
            Guid.NewGuid(),
            "component",
            Guid.NewGuid(),
            new string('a', 64),
            Guid.NewGuid()
        );

    private sealed class FakeGateway(bool unavailable) : IAuthenticatedOfferingUsageGateway
    {
        public int ReserveCalls { get; private set; }

        public Task<OfferingUsageReceipt> ReserveAsync(
            OfferingUsageIdentity identity,
            long maximumUnits,
            CancellationToken ct
        )
        {
            ReserveCalls++;
            if (unavailable)
                throw new OfferingUsageOwnerUnavailableException("owner unreachable");
            return Task.FromResult(
                new OfferingUsageReceipt(
                    Guid.NewGuid(),
                    "RESERVED",
                    maximumUnits,
                    maximumUnits,
                    maximumUnits,
                    "thread",
                    Guid.NewGuid(),
                    "v1",
                    false
                )
            );
        }

        public Task<OfferingUsageReceipt> SettleAsync(
            OfferingUsageIdentity identity,
            Guid reservationId,
            long actualUnits,
            Guid evidenceId,
            CancellationToken ct
        ) => throw new NotSupportedException();

        public Task<OfferingUsageReceipt> ReleaseAsync(
            OfferingUsageIdentity identity,
            Guid reservationId,
            Guid nonDispatchEvidenceId,
            CancellationToken ct
        ) => throw new NotSupportedException();

        public Task<OfferingUsageReceipt?> ReconcileAsync(
            OfferingUsageIdentity identity,
            Guid? reservationId,
            CancellationToken ct
        ) => throw new NotSupportedException();
    }
}
