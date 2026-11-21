// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004, WC137-R005
// Constitutional basis: C-009, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.PlatformAccess;

public sealed record PlatformRoleGrant(
    Guid GrantId,
    string Email,
    string? Subject,
    string Role,
    string Source,
    string GrantedBy,
    DateTimeOffset GrantedAt,
    DateTimeOffset? ExpiresAt
);

public sealed record PlatformAccessRequest(
    Guid RequestId,
    string Email,
    string Role,
    string Justification,
    string Status,
    DateTimeOffset RequestedAt,
    DateTimeOffset? DecidedAt,
    string? DecidedBy,
    string? DecisionReason
);

public enum AccessRequestResult
{
    Created,
    AlreadyGranted,
    AlreadyPending,
    RateLimited,
    BacklogFull,
}

public enum AccessDecisionResult
{
    Decided,
    NotFound,
    NotPending,
    SelfApproval,
}

public enum AccessRevocationResult
{
    Revoked,
    NotFound,
    ProtectedFounder,
}

public interface IPlatformAccessStore
{
    Task ReconcileFoundersAsync(
        IReadOnlyList<ConfiguredFounder> founders,
        DateTimeOffset now,
        CancellationToken ct
    );

    Task<IReadOnlyList<string>> ResolveRolesAsync(
        string email,
        string subject,
        DateTimeOffset now,
        CancellationToken ct
    );

    Task<(AccessRequestResult Result, Guid? RequestId)> CreateRequestAsync(
        string subject,
        string email,
        string role,
        string justification,
        DateTimeOffset now,
        CancellationToken ct
    );

    Task<IReadOnlyList<PlatformAccessRequest>> ListRequestsAsync(
        string? status,
        string? subject,
        int limit,
        CancellationToken ct
    );

    Task<AccessDecisionResult> DecideAsync(
        Guid requestId,
        bool approve,
        string deciderEmail,
        string? reason,
        DateTimeOffset now,
        CancellationToken ct
    );

    Task<IReadOnlyList<PlatformRoleGrant>> ListGrantsAsync(
        DateTimeOffset now,
        CancellationToken ct
    );

    Task<AccessRevocationResult> RevokeAsync(
        Guid grantId,
        string revokedBy,
        string reason,
        DateTimeOffset now,
        CancellationToken ct
    );
}

/// <summary>
/// Stores staff role grants, access requests and the append-only event trail. Every state change runs in one
/// transaction with its event; unique indexes in the migration make concurrent replays safe.
/// </summary>
public sealed class PostgresPlatformAccessStore(
    IDbContextFactory<ConversationStoreDbContext> factory,
    IOptions<PlatformAccessOptions> options
) : IPlatformAccessStore
{
    private const string Configuration = "configuration";

    private sealed class GrantRow
    {
        public Guid GrantId { get; init; }
        public string Email { get; init; } = string.Empty;
        public string? Subject { get; init; }
        public string Role { get; init; } = string.Empty;
        public string Source { get; init; } = string.Empty;
        public string GrantedBy { get; init; } = string.Empty;
        public DateTimeOffset GrantedAt { get; init; }
        public DateTimeOffset? ExpiresAt { get; init; }
    }

    private sealed class RequestRow
    {
        public Guid RequestId { get; init; }
        public string Subject { get; init; } = string.Empty;
        public string Email { get; init; } = string.Empty;
        public string Role { get; init; } = string.Empty;
        public string Justification { get; init; } = string.Empty;
        public string Status { get; init; } = string.Empty;
        public DateTimeOffset RequestedAt { get; init; }
        public DateTimeOffset? DecidedAt { get; init; }
        public string? DecidedBy { get; init; }
        public string? DecisionReason { get; init; }
    }

    private static Task AppendEventAsync(
        ConversationStoreDbContext db,
        string type,
        string actor,
        string? email,
        string? role,
        Guid? reference,
        DateTimeOffset now,
        CancellationToken ct
    ) =>
        db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.platform_access_events
                (event_id, event_type, actor, target_email, role, reference_id, occurred_at)
            VALUES ({Guid.NewGuid()}, {type}, {actor}, {email}, {role}, {reference}, {now})
            """,
            ct
        );

    private static Task<long> CountAsync(
        ConversationStoreDbContext db,
        FormattableString sql,
        CancellationToken ct
    ) => db.Database.SqlQuery<long>(sql).SingleAsync(ct);

    public async Task ReconcileFoundersAsync(
        IReadOnlyList<ConfiguredFounder> founders,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended('platform-access-bootstrap',0))",
            ct
        );
        foreach (var founder in founders)
        {
            var email = founder.NormalizedEmail;
            var inserted = await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.platform_role_grants
                    (grant_id, email_normalized, subject, role, source, granted_by, granted_at)
                VALUES ({Guid.NewGuid()}, {email}, {founder.Subject}, 'founder', 'BOOTSTRAP', {Configuration}, {now})
                ON CONFLICT (email_normalized, role) WHERE revoked_at IS NULL DO NOTHING
                """,
                ct
            );
            if (inserted == 1)
            {
                await AppendEventAsync(
                    db,
                    "FOUNDER_BOOTSTRAPPED",
                    Configuration,
                    email,
                    "founder",
                    null,
                    now,
                    ct
                );
                continue;
            }
            if (founder.Subject is null)
                continue;
            var rebound = await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                UPDATE business.platform_role_grants
                SET subject = {founder.Subject}
                WHERE email_normalized = {email} AND role = 'founder' AND revoked_at IS NULL
                    AND subject IS DISTINCT FROM {founder.Subject}
                """,
                ct
            );
            if (rebound > 0)
                await AppendEventAsync(
                    db,
                    "FOUNDER_SUBJECT_BOUND",
                    Configuration,
                    email,
                    "founder",
                    null,
                    now,
                    ct
                );
        }

        // An empty list is treated as "not configured", so a missing value can never lock every Founder out.
        if (founders.Count > 0)
        {
            var keep = founders.Select(founder => founder.NormalizedEmail).ToArray();
            var removed = await db
                .Database.SqlQuery<string>(
                    $"""
                    SELECT email_normalized AS "Value"
                    FROM business.platform_role_grants
                    WHERE role = 'founder' AND source = 'BOOTSTRAP' AND revoked_at IS NULL
                        AND email_normalized <> ALL({keep})
                    """
                )
                .ToListAsync(ct);
            foreach (var email in removed)
            {
                await db.Database.ExecuteSqlInterpolatedAsync(
                    $"""
                    UPDATE business.platform_role_grants
                    SET revoked_at = {now}, revoked_by = {Configuration},
                        revoke_reason = 'Removed from the environment configuration'
                    WHERE email_normalized = {email} AND role = 'founder' AND revoked_at IS NULL
                    """,
                    ct
                );
                await AppendEventAsync(
                    db,
                    "FOUNDER_REMOVED_BY_CONFIGURATION",
                    Configuration,
                    email,
                    "founder",
                    null,
                    now,
                    ct
                );
            }
        }
        await transaction.CommitAsync(ct);
    }

    public async Task<IReadOnlyList<string>> ResolveRolesAsync(
        string email,
        string subject,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        var normalized = PlatformRoles.NormalizeEmail(email);
        await using var db = await factory.CreateDbContextAsync(ct);
        var rows = await db
            .Database.SqlQuery<GrantRow>(
                $"""
                SELECT grant_id AS "GrantId", email_normalized AS "Email", subject AS "Subject", role AS "Role",
                    source AS "Source", granted_by AS "GrantedBy", granted_at AS "GrantedAt",
                    expires_at AS "ExpiresAt"
                FROM business.platform_role_grants
                WHERE email_normalized = {normalized} AND revoked_at IS NULL
                    AND (expires_at IS NULL OR expires_at > {now})
                """
            )
            .ToListAsync(ct);
        if (rows.Count == 0)
            return [];
        var unbound = rows.Any(row => row.Subject is null);
        if (unbound)
        {
            // The first verified sign-in of a configured Founder binds the identity-provider subject; a later
            // sign-in with the same email but another subject receives no role.
            var bound = await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                UPDATE business.platform_role_grants
                SET subject = {subject}
                WHERE email_normalized = {normalized} AND subject IS NULL AND revoked_at IS NULL
                """,
                ct
            );
            if (bound > 0)
                await AppendEventAsync(
                    db,
                    "FOUNDER_SUBJECT_BOUND",
                    subject,
                    normalized,
                    null,
                    null,
                    now,
                    ct
                );
        }
        return rows.Where(row => row.Subject is null || row.Subject == subject)
            .Select(row => row.Role)
            .Distinct(StringComparer.Ordinal)
            .Order(StringComparer.Ordinal)
            .ToList();
    }

    public async Task<(AccessRequestResult Result, Guid? RequestId)> CreateRequestAsync(
        string subject,
        string email,
        string role,
        string justification,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        var normalized = PlatformRoles.NormalizeEmail(email);
        var limits = options.Value;
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var granted = await CountAsync(
            db,
            $"""
            SELECT count(*) AS "Value" FROM business.platform_role_grants
            WHERE email_normalized = {normalized} AND role = {role} AND revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > {now})
            """,
            ct
        );
        if (granted > 0)
            return (AccessRequestResult.AlreadyGranted, null);
        var since = now.AddHours(-24);
        var recent = await CountAsync(
            db,
            $"""
            SELECT count(*) AS "Value" FROM business.platform_access_requests
            WHERE subject = {subject} AND requested_at > {since}
            """,
            ct
        );
        if (recent >= limits.MaximumRequestsPerDay)
            return (AccessRequestResult.RateLimited, null);
        var pending = await CountAsync(
            db,
            $"""SELECT count(*) AS "Value" FROM business.platform_access_requests WHERE status = 'PENDING'""",
            ct
        );
        if (pending >= limits.MaximumPendingRequests)
            return (AccessRequestResult.BacklogFull, null);
        var requestId = Guid.NewGuid();
        var inserted = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.platform_access_requests
                (request_id, subject, email_normalized, role, justification, status, requested_at)
            VALUES ({requestId}, {subject}, {normalized}, {role}, {justification}, 'PENDING', {now})
            ON CONFLICT (subject) WHERE status = 'PENDING' DO NOTHING
            """,
            ct
        );
        if (inserted == 0)
            return (AccessRequestResult.AlreadyPending, null);
        await AppendEventAsync(db, "REQUESTED", subject, normalized, role, requestId, now, ct);
        await transaction.CommitAsync(ct);
        return (AccessRequestResult.Created, requestId);
    }

    public async Task<IReadOnlyList<PlatformAccessRequest>> ListRequestsAsync(
        string? status,
        string? subject,
        int limit,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        var rows = await db
            .Database.SqlQuery<RequestRow>(
                $"""
                SELECT request_id AS "RequestId", subject AS "Subject", email_normalized AS "Email", role AS "Role",
                    justification AS "Justification", status AS "Status", requested_at AS "RequestedAt",
                    decided_at AS "DecidedAt", decided_by AS "DecidedBy", decision_reason AS "DecisionReason"
                FROM business.platform_access_requests
                WHERE ({status}::text IS NULL OR status = {status})
                    AND ({subject}::text IS NULL OR subject = {subject})
                ORDER BY requested_at DESC
                LIMIT {limit}
                """
            )
            .ToListAsync(ct);
        return rows.Select(row => new PlatformAccessRequest(
                row.RequestId,
                row.Email,
                row.Role,
                row.Justification,
                row.Status,
                row.RequestedAt,
                row.DecidedAt,
                row.DecidedBy,
                row.DecisionReason
            ))
            .ToList();
    }

    public async Task<AccessDecisionResult> DecideAsync(
        Guid requestId,
        bool approve,
        string deciderEmail,
        string? reason,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        var decider = PlatformRoles.NormalizeEmail(deciderEmail);
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var request = (
            await db
                .Database.SqlQuery<RequestRow>(
                    $"""
                    SELECT request_id AS "RequestId", subject AS "Subject", email_normalized AS "Email",
                        role AS "Role", justification AS "Justification", status AS "Status",
                        requested_at AS "RequestedAt", decided_at AS "DecidedAt", decided_by AS "DecidedBy",
                        decision_reason AS "DecisionReason"
                    FROM business.platform_access_requests
                    WHERE request_id = {requestId}
                    FOR UPDATE
                    """
                )
                .ToListAsync(ct)
        ).SingleOrDefault();
        if (request is null)
            return AccessDecisionResult.NotFound;
        if (request.Status != "PENDING")
            return AccessDecisionResult.NotPending;
        if (approve && string.Equals(request.Email, decider, StringComparison.Ordinal))
            return AccessDecisionResult.SelfApproval;
        var status = approve ? "APPROVED" : "REJECTED";
        if (approve)
        {
            var expires = now.AddDays(options.Value.ApprovedGrantDays);
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.platform_role_grants
                    (grant_id, email_normalized, subject, role, source, granted_by, request_id, granted_at, expires_at)
                VALUES ({Guid.NewGuid()}, {request.Email}, {request.Subject}, {request.Role}, 'APPROVAL',
                    {decider}, {requestId}, {now}, {expires})
                ON CONFLICT (email_normalized, role) WHERE revoked_at IS NULL DO NOTHING
                """,
                ct
            );
        }
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.platform_access_requests
            SET status = {status}, decided_at = {now}, decided_by = {decider}, decision_reason = {reason}
            WHERE request_id = {requestId}
            """,
            ct
        );
        await AppendEventAsync(
            db,
            status,
            decider,
            request.Email,
            request.Role,
            requestId,
            now,
            ct
        );
        await transaction.CommitAsync(ct);
        return AccessDecisionResult.Decided;
    }

    public async Task<IReadOnlyList<PlatformRoleGrant>> ListGrantsAsync(
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        var rows = await db
            .Database.SqlQuery<GrantRow>(
                $"""
                SELECT grant_id AS "GrantId", email_normalized AS "Email", subject AS "Subject", role AS "Role",
                    source AS "Source", granted_by AS "GrantedBy", granted_at AS "GrantedAt",
                    expires_at AS "ExpiresAt"
                FROM business.platform_role_grants
                WHERE revoked_at IS NULL AND (expires_at IS NULL OR expires_at > {now})
                ORDER BY email_normalized, role
                """
            )
            .ToListAsync(ct);
        return rows.Select(row => new PlatformRoleGrant(
                row.GrantId,
                row.Email,
                row.Subject,
                row.Role,
                row.Source,
                row.GrantedBy,
                row.GrantedAt,
                row.ExpiresAt
            ))
            .ToList();
    }

    public async Task<AccessRevocationResult> RevokeAsync(
        Guid grantId,
        string revokedBy,
        string reason,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var grant = (
            await db
                .Database.SqlQuery<GrantRow>(
                    $"""
                    SELECT grant_id AS "GrantId", email_normalized AS "Email", subject AS "Subject", role AS "Role",
                        source AS "Source", granted_by AS "GrantedBy", granted_at AS "GrantedAt",
                        expires_at AS "ExpiresAt"
                    FROM business.platform_role_grants
                    WHERE grant_id = {grantId} AND revoked_at IS NULL
                    FOR UPDATE
                    """
                )
                .ToListAsync(ct)
        ).SingleOrDefault();
        if (grant is null)
            return AccessRevocationResult.NotFound;
        if (grant.Source == "BOOTSTRAP")
            return AccessRevocationResult.ProtectedFounder;
        var actor = PlatformRoles.NormalizeEmail(revokedBy);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.platform_role_grants
            SET revoked_at = {now}, revoked_by = {actor}, revoke_reason = {reason}
            WHERE grant_id = {grantId}
            """,
            ct
        );
        await AppendEventAsync(db, "REVOKED", actor, grant.Email, grant.Role, grantId, now, ct);
        await transaction.CommitAsync(ct);
        return AccessRevocationResult.Revoked;
    }
}
