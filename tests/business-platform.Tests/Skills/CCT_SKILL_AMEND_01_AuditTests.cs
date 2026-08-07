// Implements: work-contracts/WC-040-skill-architecture-s1-catalog.md §WC040-06
// constitutional_basis: C-023 (Evidence First), C-036 (skills are constitutional units), C-076, ADR-043 §4
using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text.Encodings.Web;
using System.Text.Json;
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

// Avoids EF Core dual-provider conflict: provides factory directly.
file sealed class AmendInMemorySkillCatalogFactory : IDbContextFactory<SkillCatalogDbContext>
{
    private readonly DbContextOptions<SkillCatalogDbContext> _opts;
    public AmendInMemorySkillCatalogFactory(string dbName)
    {
        _opts = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(dbName)
            .Options;
    }
    public SkillCatalogDbContext CreateDbContext() => new(_opts);
    public Task<SkillCatalogDbContext> CreateDbContextAsync(CancellationToken ct = default)
        => Task.FromResult(CreateDbContext());
}

/// <summary>
/// CCT-SKILL-AMEND-01 — Skill amendment audit: adding a skill via AmendContract
/// requires CE.ValidateAction with action_type=SKILL_AMENDMENT before any state change.
/// ADR-043 §4: "BP calls CE.ValidateAction with action_type=SKILL_AMENDMENT."
/// C-023: CE must be called before any state change.
/// </summary>
public sealed class CCT_SKILL_AMEND_01_AuditTests
    : IClassFixture<AmendContractTestFactory>
{
    private readonly AmendContractTestFactory _factory;
    private static readonly string TenantId = Guid.NewGuid().ToString();

    public CCT_SKILL_AMEND_01_AuditTests(AmendContractTestFactory factory)
    {
        _factory = factory;
    }

    // ── Test 1: AmendContract ADD with valid skill → CE called (503 = CE unavailable in test) ─
    // The 503 proves the request passed skill validation and reached the CE call.
    // If CE call was NOT made, the test would get a different response (422 or 200).

    [Fact]
    public async Task AmendContract_AddKnownSkill_ReachesCeValidation()
    {
        // Arrange — catalog seeded with content_publish@1.0.0
        var client = _factory.CreateClientWithSkill(TenantId);

        var body = new AmendContractRequest(
            ContractId: "con-amend-001",
            SkillId: "content_publish",
            SkillVersion: "1.0.0",
            AmendmentType: "ADD");

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/agents/amend", body);

        // Assert — CE is unavailable in test → 503 confirms the request reached CE.
        // 422 would mean skill validation failed; 400 would mean request was malformed.
        response.StatusCode.Should().Be(HttpStatusCode.ServiceUnavailable,
            because: "CCT-SKILL-AMEND-01: skill passed validation; 503 proves CE was reached (C-023)");
    }

    // ── Test 2: AmendContract ADD with unknown skill → 422 before CE is called ──
    // Skill must exist at declared version before CE is invoked (same pre-condition as hire).

    [Fact]
    public async Task AmendContract_AddUnknownSkill_Returns422BeforeCe()
    {
        // Arrange — catalog seeded with content_publish@1.0.0 only
        var client = _factory.CreateClientWithSkill(TenantId);

        var body = new AmendContractRequest(
            ContractId: "con-amend-002",
            SkillId: "nonexistent_skill",
            SkillVersion: "1.0.0",
            AmendmentType: "ADD");

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/agents/amend", body);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.UnprocessableEntity,
            because: "skill not found — 422 must be returned before CE is called");

        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        json.GetProperty("error").GetString().Should().Be("SKILL_NOT_FOUND");
    }

    // ── Test 3: AmendContract REMOVE — no catalog check, goes straight to CE ──
    // REMOVE does not need a catalog lookup (skill may be deprecated; customer removes it).

    [Fact]
    public async Task AmendContract_RemoveSkill_ReachesCeValidation()
    {
        // Arrange
        var client = _factory.CreateClientWithSkill(TenantId);

        var body = new AmendContractRequest(
            ContractId: "con-amend-003",
            SkillId: "content_publish",
            SkillVersion: "1.0.0",
            AmendmentType: "REMOVE");

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/agents/amend", body);

        // Assert — REMOVE skips catalog check; CE is unreachable in test → 503
        response.StatusCode.Should().Be(HttpStatusCode.ServiceUnavailable,
            because: "REMOVE skips catalog check and goes directly to CE (C-023)");
    }

    // ── Test 4: AmendContract with invalid amendment_type → 400 ───────────────
    // Only ADD and REMOVE are valid amendment types.

    [Fact]
    public async Task AmendContract_InvalidAmendmentType_Returns400()
    {
        // Arrange
        var client = _factory.CreateClientWithSkill(TenantId);

        var body = new AmendContractRequest(
            ContractId: "con-amend-004",
            SkillId: "content_publish",
            SkillVersion: "1.0.0",
            AmendmentType: "UPGRADE");   // invalid

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/agents/amend", body);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.BadRequest,
            because: "UPGRADE is not a valid amendment type; only ADD and REMOVE are valid");
    }
}

// ─── WebApplicationFactory for amendment CCTs ────────────────────────────────

file sealed class AmendAuthOptions : AuthenticationSchemeOptions { }

file sealed class AmendAuthHandler : AuthenticationHandler<AmendAuthOptions>
{
    public AmendAuthHandler(
        IOptionsMonitor<AmendAuthOptions> opts,
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

public sealed class AmendContractTestFactory : WebApplicationFactory<Program>
{
    private readonly string _dbName = "skill-amend-" + Guid.NewGuid();

    protected override void ConfigureWebHost(Microsoft.AspNetCore.Hosting.IWebHostBuilder builder)
    {
        builder.ConfigureTestServices(services =>
        {
            services.AddAuthentication(o =>
            {
                o.DefaultAuthenticateScheme = "Test";
                o.DefaultChallengeScheme    = "Test";
            }).AddScheme<AmendAuthOptions, AmendAuthHandler>("Test", _ => { });

            var descriptors = services
                .Where(d => d.ServiceType == typeof(IDbContextFactory<SkillCatalogDbContext>)
                         || d.ServiceType == typeof(SkillCatalogDbContext)
                         || d.ServiceType == typeof(DbContextOptions<SkillCatalogDbContext>))
                .ToList();
            foreach (var d in descriptors)
                services.Remove(d);

            services.AddSingleton<IDbContextFactory<SkillCatalogDbContext>>(
                new AmendInMemorySkillCatalogFactory(_dbName));
        });
    }

    /// <summary>Client with tenant header; catalog seeded with content_publish@1.0.0.</summary>
    public HttpClient CreateClientWithSkill(string tenantId)
    {
        using var scope = Services.CreateScope();
        var dbFactory   = scope.ServiceProvider.GetRequiredService<IDbContextFactory<SkillCatalogDbContext>>();
        using var db    = dbFactory.CreateDbContext();

        if (!db.Skills.Any(s => s.SkillId == "content_publish"))
        {
            db.Skills.Add(new SkillEntry
            {
                SkillId     = "content_publish",
                Version     = "1.0.0",
                DisplayName = "Content Publishing",
                Definition  = "{}",
                CctSuite    = [],
                Status      = "PUBLISHED",
                PublishedAt = DateTimeOffset.UtcNow,
            });
            db.SaveChanges();
        }

        var c = CreateClient(new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });
        c.DefaultRequestHeaders.Add("x-test-tenant-id", tenantId);
        return c;
    }
}
