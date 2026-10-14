// Implements: WC-121 Component 01 migration and tenant isolation evidence
// constitutional_basis: C-005, C-023, C-026, C-059, C-063

using FluentAssertions;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class CustomerEngagementMigrationTests
{
    private static readonly string Migration = RepositoryPaths.Resolve(
        "infrastructure/postgres/init/54-wc121-customer-engagement-workspace.sql"
    );

    [Fact]
    public void MigrationAddsBoundedPreferencesAndRecoverableAdmissionCoordinator()
    {
        var sql = File.ReadAllText(Migration);

        sql.Should().Contain("workspace_layout_version");
        sql.Should().Contain("conversation_width_percent BETWEEN 35 AND 75");
        sql.Should().Contain("workspace_preference_version");
        sql.Should().Contain("business.customer_engagement_admission_operations");
        sql.Should().Contain("UNIQUE (tenant_id, participant_id, idempotency_key)");
        sql.Should().Contain("UNIQUE (tenant_id, participant_id, client_intent_id)");
        sql.Should().Contain("'RECONCILE_REQUIRED'");
        sql.Should().NotContain("FOREIGN KEY (tenant_id, relationship_id)");
    }

    [Fact]
    public void CoordinatorForcesFailClosedTenantIsolationAndGrantsOnlyRuntimeNeeds()
    {
        var sql = File.ReadAllText(Migration);

        sql.Should().Contain("ENABLE ROW LEVEL SECURITY");
        sql.Should().Contain("FORCE ROW LEVEL SECURITY");
        sql.Should().Contain("NULLIF(current_setting('app.current_tenant_id', true), '')::uuid");
        sql.Should().Contain("USING (");
        sql.Should().Contain("WITH CHECK (");
        sql.Should().Contain("GRANT SELECT, INSERT, UPDATE");
        sql.Should().NotContain("BYPASSRLS");
        sql.Should().NotContain("GRANT DELETE");
    }

    [Fact]
    public void MigrationIsAdditiveAndRollbackSafe()
    {
        var sql = File.ReadAllText(Migration);

        var normalized = sql.ToUpperInvariant();
        normalized.Should().NotContain("DROP TABLE");
        normalized.Should().NotContain("TRUNCATE");
        normalized.Should().NotContain("DELETE FROM");
        normalized.Should().NotContain("DROP COLUMN");
    }
}
