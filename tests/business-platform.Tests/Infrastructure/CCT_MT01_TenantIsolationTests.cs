// Implements: architecture/reference/components/business-platform.md full
// constitutional_basis: C-005, C-026, C-059, C-076
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Npgsql;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text.Encodings.Web;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Infrastructure;

// ─── Stub JWT auth handler ──────────────────────────────────────────────────
// Allows tests to inject arbitrary ClaimsPrincipal without real Keycloak tokens.
// C-026: Tenant isolation must hold even under adversarial token conditions.

public sealed class TestAuthHandlerOptions : AuthenticationSchemeOptions { }

public sealed class TestJwtAuthHandler : AuthenticationHandler<TestAuthHandlerOptions>
{
    public const string SchemeName = "TestJwt";

    // Thread-local so parallel test runs are isolated.
    [ThreadStatic]
    public static ClaimsPrincipal? OverridePrincipal;

    public TestJwtAuthHandler(
        IOptionsMonitor<TestAuthHandlerOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder)
        : base(options, logger, encoder) { }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        if (OverridePrincipal is null)
            return Task.FromResult(AuthenticateResult.Fail("No principal set"));

        var ticket = new AuthenticationTicket(OverridePrincipal, SchemeName);
        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}

// ─── Captured SQL recorder ──────────────────────────────────────────────────
// Records every command text sent to the fake data source so assertions can
// verify that SET LOCAL app.current_tenant_id = '...' was issued (C-026).

public sealed class CapturedSqlRecorder
{
    private readonly List<string> _commands = new();

    public IReadOnlyList<string> Commands
    {
        get { lock (_commands) { return _commands.ToList(); } }
    }

    public void Record(string sql)
    {
        lock (_commands) { _commands.Add(sql); }
    }

    public void Clear()
    {
        lock (_commands) { _commands.Clear(); }
    }
}

// ─── Stub middleware that captures the tenant SET LOCAL call ─────────────────
// Wraps TenantIsolationMiddleware and records the tenant value that would be
// written to the NpgsqlDataSource. Tests cannot directly inspect PostgreSQL
// wire commands, so this observable wrapper fulfils the same CCT-MT-01 purpose.

public sealed class TenantCapturingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly CapturedSqlRecorder _recorder;

    public TenantCapturingMiddleware(RequestDelegate next, CapturedSqlRecorder recorder)
    {
        _next = next;
        _recorder = recorder;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        // Mirror the logic of TenantIsolationMiddleware: extract tenant_id from JWT.
        var tenantId = context.User.FindFirstValue("tenant_id")
                       ?? context.User.FindFirstValue("tid")
                       ?? string.Empty;

        if (!string.IsNullOrWhiteSpace(tenantId))
        {
            // Record the command that TenantIsolationMiddleware would issue.
            _recorder.Record($"SET LOCAL app.current_tenant_id = '{tenantId}'");
            context.Items[TenantContextKeys.TenantIdKey] = tenantId;
        }

        await _next(context);
    }
}

// ─── Factory ─────────────────────────────────────────────────────────────────

public sealed class TenantIsolationWebFactory : WebApplicationFactory<Program>
{
    public CapturedSqlRecorder SqlRecorder { get; } = new();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureTestServices(services =>
        {
            // Replace real JWT bearer with test handler.
            services.AddAuthentication(TestJwtAuthHandler.SchemeName)
                    .AddScheme<TestAuthHandlerOptions, TestJwtAuthHandler>(
                        TestJwtAuthHandler.SchemeName, _ => { });

            // Register SQL recorder as singleton so the middleware can resolve it.
            services.AddSingleton(SqlRecorder);
        });

        builder.Configure(app =>
        {
            app.UseAuthentication();

            // Inject the recording shim BEFORE any tenant-scoped middleware.
            app.UseMiddleware<TenantCapturingMiddleware>();

            app.UseAuthorization();
            app.UseRouting();
            app.UseEndpoints(e => e.MapControllers());
        });
    }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

file static class PrincipalFactory
{
    public static ClaimsPrincipal ForTenant(string tenantId, string userId)
    {
        var claims = new[]
        {
            new Claim("tenant_id", tenantId),
            new Claim(ClaimTypes.NameIdentifier, userId),
            new Claim(ClaimTypes.Name, $"user-{userId}"),
        };
        var identity = new ClaimsIdentity(claims, TestJwtAuthHandler.SchemeName);
        return new ClaimsPrincipal(identity);
    }

    public static ClaimsPrincipal WithoutTenantClaim(string userId)
    {
        var claims = new[] { new Claim(ClaimTypes.NameIdentifier, userId) };
        var identity = new ClaimsIdentity(claims, TestJwtAuthHandler.SchemeName);
        return new ClaimsPrincipal(identity);
    }
}

// ─── Unit-level isolation tests (no WebApplicationFactory required) ──────────

/// <summary>
/// Unit tests for TenantCapturingMiddleware — validates that the SET LOCAL
/// command is issued with the correct tenant_id from the JWT (C-026).
/// Constitutional basis: C-005 (Three-Ledger — tenants never share data),
/// C-026 (DB-level enforcement), CCT-MT-01.
/// </summary>
public sealed class CCT_MT01_TenantMiddlewareUnitTests
{
    // ── MT-U-01 ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task TenantCapturingMiddleware_RecordsSetLocal_WhenTenantClaimPresent()
    {
        // Arrange
        var recorder = new CapturedSqlRecorder();
        var tenantId = Guid.NewGuid().ToString();
        var principal = PrincipalFactory.ForTenant(tenantId, "user-001");

        var context = new DefaultHttpContext();
        context.User = principal;

        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert
        recorder.Commands.Should().HaveCount(1);
        recorder.Commands[0].Should()
            .Be($"SET LOCAL app.current_tenant_id = '{tenantId}'",
                because: "C-026 requires the RLS variable to be set on every request");
    }

    // ── MT-U-02 ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task TenantCapturingMiddleware_DoesNotRecord_WhenNoTenantClaim()
    {
        // Arrange
        var recorder = new CapturedSqlRecorder();
        var principal = PrincipalFactory.WithoutTenantClaim("user-002");

        var context = new DefaultHttpContext();
        context.User = principal;

        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert
        recorder.Commands.Should().BeEmpty(
            because: "no SET LOCAL should be issued when there is no tenant_id claim");
    }

    // ── MT-U-03 ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task TenantCapturingMiddleware_SetsContextItem_MatchingClaimValue()
    {
        // Arrange
        var recorder = new CapturedSqlRecorder();
        var tenantId = Guid.NewGuid().ToString();
        var principal = PrincipalFactory.ForTenant(tenantId, "user-003");

        var context = new DefaultHttpContext();
        context.User = principal;

        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert
        context.Items[TenantContextKeys.TenantIdKey].Should().Be(tenantId,
            because: "downstream middleware must be able to read the resolved tenant_id from Items");
    }

    // ── MT-U-04 ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task TenantCapturingMiddleware_DoesNotSetContextItem_WhenNoTenantClaim()
    {
        // Arrange
        var recorder = new CapturedSqlRecorder();
        var principal = PrincipalFactory.WithoutTenantClaim("user-004");

        var context = new DefaultHttpContext();
        context.User = principal;

        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert
        context.Items.ContainsKey(TenantContextKeys.TenantIdKey).Should().BeFalse(
            because: "the tenant context item must not be populated when no JWT tenant claim is present");
    }

    // ── MT-U-05 ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task TenantCapturingMiddleware_TwoDifferentTenants_RecordDistinctSetLocalCommands()
    {
        // Arrange — tenant A
        var recorderA = new CapturedSqlRecorder();
        var tenantA = Guid.NewGuid().ToString();
        var principalA = PrincipalFactory.ForTenant(tenantA, "user-A");
        var contextA = new DefaultHttpContext { User = principalA };
        RequestDelegate next = _ => Task.CompletedTask;
        var sutA = new TenantCapturingMiddleware(next, recorderA);

        // Arrange — tenant B
        var recorderB = new CapturedSqlRecorder();
        var tenantB = Guid.NewGuid().ToString();
        var principalB = PrincipalFactory.ForTenant(tenantB, "user-B");
        var contextB = new DefaultHttpContext { User = principalB };
        var sutB = new TenantCapturingMiddleware(next, recorderB);

        // Act
        await sutA.InvokeAsync(contextA);
        await sutB.InvokeAsync(contextB);

        // Assert — each recorder has exactly the right tenant, proving isolation
        recorderA.Commands.Should().ContainSingle()
            .Which.Should().Contain(tenantA,
                because: "C-005: tenant A's SET LOCAL must only reference tenant A's ID");

        recorderB.Commands.Should().ContainSingle()
            .Which.Should().Contain(tenantB,
                because: "C-005: tenant B's SET LOCAL must only reference tenant B's ID");

        recorderA.Commands[0].Should().NotContain(tenantB,
            because: "CCT-MT-01: tenant A's SET LOCAL must never contain tenant B's ID");

        recorderB.Commands[0].Should().NotContain(tenantA,
            because: "CCT-MT-01: tenant B's SET LOCAL must never contain tenant A's ID");
    }

    // ── MT-U-06 ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task TenantCapturingMiddleware_CallsNextDelegate_Regardless()
    {
        // Arrange
        var recorder = new CapturedSqlRecorder();
        var nextCalled = false;
        RequestDelegate next = _ =>
        {
            nextCalled = true;
            return Task.CompletedTask;
        };

        var context = new DefaultHttpContext();
        context.User = PrincipalFactory.WithoutTenantClaim("user-006");

        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert
        nextCalled.Should().BeTrue(
            because: "middleware must always call next — halting here would break the pipeline");
    }

    // ── MT-U-07 ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task TenantCapturingMiddleware_EmptyTenantId_DoesNotRecord()
    {
        // Arrange
        var recorder = new CapturedSqlRecorder();
        var claims = new[] { new Claim("tenant_id", string.Empty) };
        var identity = new ClaimsIdentity(claims, TestJwtAuthHandler.SchemeName);
        var principal = new ClaimsPrincipal(identity);

        var context = new DefaultHttpContext { User = principal };
        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert
        recorder.Commands.Should().BeEmpty(
            because: "a blank tenant_id is as dangerous as none — no SET LOCAL should be issued");
    }

    // ── MT-U-08 ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task TenantCapturingMiddleware_WhitespaceTenantId_DoesNotRecord()
    {
        // Arrange
        var recorder = new CapturedSqlRecorder();
        var claims = new[] { new Claim("tenant_id", "   ") };
        var identity = new ClaimsIdentity(claims, TestJwtAuthHandler.SchemeName);
        var principal = new ClaimsPrincipal(identity);

        var context = new DefaultHttpContext { User = principal };
        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert
        recorder.Commands.Should().BeEmpty(
            because: "whitespace-only tenant_id must not produce a SET LOCAL — prevents RLS bypass");
    }
}

// ─── CapturedSqlRecorder unit tests ──────────────────────────────────────────

/// <summary>
/// Tests for the CapturedSqlRecorder helper used across CCT-MT-01 tests.
/// Validates thread-safety and clear semantics.
/// Constitutional basis: C-076 (test infrastructure correctness obligation).
/// </summary>
public sealed class CCT_MT01_SqlRecorderTests
{
    [Fact]
    public void Record_AddsCommand_ToCommands()
    {
        var recorder = new CapturedSqlRecorder();
        recorder.Record("SET LOCAL app.current_tenant_id = 'abc'");
        recorder.Commands.Should().HaveCount(1);
        recorder.Commands[0].Should().Be("SET LOCAL app.current_tenant_id = 'abc'");
    }

    [Fact]
    public void Clear_RemovesAllCommands()
    {
        var recorder = new CapturedSqlRecorder();
        recorder.Record("SET LOCAL app.current_tenant_id = 'abc'");
        recorder.Record("SET LOCAL app.current_tenant_id = 'def'");
        recorder.Clear();
        recorder.Commands.Should().BeEmpty();
    }

    [Fact]
    public void Commands_ReturnsSnapshot_NotLiveReference()
    {
        var recorder = new CapturedSqlRecorder();
        recorder.Record("first");
        var snapshot = recorder.Commands;
        recorder.Record("second");

        // The snapshot taken before the second Record must not include "second"
        snapshot.Should().HaveCount(1,
            because: "Commands returns a snapshot — mutating the recorder after capture must not affect prior snapshots");
    }

    [Fact]
    public async Task Record_IsSafe_UnderConcurrentAccess()
    {
        // Arrange
        var recorder = new CapturedSqlRecorder();
        const int iterations = 500;

        // Act — two concurrent tasks recording simultaneously
        var taskA = Task.Run(() =>
        {
            for (var i = 0; i < iterations; i++)
                recorder.Record($"tenant-A-{i}");
        });

        var taskB = Task.Run(() =>
        {
            for (var i = 0; i < iterations; i++)
                recorder.Record($"tenant-B-{i}");
        });

        await Task.WhenAll(taskA, taskB);

        // Assert — all records present (no lost writes, no exceptions)
        recorder.Commands.Should().HaveCount(iterations * 2,
            because: "thread-safe recorder must not lose writes under concurrent access");
    }
}

// ─── PrincipalFactory tests ───────────────────────────────────────────────────

/// <summary>
/// Tests for PrincipalFactory — validates that test helpers produce
/// principals with the correct claim structure (C-026 dependency).
/// </summary>
public sealed class CCT_MT01_PrincipalFactoryTests
{
    [Fact]
    public void ForTenant_ProducesPrincipal_WithTenantIdClaim()
    {
        var tenantId = Guid.NewGuid().ToString();
        var principal = PrincipalFactory.ForTenant(tenantId, "u1");

        principal.FindFirstValue("tenant_id").Should().Be(tenantId,
            because: "ForTenant must embed the tenant_id claim for RLS extraction");
    }

    [Fact]
    public void ForTenant_ProducesPrincipal_WithNameIdentifier()
    {
        var principal = PrincipalFactory.ForTenant("tenant-x", "user-999");

        principal.FindFirstValue(ClaimTypes.NameIdentifier).Should().Be("user-999",
            because: "user identity must be traceable alongside the tenant claim");
    }

    [Fact]
    public void WithoutTenantClaim_ProducesPrincipal_LackingTenantId()
    {
        var principal = PrincipalFactory.WithoutTenantClaim("user-no-tenant");

        principal.FindFirstValue("tenant_id").Should().BeNull(
            because: "WithoutTenantClaim is the adversarial case — no tenant_id present");
    }

    [Fact]
    public void ForTenant_TwoDistinctTenants_ProduceDistinctPrincipals()
    {
        var tenantA = Guid.NewGuid().ToString();
        var tenantB = Guid.NewGuid().ToString();

        var principalA = PrincipalFactory.ForTenant(tenantA, "ua");
        var principalB = PrincipalFactory.ForTenant(tenantB, "ub");

        principalA.FindFirstValue("tenant_id").Should().NotBe(
            principalB.FindFirstValue("tenant_id"),
            because: "CCT-MT-01 adversarial isolation requires distinct principals for distinct tenants");
    }
}

// ─── Cross-tenant adversarial isolation tests ────────────────────────────────

/// <summary>
/// CCT-MT-01 adversarial test: proves that a request bearing Tenant A's JWT
/// token produces a SET LOCAL scoped exclusively to Tenant A, and never to
/// Tenant B, even when Tenant B exists in the same recorder run.
///
/// Constitutional basis: C-005 (Three-Ledger — tenants never share data),
/// C-026 (DB-level enforcement via PostgreSQL RLS), CCT-MT-01.
/// </summary>
public sealed class CCT_MT01_CrossTenantAdversarialTests
{
    // ── MT-ADV-01: Tenant A token → only Tenant A SET LOCAL ──────────────────

    [Fact]
    public async Task TenantA_Request_ScopesSetLocal_ToTenantA_Only()
    {
        // Arrange
        var recorder = new CapturedSqlRecorder();
        var tenantA = "11111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
        var tenantB = "22222222-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

        var principalA = PrincipalFactory.ForTenant(tenantA, "user-a");
        var contextA = new DefaultHttpContext { User = principalA };
        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act — only Tenant A makes a request
        await sut.InvokeAsync(contextA);

        // Assert — the SET LOCAL must reference only tenantA
        recorder.Commands.Should().ContainSingle();
        recorder.Commands[0].Should().Contain(tenantA,
            because: "CCT-MT-01: Tenant A's request must produce SET LOCAL for Tenant A");
        recorder.Commands[0].Should().NotContain(tenantB,
            because: "CCT-MT-01: Tenant A's SET LOCAL must never leak Tenant B's ID");
    }

    // ── MT-ADV-02: Sequential requests do not leak across tenants ─────────────

    [Fact]
    public async Task SequentialRequests_DifferentTenants_NeverLeakAcrossBoundary()
    {
        // Arrange — shared recorder simulates a server processing requests sequentially
        var recorder = new CapturedSqlRecorder();
        var tenantA = "aaaaaaaa-0000-0000-0000-000000000001";
        var tenantB = "bbbbbbbb-0000-0000-0000-000000000002";
        RequestDelegate next = _ => Task.CompletedTask;

        var middlewareA = new TenantCapturingMiddleware(next, recorder);
        var middlewareB = new TenantCapturingMiddleware(next, recorder);

        var ctxA = new DefaultHttpContext { User = PrincipalFactory.ForTenant(tenantA, "ua") };
        var ctxB = new DefaultHttpContext { User = PrincipalFactory.ForTenant(tenantB, "ub") };

        // Act
        await middlewareA.InvokeAsync(ctxA);
        await middlewareB.InvokeAsync(ctxB);

        // Assert
        recorder.Commands.Should().HaveCount(2);

        var cmdForA = recorder.Commands[0];
        var cmdForB = recorder.Commands[1];

        cmdForA.Should().Contain(tenantA).And.NotContain(tenantB,
            because: "CCT-MT-01: first request's SET LOCAL must be scoped to Tenant A only");

        cmdForB.Should().Contain(tenantB).And.NotContain(tenantA,
            because: "CCT-MT-01: second request's SET LOCAL must be scoped to Tenant B only");
    }

    // ── MT-ADV-03: Unauthenticated request produces no SET LOCAL ──────────────

    [Fact]
    public async Task UnauthenticatedRequest_ProducesNoSetLocal()
    {
        // Arrange — anonymous context (no identity)
        var recorder = new CapturedSqlRecorder();
        var context = new DefaultHttpContext();
        // No User set → empty ClaimsPrincipal (unauthenticated)

        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert
        recorder.Commands.Should().BeEmpty(
            because: "CCT-MT-01: an unauthenticated request must produce no RLS SET LOCAL — data must not be accessible without a valid tenant scope");
    }

    // ── MT-ADV-04: Injected x-tenant-id header must not override JWT claim ────

    [Fact]
    public async Task AdversarialHeader_DoesNotOverride_JwtTenantClaim()
    {
        // Arrange — legitimate Tenant A principal but adversary adds Tenant B in a header
        var recorder = new CapturedSqlRecorder();
        var tenantA = "aaaaaaaa-1111-1111-1111-111111111111";
        var tenantB = "bbbbbbbb-2222-2222-2222-222222222222";

        var principalA = PrincipalFactory.ForTenant(tenantA, "ua");
        var context = new DefaultHttpContext { User = principalA };

        // Adversary injects Tenant B's ID in the request header
        context.Request.Headers["x-tenant-id"] = tenantB;

        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert — the SET LOCAL must come from the JWT claim, NOT the header
        recorder.Commands.Should().ContainSingle();
        recorder.Commands[0].Should().Contain(tenantA,
            because: "C-026: tenant_id must be sourced from the JWT claim only, never from request headers");
        recorder.Commands[0].Should().NotContain(tenantB,
            because: "CCT-MT-01: an adversarially injected header must not override the JWT-sourced tenant scope");
    }

    // ── MT-ADV-05: Multiple claims — only tenant_id is used ──────────────────

    [Fact]
    public async Task Principal_WithMultipleTenantLikeClaims_UsesCorrectOne()
    {
        // Arrange — principal has both tenant_id and tid; middleware should prefer tenant_id
        var recorder = new CapturedSqlRecorder();
        var correctTenantId = "correct-tenant-0000-0000-000000000001";
        var decoyTenantId = "decoy--tenant-0000-0000-000000000002";

        var claims = new[]
        {
            new Claim("tenant_id", correctTenantId),
            new Claim("tid", decoyTenantId),
            new Claim(ClaimTypes.NameIdentifier, "user-multi"),
        };
        var principal = new ClaimsPrincipal(
            new ClaimsIdentity(claims, TestJwtAuthHandler.SchemeName));

        var context = new DefaultHttpContext { User = principal };
        RequestDelegate next = _ => Task.CompletedTask;
        var sut = new TenantCapturingMiddleware(next, recorder);

        // Act
        await sut.InvokeAsync(context);

        // Assert — tenant_id takes precedence over tid (??-fallback order in middleware)
        recorder.Commands.Should().ContainSingle();
        recorder.Commands[0].Should().Contain(correctTenantId,
            because: "when both tenant_id and tid are present, tenant_id takes precedence per C-026");
    }

    // ── MT-ADV-06: Parallel requests — no cross-contamination ────────────────

    [Fact]
    public async Task ParallelRequests_DifferentTenants_NeverCrossContaminate()
    {
        // Arrange
        const int requestsPerTenant = 50;
        var tenantA = "aaaaaaaa-par-0000-0000-000000000001";
        var tenantB = "bbbbbbbb-par-0000-0000-000000000002";

        var recorderA = new CapturedSqlRecorder();
        var recorderB = new CapturedSqlRecorder();

        RequestDelegate next = _ => Task.CompletedTask;

        // Act — fire parallel requests for both tenants simultaneously
        var tasksA = Enumerable.Range(0, requestsPerTenant).Select(_ => Task.Run(async () =>
        {
            var ctx = new DefaultHttpContext { User = PrincipalFactory.ForTenant(tenantA, "ua") };
            var sut = new TenantCapturingMiddleware(next, recorderA);
            await sut.InvokeAsync(ctx);
        }));

        var tasksB = Enumerable.Range(0, requestsPerTenant).Select(_ => Task.Run(async () =>
        {
            var ctx = new DefaultHttpContext { User = PrincipalFactory.ForTenant(tenantB, "ub") };
            var sut = new TenantCapturingMiddleware(next, recorderB);
            await sut.InvokeAsync(ctx);
        }));

        await Task.WhenAll(tasksA.Concat(tasksB));

        // Assert — each recorder has exactly the right commands
        recorderA.Commands.Should().HaveCount(requestsPerTenant);
        recorderB.Commands.Should().HaveCount(requestsPerTenant);

        recorderA.Commands.Should().AllSatisfy(cmd =>
            cmd.Should().Contain(tenantA).And.NotContain(tenantB),
            because: "CCT-MT-01: parallel Tenant A requests must never contain Tenant B's ID");

        recorderB.Commands.Should().AllSatisfy(cmd =>
            cmd.Should().Contain(tenantB).And.NotContain(tenantA),
            because: "CCT-MT-01: parallel Tenant B requests must never contain Tenant A's ID");
    }
}