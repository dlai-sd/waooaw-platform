// Implements: WC-084 Customer Portal Solution Contract section 4.3
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using FluentAssertions;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class CustomerPortalRelationshipMigrationTests
{
    private static readonly string Migration = RepositoryPaths.Resolve(
        "infrastructure/postgres/init/27-customer-portal-relationship.sql");

    [Fact]
    public void MigrationBindsPreferencesToTenantRelationshipAndForcesRls()
    {
        var sql = File.ReadAllText(Migration);

        sql.Should().Contain("FOREIGN KEY (tenant_id, relationship_id)");
        sql.Should().Contain("UNIQUE (tenant_id, relationship_id)");
        sql.Should().Contain("ENABLE ROW LEVEL SECURITY");
        sql.Should().Contain("FORCE ROW LEVEL SECURITY");
        sql.Should().Contain("app.current_tenant_id");
        sql.Should().NotContain("BYPASSRLS");
    }

    [Fact]
    public void MigrationConstrainsOnboardPresentationEnums()
    {
        var sql = File.ReadAllText(Migration);

        sql.Should().Contain("'CONSTITUTIONAL', 'COMPACT'");
        sql.Should().Contain("'RELATIVE', 'ABSOLUTE'");
        sql.Should().Contain("'SYSTEM', 'LIGHT', 'DARK'");
    }
}