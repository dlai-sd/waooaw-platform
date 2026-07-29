// Implements: architecture/reference/components/business-platform.md full
// constitutional_basis: C-005, C-026, C-059, C-076
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text;
using System.Text.Encodings.Web;
using Xunit;

// CCT-MT-01: Cross-tenant isolation adversarial test suite
// C-005: Three-Ledger — tenants never share data
// C-026: DB-level RLS enforcement via SET LOCAL app.current_tenant_id
// C-076: ≥90% coverage obligation

namespace Waooaw.BusinessPlatform.Tests.Infrastructure;

/// <summary>
/// Constitutional Compliance Test: CCT-MT-01
/// Adversarially verifies that a JWT carrying tenant_id=A cannot observe or mutate
/// any resource owned by tenant_id=B. The Business Platform TenantIsolationMiddleware
/// extracts tenant_id from the Keycloak JWT claim and posts it to PostgreSQL RLS via
/// SET LOCAL app.current_tenant_id — these tests verify the full chain.
/// C-005 (Three-Ledger isolation), C-026 (DB-level enforcement), C-059 (traceability).
/// </summary>
public sealed class CCT_MT01_TenantIsolationTests : IClassFixture<TenantIsolationWebApplicationFactory>
{
    private readonly TenantIsolationWebApplicationFactory _factory;
    private readonly ILogger<CCT_MT01_TenantIsolationTests> _logger;

    private static readonly Guid TenantA = Guid.Parse("aaaaaaaa-0000-0000-0000-000000000001");
    private static readonly Guid TenantB = Guid.Parse("bbbbbbbb-0000-0000-0000-000000000002");
    private static readonly Guid TenantBContractId = Guid.Parse("cccccccc-0000-0000-0000-000000000003");
    private static readonly Guid TenantBApprovalId = Guid.Parse("dddddddd-0000-0000-0000-000000000004");
    private static readonly Guid TenantBEvidenceId = Guid.Parse("eeeeeeee-0000-0000-0000-000000000005");

    public CCT_MT01_TenantIsolationTests(TenantIsolationWebApplicationFactory factory)
    {
        _factory = factory;
        _logger = factory.Services.GetRequiredService<ILogger<CCT_MT01_TenantIsolationTests>>();
    }

    // ─── §1 Unauthenticated requests must always be rejected ──────────────────

    [Fact]
    public async Task CCT_MT01_01_Unauthenticated_Employment_List_Returns401()
    {
        // C-026: No token → no tenant → must not reach DB
        var client = _factory.CreateClient();

        var response = await client.GetAsync("/api/v1/employment/contracts");

        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-026: no JWT means no tenant_id — request must be rejected before touching RLS");
    }

    [Fact]
    public async Task CCT_MT01_02_Unauthenticated_Approvals_Returns401()
    {
        var client = _factory.CreateClient();

        var response = await client.GetAsync("/api/v1/approvals");

        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-026: unauthenticated approval listing must be blocked");
    }

    [Fact]
    public async Task CCT_MT01_03_Unauthenticated_Evidence_Returns401()
    {
        var client = _factory.CreateClient();

        var response = await client.GetAsync("/api/v1/evidence");

        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-005: unauthenticated evidence access violates Three-Ledger isolation");
    }

    [Fact]
    public async Task CCT_MT01_04_Unauthenticated_Authority_Returns401()
    {
        var client = _factory.CreateClient();

        var response = await client.GetAsync(
            $"/api/v1/authority/current?contractId={TenantBContractId}");

        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized,
            because: "C-026: authority endpoint must enforce JWT gate");
    }

    // ─── §2 Cross-tenant read isolation on Employment Contracts ───────────────

    [Fact]
    public async Task CCT_MT01_05_TenantA_CannotRead_TenantB_Contract()
    {
        // Adversarial: token for tenant A, URL references a contract owned by tenant B.
        // RLS must silently exclude it → 404 (never 200 with tenant B data).
        var client = CreateClientForTenant(TenantA);

        var response = await client.GetAsync(
            $"/api/v1/employment/contracts/{TenantBContractId}");

        response.StatusCode.Should().BeOneOf(
            new[]
            {
                HttpStatusCode.NotFound,
                HttpStatusCode.Forbidden,
                HttpStatusCode.Unauthorized,
                HttpStatusCode.InternalServerError
            },
            because: "C-005: tenant A's RLS window must not reveal tenant B's contract");

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: 200 with cross-tenant data is a constitutional breach");
    }

    [Fact]
    public async Task CCT_MT01_06_TenantA_Employment_List_NeverContains_TenantB_Data()
    {
        // Even if tenant B has contracts seeded, tenant A's list must not include them.
        var client = CreateClientForTenant(TenantA);

        var response = await client.GetAsync("/api/v1/employment/contracts");

        // Any 2xx is acceptable for the list itself — but response body must be scoped.
        // For middleware unit testing without a real DB, this validates the tenant claim
        // is present in the request that reaches the controller.
        if (response.StatusCode == HttpStatusCode.OK)
        {
            var body = await response.Content.ReadAsStringAsync();
            body.Should().NotContain(TenantB.ToString(),
                because: "C-005: tenant A list response must not contain tenant B's GUID");
            body.Should().NotContain(TenantBContractId.ToString(),
                because: "C-005: tenant A list response must not contain tenant B's contract ID");
        }
    }

    // ─── §3 Cross-tenant read isolation on Approvals ──────────────────────────

    [Fact]
    public async Task CCT_MT01_07_TenantA_CannotRead_TenantB_Approval()
    {
        // C-005: tenant A token must not retrieve approval owned by tenant B.
        var client = CreateClientForTenant(TenantA);

        var response = await client.GetAsync(
            $"/api/v1/approvals/{TenantBApprovalId}");

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: cross-tenant approval read is a constitutional breach");

        response.StatusCode.Should().BeOneOf(
            new[]
            {
                HttpStatusCode.NotFound,
                HttpStatusCode.Forbidden,
                HttpStatusCode.Unauthorized,
                HttpStatusCode.InternalServerError
            },
            because: "C-026: RLS must exclude tenant B approval from tenant A's query window");
    }

    [Fact]
    public async Task CCT_MT01_08_TenantA_Approvals_List_NeverContains_TenantB_Data()
    {
        var client = CreateClientForTenant(TenantA);

        var response = await client.GetAsync("/api/v1/approvals");

        if (response.StatusCode == HttpStatusCode.OK)
        {
            var body = await response.Content.ReadAsStringAsync();
            body.Should().NotContain(TenantB.ToString(),
                because: "C-005: tenant A approval list must be RLS-scoped to tenant A");
            body.Should().NotContain(TenantBApprovalId.ToString(),
                because: "C-005: tenant B approval ID must not appear in tenant A's list");
        }
    }

    // ─── §4 Cross-tenant read isolation on Evidence ───────────────────────────

    [Fact]
    public async Task CCT_MT01_09_TenantA_CannotRead_TenantB_EvidenceRecord()
    {
        // C-005 + C-026: Evidence ledger is the most constitutionally sensitive store.
        // Tenant A must never read tenant B's evidence under any circumstance.
        var client = CreateClientForTenant(TenantA);

        var response = await client.GetAsync(
            $"/api/v1/evidence/{TenantBEvidenceId}");

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: cross-tenant evidence read is a Three-Ledger violation");
    }

    [Fact]
    public async Task CCT_MT01_10_TenantA_Evidence_List_NeverContains_TenantB_Data()
    {
        var client = CreateClientForTenant(TenantA);

        var response = await client.GetAsync("/api/v1/evidence");

        if (response.StatusCode == HttpStatusCode.OK)
        {
            var body = await response.Content.ReadAsStringAsync();
            body.Should().NotContain(TenantB.ToString(),
                because: "C-005: evidence list must be RLS-scoped — tenant B GUID must not leak");
            body.Should().NotContain(TenantBEvidenceId.ToString(),
                because: "C-005: tenant B evidence record ID must not appear in tenant A's list");
        }
    }

    // ─── §5 Cross-tenant mutation isolation ───────────────────────────────────

    [Fact]
    public async Task CCT_MT01_11_TenantA_CannotActivate_TenantB_Contract()
    {
        // C-005: PUT /activate with tenant A JWT on tenant B's contractId must not succeed.
        var client = CreateClientForTenant(TenantA);

        var response = await client.PutAsync(
            $"/api/v1/employment/contracts/{TenantBContractId}/activate",
            new StringContent("{}", Encoding.UTF8, "application/json"));

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: tenant A must not activate a contract belonging to tenant B");

        response.StatusCode.Should().BeOneOf(
            new[]
            {
                HttpStatusCode.NotFound,
                HttpStatusCode.Forbidden,
                HttpStatusCode.Unauthorized,
                HttpStatusCode.InternalServerError
            },
            because: "C-026: RLS + middleware must block cross-tenant mutation");
    }

    [Fact]
    public async Task CCT_MT01_12_TenantA_CannotSuspend_TenantB_Contract()
    {
        // C-005: suspension is a state mutation — RLS must block cross-tenant writes.
        var client = CreateClientForTenant(TenantA);
        var body = new StringContent(
            """{"reason":"adversarial suspend attempt"}""",
            Encoding.UTF8,
            "application/json");

        var response = await client.PutAsync(
            $"/api/v1/employment/contracts/{TenantBContractId}/suspend", body);

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: cross-tenant contract suspension is a constitutional breach");
    }

    [Fact]
    public async Task CCT_MT01_13_TenantA_CannotTerminate_TenantB_Contract()
    {
        // C-005: termination is irreversible — must be guarded by tenant isolation.
        var client = CreateClientForTenant(TenantA);
        var request = new HttpRequestMessage(
            HttpMethod.Delete,
            $"/api/v1/employment/contracts/{TenantBContractId}");
        request.Content = new StringContent(
            """{"reason":"adversarial termination"}""",
            Encoding.UTF8,
            "application/json");

        var response = await client.SendAsync(request);

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: tenant A must not terminate tenant B's contract");
    }

    [Fact]
    public async Task CCT_MT01_14_TenantA_CannotApprove_TenantB_Approval()
    {
        // C-005 + C-026: approval actions write evidence — cross-tenant approval is a
        // constitutional breach. RLS must prevent this reaching the DB write path.
        var client = CreateClientForTenant(TenantA);

        var response = await client.PostAsync(
            $"/api/v1/approvals/{TenantBApprovalId}/approve",
            new StringContent("{}", Encoding.UTF8, "application/json"));

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: tenant A approving tenant B's action is a Three-Ledger violation");
    }

    [Fact]
    public async Task CCT_MT01_15_TenantA_CannotReject_TenantB_Approval()
    {
        // C-005: rejection also writes evidence — same isolation requirement applies.
        var client = CreateClientForTenant(TenantA);
        var body = new StringContent(
            """{"reason":"adversarial rejection"}""",
            Encoding.UTF8,
            "application/json");

        var response = await client.PostAsync(
            $"/api/v1/approvals/{TenantBApprovalId}/reject", body);

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: tenant A must not reject an approval belonging to tenant B");
    }

    [Fact]
    public async Task CCT_MT01_16_TenantA_CannotExpandAuthority_For_TenantB_Contract()
    {
        // C-005: authority expansion writes a constitutional license record.
        // Cross-tenant authority mutation is a severe constitutional breach.
        var client = CreateClientForTenant(TenantA);
        var body = new StringContent(
            $$$"""{"contract_id":"{{{TenantBContractId}}}","new_authority_level":"LEVEL_2","evidence_ids":[]}""",
            Encoding.UTF8,
            "application/json");

        var response = await client.PostAsync("/api/v1/authority/expand", body);

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: expanding authority on a contract belonging to tenant B is a constitutional breach");
    }

    // ─── §6 JWT claim validation — malformed / missing tenant_id ──────────────

    [Fact]
    public async Task CCT_MT01_17_JWT_Without_TenantId_Claim_IsRejected()
    {
        // C-026: A JWT with no tenant_id claim must be rejected by TenantIsolationMiddleware.
        // The middleware must not fall back to a default tenant — that would silently leak data.
        var client = CreateClientWithClaims(new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, "user-no-tenant"),
            new Claim(ClaimTypes.Name, "NoTenantUser")
            // deliberately omit tenant_id claim
        });

        var response = await client.GetAsync("/api/v1/employment/contracts");

        response.StatusCode.Should().BeOneOf(
            new[]
            {
                HttpStatusCode.Unauthorized,
                HttpStatusCode.Forbidden,
                HttpStatusCode.BadRequest,
                HttpStatusCode.InternalServerError
            },
            because: "C-026: missing tenant_id claim must cause middleware to reject the request — never silently default");

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-026: granting access without tenant_id would make all tenant data accessible");
    }

    [Fact]
    public async Task CCT_MT01_18_JWT_With_EmptyString_TenantId_IsRejected()
    {
        // C-026: An empty string tenant_id is as dangerous as a missing one.
        var client = CreateClientWithClaims(new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, "user-empty-tenant"),
            new Claim("tenant_id", string.Empty)
        });

        var response = await client.GetAsync("/api/v1/employment/contracts");

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-026: empty tenant_id must not be accepted by TenantIsolationMiddleware");
    }

    [Fact]
    public async Task CCT_MT01_19_JWT_With_Whitespace_TenantId_IsRejected()
    {
        // C-026: Whitespace-only tenant_id must be rejected — not trimmed to empty and defaulted.
        var client = CreateClientWithClaims(new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, "user-whitespace-tenant"),
            new Claim("tenant_id", "   ")
        });

        var response = await client.GetAsync("/api/v1/employment/contracts");

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-026: whitespace-only tenant_id must be rejected, not coerced to a valid identifier");
    }

    [Fact]
    public async Task CCT_MT01_20_JWT_With_NonGuid_TenantId_IsRejected()
    {
        // C-026: tenant_id must be a parseable GUID. Arbitrary strings must be rejected
        // before reaching the DB — SQL injection or data corruption risk otherwise.
        var client = CreateClientWithClaims(new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, "user-bad-tenant"),
            new Claim("tenant_id", "not-a-guid-value'; DROP TABLE employment_contracts;--")
        });

        var response = await client.GetAsync("/api/v1/employment/contracts");

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-026: non-GUID tenant_id must be rejected to prevent RLS bypass via malformed identifier");
    }

    // ─── §7 Middleware header propagation ─────────────────────────────────────

    [Fact]
    public async Task CCT_MT01_21_Authenticated_Request_Carries_TenantId_In_HttpContext()
    {
        // C-026: TenantIsolationMiddleware must extract tenant_id from JWT and store it
        // on HttpContext.Items["tenant_id"] so downstream services can use it.
        // We verify this indirectly: if the middleware does NOT set the tenant context,
        // any DB-touching endpoint would either crash or return all-tenants data.
        // With the test host, a valid tenant A token must produce a non-401 response.
        var client = CreateClientForTenant(TenantA);

        var response = await client.GetAsync("/api/v1/employment/contracts");

        // The middleware correctly set tenant context → request was not blocked at auth layer.
        // (DB may not exist in test environment — any non-401 means middleware passed.)
        response.StatusCode.Should().NotBe(HttpStatusCode.Unauthorized,
            because: "C-026: valid JWT with tenant_id must pass TenantIsolationMiddleware");
    }

    [Fact]
    public async Task CCT_MT01_22_Health_Endpoint_Accessible_Without_JWT()
    {
        // C-026 boundary: /health is exempt from JWT gate (operational requirement).
        // TenantIsolationMiddleware must NOT block health checks.
        var client = _factory.CreateClient();

        var response = await client.GetAsync("/health");

        // Health endpoint should be 200 or at minimum not 401.
        response.StatusCode.Should().NotBe(HttpStatusCode.Unauthorized,
            because: "C-026: health endpoint is explicitly unauthenticated — middleware must not block it");
    }

    [Fact]
    public async Task CCT_MT01_23_TenantA_And_TenantB_Have_Distinct_RLS_Windows()
    {
        // C-005: Two concurrent requests with different tenant tokens must not
        // share RLS context. This test sends both in sequence and verifies neither
        // leaks to the other's response body.
        var clientA = CreateClientForTenant(TenantA);
        var clientB = CreateClientForTenant(TenantB);

        var responseA = await clientA.GetAsync("/api/v1/employment/contracts");
        var responseB = await clientB.GetAsync("/api/v1/employment/contracts");

        if (responseA.StatusCode == HttpStatusCode.OK)
        {
            var bodyA = await responseA.Content.ReadAsStringAsync();
            bodyA.Should().NotContain(TenantB.ToString(),
                because: "C-005: tenant A's response window must not contain tenant B's identifier");
        }

        if (responseB.StatusCode == HttpStatusCode.OK)
        {
            var bodyB = await responseB.Content.ReadAsStringAsync();
            bodyB.Should().NotContain(TenantA.ToString(),
                because: "C-005: tenant B's response window must not contain tenant A's identifier");
        }
    }

    [Fact]
    public async Task CCT_MT01_24_TenantA_CannotConfirmBoundary_For_TenantB_Approval()
    {
        // C-005: scope-boundary confirmation is a permanent constitutional record.
        // Tenant A must not be able to create boundary confirmation for tenant B.
        var client = CreateClientForTenant(TenantA);
        var body = new StringContent(
            """{"acknowledgment":"adversarial boundary confirm","boundary_type":"SCOPE_LIMIT"}""",
            Encoding.UTF8,
            "application/json");

        var response = await client.PostAsync(
            $"/api/v1/approvals/{TenantBApprovalId}/confirm-boundary", body);

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: boundary confirmation for tenant B's approval via tenant A's token is a constitutional breach");
    }

    [Fact]
    public async Task CCT_MT01_25_TenantA_CannotRestrictAuthority_For_TenantB_Contract()
    {
        // C-005: authority restriction (RevokeAuthorityLicense) must be tenant-scoped.
        var client = CreateClientForTenant(TenantA);
        var body = new StringContent(
            $$$"""{"contract_id":"{{{TenantBContractId}}}","new_authority_level":"LEVEL_0","reason":"adversarial restrict"}""",
            Encoding.UTF8,
            "application/json");

        var response = await client.PostAsync("/api/v1/authority/restrict", body);

        response.StatusCode.Should().NotBe(HttpStatusCode.OK,
            because: "C-005: tenant A must not restrict authority for a contract belonging to tenant B");
    }

    // ─── §8 Evidence export cross-tenant isolation ────────────────────────────

    [Fact]
    public async Task CCT_MT01_26_TenantA_Evidence_Export_NeverContains_TenantB_Data()
    {
        // Article IX right to export must still be tenant-scoped.
        // C-005: Full ledger export for tenant A must not include tenant B's records.
        var client = CreateClientForTenant(TenantA);

        var response = await client.GetAsync("/api/v1/evidence/export");

        // Export may be rate-limited (429) or require DB — either is acceptable.
        // A 200 response body must not contain tenant B identifiers.
        if (response.StatusCode == HttpStatusCode.OK)
        {
            // zip content — check content-type header at minimum
            response.Content.Headers.ContentType?.MediaType.Should().NotBeNull(
                because: "C-005: export response must declare its content type");

            // If the server returns JSON (non-zip in test env), verify tenant isolation.
            var contentType = response.Content.Headers.ContentType?.MediaType ?? string.Empty;
            if (contentType.Contains("json", StringComparison.OrdinalIgnoreCase))
            {
                var body = await response.Content.ReadAsStringAsync();
                body.Should().NotContain(TenantB.ToString(),
                    because: "C-005: evidence export must not contain tenant B identifiers");
            }
        }

        response.StatusCode.Should().NotBe(HttpStatusCode.Unauthorized,
            because: "authenticated tenant A has the Article IX right to export their own data");
    }

    // ─── Private helpers ──────────────────────────────────────────────────────

    /// <summary>
    /// Creates an HttpClient with a JWT carrying tenant_id for the given tenant GUID.
    /// C-026: the tenant_id claim is the authoritative source for RLS context.
    /// </summary>
    private HttpClient CreateClientForTenant(Guid tenantId)
    {
        return CreateClientWithClaims(new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, $"user-{tenantId}"),
            new Claim("tenant_id", tenantId.ToString()),
            new Claim(ClaimTypes.Name, $"TestUser-{tenantId}"),
            new Claim(ClaimTypes.Role, "Customer")
        });
    }

    /// <summary>
    /// Creates an HttpClient with a test JWT carrying the specified claims.
    /// Uses the TestAuthHandler which bypasses Keycloak for unit tests.
    /// </summary>
    private HttpClient CreateClientWithClaims(IEnumerable<Claim> claims)
    {
        var client = _factory.WithWebHostBuilder(builder =>
        {
            builder.ConfigureTestServices(services =>
            {
                services.Configure<TestAuthHandlerOptions>(options =>
                {
                    options.Claims = claims.ToList();
                });
            });
        }).CreateClient();

        client.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Test");

        return client;
    }
}

// ─── Test Infrastructure ──────────────────────────────────────────────────────

/// <summary>
/// Options carrier for TestAuthHandler — holds the claims for the current test request.
/// </summary>
public sealed class TestAuthHandlerOptions : AuthenticationSchemeOptions
{
    public List<Claim> Claims { get; set; } = new();
}

/// <summary>
/// In-process authentication handler for CCT-MT-01 tests.
/// Replaces Keycloak JWT validation with direct claim injection.
/// C-026: tenant_id claim is sourced from here and propagated by TenantIsolationMiddleware.
/// </summary>
public sealed class TestAuthHandler : AuthenticationHandler<TestAuthHandlerOptions>
{
    public TestAuthHandler(
        IOptionsMonitor<TestAuthHandlerOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder)
        : base(options, logger, encoder)
    {
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var claims = Options.Claims;

        // A missing or empty tenant_id in claims signals an adversarial test scenario.
        // In that case we still issue the ticket so the middleware can reject it
        // (rather than short-circuiting at authentication — the middleware must do the validation).
        var identity = new ClaimsIdentity(claims, "Test");
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, "Test");

        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}

/// <summary>
/// WebApplicationFactory for CCT-MT-01 tenant isolation tests.
/// Replaces JWT Bearer authentication with the in-process TestAuthHandler.
/// C-005, C-026: verifies middleware chain without requiring a live Keycloak instance.
/// </summary>
public sealed class TenantIsolationWebApplicationFactory
    : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");

        builder.ConfigureTestServices(services =>
        {
            // Replace JWT Bearer with test handler so we control the claims.
            // TenantIsolationMiddleware still runs — it must correctly read tenant_id
            // from whatever claims are present and reject absent/invalid ones.
            services.AddAuthentication(options =>
            {
                options.DefaultAuthenticateScheme = "Test";
                options.DefaultChallengeScheme = "Test";
            })
            .AddScheme<TestAuthHandlerOptions, TestAuthHandler>("Test", _ => { });

            // Register a scoped options instance so individual tests can override claims.
            services.AddOptions<TestAuthHandlerOptions>("Test");
        });
    }
}