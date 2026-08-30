// Implements: WC-079 AA-03, AA-12
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using FluentAssertions;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AgentAdmissionMigrationTests
{
    private static readonly string Migration = RepositoryPaths.Resolve("infrastructure/postgres/init/25-agent-admission.sql");

    [Fact]
    public void Migration_DefinesFrozenTables_WithForcedRlsAndTenantPolicy()
    {
        var sql = File.ReadAllText(Migration);
        var tables = new[]
        {
            "agent_admissions", "agent_admission_revisions", "agent_admission_validations",
            "agent_admission_findings", "agent_admission_assertions", "agent_admission_transitions",
            "agent_admission_idempotency", "agent_admission_outbox",
        };

        foreach (var table in tables)
        {
            sql.Should().Contain($"business.{table}");
            sql.Should().Contain($"'{table}'");
        }
        sql.Should().Contain("FORCE ROW LEVEL SECURITY");
        sql.Should().Contain("app.current_tenant_id");
        sql.Should().Contain("reject_agent_admission_lineage_mutation");
        sql.Should().Contain("FOREIGN KEY (tenant_id, admission_id, predecessor_revision_id)");
        sql.Should().Contain("UNIQUE (tenant_id, operation, idempotency_key)");
        sql.Should().NotContain("BYPASSRLS");
    }

    [Fact]
    public void Migration_ConstrainsDigestsStatesAndReadinessExpiry()
    {
        var sql = File.ReadAllText(Migration);

        sql.Should().Contain("^sha256:[0-9a-f]{64}$");
        sql.Should().Contain("REMEDIATION_REQUIRED");
        sql.Should().Contain("valid_until > observed_at");
        sql.Should().Contain("UNKNOWN");
        sql.Should().Contain("UNAVAILABLE");
    }
}