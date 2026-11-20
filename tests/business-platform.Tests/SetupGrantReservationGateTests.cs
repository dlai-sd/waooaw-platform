// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
// constitutional_basis: C-023, C-059, C-063, C-076
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Spend;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class SetupGrantReservationGateTests
{
    private sealed class FakeAccounts : IPlatformAccountGateway
    {
        public string DrawStatus { get; set; } = SetupGrantDrawReceipt.Reserved;
        public bool Unavailable { get; set; }
        public List<string> Calls { get; } = [];

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
            Calls.Add("reserve");
            if (Unavailable)
                throw new OfferingUsageOwnerUnavailableException("down");
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
            Calls.Add("settle");
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
            Calls.Add("release");
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

    private static Task<SetupGrantDraw> DrawAsync(FakeAccounts accounts) =>
        SetupGrantReservationGate.ReserveAsync(
            accounts,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            "DMA",
            "1.0.0",
            "llm_cloud",
            200,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

    [Fact]
    public async Task AReservedDrawCarriesTheReservationAndNoCustomerText()
    {
        var draw = await DrawAsync(new FakeAccounts());

        Assert.False(draw.Exhausted);
        Assert.NotNull(draw.ReservationId);
        Assert.Equal(200, draw.ReservedPaise);
        Assert.Null(draw.ConversationText);
    }

    [Fact]
    public async Task ExhaustionIsATypedResultWithConversationalTextAndNoReservation()
    {
        var draw = await DrawAsync(
            new FakeAccounts { DrawStatus = SetupGrantDrawReceipt.Exhausted }
        );

        Assert.True(draw.Exhausted);
        Assert.Null(draw.ReservationId);
        Assert.Equal(SetupGrantReservationGate.ExhaustedConversationText, draw.ConversationText);
        Assert.DoesNotContain("paise", draw.ConversationText!, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task AnUnavailableOwnerFailsClosedAsACommercialRefusal()
    {
        var refusal = await Assert.ThrowsAsync<SpendRefusedException>(() =>
            DrawAsync(new FakeAccounts { Unavailable = true })
        );

        Assert.Equal(SpendRefusalCodes.CommercialUnavailable, refusal.Code);
    }

    [Theory]
    [InlineData(150, "settle")]
    [InlineData(0, "release")]
    public async Task ZeroActualCostReleasesAndPositiveCostSettles(long actual, string expected)
    {
        var accounts = new FakeAccounts();

        await SetupGrantReservationGate.SettleOrReleaseAsync(
            accounts,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            actual,
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(new[] { expected }, accounts.Calls);
    }
}
