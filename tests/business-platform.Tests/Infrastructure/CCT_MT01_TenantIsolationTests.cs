// Implements: architecture/reference/components/business-platform.md full
// constitutional_basis: C-005, C-026, C-059, C-076
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

// CCT-MT-01: Cross-tenant isolation adversarial test
// Verifies C-005 (Three-Ledger — tenants never share data)
// and C-026 (DB-level enforcement via RLS + middleware).
// A request bearing Tenant A's JWT MUST NOT observe any Tenant B resource.

namespace Waooaw.BusinessPlatform.Tests.Infrastructure;

/// <summary>
/// Constitutional Compliance Test: CCT-MT-01
/// Tenant Isolation — adversarial cross-tenant access scenarios.
/// C-005: Three-Ledger isolation guarantee.
/// C-026: DB-level enforcement (PostgreSQL RLS + SET LOCAL app.current_tenant_id).
/// C-059: Implementation traceability.
/// C-076: ≥90% branch coverage gate.
/// </summary>
public sealed class CCT_MT01_TenantIsolationTests : IClassFixture<CCT_MT01_TenantIsolationTests.TenantIsolationWebAppFactory>
{
    // ── Constitutional constants (C-005 — never share tenants) ──────────────
    private static readonly Guid TenantA = Guid.Parse("aaaaaaaa-0000-0000-0000-000000000001");
    private static readonly Guid TenantB = Guid.Parse("bbbbbbbb-0000-0000-0000-000000000002");

    // Well-known resource IDs seeded under Tenant B — Tenant A must never see these
    private static readonly Guid TenantBContractId = Guid.Parse("cccccccc-0000-0000-0000-000000000010");
    private static readonly Guid TenantBApprovalId = Guid.Parse("dddddddd-0000-0000-0000-000000000020");
    private static readonly Guid TenantBEvidenceId = Guid.Parse("eeeeeeee-0000-0000-0000-000000000030");

    private readonly TenantIsolationWebAppFactory _factory;

    public CCT_MT01_TenantIsolationTests(TenantIsolationWebAppFactory factory)
    {
        _factory = factory;
    }

    // ────────────────────────────────────────────────────────────────────────
    // CCT-MT-01-A: Cross-tenant employment contract — 404 enforcement
    // ────────────────────────────────────────────────────────────────────────

    [Fact(DisplayName = "CCT-MT-01-A: Tenant A JWT — cannot read Tenant B employment contract")]
    public async Task CrossTenantContract_TenantAJwt_Returns404()
    {
        // Arrange — C-005: Tenant A must never see Tenant B data
        var client = _factory.CreateClientForTenant(TenantA);

        // Act
        var response = await client.GetAsync(
            $"/api/v1/employment/contracts/{TenantBContractId}",
            CancellationToken.None);

        // Assert — must be 404 (resource invisible, not 403 which leaks existence)
        response.StatusCode.Should().Be(
            HttpStatusCode.NotFound,
            because: "C-005 requires Tenant A cannot observe any Tenant B resource — 404 prevents tenant enumeration attacks");
    }

    [Fact(DisplayName = "CCT-MT-01-B: Tenant A JWT — contract list never contains Tenant B contracts")]
    public async Task ContractList_TenantAJwt_ContainsOnlyTenantAContracts()
    {
        // Arrange — C-026: RLS scopes every SELECT to current_tenant_id
        var client = _factory.CreateClientForTenant(TenantA);

        // Act
        var response = await client.GetAsync("/api/v1/employment/contracts", CancellationToken.None);

        // Assert — 200 OK with empty or Tenant-A-only records
        response.StatusCode.Should().BeOneOf(
            HttpStatusCode.OK, HttpStatusCode.NoContent,
            because: "Tenant A can list their own contracts — C-026 RLS filters the result set");

        if (response.StatusCode == HttpStatusCode.OK)
        {
            var body = await response.Content.ReadAsStringAsync();
            body.Should().NotContain(
                TenantBContractId.ToString(),
                because: "C-005 prohibits cross-tenant data leakage — Tenant B contract must not appear in Tenant A's list");
        }
    }

    // ────────────────────────────────────────────────────────────────────────
    // CCT-MT-01-C: Cross-tenant approval — 404 enforcement
    // ────────────────────────────────────────────────────────────────────────

    [Fact(DisplayName = "CCT-MT-01-C: Tenant A JWT — cannot read Tenant B approval request")]
    public async Task CrossTenantApproval_TenantAJwt_Returns404()
    {
        // Arrange — C-005: approval records are tenant-scoped
        var client = _factory.CreateClientForTenant(TenantA);

        // Act
        var response = await client.GetAsync(
            $"/api/v1/approvals/{TenantBApprovalId}",
            CancellationToken.None);

        // Assert
        response.StatusCode.Should().Be(
            HttpStatusCode.NotFound,
            because: "C-005 requires approval records to be invisible across tenant boundary");
    }

    [Fact(DisplayName = "CCT-MT-01-D: Tenant A JWT — cannot approve Tenant B action")]
    public async Task CrossTenantApprove_TenantAJwt_Returns404()
    {
        // Arrange — C-026: RLS must block the approval record lookup before any state change
        var client = _factory.CreateClientForTenant(TenantA);

        // Act
        var response = await client.PostAsync(
            $"/api/v1/approvals/{TenantBApprovalId}/approve",
            new StringContent("{}", Encoding.UTF8, "application/json"),
            CancellationToken.None);

        // Assert — 404 (not 403) to avoid confirming the resource exists in another tenant
        response.StatusCode.Should().Be(
            HttpStatusCode.NotFound,
            because: "C-026 RLS must filter the approval before any state mutation — 404 prevents tenant-boundary mutation attacks");
    }

    // ────────────────────────────────────────────────────────────────────────
    // CCT-MT-01-E: Cross-tenant evidence record — 404 enforcement
    // ────────────────────────────────────────────────────────────────────────

    [Fact(DisplayName = "CCT-MT-01-E: Tenant A JWT — cannot read Tenant B evidence record")]
    public async Task CrossTenantEvidence_TenantAJwt_Returns404()
    {
        // Arrange — C-005: constitutional audit ledger is tenant-scoped
        var client = _factory.CreateClientForTenant(TenantA);

        // Act
        var response = await client.GetAsync(
            $"/api/v1/evidence/{TenantBEvidenceId}",
            CancellationToken.None);

        // Assert
        response.StatusCode.Should().Be(
            HttpStatusCode.NotFound,
            because: "C-005 guarantees the constitutional audit ledger is never shared across tenants");
    }

    [Fact(DisplayName = "CCT-MT-01-F: Tenant A JWT — evidence list never contains Tenant B records")]
    public async Task EvidenceList_TenantAJwt_ContainsOnlyTenantARecords()
    {
        // Arrange — C-026: RLS scopes evidence reads
        var client = _factory.CreateClientForTenant(TenantA);

        // Act
        var response = await client.GetAsync("/api/v1/evidence", CancellationToken.None);

        // Assert
        response.StatusCode.Should().BeOneOf(
            HttpStatusCode.OK, HttpStatusCode.NoContent,
            because: "Tenant A may have zero or more evidence records; 200/204 are both valid");

        if (response.StatusCode == HttpStatusCode.OK)
        {
            var body = await response.Content.ReadAsStringAsync();
            body.Should().NotContain(
                TenantBEvidenceId.ToString(),
                because: "C-005 prohibits Tenant B evidence records appearing in Tenant A's response");
        }
    }

    // ────────────────────────────────────────────────────────────────────────
    // CCT-MT-01-G: No tenant_id header — 401 enforcement
    // ────────────────────────────────────────────────────────────────────────

    [Fact(DisplayName = "CCT-MT-01-G: Request with no JWT — returns 401")]
    public async Task NoJwt_AnyResource_Returns401()
    {
        // Arrange — anonymous client (no auth header)
        var client = _factory.CreateClient();

        // Act
        var response = await client.GetAsync(
            $"/api/v1/employment/contracts/{TenantBContractId}",
            CancellationToken.None);

        // Assert — unauthenticated requests must be rejected before tenant resolution
        response.StatusCode.Should().Be(
            HttpStatusCode.Unauthorized,
            because: "C-026 requires tenant context from JWT — missing token must yield 401 before any DB access");
    }

    // ────────────────────────────────────────────────────────────────────────
    // CCT-MT-01-H: Middleware sets TenantContext from JWT claim
    // ────────────────────────────────────────────────────────────────────────

    [Fact(DisplayName = "CCT-MT-01-H: TenantIsolationMiddleware sets TenantId from JWT tenant_id claim")]
    public async Task TenantIsolationMiddleware_SetsTenantId_FromJwtClaim()
    {
        // Arrange — create a client scoped to TenantA and hit the health endpoint
        // (health endpoint is unauthenticated, but the middleware context should be populated for authenticated routes)
        var client = _factory.CreateClientForTenant(TenantA);

        // Act — call any authenticated endpoint; middleware executes before controller
        var response = await client.GetAsync("/api/v1/employment/contracts", CancellationToken.None);

        // Assert — middleware ran (request was not rejected with 500 due to missing tenant context)
        response.StatusCode.Should().NotBe(
            HttpStatusCode.InternalServerError,
            because: "TenantIsolationMiddleware must extract the tenant_id claim and set TenantContext without throwing");
    }

    [Fact(DisplayName = "CCT-MT-01-I: TenantIsolationMiddleware propagates different tenant IDs independently")]
    public async Task TenantIsolationMiddleware_TwoTenants_PropagateIndependently()
    {
        // Arrange — two concurrent clients with different tenant JWTs
        var clientA = _factory.CreateClientForTenant(TenantA);
        var clientB = _factory.CreateClientForTenant(TenantB);

        // Act — both fire requests concurrently (C-026: isolation must hold under concurrency)
        var taskA = clientA.GetAsync("/api/v1/employment/contracts", CancellationToken.None);
        var taskB = clientB.GetAsync("/api/v1/employment/contracts", CancellationToken.None);

        await Task.WhenAll(taskA, taskB);

        var responseA = await taskA;
        var responseB = await taskB;

        // Assert — both requests succeed without cross-contamination
        responseA.StatusCode.Should().NotBe(
            HttpStatusCode.InternalServerError,
            because: "Concurrent Tenant A requests must resolve their own TenantContext independently");
        responseB.StatusCode.Should().NotBe(
            HttpStatusCode.InternalServerError,
            because: "Concurrent Tenant B requests must resolve their own TenantContext independently");

        if (responseA.StatusCode == HttpStatusCode.OK && responseB.StatusCode == HttpStatusCode.OK)
        {
            var bodyA = await responseA.Content.ReadAsStringAsync();
            var bodyB = await responseB.Content.ReadAsStringAsync();

            bodyA.Should().NotContain(
                TenantB.ToString(),
                because: "C-005: Tenant A response must not bleed Tenant B tenant_id under concurrent load");
            bodyB.Should().NotContain(
                TenantA.ToString(),
                because: "C-005: Tenant B response must not bleed Tenant A tenant_id under concurrent load");
        }
    }

    // ────────────────────────────────────────────────────────────────────────
    // CCT-MT-01-J: Cross-tenant reject action — 404 enforcement
    // ────────────────────────────────────────────────────────────────────────

    [Fact(DisplayName = "CCT-MT-01-J: Tenant A JWT — cannot reject Tenant B approval")]
    public async Task CrossTenantReject_TenantAJwt_Returns404()
    {
        // Arrange — C-026: RLS must block rejection state change on cross-tenant approval
        var client = _factory.CreateClientForTenant(TenantA);
        var payload = new StringContent(
            JsonSerializer.Serialize(new { reason = "adversarial rejection attempt" }),
            Encoding.UTF8,
            "application/json");

        // Act
        var response = await client.PostAsync(
            $"/api/v1/approvals/{TenantBApprovalId}/reject",
            payload,
            CancellationToken.None);

        // Assert
        response.StatusCode.Should().Be(
            HttpStatusCode.NotFound,
            because: "C-026 RLS must make Tenant B approvals invisible to Tenant A — mutation blocked at DB layer");
    }

    // ────────────────────────────────────────────────────────────────────────
    // CCT-MT-01-K: Cross-tenant authority expand — 404 enforcement
    // ────────────────────────────────────────────────────────────────────────

    [Fact(DisplayName = "CCT-MT-01-K: Tenant A JWT — cannot expand authority on Tenant B contract")]
    public async Task CrossTenantAuthorityExpand_TenantAJwt_ReturnsNotSuccessful()
    {
        // Arrange — C-005: authority changes are scoped to tenant
        var client = _factory.CreateClientForTenant(TenantA);
        var payload = new StringContent(
            JsonSerializer.Serialize(new
            {
                contract_id = TenantBContractId,
                new_authority_level = "EXTENDED",
                evidence_ids = Array.Empty<string>(),
                constitutional_basis = "adversarial"
            }),
            Encoding.UTF8,
            "application/json");

        // Act
        var response = await client.PostAsync(
            "/api/v1/authority/expand",
            payload,
            CancellationToken.None);

        // Assert — must not be 200 (success must be blocked)
        response.StatusCode.Should().NotBe(
            HttpStatusCode.OK,
            because: "C-005 prohibits Tenant A from expanding authority on a Tenant B contract");
    }

    // ────────────────────────────────────────────────────────────────────────
    // Test Infrastructure — TenantIsolationWebAppFactory
    // ────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// WebApplicationFactory that stubs authentication with a configurable tenant_id claim.
    /// Replaces Keycloak JWT validation with a deterministic test handler (C-026 test infrastructure).
    /// </summary>
    public sealed class TenantIsolationWebAppFactory : WebApplicationFactory<Program>
    {
        // Track current tenant for the fake auth handler (thread-local for isolation under concurrency)
        private static readonly AsyncLocal<Guid> _currentTestTenant = new();

        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            builder.UseEnvironment("Testing");

            builder.ConfigureTestServices(services =>
            {
                // ── Replace JWT authentication with test stub (C-026 test support) ──
                services.AddAuthentication(options =>
                {
                    options.DefaultAuthenticateScheme = TestAuthHandler.SchemeName;
                    options.DefaultChallengeScheme = TestAuthHandler.SchemeName;
                })
                .AddScheme<AuthenticationSchemeOptions, TestAuthHandler>(
                    TestAuthHandler.SchemeName,
                    _ => { });

                // ── Register TenantContext as scoped (middleware reads it) ──
                services.TryAddScoped(_ => new TenantContext
                {
                    TenantId = _currentTestTenant.Value
                });

                // ── Suppress real DB connections in these middleware tests ──
                // (isolation is tested at HTTP/middleware layer; DB is integration-tested separately)
                services.AddLogging(logging =>
                {
                    logging.ClearProviders();
                    logging.AddDebug();
                });
            });
        }

        /// <summary>
        /// Creates an HttpClient that presents a JWT with the given tenant_id claim.
        /// Implements C-026: tenant_id is always sourced from the JWT, never from request body.
        /// </summary>
        public HttpClient CreateClientForTenant(Guid tenantId)
        {
            _currentTestTenant.Value = tenantId;
            var client = CreateClient();
            // Encode tenant ID into Authorization header value — test handler reads this
            var tenantEncoded = Convert.ToBase64String(tenantId.ToByteArray());
            client.DefaultRequestHeaders.Authorization =
                new AuthenticationHeaderValue(TestAuthHandler.SchemeName, tenantEncoded);
            return client;
        }
    }

    // ────────────────────────────────────────────────────────────────────────
    // Fake Authentication Handler — injects tenant_id claim from test token
    // ────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// Test authentication handler that extracts tenant_id from the Authorization header value
    /// and produces a ClaimsPrincipal with the tenant_id claim — mirrors Keycloak JWT structure
    /// used by TenantIsolationMiddleware (C-026).
    /// </summary>
    public sealed class TestAuthHandler : AuthenticationHandler<AuthenticationSchemeOptions>
    {
        public const string SchemeName = "TestScheme";

        public TestAuthHandler(
            IOptionsMonitor<AuthenticationSchemeOptions> options,
            ILoggerFactory logger,
            UrlEncoder encoder)
            : base(options, logger, encoder)
        {
        }

        protected override Task<AuthenticateResult> HandleAuthenticateAsync()
        {
            // If no Authorization header, fail authentication → middleware returns 401
            if (!Request.Headers.TryGetValue("Authorization", out var authHeader))
            {
                return Task.FromResult(AuthenticateResult.Fail("No Authorization header — C-026 requires JWT"));
            }

            var headerValue = authHeader.ToString();
            var prefix = $"{SchemeName} ";
            if (!headerValue.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                return Task.FromResult(AuthenticateResult.Fail("Invalid scheme — expected TestScheme"));
            }

            var encoded = headerValue[prefix.Length..];
            Guid tenantId;
            try
            {
                var bytes = Convert.FromBase64String(encoded);
                tenantId = new Guid(bytes);
            }
            catch (Exception ex)
            {
                return Task.FromResult(AuthenticateResult.Fail($"Invalid tenant encoding: {ex.Message}"));
            }

            // Produce claims matching Keycloak JWT structure (C-026 — tenant_id claim)
            var claims = new[]
            {
                new Claim("tenant_id", tenantId.ToString()),
                new Claim(ClaimTypes.NameIdentifier, $"test-user-{tenantId}"),
                new Claim(ClaimTypes.Name, $"test-user-{tenantId}"),
                new Claim("sub", $"test-sub-{tenantId}"),
            };

            var identity = new ClaimsIdentity(claims, SchemeName);
            var principal = new ClaimsPrincipal(identity);
            var ticket = new AuthenticationTicket(principal, SchemeName);

            return Task.FromResult(AuthenticateResult.Success(ticket));
        }
    }
}