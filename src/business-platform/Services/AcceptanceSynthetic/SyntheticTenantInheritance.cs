// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;

/// <summary>
/// A tenant created at first login by a registered synthetic subject inherits the label (ADR-055 decision 4). The
/// subject is the server-verified (iss, sub) of the actor the identity adapter already validated; nothing from a
/// token claim or a request body is read, and the label grants no authority. Off means no query at all.
/// </summary>
public sealed class SyntheticTenantInheritance(
    IOptions<AcceptanceSyntheticOptions> options,
    TimeProvider clock,
    ILogger<SyntheticTenantInheritance> logger
)
{
    public async Task InheritAsync(
        DbContext db,
        VerifiedCustomerActor actor,
        Guid tenantId,
        CancellationToken ct
    )
    {
        if (!options.Value.Enabled)
            return;
        var now = clock.GetUtcNow();
        var labelled = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.synthetic_tenants (tenant_id, run_id, registration_id, labelled_at)
            SELECT {tenantId}, subject.run_id, subject.registration_id, {now}
            FROM business.synthetic_subjects AS subject
            WHERE subject.issuer = {actor.Issuer} AND subject.subject = {actor.Subject}
              AND subject.deactivated_at IS NULL AND subject.expires_at > {now}
            ON CONFLICT (tenant_id) DO NOTHING
            """,
            ct
        );
        if (labelled > 0)
            logger.LogInformation(
                "Tenant {TenantId} labelled synthetic at creation by a registered acceptance subject.",
                tenantId
            );
    }
}
