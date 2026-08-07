// Implements: work-contracts/WC-040-skill-architecture-s1-catalog.md §WC040-06
// constitutional_basis: C-036 (skills are constitutional units), C-076 (≥90% coverage), ADR-043 §5
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
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Skills;

// Avoids EF Core dual-provider conflict: provides factory directly.
file sealed class VersionInMemorySkillCatalogFactory : IDbContextFactory<SkillCatalogDbContext>
{
    private readonly DbContextOptions<SkillCatalogDbContext> _opts;
    public VersionInMemorySkillCatalogFactory(string dbName)
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
/// CCT-SKILL-VER-01 — Version pinning: hiring with @1.0.0 pinned resolves to @1.0.0 definition,
/// not @2.0.0, even when both are PUBLISHED.
/// ADR-043 §5: version is pinned at assignment — agent stays on the assigned version
/// until the customer explicitly accepts an upgrade.
/// </summary>
public sealed class CCT_SKILL_VER_01_VersionPinTests
    : IClassFixture<SkillVersionTestFactory>
{
    private readonly SkillVersionTestFactory _factory;
    private static readonly string TenantId = Guid.NewGuid().ToString();

    public CCT_SKILL_VER_01_VersionPinTests(SkillVersionTestFactory factory)
    {
        _factory = factory;
    }

    // ── Test 1: GET pinned @1.0.0 returns @1.0.0 definition ──────────────────
    // With both @1.0.0 and @2.0.0 PUBLISHED, pinned-version endpoint must return @1.0.0.

    [Fact]
    public async Task GetPinnedVersion_Returns1_0_0_Not2_0_0()
    {
        // Arrange
        var client = _factory.CreateClientForTenant(TenantId);

        // Act
        var response = await client.GetAsync("/api/v1/skills/content_publish/1.0.0");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK,
            because: "content_publish@1.0.0 is PUBLISHED in the catalog");

        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        json.GetProperty("skillId").GetString().Should().Be("content_publish");
        json.GetProperty("version").GetString().Should().Be("1.0.0",
            because: "CCT-SKILL-VER-01: pinned @1.0.0 must resolve to @1.0.0, not @2.0.0");
    }

    // ── Test 2: GET pinned @2.0.0 returns @2.0.0 definition ──────────────────
    // Both versions are independently resolvable.

    [Fact]
    public async Task GetPinnedVersion_Returns2_0_0_Independently()
    {
        // Arrange
        var client = _factory.CreateClientForTenant(TenantId);

        // Act
        var response = await client.GetAsync("/api/v1/skills/content_publish/2.0.0");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK,
            because: "content_publish@2.0.0 is PUBLISHED in the catalog");

        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        json.GetProperty("version").GetString().Should().Be("2.0.0");
    }

    // ── Test 3: GET latest returns @2.0.0 (most recently published) ──────────
    // Latest-version endpoint returns the most recently published version.

    [Fact]
    public async Task GetLatestVersion_Returns2_0_0_NotPinnedVersion()
    {
        // Arrange
        var client = _factory.CreateClientForTenant(TenantId);

        // Act
        var response = await client.GetAsync("/api/v1/skills/content_publish");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        json.GetProperty("version").GetString().Should().Be("2.0.0",
            because: "latest-version endpoint returns the most recently published version");
    }

    // ── Test 4: GET pinned nonexistent version → 404 SKILL_NOT_FOUND ─────────
    // Version pinning is strict — a non-existent version must return 404.

    [Fact]
    public async Task GetPinnedVersion_NonExistent_Returns404()
    {
        // Arrange
        var client = _factory.CreateClientForTenant(TenantId);

        // Act
        var response = await client.GetAsync("/api/v1/skills/content_publish/99.0.0");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.NotFound,
            because: "version 99.0.0 does not exist — pinned resolution must return 404");

        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        json.GetProperty("error").GetString().Should().Be("SKILL_NOT_FOUND");
    }
}

// ─── WebApplicationFactory with two-version catalog ──────────────────────────

file sealed class SkillVersionAuthOptions : AuthenticationSchemeOptions { }

file sealed class SkillVersionAuthHandler : AuthenticationHandler<SkillVersionAuthOptions>
{
    public SkillVersionAuthHandler(
        IOptionsMonitor<SkillVersionAuthOptions> opts,
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

public sealed class SkillVersionTestFactory : WebApplicationFactory<Program>
{
    private readonly string _dbName = "skill-ver-" + Guid.NewGuid();

    protected override void ConfigureWebHost(Microsoft.AspNetCore.Hosting.IWebHostBuilder builder)
    {
        builder.ConfigureTestServices(services =>
        {
            services.AddAuthentication(o =>
            {
                o.DefaultAuthenticateScheme = "Test";
                o.DefaultChallengeScheme    = "Test";
            }).AddScheme<SkillVersionAuthOptions, SkillVersionAuthHandler>("Test", _ => { });

            var descriptors = services
                .Where(d => d.ServiceType == typeof(IDbContextFactory<SkillCatalogDbContext>)
                         || d.ServiceType == typeof(SkillCatalogDbContext)
                         || d.ServiceType == typeof(DbContextOptions<SkillCatalogDbContext>))
                .ToList();
            foreach (var d in descriptors)
                services.Remove(d);

            services.AddSingleton<IDbContextFactory<SkillCatalogDbContext>>(
                new VersionInMemorySkillCatalogFactory(_dbName));
        });
    }

    protected override void Dispose(bool disposing)
    {
        // Seed is done once in constructor via service locator pattern
        base.Dispose(disposing);
    }

    /// <summary>
    /// Returns a client seeded with content_publish@1.0.0 and @2.0.0 both PUBLISHED.
    /// @2.0.0 has a later PublishedAt so it is returned by the latest-version endpoint.
    /// </summary>
    public HttpClient CreateClientForTenant(string tenantId)
    {
        using var scope   = Services.CreateScope();
        var dbFactory     = scope.ServiceProvider.GetRequiredService<IDbContextFactory<SkillCatalogDbContext>>();
        using var db      = dbFactory.CreateDbContext();

        if (!db.Skills.Any(s => s.SkillId == "content_publish"))
        {
            var now = DateTimeOffset.UtcNow;
            db.Skills.AddRange(
                new SkillEntry
                {
                    SkillId     = "content_publish",
                    Version     = "1.0.0",
                    DisplayName = "Content Publishing",
                    Definition  = "{\"version\":\"1.0.0\"}",
                    CctSuite    = [],
                    Status      = "PUBLISHED",
                    PublishedAt = now.AddMinutes(-10),
                },
                new SkillEntry
                {
                    SkillId     = "content_publish",
                    Version     = "2.0.0",
                    DisplayName = "Content Publishing v2",
                    Definition  = "{\"version\":\"2.0.0\"}",
                    CctSuite    = [],
                    Status      = "PUBLISHED",
                    PublishedAt = now,                // more recent → returned as "latest"
                });
            db.SaveChanges();
        }

        var c = CreateClient(new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });
        c.DefaultRequestHeaders.Add("x-test-tenant-id", tenantId);
        return c;
    }
}
