// Implements: architecture/reference/components/identity-boundary.md §12.1 Environment and deployment qualification
// Constitutional basis: C-023 (Evidence First), C-026 (Tenant Isolation), C-059 (Implementation Traceability)

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace Waooaw.BusinessPlatform.Infrastructure;

public sealed class IdentitySchemaHealthCheck(IDbContextFactory<IdentityDbContext> factory)
    : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default
    )
    {
        try
        {
            await using var db = await factory.CreateDbContextAsync(cancellationToken);
            await using var command = db.Database.GetDbConnection().CreateCommand();
            command.CommandText = """
                SELECT
                    to_regclass('identity.registrations') IS NOT NULL
                    AND to_regclass('identity.idempotency_ledger') IS NOT NULL
                    AND to_regclass('identity.accounts') IS NOT NULL
                    AND to_regclass('identity.login_methods') IS NOT NULL
                    AND to_regclass('identity.actor_bindings') IS NOT NULL
                    AND to_regclass('identity.memberships') IS NOT NULL
                    AND EXISTS (
                        SELECT 1
                        FROM pg_catalog.pg_class AS relation
                        JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                        WHERE namespace.nspname = 'identity'
                          AND relation.relname = 'memberships'
                          AND relation.relrowsecurity
                          AND relation.relforcerowsecurity
                    )
                """;
            await db.Database.OpenConnectionAsync(cancellationToken);
            var result = await command.ExecuteScalarAsync(cancellationToken);
            return result is true
                ? HealthCheckResult.Healthy()
                : HealthCheckResult.Unhealthy("Required identity schema or forced RLS is absent.");
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return HealthCheckResult.Unhealthy("Identity database readiness check failed.");
        }
    }
}
