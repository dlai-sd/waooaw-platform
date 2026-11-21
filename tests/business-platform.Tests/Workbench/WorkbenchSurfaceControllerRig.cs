// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

/// <summary>An employer-owned relationship with a declared experience, driven through the real controller.</summary>
internal sealed class WorkbenchSurfaceRig
{
    public const string Schema = "\"schemaVersion\":\"1.0\"";

    private WorkbenchSurfaceRig() { }

    public WorkbenchCommandServiceFixture Fixture { get; private init; } = null!;
    public WorkbenchProjectionService Projection { get; private init; } = null!;

    public static async Task<WorkbenchSurfaceRig> CreateAsync(
        bool withDeclaration = true,
        bool withWorkspace = true
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(
            withDeclaration: withDeclaration,
            withWorkspace: withWorkspace
        );
        fixture
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(
                WorkbenchCommercialSnapshot.Unavailable(
                    UnconfiguredWorkbenchCommercialReader.Limitation
                )
            );
        var projection = new WorkbenchProjectionService(
            fixture.Relationships,
            fixture.Employment,
            fixture.Configuration,
            new PerformanceReviewService(fixture.RelationshipFactory, fixture.Constitutional),
            new RelationshipEvidenceService(
                fixture.RelationshipFactory,
                new Mock<IRelationshipEvidenceGateway>().Object,
                fixture.Constitutional,
                Options.Create(
                    new RelationshipEvidenceExportOptions
                    {
                        DownloadBaseUrl = "https://api.example.test",
                        SigningKey = new string('k', 32),
                    }
                )
            ),
            new Mock<IRelationshipWorkspaceOwnerGateway>().Object,
            fixture.Manifests.Object,
            fixture.Commercial.Object,
            fixture.GoalHistory,
            TimeProvider.System,
            NullLogger<WorkbenchProjectionService>.Instance
        );
        return new WorkbenchSurfaceRig { Fixture = fixture, Projection = projection };
    }

    public Guid RelationshipId => Fixture.RelationshipId;

    public Task<string> VersionAsync() => Fixture.VersionAsync();

    public WorkbenchController Controller(
        Guid participant,
        string? body = null,
        bool strongAuth = true,
        bool enabled = true,
        Action<DefaultHttpContext>? configure = null,
        Guid? idempotencyKey = null,
        IEnumerable<Claim>? extraClaims = null,
        string? participantClaim = "participant_id"
    )
    {
        var claims = new List<Claim>();
        if (participantClaim is not null)
            claims.Add(new Claim(participantClaim, participant.ToString("D")));
        if (strongAuth)
        {
            claims.Add(new Claim("authentication_assurance", "AAL3_FRESH"));
            claims.Add(
                new Claim("auth_time", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString())
            );
        }
        if (extraClaims is not null)
            claims.AddRange(extraClaims);
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test")),
        };
        context.Items[TenantIsolationMiddleware.TenantIdItemKey] = Fixture.TenantId.ToString("D");
        context.Request.Headers["X-Correlation-ID"] = Guid.NewGuid().ToString("D");
        context.Request.Headers["Idempotency-Key"] = (idempotencyKey ?? Guid.NewGuid()).ToString(
            "D"
        );
        if (body is not null)
        {
            context.Request.ContentType = "application/json";
            context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body));
        }
        configure?.Invoke(context);
        return new WorkbenchController(
            Fixture.Relationships,
            Projection,
            Fixture.Commands,
            Options.Create(new WorkbenchOptions { Enabled = enabled })
        )
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
    }

    public WorkbenchController Owner(string? body = null, bool strongAuth = true) =>
        Controller(Fixture.EmployerId, body, strongAuth);

    public async Task<string> EnvelopeAsync() =>
        $"{Schema},\"expectedVersion\":\"{await VersionAsync()}\"";
}
