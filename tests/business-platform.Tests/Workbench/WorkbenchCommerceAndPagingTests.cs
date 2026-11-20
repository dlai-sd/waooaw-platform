// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Nodes;
using Moq;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchCommerceAndPagingTests
{
    private static readonly DateTimeOffset PeriodEnd = new(2030, 1, 31, 0, 0, 0, TimeSpan.Zero);
    private static readonly Guid PackageId = Guid.Parse("40000000-0000-0000-0000-000000000004");

    private static async Task<string> VersionAsync(WorkbenchHarness harness)
    {
        var relationship = await harness.Relationships.GetAsync(
            harness.TenantId,
            harness.RelationshipId,
            CancellationToken.None
        );
        return WorkbenchProjectionService.VersionOf(relationship!);
    }

    private static JsonElement Json(string text) => JsonDocument.Parse(text).RootElement.Clone();

    private static OwnerPackagePage Page(string? next = null, params Guid[] ids) =>
        new(
            ids.Select(id => new OwnerPackage(
                    id,
                    id == PackageId ? "GROWTH" : "OTHER",
                    "Package",
                    "NEUTRAL",
                    "1.0.0",
                    30,
                    11800,
                    10000,
                    1800,
                    18,
                    []
                ))
                .ToArray(),
            next
        );

    private static void ReturnsPackages(WorkbenchHarness harness, params OwnerPackagePage[] pages)
    {
        var sequence = harness.Packages.SetupSequence(item =>
            item.ListAsync(
                It.IsAny<Guid>(),
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<string?>(),
                It.IsAny<int>(),
                It.IsAny<string>(),
                It.IsAny<CancellationToken>()
            )
        );
        foreach (var page in pages)
            sequence = sequence.ReturnsAsync(page);
    }

    private static void WalletIsAvailable(WorkbenchHarness harness) =>
        harness
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(
                new WorkbenchCommercialSnapshot(true, "projection-1", PeriodEnd, [], false, null)
            );

    private static void CaptureSubmit(
        WorkbenchHarness harness,
        WorkbenchCommercialCommandResult answer,
        out Func<JsonObject?> captured
    )
    {
        JsonObject? payload = null;
        harness
            .Commercial.Setup(item =>
                item.SubmitAsync(
                    It.IsAny<WorkbenchContext>(),
                    It.IsAny<Guid>(),
                    It.IsAny<string>(),
                    It.IsAny<JsonObject>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .Callback<WorkbenchContext, Guid, string, JsonObject, CancellationToken>(
                (_, _, _, body, _) => payload = body
            )
            .ReturnsAsync(answer);
        captured = () => payload;
    }

    [Fact]
    public void Paging_DefaultsToTheFirstPageOfTwentyFive()
    {
        var page = WorkbenchPaging.Parse(null, null, out var problem);

        Assert.Null(problem);
        Assert.Equal(0, page.Offset);
        Assert.Equal(WorkbenchPaging.DefaultLimit, page.Limit);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(101)]
    public void Paging_RefusesALimitOutsideOneToOneHundred(int limit)
    {
        WorkbenchPaging.Parse(null, limit, out var problem);

        Assert.Equal("limit must be 1 to 100.", problem);
    }

    [Theory]
    [InlineData("")]
    [InlineData("guessed")]
    [InlineData("o1.!!!")]
    public void Paging_RefusesACursorThisServiceDidNotIssue(string cursor)
    {
        WorkbenchPaging.Parse(cursor, 10, out var problem);

        Assert.NotNull(problem);
    }

    [Fact]
    public void Paging_WalksEveryItemOnceThroughTheIssuedCursors()
    {
        var all = Enumerable.Range(1, 7).ToArray();
        var seen = new List<int>();
        string? cursor = null;
        var pages = 0;

        do
        {
            var page = WorkbenchPaging.Parse(cursor, 3, out var problem);
            Assert.Null(problem);
            var (items, next) = WorkbenchPaging.Slice(all, page);
            seen.AddRange(items);
            cursor = next;
            pages++;
        } while (cursor is not null);

        Assert.Equal(all, seen);
        Assert.Equal(3, pages);
    }

    [Fact]
    public async Task Consume_RedeemsAHandoffOnceForItsParticipant_AndRefusesAnyOtherUse()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        var context = harness.Context();
        var issued = await harness.Commands.CreateHandoffAsync(
            context,
            Guid.NewGuid(),
            new CreateWorkbenchHandoffRequest("1.0", await VersionAsync(harness), "APPROVAL"),
            CancellationToken.None
        );
        var request = new ConsumeWorkbenchHandoffRequest("1.0", issued.Body.DestinationRef);

        var stranger = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.ConsumeHandoffAsync(
                harness.Context(participant: Guid.NewGuid()),
                request,
                CancellationToken.None
            )
        );
        var redeemed = await harness.Commands.ConsumeHandoffAsync(
            context,
            request,
            CancellationToken.None
        );
        var second = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.ConsumeHandoffAsync(context, request, CancellationToken.None)
        );

        Assert.Equal(404, stranger.Status);
        Assert.Equal("APPROVAL", redeemed.Purpose);
        Assert.Equal(404, second.Status);
        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, second.Code);
    }

    [Fact]
    public async Task Consume_WithAnInvalidBody_IsRefusedAsInvalid()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var version = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.ConsumeHandoffAsync(
                harness.Context(),
                new ConsumeWorkbenchHandoffRequest("2.0", "h-token"),
                CancellationToken.None
            )
        );
        var blank = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.ConsumeHandoffAsync(
                harness.Context(),
                new ConsumeWorkbenchHandoffRequest("1.0", " "),
                CancellationToken.None
            )
        );

        Assert.Equal(400, version.Status);
        Assert.Equal(400, blank.Status);
    }

    [Fact]
    public async Task TopUp_IsRefusedBecauseBillingPublishesNoTopUpRoute_AndNeverCallsBilling()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            harness.Commands.CreateTopupAsync(
                harness.Context(WorkbenchAudiences.CustomerOwner),
                Guid.NewGuid(),
                new CreateWorkbenchTopupRequest("1.0", "relationship-1", "PROACTIVE_MESSAGE", 5),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendCommercialUnavailable, failure.Code);
        Assert.Equal(WorkbenchProjectionService.TopUpNotOffered, failure.Detail);
        harness.Commercial.Verify(
            item =>
                item.SubmitAsync(
                    It.IsAny<WorkbenchContext>(),
                    It.IsAny<Guid>(),
                    It.IsAny<string>(),
                    It.IsAny<JsonObject>(),
                    It.IsAny<CancellationToken>()
                ),
            Times.Never
        );
    }

    [Fact]
    public async Task Wallet_NeverOffersATopUp_EvenWhenBillingSaysAPackageAllowsOne()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        harness
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(
                new WorkbenchCommercialSnapshot(true, "projection-1", PeriodEnd, [], true, null)
            );

        var wallet = await harness.Projection.GetWalletAsync(
            harness.Context(WorkbenchAudiences.CustomerOwner),
            CancellationToken.None
        );

        Assert.False(wallet.TopUpAvailable);
    }

    [Fact]
    public async Task Upgrade_CommandsBillingByPackageCode_AndReportsTheFeeFromTheOutcome()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        WalletIsAvailable(harness);
        ReturnsPackages(harness, Page("next", Guid.NewGuid()), Page(null, PackageId));
        var commandId = Guid.NewGuid();
        CaptureSubmit(
            harness,
            new WorkbenchCommercialCommandResult(
                "COMPLETED",
                commandId,
                false,
                null,
                Json(
                    $$"""{"commandId":"{{commandId}}","status":"COMPLETED","effectiveAt":"2030-01-05T00:00:00Z","proratedFeeDifferencePaise":1500}"""
                )
            ),
            out var payload
        );

        var result = await harness.Commands.ChangeSubscriptionAsync(
            harness.Context(WorkbenchAudiences.CustomerOwner),
            Guid.NewGuid(),
            new SubscriptionChangeRequest("1.0", await VersionAsync(harness), "UPGRADE", PackageId),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal(1500L, result.Body.ProratedFeeDifferencePaise);
        Assert.Equal(commandId, result.Body.OperationRef);
        Assert.Equal(
            new DateTimeOffset(2030, 1, 5, 0, 0, 0, TimeSpan.Zero),
            result.Body.EffectiveAt
        );
        Assert.Equal("UPGRADE_PACKAGE", payload()!["commandKind"]!.GetValue<string>());
        Assert.Equal("GROWTH", payload()!["targetPackageCode"]!.GetValue<string>());
        Assert.False(payload()!.ContainsKey("targetPackageId"));
    }

    [Fact]
    public async Task Upgrade_ToAPackageThatIsNotOnSale_IsRefusedAsInvalid()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        WalletIsAvailable(harness);
        ReturnsPackages(harness, Page(null, Guid.NewGuid()));

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await harness.Commands.ChangeSubscriptionAsync(
                harness.Context(WorkbenchAudiences.CustomerOwner),
                Guid.NewGuid(),
                new SubscriptionChangeRequest(
                    "1.0",
                    await VersionAsync(harness),
                    "UPGRADE",
                    PackageId
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, failure.Code);
    }

    [Fact]
    public async Task Upgrade_WhenTheCatalogueIsDown_IsUnavailableAndSendsNothingToBilling()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        WalletIsAvailable(harness);
        harness
            .Packages.Setup(item =>
                item.ListAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<string>(),
                    It.IsAny<string>(),
                    It.IsAny<string>(),
                    It.IsAny<string?>(),
                    It.IsAny<int>(),
                    It.IsAny<string>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ThrowsAsync(new PackageCatalogUnavailableException("down"));

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await harness.Commands.ChangeSubscriptionAsync(
                harness.Context(WorkbenchAudiences.CustomerOwner),
                Guid.NewGuid(),
                new SubscriptionChangeRequest(
                    "1.0",
                    await VersionAsync(harness),
                    "UPGRADE",
                    PackageId
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendCommercialUnavailable, failure.Code);
        harness.Commercial.Verify(
            item =>
                item.SubmitAsync(
                    It.IsAny<WorkbenchContext>(),
                    It.IsAny<Guid>(),
                    It.IsAny<string>(),
                    It.IsAny<JsonObject>(),
                    It.IsAny<CancellationToken>()
                ),
            Times.Never
        );
    }

    [Fact]
    public async Task Terminate_ReportsTheBillingAdjustmentAndAHumanizedBlockedReason()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        WalletIsAvailable(harness);
        var commandId = Guid.NewGuid();
        CaptureSubmit(
            harness,
            new WorkbenchCommercialCommandResult(
                "BLOCKED",
                commandId,
                false,
                null,
                Json(
                    $$"""{"commandId":"{{commandId}}","status":"BLOCKED","blockedReason":"POLICY_ABSENT","refundFeePaise":0}"""
                )
            ),
            out var payload
        );

        var result = await harness.Commands.ChangeSubscriptionAsync(
            harness.Context(WorkbenchAudiences.CustomerOwner),
            Guid.NewGuid(),
            new SubscriptionChangeRequest("1.0", await VersionAsync(harness), "TERMINATE"),
            CancellationToken.None
        );

        Assert.Equal("BLOCKED", result.Body.Status);
        Assert.Equal("Policy absent", result.Body.BlockedReason);
        Assert.Equal(0L, result.Body.RefundFeePaise);
        Assert.Equal("TERMINATE_RELATIONSHIP", payload()!["commandKind"]!.GetValue<string>());
        Assert.False(payload()!.ContainsKey("targetPackageCode"));
    }

    [Theory]
    [InlineData("CONFLICT", 409, WorkbenchProblemCodes.VersionConflict)]
    [InlineData("REJECTED", 400, WorkbenchProblemCodes.RequestInvalid)]
    [InlineData("UNAVAILABLE", 503, WorkbenchProblemCodes.SpendCommercialUnavailable)]
    [InlineData("UNKNOWN", 503, WorkbenchProblemCodes.SpendCommercialUnavailable)]
    public async Task Pause_MapsTheOwnersRefusalStatusToATypedProblem(
        string status,
        int http,
        string code
    )
    {
        var harness = await WorkbenchHarness.CreateAsync();
        WalletIsAvailable(harness);
        CaptureSubmit(
            harness,
            new WorkbenchCommercialCommandResult(status, Guid.NewGuid(), false, null, null),
            out _
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await harness.Commands.ChangeSubscriptionAsync(
                harness.Context(WorkbenchAudiences.CustomerOwner),
                Guid.NewGuid(),
                new SubscriptionChangeRequest("1.0", await VersionAsync(harness), "PAUSE"),
                CancellationToken.None
            )
        );

        Assert.Equal(http, failure.Status);
        Assert.Equal(code, failure.Code);
    }

    [Theory]
    [InlineData("PAUSE", "skill-1", null)]
    [InlineData("UPGRADE", null, "item")]
    public async Task SubscriptionChange_RefusesFieldsTheBillingOwnerDoesNotTake(
        string kind,
        string? skillId,
        string? item
    )
    {
        var harness = await WorkbenchHarness.CreateAsync();
        var selections = item is null
            ? null
            : new List<SubscriptionChangeSelection> { new("component-1", ["item-1"]) };

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await harness.Commands.ChangeSubscriptionAsync(
                harness.Context(WorkbenchAudiences.CustomerOwner),
                Guid.NewGuid(),
                new SubscriptionChangeRequest(
                    "1.0",
                    await VersionAsync(harness),
                    kind,
                    kind == "UPGRADE" ? PackageId : null,
                    skillId,
                    selections
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
    }

    [Fact]
    public void Reader_ReadsTheRefusalFromDetailAsAStringOrAnObject()
    {
        Assert.Equal(
            "WBE_COMMERCIAL_CONFLICT",
            AuthenticatedWorkbenchCommercialReader.ProblemCode(
                Json("""{"detail":"WBE_COMMERCIAL_CONFLICT"}""")
            )
        );
        Assert.Equal(
            "WALLET_INSUFFICIENT",
            AuthenticatedWorkbenchCommercialReader.ProblemCode(
                Json("""{"detail":{"code":"WALLET_INSUFFICIENT"}}""")
            )
        );
        Assert.Equal(
            "LEGACY",
            AuthenticatedWorkbenchCommercialReader.ProblemCode(Json("""{"code":"LEGACY"}"""))
        );
        Assert.Null(
            AuthenticatedWorkbenchCommercialReader.ProblemCode(
                Json("""{"detail":[{"loc":["body"]}]}""")
            )
        );
        Assert.Null(AuthenticatedWorkbenchCommercialReader.ProblemCode(Json("[]")));
    }

    [Fact]
    public void Reader_ParsesTheComponentsIncludingTheProactiveMessageAllowance()
    {
        var relationship = Guid.NewGuid();
        var projection = Json(
            $$$"""
            {"schemaVersion":"1.0","relationshipId":"{{{relationship}}}","projectionVersion":"abc","currencyState":"CURRENT",
             "wallet":{"periodEnd":"2030-01-31T00:00:00Z","topUpAvailable":true,
               "components":[{"componentId":"PROACTIVE_MESSAGE","label":"Proactive message","remaining":12,"quantity":30}]}}
            """
        );

        var snapshot = AuthenticatedWorkbenchCommercialReader.Parse(projection, relationship);

        Assert.True(snapshot.Available);
        Assert.Equal("abc", snapshot.ProjectionVersion);
        var component = Assert.Single(snapshot.Components);
        Assert.Equal("PROACTIVE_MESSAGE", component.ComponentId);
        Assert.Equal(12, component.Remaining);
        Assert.Equal(30, component.Quantity);
        Assert.Null(snapshot.Limitation);
    }

    [Fact]
    public void Reader_AnEmptyComponentListIsAValue_AndAStaleProjectionIsSaidToBeStale()
    {
        var relationship = Guid.NewGuid();
        var projection = Json(
            $$$"""
            {"schemaVersion":"1.0","relationshipId":"{{{relationship}}}","projectionVersion":"abc","currencyState":"STALE",
             "wallet":{"periodEnd":"2030-01-31T00:00:00Z","topUpAvailable":false,"components":[]}}
            """
        );

        var snapshot = AuthenticatedWorkbenchCommercialReader.Parse(projection, relationship);

        Assert.True(snapshot.Available);
        Assert.Empty(snapshot.Components);
        Assert.Equal(AuthenticatedWorkbenchCommercialReader.FiguresMayBeStale, snapshot.Limitation);
    }

    [Fact]
    public void Reader_AProjectionForAnotherRelationshipIsUnavailable()
    {
        var projection = Json(
            $$"""{"schemaVersion":"1.0","relationshipId":"{{Guid.NewGuid()}}","projectionVersion":"abc"}"""
        );

        var snapshot = AuthenticatedWorkbenchCommercialReader.Parse(projection, Guid.NewGuid());

        Assert.False(snapshot.Available);
    }
}
