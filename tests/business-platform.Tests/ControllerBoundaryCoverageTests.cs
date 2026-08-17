// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-005, C-036, C-041, C-059, C-076
using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ControllerBoundaryCoverageTests
{
    private sealed class Factory<TContext>(DbContextOptions<TContext> options)
        : IDbContextFactory<TContext>
        where TContext : DbContext
    {
        public TContext CreateDbContext() =>
            (TContext)Activator.CreateInstance(typeof(TContext), options)!;
    }

    [Fact]
    public async Task WorkspaceReadEndpoints_ReturnCanonicalSectionsAndCursor()
    {
        var fixture = await CreateWorkspaceAsync();

        var changes = Json(await fixture.Controller.GetChangesAsync(
            fixture.Relationship.RelationshipId, null, CancellationToken.None));
        var plan = Json(await fixture.Controller.GetPlanAsync(
            fixture.Relationship.RelationshipId, CancellationToken.None));
        var attention = Json(await fixture.Controller.GetAttentionAsync(
            fixture.Relationship.RelationshipId, CancellationToken.None));
        var results = Json(await fixture.Controller.GetResultsAsync(
            fixture.Relationship.RelationshipId, CancellationToken.None));
        var rights = Json(await fixture.Controller.GetRightsControlsAsync(
            fixture.Relationship.RelationshipId, CancellationToken.None));

        Assert.StartsWith("workspace:", changes.GetProperty("authoritativeCursor").GetString());
        Assert.Equal("PLAN", plan.GetProperty("sectionType").GetString());
        Assert.Equal("ATTENTION", attention.GetProperty("sectionType").GetString());
        Assert.Equal("RESULTS", results.GetProperty("sectionType").GetString());
        Assert.Equal("RIGHTS_CONTROLS", rights.GetProperty("sectionType").GetString());
        Assert.True(rights.GetProperty("emergencyStopReachable").GetBoolean());
    }

    [Fact]
    public async Task WorkspaceSnapshot_UsesAuthenticatedOwnerTruthAndActorFallbacks()
    {
        var fixture = await CreateWorkspaceAsync();
        var producedAt = DateTimeOffset.UtcNow;
        fixture.Gateway.Execution = new ExecutionOwnerProjection("execution-7", "RUNNING", producedAt);
        fixture.Gateway.Commercial = new CommercialOwnerProjection(
            "commercial-8", "INR", "100", "200", "300", producedAt);

        var snapshot = Json(await fixture.Controller.GetWorkspaceAsync(
            fixture.Relationship.RelationshipId, CancellationToken.None));

        var sections = snapshot.GetProperty("sections").EnumerateArray().ToArray();
        Assert.Contains(sections, value => value.GetProperty("sectionType").GetString() == "WORK"
            && value.GetProperty("currencyState").GetString() == "RUNNING");
        Assert.Contains(sections, value => value.GetProperty("sectionType").GetString() == "USAGE_BUDGET"
            && value.GetProperty("currencyState").GetString() == "INR");

        foreach (var (claimType, claimValue, expectedActor) in new[]
        {
            (ClaimTypes.NameIdentifier, "name-actor", "name-actor"),
            ("sub", "subject-actor", "subject-actor"),
        })
        {
            var context = Context(fixture.Relationship.TenantId, Guid.NewGuid());
            var identity = (ClaimsIdentity)context.HttpContext.User.Identity!;
            foreach (var claim in identity.FindAll("participant_id").ToList()) identity.RemoveClaim(claim);
            identity.AddClaim(new Claim(claimType, claimValue));
            fixture.Controller.ControllerContext = context;
            await fixture.Controller.GetWorkAsync(fixture.Relationship.RelationshipId, CancellationToken.None);
            Assert.Equal(expectedActor, fixture.Gateway.LastContext?.ActorSubject);
        }

        var unknownContext = Context(fixture.Relationship.TenantId, Guid.NewGuid());
        var unknownIdentity = (ClaimsIdentity)unknownContext.HttpContext.User.Identity!;
        foreach (var claim in unknownIdentity.FindAll("participant_id").ToList()) unknownIdentity.RemoveClaim(claim);
        foreach (var claim in unknownIdentity.FindAll("participant_role").ToList()) unknownIdentity.RemoveClaim(claim);
        foreach (var claim in unknownIdentity.FindAll("correlation_id").ToList()) unknownIdentity.RemoveClaim(claim);
        unknownContext.HttpContext.TraceIdentifier = "trace-correlation";
        fixture.Controller.ControllerContext = unknownContext;
        await fixture.Controller.GetWorkAsync(fixture.Relationship.RelationshipId, CancellationToken.None);
        Assert.Equal("unknown", fixture.Gateway.LastContext?.ActorSubject);
        Assert.Equal("EMPLOYER", fixture.Gateway.LastContext?.EffectiveRole);
        Assert.Equal("trace-correlation", fixture.Gateway.LastContext?.CorrelationId);
    }

    [Fact]
    public async Task WorkspaceCommandEndpoints_EnforceIdempotencyAndBlockedPosture()
    {
        var fixture = await CreateWorkspaceAsync();
        using var document = JsonDocument.Parse("{\"type\":\"CHANGE_PLAN\"}");

        var missingKey = Assert.IsType<ObjectResult>(await fixture.Controller.SubmitCommandAsync(
            fixture.Relationship.RelationshipId, document.RootElement, null, CancellationToken.None));
        var blocked = Assert.IsType<ObjectResult>(await fixture.Controller.SubmitCommandAsync(
            fixture.Relationship.RelationshipId, document.RootElement, Guid.NewGuid().ToString(), CancellationToken.None));
        var missingCommand = Assert.IsType<ObjectResult>(await fixture.Controller.GetCommandAsync(
            fixture.Relationship.RelationshipId, Guid.NewGuid(), CancellationToken.None));

        Assert.Equal(400, missingKey.StatusCode);
        Assert.Equal(423, blocked.StatusCode);
        Assert.Equal(404, missingCommand.StatusCode);
    }

    [Fact]
    public async Task WorkspaceEndpoints_HideMissingOrForeignRelationships()
    {
        var fixture = await CreateWorkspaceAsync();
        var unknown = Guid.NewGuid();

        var workspace = Assert.IsType<ObjectResult>(await fixture.Controller.GetWorkspaceAsync(
            unknown, CancellationToken.None));
        var work = Assert.IsType<ObjectResult>(await fixture.Controller.GetWorkAsync(
            unknown, CancellationToken.None));
        var usage = Assert.IsType<ObjectResult>(await fixture.Controller.GetUsageBudgetAsync(
            unknown, CancellationToken.None));

        Assert.Equal(404, workspace.StatusCode);
        Assert.Equal(404, work.StatusCode);
        Assert.Equal(404, usage.StatusCode);
    }

    [Fact]
    public async Task WorkspaceEvidenceEndpoints_AreUnavailableWithoutEvidenceService()
    {
        var fixture = await CreateWorkspaceAsync();

        var list = Assert.IsType<ObjectResult>(await fixture.Controller.ListEvidenceAsync(
            fixture.Relationship.RelationshipId, CancellationToken.None));
        var item = Assert.IsType<ObjectResult>(await fixture.Controller.GetEvidenceAsync(
            fixture.Relationship.RelationshipId, Guid.NewGuid(), CancellationToken.None));
        var export = Assert.IsType<ObjectResult>(await fixture.Controller.RequestEvidenceExportAsync(
            fixture.Relationship.RelationshipId,
            new RequestRelationshipEvidenceExport("1.0", "audit"),
            Guid.NewGuid().ToString(),
            CancellationToken.None));
        var exportStatus = Assert.IsType<ObjectResult>(await fixture.Controller.GetEvidenceExportAsync(
            fixture.Relationship.RelationshipId, Guid.NewGuid(), CancellationToken.None));

        Assert.Equal(404, list.StatusCode);
        Assert.Equal(404, item.StatusCode);
        Assert.Equal(404, export.StatusCode);
        Assert.Equal(404, exportStatus.StatusCode);
    }

    [Fact]
    public async Task WorkspaceEvidenceIdentity_RejectsEachMalformedContextBoundary()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationships = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId, participantId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        var evidence = new RelationshipEvidenceService(factory, new EmptyEvidenceGateway());
        var controller = new RelationshipWorkspaceController(
            relationships, new RelationshipOwnerGatewayStub(), evidence);

        foreach (var (tenantValue, participantClaim) in new (object?, string?)[]
        {
            (null, participantId.ToString()),
            (tenantId, participantId.ToString()),
            ("not-a-uuid", participantId.ToString()),
            (tenantId.ToString(), null),
            (tenantId.ToString(), "not-a-uuid"),
        })
        {
            var context = new DefaultHttpContext
            {
                User = new ClaimsPrincipal(new ClaimsIdentity(
                    participantClaim is null ? [] : [new Claim("participant_id", participantClaim)], "Test")),
            };
            if (tenantValue is not null) context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantValue;
            controller.ControllerContext = new ControllerContext { HttpContext = context };
            var result = Assert.IsType<ObjectResult>(await controller.GetEvidenceAsync(
                admitted.Relationship.RelationshipId, Guid.NewGuid(), CancellationToken.None));
            Assert.Equal(404, result.StatusCode);
        }

        var fallback = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim(ClaimTypes.NameIdentifier, participantId.ToString())], "Test")),
        };
        fallback.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        controller.ControllerContext = new ControllerContext { HttpContext = fallback };
        Assert.IsType<ObjectResult>(await controller.GetEvidenceAsync(
            admitted.Relationship.RelationshipId, Guid.NewGuid(), CancellationToken.None));
    }

    [Fact]
    public async Task SkillQueries_RespectLifecycleAndMalformedDefinitionFailSafe()
    {
        var options = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        await using (var db = new SkillCatalogDbContext(options))
        {
            db.Skills.AddRange(
                Skill("draft", "1", "DRAFT", "{}", null),
                Skill("published", "1", "PUBLISHED", "{invalid", DateTimeOffset.UtcNow.AddMinutes(-1)),
                Skill("published", "2", "PUBLISHED", "{\"schema\":2}", DateTimeOffset.UtcNow),
                Skill("legacy", "1", "DEPRECATED", "{\"schema\":1}", DateTimeOffset.UtcNow.AddDays(-1)));
            await db.SaveChangesAsync();
        }
        var controller = new SkillsController(
            new Factory<SkillCatalogDbContext>(options),
            new ConfigurationBuilder().Build(),
            NullLogger<SkillsController>.Instance);

        var listedResult = await controller.ListSkillsAsync(CancellationToken.None);
        var listed = Assert.IsType<OkObjectResult>(listedResult.Result);
        var list = Assert.IsAssignableFrom<IReadOnlyList<SkillResponse>>(listed.Value);
        var latestResult = await controller.GetLatestSkillAsync("published", CancellationToken.None);
        var latest = Assert.IsType<OkObjectResult>(latestResult.Result);
        var deprecatedResult = await controller.GetPinnedSkillAsync("legacy", "1", CancellationToken.None);
        var deprecated = Assert.IsType<OkObjectResult>(deprecatedResult.Result);
        var malformedResult = await controller.GetPinnedSkillAsync("published", "1", CancellationToken.None);
        var malformed = Assert.IsType<OkObjectResult>(malformedResult.Result);
        var missing = await controller.GetPinnedSkillAsync("draft", "1", CancellationToken.None);

        Assert.Equal(2, list.Count);
        Assert.Equal("2", Assert.IsType<SkillResponse>(latest.Value).Version);
        Assert.Equal("DEPRECATED", Assert.IsType<SkillResponse>(deprecated.Value).Status);
        Assert.Equal(JsonValueKind.Object, Assert.IsType<SkillResponse>(malformed.Value).Definition.ValueKind);
        Assert.IsType<NotFoundObjectResult>(missing.Result);
    }

    [Fact]
    public async Task SkillPublish_RejectsMissingBodyRoleAndCeConfiguration()
    {
        var options = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        var controller = SkillController(options, new ConfigurationBuilder().Build());
        controller.ControllerContext = Context(Guid.NewGuid(), Guid.NewGuid());
        var request = new PublishSkillRequest(
            "skill", "1", "Skill", JsonDocument.Parse("{}").RootElement, ["CCT-1"]);

        Assert.IsType<BadRequestObjectResult>(await controller.PublishSkillAsync(null!, CancellationToken.None));
        var forbidden = Assert.IsType<ObjectResult>(await controller.PublishSkillAsync(request, CancellationToken.None));
        Assert.Equal(403, forbidden.StatusCode);

        controller.HttpContext.User = new ClaimsPrincipal(new ClaimsIdentity(
            [new Claim("role", "founder")], "Test"));
        var unavailable = Assert.IsType<ObjectResult>(await controller.PublishSkillAsync(request, CancellationToken.None));
        Assert.Equal(503, unavailable.StatusCode);
    }

    [Fact]
    public async Task SkillQueriesAndPublish_HandleMissingSkillAndUnreachableCe()
    {
        var options = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["ConstitutionalEngine:GrpcUrl"] = "http://127.0.0.1:1",
            })
            .Build();
        var controller = SkillController(options, configuration);
        controller.ControllerContext = Context(Guid.NewGuid(), Guid.NewGuid());
        controller.HttpContext.User = new ClaimsPrincipal(new ClaimsIdentity(
            [new Claim("roles", "platform-founder")], "Test"));
        var request = new PublishSkillRequest(
            "skill", "1", "Skill", JsonDocument.Parse("{}").RootElement, ["CCT-1"]);

        var missing = await controller.GetLatestSkillAsync("missing", CancellationToken.None);
        var unavailable = Assert.IsType<ObjectResult>(await controller.PublishSkillAsync(
            request, CancellationToken.None));

        Assert.IsType<NotFoundObjectResult>(missing.Result);
        Assert.Equal(503, unavailable.StatusCode);
    }

    [Fact]
    public async Task Providers_ApplyTenantPrecedenceVisibilityAndNotFound()
    {
        var options = new DbContextOptionsBuilder<ProviderRegistryDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        var tenantId = Guid.NewGuid();
        await using (var db = new ProviderRegistryDbContext(options))
        {
            db.ProviderConfigs.AddRange(
                Provider("shared", null, "platform"),
                Provider("shared", tenantId, "tenant"),
                Provider("inactive", tenantId, "hidden", active: false),
                Provider("foreign", Guid.NewGuid(), "hidden"));
            await db.SaveChangesAsync();
        }
        var controller = new ProvidersController(
            new Factory<ProviderRegistryDbContext>(options),
            NullLogger<ProvidersController>.Instance)
        {
            ControllerContext = Context(tenantId, Guid.NewGuid()),
        };

        var listed = await controller.GetProviders(CancellationToken.None);
        var list = Assert.IsAssignableFrom<IReadOnlyList<ProviderConfigResponse>>(
            Assert.IsType<OkObjectResult>(listed.Result).Value);
        var selected = await controller.GetProvider("shared", CancellationToken.None);
        var missing = await controller.GetProvider("missing", CancellationToken.None);

        Assert.Equal(2, list.Count);
        Assert.Equal("tenant", Assert.IsType<ProviderConfigResponse>(
            Assert.IsType<OkObjectResult>(selected.Result).Value).AuthMethod);
        Assert.IsType<NotFoundObjectResult>(missing.Result);
    }

    private static SkillsController SkillController(
        DbContextOptions<SkillCatalogDbContext> options,
        IConfiguration configuration) => new(
            new Factory<SkillCatalogDbContext>(options),
            configuration,
            NullLogger<SkillsController>.Instance);

    private static SkillEntry Skill(
        string id,
        string version,
        string status,
        string definition,
        DateTimeOffset? publishedAt) => new()
        {
            SkillId = id,
            Version = version,
            DisplayName = id,
            Status = status,
            Definition = definition,
            CctSuite = ["CCT-1"],
            PublishedAt = publishedAt,
        };

    private static ProviderConfig Provider(
        string name,
        Guid? tenantId,
        string authMethod,
        bool active = true) => new()
        {
            ProviderName = name,
            TenantId = tenantId,
            AuthMethod = authMethod,
            ScopeSet = ["read"],
            Active = active,
        };

    private static async Task<(RelationshipWorkspaceController Controller, EmploymentRelationship Relationship,
        RelationshipOwnerGatewayStub Gateway)>
        CreateWorkspaceAsync()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await service.AdmitAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None);
        var gateway = new RelationshipOwnerGatewayStub();
        var controller = new RelationshipWorkspaceController(service, gateway)
        {
            ControllerContext = Context(tenantId, participantId),
        };
        return (controller, admitted.Relationship, gateway);
    }

    private static ControllerContext Context(Guid tenantId, Guid participantId)
    {
        var httpContext = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                [
                    new Claim("tenant_id", tenantId.ToString()),
                    new Claim("participant_id", participantId.ToString()),
                    new Claim("participant_role", "EMPLOYER"),
                    new Claim("correlation_id", Guid.NewGuid().ToString()),
                ],
                "Test")),
            TraceIdentifier = Guid.NewGuid().ToString(),
        };
        httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        return new ControllerContext { HttpContext = httpContext };
    }

    private static JsonElement Json(IActionResult result) =>
        JsonSerializer.SerializeToElement(Assert.IsType<OkObjectResult>(result).Value);

    private sealed class EmptyEvidenceGateway : IRelationshipEvidenceGateway
    {
        public Task<IReadOnlyList<Waooaw.ConstitutionalEngine.Grpc.CustomerVisibleEvidenceRecord>> QueryAsync(
            Guid tenantId,
            IReadOnlyCollection<Guid> evidenceIds,
            CancellationToken cancellationToken) =>
            Task.FromResult<IReadOnlyList<Waooaw.ConstitutionalEngine.Grpc.CustomerVisibleEvidenceRecord>>([]);
    }
}
