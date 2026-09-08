// Implements: WC-084 Customer Portal Solution Contract section 4.1
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using FluentAssertions;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class CustomerPortalIdentityMigrationTests
{
    private static readonly string Migration = RepositoryPaths.Resolve(
        "infrastructure/postgres/init/26-customer-portal-identity.sql");

    [Fact]
    public void Migration_DefinesTenantBoundPreferencesWithForcedRls()
    {
        var sql = File.ReadAllText(Migration);

        sql.Should().Contain("identity.customer_portal_preferences");
        sql.Should().Contain("UNIQUE (actor_subject, tenant_id)");
        sql.Should().Contain("ENABLE ROW LEVEL SECURITY");
        sql.Should().Contain("FORCE ROW LEVEL SECURITY");
        sql.Should().Contain("app.current_tenant_id");
        sql.Should().NotContain("BYPASSRLS");
    }

    [Fact]
    public void Migration_ConstrainsPortalEnumsAndUsesJsonPreferences()
    {
        var sql = File.ReadAllText(Migration);

        sql.Should().Contain("'SYSTEM', 'LIGHT', 'DARK'");
        sql.Should().Contain("'RELATIVE', 'ABSOLUTE'");
        sql.Should().Contain("JSONB");
    }
}