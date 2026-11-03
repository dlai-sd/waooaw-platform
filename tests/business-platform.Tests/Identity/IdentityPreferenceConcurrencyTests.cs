// Implements: work-contracts/WC-133-whatsapp-first-registration-and-web-registration-repair.md R006
// constitutional_basis: C-026, C-059

using System.Reflection;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class IdentityPreferenceConcurrencyTests
{
    [Fact]
    public async Task ConcurrentInitializationPreservesOneRowAndExistingPreferencesUnderForcedRls()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("preferences")
            .WithUsername("owner")
            .WithPassword("synthetic-owner-password")
            .Build();
        await postgres.StartAsync();
        var options = new DbContextOptionsBuilder<IdentityDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var db = new IdentityDbContext(options))
            await db.Database.EnsureCreatedAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        await using (
            var setup = new NpgsqlCommand(
                """
                CREATE ROLE preference_app LOGIN PASSWORD 'synthetic-app-password' NOBYPASSRLS;
                GRANT USAGE ON SCHEMA identity TO preference_app;
                GRANT SELECT, INSERT, UPDATE ON identity.customer_portal_preferences TO preference_app;
                ALTER TABLE identity.customer_portal_preferences ENABLE ROW LEVEL SECURITY;
                ALTER TABLE identity.customer_portal_preferences FORCE ROW LEVEL SECURITY;
                CREATE POLICY tenant_scope ON identity.customer_portal_preferences
                  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN locale SET DEFAULT 'en';
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN theme SET DEFAULT 'SYSTEM';
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN timestamp_visibility SET DEFAULT 'RELATIVE';
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN approval_request_channels SET DEFAULT '["IN_APP"]';
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN maturity_report_channels SET DEFAULT '["IN_APP"]';
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN monthly_narrative_channels SET DEFAULT '["IN_APP"]';
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN self_governance_alert_channels SET DEFAULT '["IN_APP"]';
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN navigation_visibility SET DEFAULT 'EXPANDED';
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN progress_visibility SET DEFAULT 'EXPANDED';
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN conversation_width_percent SET DEFAULT 50;
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN reduce_motion SET DEFAULT false;
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN workspace_layout_version SET DEFAULT 0;
                ALTER TABLE identity.customer_portal_preferences ALTER COLUMN updated_at SET DEFAULT now();
                """,
                owner
            )
        )
            await setup.ExecuteNonQueryAsync();
        var appConnection = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "preference_app",
            Password = "synthetic-app-password",
        }.ConnectionString;
        var appOptions = new DbContextOptionsBuilder<IdentityDbContext>()
            .UseNpgsql(appConnection)
            .Options;
        var tenant = Guid.NewGuid();
        var method = typeof(IdentityService).GetMethod(
            "GetOrCreatePortalPreferenceAsync",
            BindingFlags.NonPublic | BindingFlags.Static
        )!;

        async Task<Guid> Initialize(bool update = false)
        {
            await using var db = new IdentityDbContext(appOptions);
            await using var transaction = await db.Database.BeginTransactionAsync();
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT set_config('app.current_tenant_id', {tenant.ToString("D")}, true)"
            );
            var preference = await (Task<CustomerPortalPreferenceRecord>)
                method.Invoke(null, [db, "synthetic-subject", tenant, CancellationToken.None])!;
            if (update)
            {
                preference.Theme = "DARK";
                preference.WorkspaceLayoutVersion = 7;
            }
            await db.SaveChangesAsync();
            await transaction.CommitAsync();
            return preference.PreferenceId;
        }

        var results = await Task.WhenAll(Enumerable.Range(0, 12).Select(_ => Initialize()));
        Assert.Single(results.Distinct());
        await Task.WhenAll(Initialize(true), Initialize(), Initialize());
        await using var verify = new IdentityDbContext(options);
        var saved = Assert.Single(await verify.CustomerPortalPreferences.ToListAsync());
        Assert.Equal("DARK", saved.Theme);
        Assert.Equal(7, saved.WorkspaceLayoutVersion);

        await using var denied = new IdentityDbContext(appOptions);
        await using var scope = await denied.Database.BeginTransactionAsync();
        await denied.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT set_config('app.current_tenant_id', {Guid.NewGuid().ToString("D")}, true)"
        );
        Assert.Empty(await denied.CustomerPortalPreferences.ToListAsync());
    }
}
