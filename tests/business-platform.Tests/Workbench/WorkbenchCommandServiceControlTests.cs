// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Nodes;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchCommandServiceControlTests
{
    private static WorkbenchControlRequest Control(string version, string? reason = null) =>
        new("1.0", version, reason);

    private static ExportWorkbenchEvidenceRequest Export(
        string version,
        string scope = "RELATIONSHIP",
        string format = "PDF",
        string? scopeRef = null,
        string? from = null,
        string? to = null,
        string schema = "1.0"
    ) => new(schema, version, scope, format, scopeRef, from, to);

    [Theory]
    [InlineData("RELATIONSHIP", "PDF", null, null)]
    [InlineData("GOAL", "JSON", "goal-ref", null)]
    [InlineData("PLAN", "JSON", null, null)]
    [InlineData("PERIOD", "PDF", null, "2030-01-01")]
    public async Task Export_CreatesTheOwnersExportAndAnswersCompleted(
        string scope,
        string format,
        string? scopeRef,
        string? from
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var relationship = await fixture.RelationshipAsync();
        var context = fixture.Employer();

        var result = await fixture.Commands.ExportEvidenceAsync(
            context,
            Guid.NewGuid(),
            Export(
                await fixture.VersionAsync(),
                scope,
                format,
                scopeRef,
                from,
                from is null ? null : "2030-02-01"
            ),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.False(result.Replayed);
        Assert.Equal(result.Body.OperationRef.ToString("D"), result.Body.ResourceRef);
        Assert.Equal(context.CorrelationId, result.Body.CorrelationId);
        Assert.Equal(WorkbenchProjectionService.VersionOf(relationship), result.Body.Version);
    }

    [Fact]
    public async Task Export_ReplaysTheSameCommandAndKeepsTheOriginalExport()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var key = Guid.NewGuid();
        var request = Export(await fixture.VersionAsync());

        var first = await fixture.Commands.ExportEvidenceAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );
        var second = await fixture.Commands.ExportEvidenceAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );

        Assert.True(second.Replayed);
        Assert.True(second.Body.Replayed);
        Assert.Equal(first.Body.OperationRef, second.Body.OperationRef);
    }

    [Fact]
    public async Task Export_ReusingAKeyForADifferentExportIsAConflict()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var key = Guid.NewGuid();
        var version = await fixture.VersionAsync();
        await fixture.Commands.ExportEvidenceAsync(
            fixture.Employer(),
            key,
            Export(version),
            CancellationToken.None
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ExportEvidenceAsync(
                fixture.Employer(),
                key,
                Export(version, format: "JSON"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.IdempotencyConflict, failure.Code);
    }

    public static TheoryData<string, string, string, string?, string?, string?> InvalidExports() =>
        new()
        {
            { "9.9", "RELATIONSHIP", "PDF", null, null, null },
            { "1.0", "EVERYTHING", "PDF", null, null, null },
            { "1.0", "RELATIONSHIP", "XML", null, null, null },
            { "1.0", "GOAL", "PDF", "", null, null },
            { "1.0", "GOAL", "PDF", "r", null, null },
            { "1.0", "PERIOD", "PDF", null, null, null },
            { "1.0", "PERIOD", "PDF", null, "2030-01-01", null },
            { "1.0", "PERIOD", "PDF", null, "yesterday", "2030-01-01" },
            { "1.0", "PERIOD", "PDF", null, "2030-03-01", "2030-02-01" },
        };

    [Theory]
    [MemberData(nameof(InvalidExports))]
    public async Task Export_RejectsAnInvalidRequestBeforeTouchingTheOwner(
        string schema,
        string scope,
        string format,
        string? scopeRef,
        string? from,
        string? to
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        if (scopeRef == "r")
            scopeRef = new string('r', 129);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ExportEvidenceAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Export("relationship-1", scope, format, scopeRef, from, to, schema),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, failure.Code);
        Assert.Equal(0, fixture.Constitutional.CallCount);
    }

    [Fact]
    public async Task Export_IsRefusedWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ExportEvidenceAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Export("relationship-0"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }

    [Fact]
    public async Task Export_MapsAnEvidenceCommitmentOutageToUnavailable()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        fixture.Constitutional.FailNext = true;

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ExportEvidenceAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Export(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.Unavailable, failure.Code);
    }

    [Fact]
    public async Task Export_ReportsAnUnknownRelationshipAsNotFound()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var stranger = fixture.Employer() with { RelationshipId = Guid.NewGuid() };

        await Assert.ThrowsAsync<KeyNotFoundException>(() =>
            fixture.Commands.ExportEvidenceAsync(
                stranger,
                Guid.NewGuid(),
                Export("relationship-1"),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task Stop_LatchesTheEmergencyStopEvenWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var context = fixture.Manager();

        var result = await fixture.Commands.StopAsync(
            context,
            Guid.NewGuid(),
            Control("relationship-0", " shop is closing "),
            CancellationToken.None
        );

        var stopped = await fixture.RelationshipAsync();
        Assert.Equal(EmploymentRelationshipState.StoppedEmergency, stopped.State);
        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal(WorkbenchProjectionService.VersionOf(stopped), result.Body.Version);
        Assert.Equal(context.RelationshipId.ToString("D"), result.Body.ResourceRef);
    }

    [Fact]
    public async Task Stop_OfAnAlreadyStoppedRelationshipChangesNothingAndStillCompletes()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(
            EmploymentRelationshipState.StoppedEmergency
        );
        var before = await fixture.RelationshipAsync();

        var result = await fixture.Commands.StopAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            Control("relationship-1"),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal(before.StateVersion, (await fixture.RelationshipAsync()).StateVersion);
        Assert.Empty(fixture.StopGateway.ExecutionIds);
    }

    [Fact]
    public async Task Stop_ReplaysTheSameCommandWithoutStoppingTwice()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var key = Guid.NewGuid();
        var request = Control("relationship-1");

        var first = await fixture.Commands.StopAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );
        var second = await fixture.Commands.StopAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );

        Assert.True(second.Replayed);
        Assert.Equal(first.Body.OperationRef, second.Body.OperationRef);
    }

    [Fact]
    public async Task Stop_WhenTheRuntimeCannotBeReachedIsUnavailableAndTheStopIsNotReportedDone()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        fixture.StopGateway.Failure = new InvalidOperationException("runtime unreachable");

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.StopAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Control("relationship-1"),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.Unavailable, failure.Code);
        Assert.NotEqual(
            EmploymentRelationshipState.StoppedEmergency,
            (await fixture.RelationshipAsync()).State
        );
    }

    [Theory]
    [InlineData("9.9", "v", null)]
    [InlineData("1.0", "", null)]
    [InlineData("1.0", "v", " ")]
    public async Task Stop_RejectsAnInvalidRequest(string schema, string version, string? reason)
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.StopAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                new WorkbenchControlRequest(schema, version, reason),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Equal(EmploymentRelationshipState.Active, (await fixture.RelationshipAsync()).State);
    }

    [Fact]
    public async Task Pause_MovesAnActiveRelationshipToPaused()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var context = fixture.Employer();

        var result = await fixture.Commands.PauseAsync(
            context,
            Guid.NewGuid(),
            Control(await fixture.VersionAsync(), " holiday "),
            CancellationToken.None
        );

        var paused = await fixture.RelationshipAsync();
        Assert.Equal(EmploymentRelationshipState.Paused, paused.State);
        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal(WorkbenchProjectionService.VersionOf(paused), result.Body.Version);
        Assert.Equal(context.RelationshipId.ToString("D"), result.Body.ResourceRef);
    }

    [Fact]
    public async Task Pause_OfAnAlreadyPausedRelationshipChangesNothingAndStillCompletes()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(
            EmploymentRelationshipState.Paused
        );
        var before = await fixture.RelationshipAsync();

        var result = await fixture.Commands.PauseAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            Control(await fixture.VersionAsync()),
            CancellationToken.None
        );

        var after = await fixture.RelationshipAsync();
        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal(before.StateVersion, after.StateVersion);
    }

    [Fact]
    public async Task Pause_ReplaysTheSameCommandWithoutPausingTwice()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var key = Guid.NewGuid();
        var request = Control(await fixture.VersionAsync());

        var first = await fixture.Commands.PauseAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );
        var second = await fixture.Commands.PauseAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );

        Assert.True(second.Replayed);
        Assert.Equal(first.Body.OperationRef, second.Body.OperationRef);
    }

    [Fact]
    public async Task Pause_IsRefusedFromAStateThatMayNotBePausedWithAnExplanation()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(
            EmploymentRelationshipState.Interviewing
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.PauseAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Control(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(422, failure.Status);
        Assert.Contains("current state", failure.Detail);
        Assert.Equal(
            EmploymentRelationshipState.Interviewing,
            (await fixture.RelationshipAsync()).State
        );
    }

    [Fact]
    public async Task Pause_MapsAnEvidenceCommitmentOutageToUnavailable()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        fixture.Constitutional.FailNext = true;

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.PauseAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Control(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(EmploymentRelationshipState.Active, (await fixture.RelationshipAsync()).State);
    }

    [Fact]
    public async Task Pause_IsRefusedForAnAudienceThatMayNotDecide()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.PauseAsync(
                fixture.Evaluator(),
                Guid.NewGuid(),
                Control("relationship-1"),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
        Assert.Equal(WorkbenchCommandService.RoleDetail, failure.Detail);
    }

    [Fact]
    public async Task Pause_IsRefusedOnAStoppedRelationship()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(
            EmploymentRelationshipState.StoppedEmergency
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.PauseAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Control(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Contains("stopped", failure.Detail);
    }

    [Fact]
    public async Task Pause_IsRefusedWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.PauseAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Control("relationship-0"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }

    [Theory]
    [InlineData("", false)]
    [InlineData("   ", false)]
    [InlineData("r", true)]
    public async Task Pause_RejectsAReasonOutsideOneToFiveHundredCharacters(
        string reason,
        bool tooLong
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.PauseAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Control("relationship-1", tooLong ? new string(reason[0], 501) : reason),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains("reason", failure.Detail);
    }

    [Theory]
    [InlineData("WEB_WORKBENCH", null)]
    [InlineData("APPROVAL", "decision-ref")]
    [InlineData("PAYMENT", null)]
    [InlineData("EVIDENCE", null)]
    public async Task Handoff_IssuesAOneTimeLinkThatTheSameParticipantCanRedeemOnce(
        string purpose,
        string? contextRef
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var context = fixture.Employer();

        var created = await fixture.Commands.CreateHandoffAsync(
            context,
            Guid.NewGuid(),
            new CreateWorkbenchHandoffRequest(
                "1.0",
                await fixture.VersionAsync(),
                purpose,
                contextRef
            ),
            CancellationToken.None
        );

        Assert.True(created.Body.SingleUse);
        Assert.False(string.IsNullOrWhiteSpace(created.Body.DestinationRef));
        var redeemed = await fixture.Commands.ConsumeHandoffAsync(
            context,
            new ConsumeWorkbenchHandoffRequest("1.0", created.Body.DestinationRef),
            CancellationToken.None
        );
        Assert.Equal(purpose, redeemed.Purpose);
        Assert.Equal(contextRef, redeemed.ContextRef);
        var again = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ConsumeHandoffAsync(
                context,
                new ConsumeWorkbenchHandoffRequest("1.0", created.Body.DestinationRef),
                CancellationToken.None
            )
        );
        Assert.Equal(404, again.Status);
    }

    [Fact]
    public async Task Handoff_AnotherParticipantCannotRedeemTheLink()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var created = await fixture.Commands.CreateHandoffAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            new CreateWorkbenchHandoffRequest("1.0", await fixture.VersionAsync(), "APPROVAL"),
            CancellationToken.None
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ConsumeHandoffAsync(
                fixture.Manager(),
                new ConsumeWorkbenchHandoffRequest("1.0", created.Body.DestinationRef),
                CancellationToken.None
            )
        );

        Assert.Equal(404, failure.Status);
        Assert.Contains("not valid any more", failure.Detail);
    }

    [Fact]
    public async Task Handoff_ReplaysTheSameCommandWithTheSameLink()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var key = Guid.NewGuid();
        var request = new CreateWorkbenchHandoffRequest(
            "1.0",
            await fixture.VersionAsync(),
            "WEB_WORKBENCH"
        );

        var first = await fixture.Commands.CreateHandoffAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );
        var second = await fixture.Commands.CreateHandoffAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );

        Assert.True(second.Replayed);
        Assert.Equal(first.Body.HandoffRef, second.Body.HandoffRef);
        Assert.Equal(first.Body.DestinationRef, second.Body.DestinationRef);
    }

    [Theory]
    [InlineData("9.9", "x", "WEB_WORKBENCH", null)]
    [InlineData("1.0", "", "WEB_WORKBENCH", null)]
    [InlineData("1.0", "x", "TELEPORT", null)]
    [InlineData("1.0", "x", "WEB_WORKBENCH", "")]
    public async Task Handoff_RejectsAnInvalidRequest(
        string schema,
        string version,
        string purpose,
        string? contextRef
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CreateHandoffAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                new CreateWorkbenchHandoffRequest(schema, version, purpose, contextRef),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
    }

    [Fact]
    public async Task Handoff_IsRefusedWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CreateHandoffAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                new CreateWorkbenchHandoffRequest("1.0", "relationship-0", "WEB_WORKBENCH"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
    }

    [Theory]
    [InlineData("9.9", "dest")]
    [InlineData("1.0", "")]
    [InlineData("1.0", "d")]
    public async Task ConsumeHandoff_RejectsAnInvalidRequest(string schema, string destination)
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        if (destination == "d")
            destination = new string('d', 129);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ConsumeHandoffAsync(
                fixture.Employer(),
                new ConsumeWorkbenchHandoffRequest(schema, destination),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
    }

    [Fact]
    public async Task ConsumeHandoff_AnUnknownLinkLooksLikeAnyOtherInvalidLink()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ConsumeHandoffAsync(
                fixture.Employer(),
                new ConsumeWorkbenchHandoffRequest("1.0", "never-issued"),
                CancellationToken.None
            )
        );

        Assert.Equal(404, failure.Status);
        Assert.Contains("Ask for a new one", failure.Detail);
    }

    [Fact]
    public async Task Topup_IsRefusedDeterministicallyBecauseBillingPublishesNoPrice()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CreateTopupAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                new CreateWorkbenchTopupRequest("1.0", "version-1", "component", 5),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendCommercialUnavailable, failure.Code);
        Assert.Equal(WorkbenchProjectionService.TopUpNotOffered, failure.Detail);
    }

    [Fact]
    public async Task Topup_IsRefusedForAnAudienceThatMayNotManageSpend()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CreateTopupAsync(
                fixture.Manager(),
                Guid.NewGuid(),
                new CreateWorkbenchTopupRequest("1.0", "version-1", "component", 5),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendAuthorityUnavailable, failure.Code);
    }

    [Theory]
    [InlineData("9.9", "component", 5)]
    [InlineData("1.0", "", 5)]
    [InlineData("1.0", "c", 5)]
    [InlineData("1.0", "component", 0)]
    [InlineData("1.0", "component", 1001)]
    public async Task Topup_RejectsAnInvalidRequestBeforeCheckingSpendAuthority(
        string schema,
        string component,
        int quantity
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        if (component == "c")
            component = new string('c', 161);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CreateTopupAsync(
                fixture.Manager(),
                Guid.NewGuid(),
                new CreateWorkbenchTopupRequest(schema, "version-1", component, quantity),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
    }
}

public sealed class WorkbenchCommandServiceSubscriptionTests
{
    private static readonly Guid PackageId = Guid.Parse("7f2e1f0a-6c0f-4a43-8f6e-0c2f0f6f0a11");

    private static JsonElement Json(string text) => JsonDocument.Parse(text).RootElement.Clone();

    private static void WalletIs(
        WorkbenchCommandServiceFixture fixture,
        WorkbenchCommercialSnapshot snapshot
    ) =>
        fixture
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(snapshot);

    private static void WalletIsAvailable(WorkbenchCommandServiceFixture fixture) =>
        WalletIs(
            fixture,
            new WorkbenchCommercialSnapshot(true, "projection-7", null, [], false, null)
        );

    private static Func<(string Projection, JsonObject Payload)?> BillingAnswers(
        WorkbenchCommandServiceFixture fixture,
        WorkbenchCommercialCommandResult? answer
    )
    {
        (string, JsonObject)? captured = null;
        fixture
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
                (_, _, projection, payload, _) => captured = (projection, payload)
            )
            .ReturnsAsync(answer);
        return () => captured;
    }

    private static void CatalogueHas(WorkbenchCommandServiceFixture fixture, params Guid[] ids) =>
        fixture
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
            .ReturnsAsync(
                new OwnerPackagePage(
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
                    null
                )
            );

    private static WorkbenchCommercialCommandResult Answer(
        string status,
        string outcome = "{}",
        string? problem = null
    ) => new(status, Guid.NewGuid(), false, problem, Json(outcome));

    private static async Task<SubscriptionChangeRequest> RequestAsync(
        WorkbenchCommandServiceFixture fixture,
        string kind,
        Guid? target = null,
        List<SubscriptionChangeSelection>? selections = null,
        string? reason = null
    ) => new("1.0", await fixture.VersionAsync(), kind, target, null, selections, reason);

    [Theory]
    [InlineData("PAUSE", "PAUSE_RELATIONSHIP")]
    [InlineData("RESUME", "RESUME_RELATIONSHIP")]
    [InlineData("TERMINATE", "TERMINATE_RELATIONSHIP")]
    public async Task Change_WholeRelationshipKindsAreSentToBillingWithoutAPackage(
        string kind,
        string commandKind
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        var captured = BillingAnswers(
            fixture,
            Answer(
                "COMPLETED",
                """{"effectiveAt":"2030-01-05T00:00:00Z","refundFeePaise":2500,"creditFeePaise":1800,"exportAvailableUntil":"2030-04-05T00:00:00Z","proratedFeeDifferencePaise":99}"""
            )
        );

        var result = await fixture.Commands.ChangeSubscriptionAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            await RequestAsync(fixture, kind, reason: "closing the shop"),
            CancellationToken.None
        );

        var (projection, payload) = captured()!.Value;
        Assert.Equal("projection-7", projection);
        Assert.Equal(commandKind, payload["commandKind"]!.GetValue<string>());
        Assert.Null(payload["targetPackageCode"]);
        Assert.Null(payload["componentIds"]);
        Assert.Equal(kind, result.Body.Kind);
        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal(
            new DateTimeOffset(2030, 1, 5, 0, 0, 0, TimeSpan.Zero),
            result.Body.EffectiveAt
        );
        Assert.Null(result.Body.ProratedFeeDifferencePaise);
        Assert.Equal(kind == "TERMINATE" ? 2500L : null, result.Body.RefundFeePaise);
        Assert.Equal(kind == "PAUSE" ? 1800L : null, result.Body.CreditFeePaise);
        Assert.Equal(
            kind == "TERMINATE" ? new DateTimeOffset(2030, 4, 5, 0, 0, 0, TimeSpan.Zero) : null,
            result.Body.ExportAvailableUntil
        );
        Assert.Equal("GST_INCLUSIVE", result.Body.TaxTreatment);
    }

    [Fact]
    public async Task Change_ADowngradeSendsThePackageCodeAndTheComponentsToKeep()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        CatalogueHas(fixture, PackageId);
        var captured = BillingAnswers(fixture, Answer("COMPLETED"));

        var result = await fixture.Commands.ChangeSubscriptionAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            await RequestAsync(fixture, "DOWNGRADE", PackageId, [new("posts"), new("images", [])]),
            CancellationToken.None
        );

        var (_, payload) = captured()!.Value;
        Assert.Equal("DOWNGRADE_PACKAGE", payload["commandKind"]!.GetValue<string>());
        Assert.Equal("GROWTH", payload["targetPackageCode"]!.GetValue<string>());
        Assert.Equal(
            ["posts", "images"],
            payload["componentIds"]!.AsArray().Select(item => item!.GetValue<string>())
        );
        Assert.Equal("DOWNGRADE", result.Body.Kind);
        Assert.Null(result.Body.ProratedFeeDifferencePaise);
    }

    [Fact]
    public async Task Change_ABlockedAnswerCarriesTheHumanisedReason()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        BillingAnswers(fixture, Answer("BLOCKED", """{"blockedReason":"OPEN_INVOICE"}"""));

        var result = await fixture.Commands.ChangeSubscriptionAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            await RequestAsync(fixture, "PAUSE"),
            CancellationToken.None
        );

        Assert.Equal("BLOCKED", result.Body.Status);
        Assert.Equal(ExperienceBlockBuilder.Humanize("OPEN_INVOICE"), result.Body.BlockedReason);
    }

    [Theory]
    [InlineData("2999-01-01T00:00:00Z", "SCHEDULED")]
    [InlineData("2001-01-01T00:00:00Z", "ACCEPTED")]
    [InlineData("not-a-date", "ACCEPTED")]
    public async Task Change_APendingAnswerIsScheduledOnlyWhenItTakesEffectLater(
        string effectiveAt,
        string expected
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        BillingAnswers(fixture, Answer("PENDING", $$"""{"effectiveAt":"{{effectiveAt}}"}"""));

        var result = await fixture.Commands.ChangeSubscriptionAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            await RequestAsync(fixture, "TERMINATE"),
            CancellationToken.None
        );

        Assert.Equal(expected, result.Body.Status);
    }

    [Fact]
    public async Task Change_AnAnswerWithoutACommandIdStillGetsAnOperationReference()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        BillingAnswers(
            fixture,
            new WorkbenchCommercialCommandResult("COMPLETED", Guid.Empty, false, null, null)
        );

        var result = await fixture.Commands.ChangeSubscriptionAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            await RequestAsync(fixture, "PAUSE"),
            CancellationToken.None
        );

        Assert.NotEqual(Guid.Empty, result.Body.OperationRef);
        Assert.Equal("COMPLETED", result.Body.Status);
    }

    [Fact]
    public async Task Change_ReplaysTheSameCommandWithoutBillingAgain()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        BillingAnswers(fixture, Answer("COMPLETED"));
        var key = Guid.NewGuid();
        var request = await RequestAsync(fixture, "PAUSE");

        var first = await fixture.Commands.ChangeSubscriptionAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );
        var second = await fixture.Commands.ChangeSubscriptionAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );

        Assert.True(second.Replayed);
        Assert.Equal(first.Body.OperationRef, second.Body.OperationRef);
        fixture.Commercial.Verify(
            item =>
                item.SubmitAsync(
                    It.IsAny<WorkbenchContext>(),
                    It.IsAny<Guid>(),
                    It.IsAny<string>(),
                    It.IsAny<JsonObject>(),
                    It.IsAny<CancellationToken>()
                ),
            Times.Once
        );
    }

    [Theory]
    [InlineData("WBE_COMMERCIAL_CONFLICT", 409, "WORKBENCH_VERSION_CONFLICT")]
    [InlineData("WBE_COMMERCIAL_UNAUTHORIZED", 403, "SPEND_AUTHORITY_UNAVAILABLE")]
    [InlineData("WBE_COMMERCIAL_NOT_ACCESSIBLE", 403, "SPEND_AUTHORITY_UNAVAILABLE")]
    [InlineData("WBE_COMMERCIAL_INVALID", 400, "WORKBENCH_REQUEST_INVALID")]
    [InlineData("HTTP_400", 400, "WORKBENCH_REQUEST_INVALID")]
    [InlineData("HTTP_422", 400, "WORKBENCH_REQUEST_INVALID")]
    [InlineData("WBE_COMMERCIAL_BLOCKED", 422, "PACKAGE_COMPONENT_NOT_AVAILABLE")]
    [InlineData("WALLET_INSUFFICIENT", 409, "WALLET_INSUFFICIENT")]
    [InlineData("WALLET_IDEMPOTENCY_CONFLICT", 409, "WALLET_IDEMPOTENCY_CONFLICT")]
    [InlineData("TRIAL_ALREADY_USED", 409, "TRIAL_ALREADY_USED")]
    [InlineData("TRIAL_ALREADY_USED_BY_IDENTITY", 409, "TRIAL_ALREADY_USED_BY_IDENTITY")]
    [InlineData("COMPONENT_NOT_YET_RELEASED", 422, "COMPONENT_NOT_YET_RELEASED")]
    [InlineData("PACKAGE_COMPONENT_NOT_AVAILABLE", 422, "PACKAGE_COMPONENT_NOT_AVAILABLE")]
    [InlineData("PROACTIVE_ALLOWANCE_EXHAUSTED", 429, "PROACTIVE_ALLOWANCE_EXHAUSTED")]
    [InlineData("SOMETHING_NEW", 503, "SPEND_COMMERCIAL_UNAVAILABLE")]
    public async Task Change_MapsEveryBillingProblemCodeToItsContractResponse(
        string problem,
        int status,
        string code
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        BillingAnswers(fixture, Answer("REJECTED", problem: problem));

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                await RequestAsync(fixture, "PAUSE"),
                CancellationToken.None
            )
        );

        Assert.Equal(status, failure.Status);
        Assert.Equal(code, failure.Code);
    }

    [Theory]
    [InlineData("CONFLICT", 409, "WORKBENCH_VERSION_CONFLICT")]
    [InlineData("REJECTED", 400, "WORKBENCH_REQUEST_INVALID")]
    [InlineData("MYSTERY", 503, "SPEND_COMMERCIAL_UNAVAILABLE")]
    public async Task Change_MapsABillingStatusThatIsNotAnAcceptanceToAFailure(
        string billingStatus,
        int status,
        string code
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        BillingAnswers(fixture, Answer(billingStatus));

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                await RequestAsync(fixture, "PAUSE"),
                CancellationToken.None
            )
        );

        Assert.Equal(status, failure.Status);
        Assert.Equal(code, failure.Code);
    }

    [Fact]
    public async Task Change_ABillingOwnerThatCannotBeReachedIsUnavailable()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        BillingAnswers(fixture, null);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                await RequestAsync(fixture, "PAUSE"),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendCommercialUnavailable, failure.Code);
    }

    [Fact]
    public async Task Change_AnUnavailableWalletStopsTheChangeWithTheOwnersLimitation()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIs(fixture, WorkbenchCommercialSnapshot.Unavailable("Billing is down."));

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                await RequestAsync(fixture, "PAUSE"),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal("Billing is down.", failure.Detail);
        fixture.Commercial.Verify(
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
    public async Task Change_IsRefusedWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                new SubscriptionChangeRequest("1.0", "relationship-0", "PAUSE"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
    }

    [Fact]
    public async Task Change_IsRefusedForAnAudienceThatMayNotManageSpend()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ChangeSubscriptionAsync(
                fixture.Manager(),
                Guid.NewGuid(),
                await RequestAsync(fixture, "PAUSE"),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendAuthorityUnavailable, failure.Code);
    }

    public static TheoryData<string, string, bool, string> InvalidChanges() =>
        new()
        {
            { "9.9", "PAUSE", false, "schemaVersion" },
            { "1.0", "VANISH", false, "kind is not supported" },
            { "1.0", "UPGRADE", false, "targetPackageId is required" },
            { "1.0", "DOWNGRADE", false, "targetPackageId is required" },
        };

    [Theory]
    [MemberData(nameof(InvalidChanges))]
    public async Task Change_RejectsAnInvalidRequest(
        string schema,
        string kind,
        bool withTarget,
        string detail
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                new SubscriptionChangeRequest(
                    schema,
                    "relationship-1",
                    kind,
                    withTarget ? PackageId : null
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains(detail, failure.Detail);
    }

    [Fact]
    public async Task Change_RejectsAReasonOutsideOneToFiveHundredCharacters()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        foreach (var reason in new[] { "  ", new string('r', 501) })
        {
            var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
                fixture.Commands.ChangeSubscriptionAsync(
                    fixture.Employer(),
                    Guid.NewGuid(),
                    new SubscriptionChangeRequest("1.0", "relationship-1", "PAUSE", Reason: reason),
                    CancellationToken.None
                )
            );
            Assert.Contains("reason", failure.Detail);
        }
    }

    [Fact]
    public async Task Change_APlanChangeCannotTargetOneCapabilityOrTooManyComponents()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var tooMany = Enumerable
            .Range(0, 51)
            .Select(index => new SubscriptionChangeSelection($"component-{index}"))
            .ToList();

        var oneSkill = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                new SubscriptionChangeRequest(
                    "1.0",
                    "relationship-1",
                    "PAUSE",
                    SkillId: "CONTENT_STRATEGY_AND_CALENDAR"
                ),
                CancellationToken.None
            )
        );
        var many = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                new SubscriptionChangeRequest(
                    "1.0",
                    "relationship-1",
                    "DOWNGRADE",
                    PackageId,
                    Selections: tooMany
                ),
                CancellationToken.None
            )
        );

        Assert.Contains("capabilities panel", oneSkill.Detail);
        Assert.Contains("at most 50", many.Detail);
    }

    public static TheoryData<string, string, string[]?> InvalidSelections() =>
        new()
        {
            { "PAUSE", "posts", null },
            { "UPGRADE", "posts", null },
            { "DOWNGRADE", "", null },
            { "DOWNGRADE", "long", null },
            { "DOWNGRADE", "posts", ["item"] },
        };

    [Theory]
    [MemberData(nameof(InvalidSelections))]
    public async Task Change_OnlyADowngradeTakesWholeComponentsToKeep(
        string kind,
        string component,
        string[]? items
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        if (component == "long")
            component = new string('c', 101);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                new SubscriptionChangeRequest(
                    "1.0",
                    "relationship-1",
                    kind,
                    kind is "UPGRADE" or "DOWNGRADE" ? PackageId : null,
                    Selections: [new SubscriptionChangeSelection(component, items?.ToList())]
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains("Only a downgrade", failure.Detail);
    }

    [Fact]
    public async Task Change_APackageNotOnSaleForTheAgentIsRejectedAndNothingIsSent()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        CatalogueHas(fixture, Guid.NewGuid());

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                await RequestAsync(fixture, "UPGRADE", PackageId),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains("not a package on sale", failure.Detail);
    }

    [Fact]
    public async Task Change_ALongCatalogueIsSearchedForAtMostTenPages()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        fixture
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
            .ReturnsAsync(new OwnerPackagePage([], "more"));

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                await RequestAsync(fixture, "UPGRADE", PackageId),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        fixture.Packages.Verify(
            item =>
                item.ListAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<string>(),
                    It.IsAny<string>(),
                    It.IsAny<string>(),
                    It.IsAny<string?>(),
                    It.IsAny<int>(),
                    It.IsAny<string>(),
                    It.IsAny<CancellationToken>()
                ),
            Times.Exactly(10)
        );
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task Change_ACatalogueFailureIsUnavailable(bool cursorProblem)
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        WalletIsAvailable(fixture);
        Exception failureToThrow = cursorProblem
            ? new PackageCatalogCursorException()
            : new PackageCatalogUnavailableException("catalogue down");
        fixture
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
            .ThrowsAsync(failureToThrow);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ChangeSubscriptionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                await RequestAsync(fixture, "UPGRADE", PackageId),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendCommercialUnavailable, failure.Code);
    }
}
