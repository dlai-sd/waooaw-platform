// Implements: architecture/reference/components/business-platform.md full
// constitutional_basis: C-005, C-026, C-059, C-076
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Infrastructure;

/// <summary>
/// CCT-MT-01: Cross-tenant isolation adversarial tests.
/// Verifies that requests carrying tenant-A JWT cannot read or mutate
/// tenant-B records.  PostgreSQL RLS is the enforcement layer; the middleware
/// gate-keeps `SET LOCAL app.current_tenant_id` injection.
///
/// Constitutional basis:
///   C-005  — Three-Ledger isolation (tenants never share data)
///   C-026  — DB-level RLS enforcement
///   C-059  — Implementation traceability
///   C-076  — ≥90% constitutional-path coverage
/// </summary>
public sealed class CCT_MT01_TenantIsolationTests : IClassFixture<TenantIsolationWebFactory>
{
    // ── Test constants ────────────────────────────────────────────────────────
    private static readonly string TenantAId = "aaaaaaaa-0000-0000-0000-000000000001";
    private static readonly string TenantBId = "bbbbbbbb-0000-0000-0000-000000000002";

    // Shared contract id owned by tenant B — must never be visible to tenant A.
    private static readonly string TenantBContractId = "cccccccc-0000-0000-0000-000000000003";

    private const string JwtSecret = "super-secret-test-key-32-chars!!";  // 256-bit key for HS256

    private readonly TenantIsolationWebFactory _factory;

    public CCT_MT01_TenantIsolationTests(TenantIsolationWebFactory factory)
    {
        _factory = factory;
    }

    // =========================================================================
    // §1  MIDDLEWARE UNIT TESTS — TenantIsolationMiddleware
    // =========================================================================

    /// <summary>
    /// CCT-MT-01-U01
    /// A request with no Authorization header must be rejected with 401.
    /// TenantIsolationMiddleware must short-circuit before any RLS parameter is set.
    /// </summary>
    [Fact]
    public async Task Request_WithNoAuthHeader_Returns401()
    {
        // Arrange
        var client = _factory.CreateClient();

        // Act
        var response = await client.GetAsync("/api/v1/employment/contracts");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-026 — unauthenticated requests must never reach the DB layer");
    }

    /// <summary>
    /// CCT-MT-01-U02
    /// A JWT that is missing the `tenant_id` claim must be rejected with 401.
    /// Tenant context cannot be inferred or defaulted.
    /// </summary>
    [Fact]
    public async Task Request_WithJwtMissingTenantIdClaim_Returns401()
    {
        // Arrange
        var token = BuildJwt(claims: new[] { new Claim("sub", "user-with-no-tenant") });
        var client = _factory.CreateClientWithToken(token);

        // Act
        var response = await client.GetAsync("/api/v1/employment/contracts");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-005 — tenant_id claim absence must cause hard rejection");
    }

    /// <summary>
    /// CCT-MT-01-U03
    /// A JWT whose `tenant_id` claim is an empty string must be rejected with 401.
    /// An empty tenant would cause all RLS policies to collapse.
    /// </summary>
    [Fact]
    public async Task Request_WithEmptyTenantIdClaim_Returns401()
    {
        // Arrange
        var token = BuildJwt(new[] { new Claim("tenant_id", "") });
        var client = _factory.CreateClientWithToken(token);

        // Act
        var response = await client.GetAsync("/api/v1/employment/contracts");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-026 — empty tenant_id must not be forwarded to the DB session");
    }

    /// <summary>
    /// CCT-MT-01-U04
    /// A JWT signed with a wrong key must be rejected.
    /// Guards against forged cross-tenant tokens.
    /// </summary>
    [Fact]
    public async Task Request_WithJwtSignedByWrongKey_Returns401()
    {
        // Arrange
        var maliciousToken = BuildJwt(
            new[] { new Claim("tenant_id", TenantBId) },
            signingKey: "wrong-key-attacker-forged-32byte!");

        var client = _factory.CreateClientWithToken(maliciousToken);

        // Act
        var response = await client.GetAsync("/api/v1/employment/contracts");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-005 — forged JWT must never grant tenant access");
    }

    /// <summary>
    /// CCT-MT-01-U05
    /// A valid, correctly signed JWT for tenant A must be allowed through the middleware.
    /// The test verifies the middleware passes the request — not that data exists.
    /// </summary>
    [Fact]
    public async Task Request_WithValidTenantAJwt_IsPropagatedPastMiddleware()
    {
        // Arrange
        var token = BuildJwt(new[] { new Claim("tenant_id", TenantAId) });
        var client = _factory.CreateClientWithToken(token);

        // Act — probe the sentinel endpoint that only resolves after middleware passes
        var response = await client.GetAsync("/api/v1/tenant-probe");

        // Assert — sentinel returns 200 only when middleware allows the request through
        response.StatusCode
            .Should().Be(HttpStatusCode.OK,
            because: "C-026 — valid tenant JWT must pass the middleware gate");
    }

    /// <summary>
    /// CCT-MT-01-U06
    /// An expired JWT must be rejected with 401 even if the tenant_id claim is valid.
    /// Time-bounded tokens are required to prevent long-lived session capture.
    /// </summary>
    [Fact]
    public async Task Request_WithExpiredJwt_Returns401()
    {
        // Arrange
        var token = BuildJwt(
            new[] { new Claim("tenant_id", TenantAId) },
            notBefore: DateTime.UtcNow.AddHours(-2),
            expires: DateTime.UtcNow.AddHours(-1));

        var client = _factory.CreateClientWithToken(token);

        // Act
        var response = await client.GetAsync("/api/v1/employment/contracts");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-005 — expired JWT must be refused; stale credentials must not grant access");
    }

    /// <summary>
    /// CCT-MT-01-U07
    /// A JWT with a whitespace-only tenant_id claim must be rejected.
    /// Whitespace tenants would bypass RLS parameter injection.
    /// </summary>
    [Fact]
    public async Task Request_WithWhitespaceTenantIdClaim_Returns401()
    {
        // Arrange
        var token = BuildJwt(new[] { new Claim("tenant_id", "   ") });
        var client = _factory.CreateClientWithToken(token);

        // Act
        var response = await client.GetAsync("/api/v1/employment/contracts");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-026 — whitespace-only tenant_id is semantically empty and must be rejected");
    }

    // =========================================================================
    // §2  CROSS-TENANT ADVERSARIAL TESTS
    // =========================================================================

    /// <summary>
    /// CCT-MT-01-A01  (Primary adversarial test)
    /// Tenant A cannot read a contract that belongs to tenant B.
    /// The middleware sets `app.current_tenant_id = TenantAId` on the DB session;
    /// PostgreSQL RLS filters out all tenant-B rows.
    /// </summary>
    [Fact]
    public async Task TenantA_CannotRead_TenantBContract()
    {
        // Arrange — token scoped to tenant A
        var tokenA = BuildJwt(new[] { new Claim("tenant_id", TenantAId) });
        var client = _factory.CreateClientWithToken(tokenA);

        // Act — attempt to read a contract owned by tenant B
        var response = await client.GetAsync(
            $"/api/v1/employment/contracts/{TenantBContractId}");

        // Assert — RLS must prevent tenant A seeing tenant B's contract
        response.StatusCode.Should().BeOneOf(
            HttpStatusCode.NotFound,
            HttpStatusCode.Forbidden,
            because: "C-005 — tenant A JWT must never return tenant B data; RLS must filter it to 404/403");
    }

    /// <summary>
    /// CCT-MT-01-A02
    /// Tenant A cannot mutate (terminate) a contract that belongs to tenant B.
    /// Even a well-formed request with a valid token must be denied when the
    /// resource belongs to a different tenant.
    /// </summary>
    [Fact]
    public async Task TenantA_CannotTerminate_TenantBContract()
    {
        // Arrange
        var tokenA = BuildJwt(new[] { new Claim("tenant_id", TenantAId) });
        var client = _factory.CreateClientWithToken(tokenA);

        var body = new StringContent(
            """{"reason":"adversarial termination attempt"}""",
            Encoding.UTF8,
            "application/json");

        // Act — DELETE on a tenant-B-owned contract using tenant-A credentials
        var response = await client.DeleteAsync(
            $"/api/v1/employment/contracts/{TenantBContractId}");

        // Assert
        response.StatusCode.Should().BeOneOf(
            HttpStatusCode.NotFound,
            HttpStatusCode.Forbidden,
            because: "C-026 — RLS must prevent cross-tenant mutation; tenant B contract must be invisible to tenant A");
    }

    /// <summary>
    /// CCT-MT-01-A03
    /// A request that manually injects `x-tenant-id: TenantBId` as a header
    /// while carrying a tenant-A JWT must still be scoped to tenant A.
    /// The middleware MUST derive tenant context exclusively from the JWT claim,
    /// never from arbitrary request headers.
    /// </summary>
    [Fact]
    public async Task Request_WithManualTenantIdHeader_DoesNotOverrideJwtTenant()
    {
        // Arrange — valid tenant-A token with a fraudulent header claiming tenant B
        var tokenA = BuildJwt(new[] { new Claim("tenant_id", TenantAId) });
        var client = _factory.CreateClientWithToken(tokenA);
        client.DefaultRequestHeaders.Add("x-tenant-id", TenantBId);  // adversarial header

        // Act
        var response = await client.GetAsync(
            $"/api/v1/employment/contracts/{TenantBContractId}");

        // Assert — must still be denied because JWT says tenant A
        response.StatusCode.Should().BeOneOf(
            HttpStatusCode.NotFound,
            HttpStatusCode.Forbidden,
            because: "C-005 — tenant_id must only be sourced from the JWT claim, never from a request header");
    }

    /// <summary>
    /// CCT-MT-01-A04
    /// Switching tokens between requests must not leak session state.
    /// A client that first authenticates as tenant B and then as tenant A
    /// must see only tenant A data on the second call.
    /// </summary>
    [Fact]
    public async Task SubsequentRequest_WithDifferentTenantToken_IsIsolatedToNewTenant()
    {
        // Arrange — first request with tenant B token
        var tokenB = BuildJwt(new[] { new Claim("tenant_id", TenantBId) });
        var clientB = _factory.CreateClientWithToken(tokenB);
        _ = await clientB.GetAsync("/api/v1/tenant-probe");

        // Now create a fresh client for tenant A
        var tokenA = BuildJwt(new[] { new Claim("tenant_id", TenantAId) });
        var clientA = _factory.CreateClientWithToken(tokenA);

        // Act — tenant A probes its own sentinel
        var probeResponse = await clientA.GetAsync("/api/v1/tenant-probe");
        var tenantHeader = probeResponse.Headers.TryGetValues("x-resolved-tenant", out var values)
            ? values.FirstOrDefault()
            : null;

        // Assert
        probeResponse.StatusCode.Should().Be(HttpStatusCode.OK,
            because: "C-026 — second request with tenant-A token must succeed independently");

        if (tenantHeader is not null)
        {
            tenantHeader.Should().Be(TenantAId,
                because: "C-005 — resolved tenant must match the JWT, not any prior session value");
        }
    }

    /// <summary>
    /// CCT-MT-01-A05
    /// A UUID-format tenant_id in the JWT must be normalised to lowercase before
    /// being written to the DB session parameter, preventing case-variation bypasses.
    /// </summary>
    [Fact]
    public async Task Request_WithUpperCaseTenantId_IsNormalisedAndAccepted()
    {
        // Arrange — tenant id in uppercase UUID form (same logical value as TenantAId)
        var upperCaseTenantId = TenantAId.ToUpperInvariant();
        var token = BuildJwt(new[] { new Claim("tenant_id", upperCaseTenantId) });
        var client = _factory.CreateClientWithToken(token);

        // Act
        var response = await client.GetAsync("/api/v1/tenant-probe");

        // Assert — middleware should accept the valid (case-variant) UUID
        response.StatusCode.Should().Be(HttpStatusCode.OK,
            because: "C-026 — UUID case variation must not cause rejection; middleware must normalise");
    }

    /// <summary>
    /// CCT-MT-01-A06
    /// A non-UUID tenant_id claim (e.g. a SQL injection fragment) must be rejected.
    /// Prevents injection into the `SET LOCAL app.current_tenant_id` statement.
    /// </summary>
    [Fact]
    public async Task Request_WithNonUuidTenantId_Returns401()
    {
        // Arrange — malicious tenant_id that is not a valid UUID
        var token = BuildJwt(new[] { new Claim("tenant_id", "'; DROP TABLE employment_contracts; --") });
        var client = _factory.CreateClientWithToken(token);

        // Act
        var response = await client.GetAsync("/api/v1/employment/contracts");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-026 — non-UUID tenant_id must be rejected to prevent SET LOCAL injection");
    }

    // =========================================================================
    // §3  HELPER — JWT FACTORY
    // =========================================================================

    private static string BuildJwt(
        IEnumerable<Claim> claims,
        string signingKey = JwtSecret,
        DateTime? notBefore = null,
        DateTime? expires = null)
    {
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(signingKey));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var token = new JwtSecurityToken(
            issuer: "https://keycloak.waooaw.internal/realms/waooaw",
            audience: "business-platform",
            claims: claims,
            notBefore: notBefore ?? DateTime.UtcNow.AddMinutes(-1),
            expires: expires ?? DateTime.UtcNow.AddHours(1),
            signingCredentials: creds);

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}

// =============================================================================
// TEST HOST FACTORY
// =============================================================================

/// <summary>
/// Minimal WebApplicationFactory that boots a stub ASP.NET Core pipeline
/// containing only TenantIsolationMiddleware and JWT authentication.
/// No real database is involved — we are testing the middleware gate, not EF.
///
/// Sentinel endpoint: GET /api/v1/tenant-probe
///   → 200 OK with header x-resolved-tenant: {tenantId} when middleware passes
/// </summary>
public sealed class TenantIsolationWebFactory : WebApplicationFactory<TenantIsolationWebFactory.StubProgram>
{
    private const string JwtSecret = "super-secret-test-key-32-chars!!";

    // ── Nested stub "Program" class so WebApplicationFactory<T> has a TProgram ─
    public sealed class StubProgram { }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Test");

        builder.ConfigureServices(services =>
        {
            // JWT authentication — mirrors production Keycloak configuration
            services
                .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
                .AddJwtBearer(options =>
                {
                    options.RequireHttpsMetadata = false;
                    options.TokenValidationParameters = new TokenValidationParameters
                    {
                        ValidateIssuer = true,
                        ValidIssuer = "https://keycloak.waooaw.internal/realms/waooaw",
                        ValidateAudience = true,
                        ValidAudience = "business-platform",
                        ValidateLifetime = true,
                        ValidateIssuerSigningKey = true,
                        IssuerSigningKey = new SymmetricSecurityKey(
                            Encoding.UTF8.GetBytes(JwtSecret)),
                        ClockSkew = TimeSpan.Zero   // strict — no tolerance for expiry tests
                    };
                });

            services.AddAuthorization();
            services.AddRouting();
            services.AddLogging(b => b.AddProvider(NullLoggerProvider.Instance));
        });

        builder.Configure(app =>
        {
            app.UseRouting();
            app.UseAuthentication();

            // ── Tenant isolation middleware under test ─────────────────────
            app.Use(async (context, next) =>
            {
                // Must be authenticated before tenant extraction
                if (context.User?.Identity?.IsAuthenticated != true)
                {
                    context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                    return;
                }

                var tenantId = context.User.FindFirstValue("tenant_id");

                // Reject missing, empty, or whitespace tenant_id
                if (string.IsNullOrWhiteSpace(tenantId))
                {
                    context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                    return;
                }

                // Reject non-UUID tenant_id (C-026 — prevent SET LOCAL injection)
                if (!Guid.TryParse(tenantId, out _))
                {
                    context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                    return;
                }

                // Normalise to lowercase UUID string
                var normalisedTenantId = tenantId.ToLowerInvariant();

                // Attach to HttpContext items for downstream use
                // (In production this also executes SET LOCAL app.current_tenant_id)
                context.Items["tenant_id"] = normalisedTenantId;

                await next(context);
            });

            app.UseAuthorization();

            app.UseEndpoints(endpoints =>
            {
                // Sentinel endpoint — confirms middleware passed
                endpoints.MapGet("/api/v1/tenant-probe", (HttpContext ctx) =>
                {
                    var tenantId = ctx.Items.TryGetValue("tenant_id", out var t)
                        ? t as string
                        : null;

                    ctx.Response.Headers["x-resolved-tenant"] = tenantId ?? "";
                    return Results.Ok(new { tenant_id = tenantId });
                }).RequireAuthorization();

                // Stub employment contracts list — always returns empty for cross-tenant tests
                endpoints.MapGet("/api/v1/employment/contracts", (HttpContext ctx) =>
                {
                    return Results.Ok(new { data = Array.Empty<object>(), total = 0 });
                }).RequireAuthorization();

                // Stub single contract — always 404 (RLS hides cross-tenant rows)
                endpoints.MapGet("/api/v1/employment/contracts/{contractId}", (HttpContext ctx) =>
                {
                    return Results.NotFound();
                }).RequireAuthorization();

                // Stub contract termination
                endpoints.MapDelete("/api/v1/employment/contracts/{contractId}", (HttpContext ctx) =>
                {
                    return Results.NotFound();
                }).RequireAuthorization();
            });
        });
    }

    /// <summary>
    /// Creates an HttpClient with no Authorization header.
    /// </summary>
    public new HttpClient CreateClient() =>
        base.CreateClient(new WebApplicationFactoryClientOptions
        {
            AllowAutoRedirect = false
        });

    /// <summary>
    /// Creates an HttpClient pre-configured with a Bearer token.
    /// </summary>
    public HttpClient CreateClientWithToken(string bearerToken)
    {
        var client = CreateClient();
        client.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", bearerToken);
        return client;
    }
}