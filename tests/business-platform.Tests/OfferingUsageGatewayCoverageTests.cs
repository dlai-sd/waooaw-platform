// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-04
// constitutional_basis: C-023, C-059, C-063, C-076, ADR-051
using System.Net;
using System.Reflection;
using System.Text;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class OfferingUsageGatewayCoverageTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    private static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    private AuthenticatedOfferingUsageGateway Gateway(
        Func<HttpRequestMessage, HttpResponseMessage> send
    )
    {
        var identity = fixture.CreateIdentity();
        var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        var field = typeof(AuthenticatedOfferingUsageGateway).GetField(
            "_client",
            BindingFlags.Instance | BindingFlags.NonPublic
        )!;
        ((HttpClient)field.GetValue(gateway)!).Dispose();
        field.SetValue(
            gateway,
            new HttpClient(new StubHandler(send)) { BaseAddress = new Uri("https://owner.test") }
        );
        return gateway;
    }

    private static Task<WalletReservationOutcome> Settle(
        AuthenticatedOfferingUsageGateway gateway
    ) =>
        gateway.SettleAccountAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            250,
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

    private static Task<WalletReservationOutcome> Release(
        AuthenticatedOfferingUsageGateway gateway
    ) =>
        gateway.ReleaseAccountAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

    [Theory]
    [InlineData(
        HttpStatusCode.Conflict,
        """{"detail":"WALLET_RESERVATION_CONFLICT"}""",
        "WALLET_RESERVATION_CONFLICT",
        null
    )]
    [InlineData(
        HttpStatusCode.UnprocessableEntity,
        """{"detail":{"code":"ACQUISITION_BUDGET_EXHAUSTED","level":"CAMPAIGN"}}""",
        "ACQUISITION_BUDGET_EXHAUSTED",
        "CAMPAIGN"
    )]
    [InlineData(
        HttpStatusCode.UnprocessableEntity,
        """{"detail":{"code":"ACQUISITION_BUDGET_EXHAUSTED"}}""",
        "ACQUISITION_BUDGET_EXHAUSTED",
        null
    )]
    [InlineData(
        HttpStatusCode.UnprocessableEntity,
        """{"detail":{"code":"ACQUISITION_BUDGET_EXHAUSTED","level":4}}""",
        "ACQUISITION_BUDGET_EXHAUSTED",
        null
    )]
    [InlineData(
        HttpStatusCode.Conflict,
        """{"detail":{"level":"CAMPAIGN"}}""",
        "WALLET_REFUSED",
        null
    )]
    [InlineData(HttpStatusCode.Conflict, """{"detail":{"code":7}}""", "WALLET_REFUSED", null)]
    [InlineData(HttpStatusCode.Conflict, """{"detail":null}""", "WALLET_REFUSED", null)]
    [InlineData(HttpStatusCode.Conflict, """{"detail":12}""", "WALLET_REFUSED", null)]
    [InlineData(HttpStatusCode.Conflict, """{"title":"no detail"}""", "WALLET_REFUSED", null)]
    [InlineData(HttpStatusCode.Conflict, "not json", "WALLET_REFUSED", null)]
    public async Task A_wallet_refusal_keeps_the_owner_code_and_level_or_falls_back_to_a_generic_refusal(
        HttpStatusCode status,
        string body,
        string code,
        string? level
    )
    {
        using var gateway = Gateway(_ => Json(status, body));

        var refusal = await Assert.ThrowsAsync<PlatformAccountRefusedException>(() =>
            Settle(gateway)
        );

        Assert.Equal((code, level), (refusal.Code, refusal.Level));
    }

    [Theory]
    [InlineData("transport")]
    [InlineData("cancelled")]
    [InlineData("status")]
    [InlineData("empty")]
    public async Task An_unreachable_or_empty_wallet_owner_leaves_the_outcome_unresolved(
        string failure
    )
    {
        using var gateway = Gateway(_ =>
            failure switch
            {
                "transport" => throw new HttpRequestException("connection reset"),
                "cancelled" => throw new TaskCanceledException("timeout"),
                "status" => Json(HttpStatusCode.BadGateway, "{}"),
                _ => Json(HttpStatusCode.OK, "null"),
            }
        );

        var unavailable = await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            Release(gateway)
        );

        Assert.Contains(
            failure is "transport" or "cancelled" ? "unresolved" : "WBE wallet owner",
            unavailable.Message
        );
        Assert.Equal(failure is "transport" or "cancelled", unavailable.InnerException is not null);
    }

    [Fact]
    public async Task A_settlement_is_signed_and_returns_the_owner_outcome()
    {
        HttpRequestMessage? seen = null;
        var reservation = Guid.NewGuid();
        using var gateway = Gateway(request =>
        {
            seen = request;
            return Json(
                HttpStatusCode.OK,
                $$"""
                {"reservationId":"{{reservation}}","accountId":"{{Guid.NewGuid()}}","state":"SETTLED",
                 "reservedPaise":300,"actualPaise":250,"overrunPaise":0,"fenced":false,"replayed":true}
                """
            );
        });

        var outcome = await Settle(gateway);

        Assert.Equal(
            ("SETTLED", 250L, true),
            (outcome.State, outcome.ActualPaise, outcome.Replayed)
        );
        Assert.Equal("/internal/v1/wallet/reservations/settle", seen!.RequestUri!.AbsolutePath);
        Assert.StartsWith("Bearer ", seen.Headers.Authorization?.ToString());
        Assert.NotEmpty(seen.Headers.GetValues("Idempotency-Key"));
    }

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> send)
        : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Task.FromResult(send(request));
    }
}
