// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R019
// Constitutional basis: C-005, C-026, C-059, C-063

using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Npgsql;
using System.Security.Claims;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Infrastructure;

public sealed class TenantDbConnectionInterceptorPostgresTests : IAsyncLifetime
{
    private const string AppPassword = "synthetic-app-password";
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("postgres:16-alpine")
        .WithDatabase("tenant_interceptor")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            $"""
            CREATE ROLE tenant_app LOGIN PASSWORD '{AppPassword}' NOSUPERUSER;
            CREATE TABLE tenant_probe (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL,
                value text NOT NULL
            );
            ALTER TABLE tenant_probe ENABLE ROW LEVEL SECURITY;
            ALTER TABLE tenant_probe FORCE ROW LEVEL SECURITY;
            CREATE POLICY tenant_probe_isolation ON tenant_probe
                USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
                WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
            GRANT SELECT, UPDATE ON tenant_probe TO tenant_app;
            """,
            connection
        );
        await command.ExecuteNonQueryAsync();
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    [Fact]
    public async Task TenantScopedRead_OwnsTransactionWithoutWarningOrSessionLeak()
    {
        var tenantA = Guid.NewGuid();
        var tenantB = Guid.NewGuid();
        await SeedAsync(tenantA, tenantB);
        var accessor = new HttpContextAccessor();
        var interceptor = new TenantDbConnectionInterceptor(
            accessor,
            NullLogger<TenantDbConnectionInterceptor>.Instance
        );
        var appConnection = new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
        {
            Username = "tenant_app",
            Password = AppPassword,
        }.ConnectionString;
        var options = new DbContextOptionsBuilder<TenantProbeDbContext>()
            .UseNpgsql(appConnection)
            .AddInterceptors(interceptor)
            .Options;
        await using var db = new TenantProbeDbContext(options);
        var warnings = new List<string>();
        ((NpgsqlConnection)db.Database.GetDbConnection()).Notice += (_, notice) =>
            warnings.Add(notice.Notice.MessageText);
        var observedTenants = new Dictionary<Guid, Guid[]>();
        var blockedMutations = new Dictionary<Guid, int>();
        var explicitTransactionTenant = string.Empty;
        var middleware = new TenantIsolationMiddleware(
            async requestContext =>
            {
                var requestTenant = Guid.Parse(
                    (string)requestContext.Items[TenantIsolationMiddleware.TenantIdItemKey]!
                );
                observedTenants[requestTenant] = await db.TenantProbes
                    .AsNoTracking()
                    .OrderBy(row => row.Value)
                    .Select(row => row.TenantId)
                    .ToArrayAsync();
                var otherTenant = requestTenant == tenantA ? tenantB : tenantA;
                blockedMutations[requestTenant] = await db.Database.ExecuteSqlRawAsync(
                    "UPDATE tenant_probe SET value = 'forbidden' WHERE tenant_id = {0}",
                    otherTenant
                );
                await using var transaction = await db.Database.BeginTransactionAsync();
                explicitTransactionTenant = await db.Database
                    .SqlQueryRaw<string>(
                        "SELECT current_setting('app.current_tenant_id', true) AS \"Value\""
                    )
                    .SingleAsync();
                await transaction.CommitAsync();
            },
            NullLogger<TenantIsolationMiddleware>.Instance
        );

        await InvokeAsTenantAsync(middleware, accessor, tenantA);
        Assert.Equal([tenantA], observedTenants[tenantA]);
        Assert.Equal(0, blockedMutations[tenantA]);
        Assert.Equal(tenantA.ToString("D"), explicitTransactionTenant);

        await InvokeAsTenantAsync(middleware, accessor, tenantB);
        Assert.Equal([tenantB], observedTenants[tenantB]);
        Assert.Equal(0, blockedMutations[tenantB]);
        Assert.Equal(tenantB.ToString("D"), explicitTransactionTenant);
        Assert.DoesNotContain(
            warnings,
            warning => warning.Contains("SET LOCAL can only be used", StringComparison.Ordinal)
        );

        accessor.HttpContext = new DefaultHttpContext();
        accessor.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantB.ToString("D");
        using (var cancellation = new CancellationTokenSource(TimeSpan.FromMilliseconds(100)))
        {
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
                db.Database.ExecuteSqlRawAsync("SELECT pg_sleep(10)", cancellation.Token)
            );
        }
        Assert.Equal(1, await db.TenantProbes.AsNoTracking().CountAsync());

        accessor.HttpContext = null;
        await using var connection = new NpgsqlConnection(appConnection);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            "SELECT current_setting('app.current_tenant_id', true)",
            connection
        );
        var leakedTenant = await command.ExecuteScalarAsync();
        Assert.True(leakedTenant is null or DBNull || string.IsNullOrEmpty(leakedTenant.ToString()));
    }

    private async Task SeedAsync(Guid tenantA, Guid tenantB)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            "INSERT INTO tenant_probe (id, tenant_id, value) VALUES (gen_random_uuid(), @tenant_a, 'A'), (gen_random_uuid(), @tenant_b, 'B')",
            connection
        );
        command.Parameters.AddWithValue("tenant_a", tenantA);
        command.Parameters.AddWithValue("tenant_b", tenantB);
        await command.ExecuteNonQueryAsync();
    }

    private static async Task InvokeAsTenantAsync(
        TenantIsolationMiddleware middleware,
        HttpContextAccessor accessor,
        Guid tenantId
    )
    {
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(
                new ClaimsIdentity([new Claim("tenant_id", tenantId.ToString("D"))], "Test")
            ),
        };
        context.Request.Path = "/api/v1/employment/relationships";
        accessor.HttpContext = context;
        await middleware.InvokeAsync(context);
        Assert.Equal(StatusCodes.Status200OK, context.Response.StatusCode);
    }

    private sealed class TenantProbe
    {
        public Guid Id { get; set; }
        public Guid TenantId { get; set; }
        public string Value { get; set; } = string.Empty;
    }

    private sealed class TenantProbeDbContext(DbContextOptions<TenantProbeDbContext> options)
        : DbContext(options)
    {
        public DbSet<TenantProbe> TenantProbes => Set<TenantProbe>();

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.Entity<TenantProbe>(entity =>
            {
                entity.ToTable("tenant_probe");
                entity.HasKey(row => row.Id);
                entity.Property(row => row.Id).HasColumnName("id");
                entity.Property(row => row.TenantId).HasColumnName("tenant_id");
                entity.Property(row => row.Value).HasColumnName("value");
            });
        }
    }
}