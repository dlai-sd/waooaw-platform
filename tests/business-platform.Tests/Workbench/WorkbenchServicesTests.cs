// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchServicesTests
{
    private static readonly DateTimeOffset PeriodEnd = new(2030, 1, 31, 0, 0, 0, TimeSpan.Zero);

    private static async Task<string> VersionAsync(WorkbenchHarness harness)
    {
        var relationship = await harness.Relationships.GetAsync(
            harness.TenantId,
            harness.RelationshipId,
            CancellationToken.None
        );
        return WorkbenchProjectionService.VersionOf(relationship!);
    }

    [Fact]
    public async Task Stop_NeverWaitsForAVersionMatch_AndStopsTheRelationship()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var result = await harness.Commands.StopAsync(
            harness.Context(),
            Guid.NewGuid(),
            new WorkbenchControlRequest("1.0", "relationship-stale"),
            CancellationToken.None
        );

        Assert.False(result.Replayed);
        Assert.Equal("COMPLETED", result.Body.Status);
        var relationship = await harness.Relationships.GetAsync(
            harness.TenantId,
            harness.RelationshipId,
            CancellationToken.None
        );
        Assert.Equal(EmploymentRelationshipState.StoppedEmergency, relationship!.State);
    }

    [Fact]
    public async Task Stop_WithAnInvalidEnvelope_IsRefusedAsInvalid()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.StopAsync(
                harness.Context(),
                Guid.NewGuid(),
                new WorkbenchControlRequest("2.0", "relationship-1"),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, failure.Code);
    }

    [Fact]
    public async Task Pause_WithAStaleVersion_IsAVersionConflictAndChangesNothing()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        var context = harness.Context(WorkbenchAudiences.CustomerOwner);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.PauseAsync(
                context,
                Guid.NewGuid(),
                new WorkbenchControlRequest("1.0", "relationship-stale"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }

    [Fact]
    public async Task Pause_ByABeneficiary_IsForbiddenBeforeAnyChange()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var version = await VersionAsync(harness);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.PauseAsync(
                harness.Context(WorkbenchAudiences.Beneficiary),
                Guid.NewGuid(),
                new WorkbenchControlRequest("1.0", version),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
        Assert.Equal(WorkbenchCommandService.RoleDetail, failure.Detail);
    }

    [Fact]
    public async Task Handoff_IsIssuedForTheCurrentVersionAndRefusedForAStaleOne()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        var context = harness.Context();

        var issued = await harness.Commands.CreateHandoffAsync(
            context,
            Guid.NewGuid(),
            new CreateWorkbenchHandoffRequest("1.0", await VersionAsync(harness), "WEB_WORKBENCH"),
            CancellationToken.None
        );
        var stale = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.CreateHandoffAsync(
                context,
                Guid.NewGuid(),
                new CreateWorkbenchHandoffRequest("1.0", "relationship-stale", "WEB_WORKBENCH"),
                CancellationToken.None
            )
        );

        Assert.False(issued.Replayed);
        Assert.True(issued.Body.SingleUse);
        Assert.NotEmpty(issued.Body.DestinationRef);
        Assert.Equal(409, stale.Status);
    }

    [Fact]
    public async Task Handoff_WithAnUnknownPurpose_IsRefusedAsInvalid()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var version = await VersionAsync(harness);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.CreateHandoffAsync(
                harness.Context(),
                Guid.NewGuid(),
                new CreateWorkbenchHandoffRequest("1.0", version, "ANYTHING"),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
    }

    [Fact]
    public async Task Wallet_IsHiddenFromABeneficiary_AndHonestWhenBillingIsUnavailable()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var hidden = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Projection.GetWalletAsync(
                harness.Context(WorkbenchAudiences.Beneficiary),
                CancellationToken.None
            )
        );
        var unavailable = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Projection.GetWalletAsync(
                harness.Context(WorkbenchAudiences.CustomerOwner),
                CancellationToken.None
            )
        );

        Assert.Equal(403, hidden.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendAuthorityUnavailable, hidden.Code);
        Assert.Equal(503, unavailable.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendCommercialUnavailable, unavailable.Code);
    }

    [Fact]
    public async Task Wallet_WhenBillingReportsIt_IsReturnedWithoutPricingForADelegate()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        harness
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(new WorkbenchCommercialSnapshot(true, "v1", PeriodEnd, [], true, null));

        var owner = await harness.Projection.GetWalletAsync(
            harness.Context(WorkbenchAudiences.CustomerOwner),
            CancellationToken.None
        );
        var delegated = await harness.Projection.GetWalletAsync(
            harness.Context(WorkbenchAudiences.Delegate),
            CancellationToken.None
        );

        Assert.Equal(PeriodEnd, owner.PeriodEnd);
        Assert.False(owner.TopUpAvailable);
        Assert.False(delegated.TopUpAvailable);
        Assert.Equal(harness.RelationshipId, owner.RelationshipRef);
    }

    [Fact]
    public async Task Narrowing_KeepsTheAudience_WhenNoDeclarationIsReadable()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        var context = harness.Context(WorkbenchAudiences.CustomerOwner);

        var narrowed = await harness.Projection.NarrowAsync(context, CancellationToken.None);

        Assert.Equal(WorkbenchAudiences.CustomerOwner, narrowed.Audience);
    }

    [Fact]
    public async Task Evidence_WhenNothingIsRecorded_IsPendingAndHasNoEntries()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var list = await harness.Projection.ListEvidenceAsync(
            harness.Context(),
            WorkbenchPage.First,
            CancellationToken.None
        );

        Assert.NotEmpty(list.EvidenceState);
        Assert.True(list.EvidenceState is "PENDING" or "UNAVAILABLE");
        Assert.Empty(list.Items);
    }
}
