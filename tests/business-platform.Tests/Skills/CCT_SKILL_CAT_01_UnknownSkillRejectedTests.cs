// Implements: work-contracts/WC-040-skill-architecture-s1-catalog.md §WC040-06
// constitutional_basis: C-036 (skills are constitutional units), C-076 (≥90% coverage), ADR-043 §4
using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text.Encodings.Web;
using FluentAssertions;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Skills;

// ─── InMemory factory helper (shared by all skill CCT files) ─────────────────
// Avoids EF Core dual-provider conflict: provides factory directly without going
// through AddDbContextFactory / Npgsql provider registration.

internal sealed class InMemorySkillCatalogFactory : IDbContextFactory<SkillCatalogDbContext>
{
    private readonly DbContextOptions<SkillCatalogDbContext> _opts;
    public InMemorySkillCatalogFactory(string dbName)
    {
        _opts = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(dbName)
            .Options;
    }
    public SkillCatalogDbContext CreateDbContext() => new(_opts);
    public Task<SkillCatalogDbContext> CreateDbContextAsync(CancellationToken ct = default)
        => Task.FromResult(CreateDbContext());
}

// ─── CCT-SKILL-CAT-01: Unknown skill on hire → 422 SKILL_NOT_FOUND ───────────

/// <summary>
/// CCT-SKILL-CAT-01 — Hiring an agent with a declared skill that does not exist
/// in the Skill Catalog returns 422 with error=SKILL_NOT_FOUND.
/// ADR-043 §4: BP.EmployAgent validates every declared skill before proceeding.
/// C-036: Skills are constitutional units — unknown skills cannot be assigned.
/// </summary>
public sealed class CCT_SKILL_CAT_01_UnknownSkillRejectedTests
    : IClassFixture<SkillCatalogTestFactory>
{
    private readonly SkillCatalogTestFactory _factory;
    private static readonly string TenantId = Guid.NewGuid().ToString();

    public CCT_SKILL_CAT_01_UnknownSkillRejectedTests(SkillCatalogTestFactory factory)
    {
        _factory = factory;
    }

    // ── Test 1: Hire with unknown skill_id → 422 SKILL_NOT_FOUND ─────────────
    // C-036: an unknown skill_id cannot be assigned to an Employment Contract.

    [Fact]
    public async Task HireAgent_WithUnknownSkill_Returns422SkillNotFound()
    {
        // Arrange — empty catalog (no skills seeded)
        var client = _factory.CreateClientWithTenant(TenantId);

        var body = new HireAgentRequest(
            ContractId: "con-test-001",
            ProfessionalType: "digital-marketing-professional",
            SkillId: "legacy-skill",
            DecisionSpaceVersion: "1",
            ApprovedBudgetInrPaise: 1_000_000,
            BillingCycleAnchorDay: "1",
            Skills: [new SkillAssignment("nonexistent_skill", "1.0.0")]);

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/agents/hire", body);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.UnprocessableEntity,
            because: "C-036 requires unknown skills to be rejected before CE is called");

        var content = await response.Content.ReadFromJsonAsync<System.Text.Json.JsonElement>();
        content.GetProperty("error").GetString().Should().Be("SKILL_NOT_FOUND",
            because: "CCT-SKILL-CAT-01: error code must be SKILL_NOT_FOUND");
        content.GetProperty("skill_id").GetString().Should().Be("nonexistent_skill");
    }

    // ── Test 2: Hire with skill present but wrong version → 422 SKILL_NOT_FOUND ──
    // Pinned version must exist PUBLISHED; a different version does not satisfy the constraint.

    [Fact]
    public async Task HireAgent_WithWrongSkillVersion_Returns422SkillNotFound()
    {
        // Arrange — seed catalog with content_publish@1.0.0 only
        var client = _factory.CreateClientWithSkillAndTenant(
            skillId: "content_publish", version: "1.0.0", tenantId: TenantId);

        var body = new HireAgentRequest(
            ContractId: "con-test-002",
            ProfessionalType: "digital-marketing-professional",
            SkillId: "legacy-skill",
            DecisionSpaceVersion: "1",
            ApprovedBudgetInrPaise: 1_000_000,
            BillingCycleAnchorDay: "1",
            Skills: [new SkillAssignment("content_publish", "9.9.9")]);   // does not exist

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/agents/hire", body);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.UnprocessableEntity,
            because: "pinned version 9.9.9 does not exist — must return 422");

        var content = await response.Content.ReadFromJsonAsync<System.Text.Json.JsonElement>();
        content.GetProperty("error").GetString().Should().Be("SKILL_NOT_FOUND");
        content.GetProperty("version").GetString().Should().Be("9.9.9");
    }

    // ── Test 3: Hire with skills[] absent → CE is reached (not a skill validation failure) ──
    // No skills[] declared means no catalog check — hire proceeds to CE.

    [Fact]
    public async Task HireAgent_WithNoSkillsArray_DoesNotReturn422()
    {
        // Arrange — empty catalog; skills[] omitted from request
        var client = _factory.CreateClientWithTenant(TenantId);

        var body = new HireAgentRequest(
            ContractId: "con-test-003",
            ProfessionalType: "digital-marketing-professional",
            SkillId: "legacy-skill",
            DecisionSpaceVersion: "1",
            ApprovedBudgetInrPaise: 1_000_000,
            BillingCycleAnchorDay: "1");   // Skills omitted → null

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/agents/hire", body);

        // Assert — 422 is NOT returned (skills check skipped); CE is unavailable in test → 503
        response.StatusCode.Should().NotBe(HttpStatusCode.UnprocessableEntity,
            because: "no skills[] declared means no catalog check is performed");
    }
}

// ─── WebApplicationFactory for skill catalog CCTs ────────────────────────────

file sealed class TestAuthOptions : AuthenticationSchemeOptions { }

file sealed class TestAuthHandler : AuthenticationHandler<TestAuthOptions>
{
    public TestAuthHandler(
        IOptionsMonitor<TestAuthOptions> opts,
        ILoggerFactory logger,
        UrlEncoder encoder)
        : base(opts, logger, encoder) { }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        if (!Request.Headers.TryGetValue("x-test-tenant-id", out var tv))
            return Task.FromResult(AuthenticateResult.Fail("Missing x-test-tenant-id"));

        var claims = new[]
        {
            new Claim("tenant_id", tv.First()!),
            new Claim(ClaimTypes.NameIdentifier, "test-user"),
        };
        return Task.FromResult(AuthenticateResult.Success(
            new AuthenticationTicket(
                new ClaimsPrincipal(new ClaimsIdentity(claims, Scheme.Name)),
                Scheme.Name)));
    }
}

public sealed class SkillCatalogTestFactory : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(Microsoft.AspNetCore.Hosting.IWebHostBuilder builder)
    {
        builder.ConfigureTestServices(services =>
        {
            services.AddAuthentication(o =>
            {
                o.DefaultAuthenticateScheme = "Test";
                o.DefaultChallengeScheme    = "Test";
            }).AddScheme<TestAuthOptions, TestAuthHandler>("Test", _ => { });

            // Replace SkillCatalogDbContext with InMemory for isolation
            var descriptors = services
                .Where(d => d.ServiceType == typeof(IDbContextFactory<SkillCatalogDbContext>)
                         || d.ServiceType == typeof(SkillCatalogDbContext)
                         || d.ServiceType == typeof(DbContextOptions<SkillCatalogDbContext>))
                .ToList();
            foreach (var d in descriptors)
                services.Remove(d);

            services.AddSingleton<IDbContextFactory<SkillCatalogDbContext>>(
                new InMemorySkillCatalogFactory("skill-catalog-" + Guid.NewGuid()));
        });
    }

    /// <summary>Client authenticated as a given tenant, with empty skill catalog.</summary>
    public HttpClient CreateClientWithTenant(string tenantId)
    {
        var c = CreateClient(new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });
        c.DefaultRequestHeaders.Add("x-test-tenant-id", tenantId);
        return c;
    }

    /// <summary>
    /// Client authenticated as a given tenant, with one PUBLISHED skill seeded
    /// into the InMemory catalog.
    /// </summary>
    public HttpClient CreateClientWithSkillAndTenant(
        string skillId, string version, string tenantId)
    {
        // Seed the InMemory DB by resolving the factory from DI
        using var scope = Services.CreateScope();
        var dbFactory   = scope.ServiceProvider.GetRequiredService<IDbContextFactory<SkillCatalogDbContext>>();
        using var db    = dbFactory.CreateDbContext();

        db.Skills.Add(new SkillEntry
        {
            SkillId     = skillId,
            Version     = version,
            DisplayName = skillId,
            Definition  = "{}",
            CctSuite    = [],
            Status      = "PUBLISHED",
            PublishedAt = DateTimeOffset.UtcNow,
        });
        db.SaveChanges();

        var c = CreateClient(new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });
        c.DefaultRequestHeaders.Add("x-test-tenant-id", tenantId);
        return c;
    }
}
