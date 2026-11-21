// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Net;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

internal sealed record SeenRequest(
    HttpMethod Method,
    string Path,
    string? Bearer,
    string? Correlation,
    string? IdempotencyKey,
    string Body
);

internal sealed class StubBillingHandler(Func<SeenRequest, HttpResponseMessage> respond)
    : HttpMessageHandler
{
    public List<SeenRequest> Seen { get; } = [];

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken
    )
    {
        var seen = new SeenRequest(
            request.Method,
            request.RequestUri!.AbsolutePath,
            request.Headers.Authorization?.Parameter,
            request.Headers.TryGetValues("X-Correlation-ID", out var correlation)
                ? correlation.Single()
                : null,
            request.Headers.TryGetValues("Idempotency-Key", out var key) ? key.Single() : null,
            request.Content is null
                ? string.Empty
                : await request.Content.ReadAsStringAsync(cancellationToken)
        );
        Seen.Add(seen);
        return respond(seen);
    }
}

public sealed class WorkbenchCommercialReaderTests(OwnerGatewayIdentityFixture identity)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    private static readonly Guid RelationshipId = Guid.Parse(
        "aaaaaaaa-0000-0000-0000-000000000001"
    );
    private static readonly Guid CommandId = Guid.Parse("cccccccc-0000-0000-0000-000000000001");

    private static readonly WorkbenchContext Context = new(
        Guid.Parse("bbbbbbbb-0000-0000-0000-000000000001"),
        RelationshipId,
        "customer-subject",
        Guid.NewGuid(),
        RelationshipParticipantRole.Employer,
        WorkbenchAudiences.CustomerOwner,
        "corr-1"
    );

    private static HttpResponseMessage Reply(HttpStatusCode status, string json) =>
        new(status) { Content = new StringContent(json, Encoding.UTF8, "application/json") };

    private AuthenticatedWorkbenchCommercialReader Reader(StubBillingHandler handler)
    {
        var reader = new AuthenticatedWorkbenchCommercialReader(
            identity.CreateIdentity(),
            new Uri("https://billing.test")
        );
        var field = typeof(AuthenticatedWorkbenchCommercialReader).GetField(
            "_client",
            BindingFlags.Instance | BindingFlags.NonPublic
        )!;
        ((HttpClient)field.GetValue(reader)!).Dispose();
        field.SetValue(
            reader,
            new HttpClient(handler) { BaseAddress = new Uri("https://billing.test") }
        );
        return reader;
    }

    private static string Projection(string relationship, string extra = "") =>
        $$$"""
            {"schemaVersion":"1.0","relationshipId":"{{{relationship}}}","projectionVersion":"p-7",
             "wallet":{"periodEnd":"2030-07-01T00:00:00Z","topUpAvailable":true,
             "components":[{"componentId":"CONTENT_DRAFT","label":"Content drafts","remaining":3,"quantity":8}]}{{{extra}}}}
            """;

    [Fact]
    public async Task GetWallet_ReadsTheProjectionOfTheRelationshipWithASignedRequest()
    {
        var handler = new StubBillingHandler(_ =>
            Reply(HttpStatusCode.OK, Projection(RelationshipId.ToString("D")))
        );
        using var reader = Reader(handler);

        var snapshot = await reader.GetWalletAsync(Context, default);

        Assert.True(snapshot.Available);
        Assert.Equal("p-7", snapshot.ProjectionVersion);
        Assert.Equal(DateTimeOffset.Parse("2030-07-01T00:00:00Z"), snapshot.PeriodEnd);
        Assert.True(snapshot.TopUpAvailable);
        Assert.Null(snapshot.Limitation);
        var component = Assert.Single(snapshot.Components);
        Assert.Equal(
            new WorkbenchComponentBalance(
                "CONTENT_DRAFT",
                "Content drafts",
                3,
                8,
                snapshot.PeriodEnd!.Value
            ),
            component
        );
        var request = Assert.Single(handler.Seen);
        Assert.Equal(HttpMethod.Get, request.Method);
        Assert.Equal(
            $"/internal/v1/relationships/{RelationshipId:D}/commercial-projection",
            request.Path
        );
        Assert.False(string.IsNullOrWhiteSpace(request.Bearer));
        Assert.Equal("corr-1", request.Correlation);
        Assert.Null(request.IdempotencyKey);
    }

    [Theory]
    [InlineData(HttpStatusCode.ServiceUnavailable, "{}")]
    [InlineData(HttpStatusCode.NotFound, "{}")]
    [InlineData(HttpStatusCode.OK, "not json")]
    [InlineData(HttpStatusCode.OK, """{"schemaVersion":1}""")]
    [InlineData(HttpStatusCode.OK, """{"schemaVersion":"2.0"}""")]
    [InlineData(
        HttpStatusCode.OK,
        """{"schemaVersion":"1.0","relationshipId":"aaaaaaaa-0000-0000-0000-000000000001","projectionVersion":"p","periodEnd":"2030-07-01T00:00:00Z","components":[{"componentId":"A","label":"a","remaining":"x","quantity":1}]}"""
    )]
    public async Task GetWallet_WhenBillingAnswersBadly_SaysBillingDidNotAnswer(
        HttpStatusCode status,
        string body
    )
    {
        using var reader = Reader(new StubBillingHandler(_ => Reply(status, body)));

        var snapshot = await reader.GetWalletAsync(Context, default);

        Assert.False(snapshot.Available);
        Assert.Equal(
            AuthenticatedWorkbenchCommercialReader.BillingUnavailable,
            snapshot.Limitation
        );
        Assert.Empty(snapshot.Components);
        Assert.False(snapshot.TopUpAvailable);
    }

    [Theory]
    [InlineData(typeof(HttpRequestException))]
    [InlineData(typeof(TaskCanceledException))]
    public async Task GetWallet_WhenBillingCannotBeReached_SaysBillingDidNotAnswer(Type failure)
    {
        using var reader = Reader(
            new StubBillingHandler(_ => throw (Exception)Activator.CreateInstance(failure)!)
        );

        var snapshot = await reader.GetWalletAsync(Context, default);

        Assert.False(snapshot.Available);
        Assert.Equal(
            AuthenticatedWorkbenchCommercialReader.BillingUnavailable,
            snapshot.Limitation
        );
    }

    [Fact]
    public async Task GetWallet_ForAnotherRelationshipsProjection_IsRefused()
    {
        using var reader = Reader(
            new StubBillingHandler(_ =>
                Reply(HttpStatusCode.OK, Projection(Guid.NewGuid().ToString("D")))
            )
        );

        var snapshot = await reader.GetWalletAsync(Context, default);

        Assert.False(snapshot.Available);
        Assert.Equal(
            AuthenticatedWorkbenchCommercialReader.BillingUnavailable,
            snapshot.Limitation
        );
    }

    [Fact]
    public void Parse_AcceptsTheFlatShapeAndSkipsMalformedComponents()
    {
        var root = JsonSerializer.SerializeToElement(
            JsonNode.Parse(
                $$"""
                {"schemaVersion":"1.0","relationshipId":"{{RelationshipId:D}}","projectionVersion":"p-1",
                 "periodEnd":"2030-07-01T00:00:00Z","topUpAvailable":false,
                 "components":[
                   {"componentId":"A","label":"Alpha","remaining":1,"quantity":2},
                   {"componentId":1,"label":"Beta","remaining":1,"quantity":2},
                   {"componentId":"C","label":2,"remaining":1,"quantity":2},
                   {"componentId":"E","label":"Echo","remaining":1},
                   {"label":"Foxtrot","remaining":1,"quantity":2},
                   "text"
                 ]}
                """
            )
        );

        var snapshot = AuthenticatedWorkbenchCommercialReader.Parse(root, RelationshipId);

        Assert.True(snapshot.Available);
        Assert.Equal("A", Assert.Single(snapshot.Components).ComponentId);
        Assert.False(snapshot.TopUpAvailable);
    }

    [Fact]
    public void Parse_WithoutAPeriodEnd_ReportsNoComponents()
    {
        var root = JsonSerializer.SerializeToElement(
            JsonNode.Parse(
                $$$"""
                {"schemaVersion":"1.0","relationshipId":"{{{RelationshipId:D}}}","projectionVersion":"p-1",
                 "wallet":{"components":[{"componentId":"A","label":"Alpha","remaining":1,"quantity":2}]}}
                """
            )
        );

        var snapshot = AuthenticatedWorkbenchCommercialReader.Parse(root, RelationshipId);

        Assert.True(snapshot.Available);
        Assert.Null(snapshot.PeriodEnd);
        Assert.Empty(snapshot.Components);
    }

    [Theory]
    [InlineData("""[]""")]
    [InlineData("""{"relationshipId":"x","projectionVersion":"p"}""")]
    [InlineData("""{"schemaVersion":"1.0","projectionVersion":"p"}""")]
    [InlineData(
        """{"schemaVersion":"1.0","relationshipId":"not-a-guid","projectionVersion":"p"}"""
    )]
    [InlineData(
        """{"schemaVersion":"1.0","relationshipId":"aaaaaaaa-0000-0000-0000-000000000001"}"""
    )]
    [InlineData(
        """{"schemaVersion":"1.0","relationshipId":"aaaaaaaa-0000-0000-0000-000000000001","projectionVersion":7}"""
    )]
    public void Parse_OfAnIncompleteProjection_IsUnavailable(string json)
    {
        var snapshot = AuthenticatedWorkbenchCommercialReader.Parse(
            JsonSerializer.SerializeToElement(JsonNode.Parse(json)),
            RelationshipId
        );

        Assert.False(snapshot.Available);
        Assert.Equal(
            AuthenticatedWorkbenchCommercialReader.BillingUnavailable,
            snapshot.Limitation
        );
    }

    [Theory]
    [InlineData("STALE", true)]
    [InlineData("UNKNOWN", true)]
    [InlineData("UNAVAILABLE", true)]
    [InlineData("CURRENT", false)]
    [InlineData("", false)]
    public void Parse_FlagsFiguresThatBillingSaysMayBeOutOfDate(string state, bool stale)
    {
        var root = JsonSerializer.SerializeToElement(
            JsonNode.Parse(
                $$"""
                {"schemaVersion":"1.0","relationshipId":"{{RelationshipId:D}}","projectionVersion":"p-1","currencyState":"{{state}}"}
                """
            )
        );

        var snapshot = AuthenticatedWorkbenchCommercialReader.Parse(root, RelationshipId);

        Assert.Equal(
            stale ? AuthenticatedWorkbenchCommercialReader.FiguresMayBeStale : null,
            snapshot.Limitation
        );
        Assert.True(snapshot.Available);
    }

    [Fact]
    public void Parse_IgnoresACurrencyStateThatIsNotText()
    {
        var root = JsonSerializer.SerializeToElement(
            JsonNode.Parse(
                $$"""
                {"schemaVersion":"1.0","relationshipId":"{{RelationshipId:D}}","projectionVersion":"p-1","currencyState":3}
                """
            )
        );

        Assert.Null(AuthenticatedWorkbenchCommercialReader.Parse(root, RelationshipId).Limitation);
    }

    private static JsonObject Payload => new() { ["action"] = "CHANGE_PLAN" };

    private static string Receipt(string status = "ACCEPTED", bool replayed = false) =>
        $$"""{"commandId":"{{CommandId:D}}","status":"{{status}}","replayed":{{replayed.ToString().ToLowerInvariant()}}}""";

    [Fact]
    public async Task Submit_SendsTheSignedCommandAndReturnsTheSettledOutcome()
    {
        var key = Guid.NewGuid();
        var handler = new StubBillingHandler(request =>
            request.Method == HttpMethod.Post
                ? Reply(HttpStatusCode.Accepted, Receipt(replayed: true))
                : Reply(
                    HttpStatusCode.OK,
                    $$"""{"commandId":"{{CommandId:D}}","status":"APPLIED","effectiveDate":"2030-07-01"}"""
                )
        );
        using var reader = Reader(handler);

        var result = await reader.SubmitAsync(Context, key, "p-7", Payload, default);

        Assert.NotNull(result);
        Assert.Equal("APPLIED", result.Status);
        Assert.Equal(CommandId, result.CommandId);
        Assert.True(result.Replayed);
        Assert.Null(result.ProblemCode);
        Assert.Equal("2030-07-01", result.Outcome!.Value.GetProperty("effectiveDate").GetString());
        var post = handler.Seen[0];
        Assert.Equal(HttpMethod.Post, post.Method);
        Assert.Equal(
            $"/internal/v1/relationships/{RelationshipId:D}/commercial-commands",
            post.Path
        );
        Assert.Equal(key.ToString("D"), post.IdempotencyKey);
        Assert.Equal("corr-1", post.Correlation);
        Assert.False(string.IsNullOrWhiteSpace(post.Bearer));
        var body = JsonNode.Parse(post.Body)!;
        Assert.Equal("1.0", body["schemaVersion"]!.GetValue<string>());
        Assert.Equal("p-7", body["expectedProjectionVersion"]!.GetValue<string>());
        Assert.Equal("CHANGE_PLAN", body["payload"]!["action"]!.GetValue<string>());
        var outcome = handler.Seen[1];
        Assert.Equal(HttpMethod.Get, outcome.Method);
        Assert.Equal(
            $"/internal/v1/relationships/{RelationshipId:D}/commercial-commands/{CommandId:D}",
            outcome.Path
        );
        Assert.Equal("corr-1", outcome.Correlation);
    }

    [Fact]
    public async Task Submit_KeepsTheReceiptStatusWhenTheOutcomeIsNotUsable()
    {
        var cases = new Func<SeenRequest, HttpResponseMessage>[]
        {
            _ => Reply(HttpStatusCode.NotFound, "{}"),
            _ =>
                Reply(
                    HttpStatusCode.OK,
                    $$"""{"commandId":"{{Guid.NewGuid():D}}","status":"APPLIED"}"""
                ),
            _ => Reply(HttpStatusCode.OK, "[]"),
            _ => Reply(HttpStatusCode.OK, """{"status":"APPLIED"}"""),
            _ => Reply(HttpStatusCode.OK, "not json"),
            _ => throw new HttpRequestException("down"),
        };

        foreach (var outcome in cases)
        {
            using var reader = Reader(
                new StubBillingHandler(request =>
                    request.Method == HttpMethod.Post
                        ? Reply(HttpStatusCode.OK, Receipt("RECEIVED"))
                        : outcome(request)
                )
            );

            var result = await reader.SubmitAsync(Context, Guid.NewGuid(), "p-7", Payload, default);

            Assert.Equal("RECEIVED", result!.Status);
            Assert.Null(result.Outcome);
            Assert.False(result.Replayed);
        }
    }

    [Fact]
    public async Task Submit_KeepsTheReceiptStatusWhenTheOutcomeCarriesNoStatus()
    {
        using var reader = Reader(
            new StubBillingHandler(request =>
                request.Method == HttpMethod.Post
                    ? Reply(HttpStatusCode.OK, Receipt("RECEIVED"))
                    : Reply(HttpStatusCode.OK, $$"""{"commandId":"{{CommandId:D}}","status":4}""")
            )
        );

        var result = await reader.SubmitAsync(Context, Guid.NewGuid(), "p-7", Payload, default);

        Assert.Equal("RECEIVED", result!.Status);
        Assert.NotNull(result.Outcome);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("""{"commandId":"nope","status":7}""")]
    public async Task Submit_ThatReturnsNoCommandIdIsUnknownAndNeverLooksUpAnOutcome(string receipt)
    {
        var handler = new StubBillingHandler(_ => Reply(HttpStatusCode.OK, receipt));
        using var reader = Reader(handler);

        var result = await reader.SubmitAsync(Context, Guid.NewGuid(), "p-7", Payload, default);

        Assert.Equal("UNKNOWN", result!.Status);
        Assert.Equal(Guid.Empty, result.CommandId);
        Assert.Null(result.Outcome);
        Assert.Single(handler.Seen);
    }

    [Theory]
    [InlineData(
        HttpStatusCode.Conflict,
        """{"detail":"PROJECTION_VERSION_MISMATCH"}""",
        "CONFLICT",
        "PROJECTION_VERSION_MISMATCH"
    )]
    [InlineData(
        HttpStatusCode.UnprocessableEntity,
        """{"detail":{"code":"PLAN_NOT_OFFERED"}}""",
        "REJECTED",
        "PLAN_NOT_OFFERED"
    )]
    [InlineData(HttpStatusCode.BadRequest, """{"code":"LEGACY"}""", "REJECTED", "LEGACY")]
    [InlineData(
        HttpStatusCode.BadRequest,
        """{"detail":{"x":1},"code":"FALLBACK"}""",
        "REJECTED",
        "FALLBACK"
    )]
    [InlineData(HttpStatusCode.BadRequest, """{"detail":7,"code":9}""", "REJECTED", "HTTP_400")]
    [InlineData(HttpStatusCode.BadRequest, "{}", "REJECTED", "HTTP_400")]
    [InlineData(HttpStatusCode.InternalServerError, "[]", "REJECTED", "HTTP_500")]
    public async Task Submit_Refused_ReportsTheOwnersProblemCode(
        HttpStatusCode status,
        string body,
        string expectedStatus,
        string expectedCode
    )
    {
        var handler = new StubBillingHandler(_ => Reply(status, body));
        using var reader = Reader(handler);

        var result = await reader.SubmitAsync(Context, Guid.NewGuid(), "p-7", Payload, default);

        Assert.Equal(expectedStatus, result!.Status);
        Assert.Equal(expectedCode, result.ProblemCode);
        Assert.Equal(Guid.Empty, result.CommandId);
        Assert.False(result.Replayed);
        Assert.Null(result.Outcome);
        Assert.Single(handler.Seen);
    }

    [Theory]
    [InlineData(typeof(HttpRequestException))]
    [InlineData(typeof(TaskCanceledException))]
    [InlineData(typeof(InvalidOperationException))]
    public async Task Submit_WhenBillingCannotBeReached_ReturnsNothing(Type failure)
    {
        using var reader = Reader(
            new StubBillingHandler(_ => throw (Exception)Activator.CreateInstance(failure)!)
        );

        Assert.Null(await reader.SubmitAsync(Context, Guid.NewGuid(), "p-7", Payload, default));
    }

    [Fact]
    public async Task Submit_WhenBillingAnswersWithSomethingThatIsNotJson_ReturnsNothing()
    {
        using var reader = Reader(
            new StubBillingHandler(_ => Reply(HttpStatusCode.OK, "<html>gateway error</html>"))
        );

        Assert.Null(await reader.SubmitAsync(Context, Guid.NewGuid(), "p-7", Payload, default));
    }

    [Fact]
    public async Task Unconfigured_ReportsBillingUnreachable_AndCannotSubmit()
    {
        var reader = new UnconfiguredWorkbenchCommercialReader();

        var snapshot = await reader.GetWalletAsync(Context, default);
        var result = await reader.SubmitAsync(Context, Guid.NewGuid(), "p-7", Payload, default);

        Assert.False(snapshot.Available);
        Assert.Equal(UnconfiguredWorkbenchCommercialReader.Limitation, snapshot.Limitation);
        Assert.Null(result);
    }

    [Fact]
    public void Context_DerivesTheRoleCodeTheOwnersExpect()
    {
        Assert.Equal(
            RelationshipRoleCodec.ToDatabase(RelationshipParticipantRole.Employer),
            Context.EffectiveRole
        );
        Assert.NotEqual(
            Context.EffectiveRole,
            (Context with { Role = RelationshipParticipantRole.RelationshipManager }).EffectiveRole
        );
    }

    [Fact]
    public void Unavailable_CarriesNoFigures()
    {
        var snapshot = WorkbenchCommercialSnapshot.Unavailable("why");

        Assert.False(snapshot.Available);
        Assert.Equal("why", snapshot.Limitation);
        Assert.Empty(snapshot.Components);
        Assert.Null(snapshot.PeriodEnd);
        Assert.Equal(string.Empty, snapshot.ProjectionVersion);
    }
}
