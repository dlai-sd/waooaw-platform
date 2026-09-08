// Implements: WC-084 Customer Portal Solution Contract section 4.5
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using System.Text;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record CustomerAlertPage(IReadOnlyList<CustomerAlert> Items, string? NextCursor);
public sealed class CustomerAlertConflictException : Exception;

public sealed class CustomerAlertService(IDbContextFactory<EmploymentRelationshipDbContext> dbFactory)
{
    public async Task<CustomerAlertPage> ListAsync(
        Guid tenantId, string? cursor, int limit, CancellationToken cancellationToken)
    {
        Guid? afterAlertId = null;
        if (!string.IsNullOrWhiteSpace(cursor))
        {
            try { afterAlertId = Guid.Parse(Encoding.UTF8.GetString(Convert.FromBase64String(cursor))); }
            catch (FormatException) { throw new ArgumentException("Cursor is invalid.", nameof(cursor)); }
        }
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var alerts = await db.CustomerAlerts.AsNoTracking()
            .Where(value => value.TenantId == tenantId)
            .OrderByDescending(value => value.OccurredAt)
            .ThenBy(value => value.AlertId)
            .ToListAsync(cancellationToken);
        var start = 0;
        if (afterAlertId.HasValue)
        {
            var index = alerts.FindIndex(value => value.AlertId == afterAlertId.Value);
            if (index < 0) throw new ArgumentException("Cursor is invalid.", nameof(cursor));
            start = index + 1;
        }
        var page = alerts.Skip(start).Take(limit + 1).ToArray();
        var selected = page.Take(limit).ToArray();
        var nextCursor = page.Length > limit
            ? Convert.ToBase64String(Encoding.UTF8.GetBytes(selected[^1].AlertId.ToString()))
            : null;
        return new CustomerAlertPage(selected, nextCursor);
    }

    public async Task<CustomerAlert> SetReadStateAsync(
        Guid tenantId, Guid alertId, string actorSubject, Guid idempotencyKey,
        string operation, string expectedVersion, string requestHash, string targetState,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var prior = await db.CustomerAlertIdempotency.SingleOrDefaultAsync(value =>
            value.TenantId == tenantId && value.ActorSubject == actorSubject
            && value.IdempotencyKey == idempotencyKey && value.Operation == operation, cancellationToken);
        if (prior is not null && (prior.AlertId != alertId || prior.RequestHash != requestHash))
            throw new CustomerAlertConflictException();
        var alert = await db.CustomerAlerts.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.AlertId == alertId, cancellationToken)
            ?? throw new KeyNotFoundException("Alert not found.");
        if (prior is not null) return alert;
        if (expectedVersion != Version(alert)) throw new CustomerAlertConflictException();

        if (targetState == "ACKNOWLEDGED" || alert.ReadState == "UNREAD")
            alert.ReadState = targetState;
        alert.Version++;
        db.CustomerAlertIdempotency.Add(new CustomerAlertIdempotency
        {
            TenantId = tenantId,
            AlertId = alertId,
            ActorSubject = actorSubject,
            IdempotencyKey = idempotencyKey,
            Operation = operation,
            RequestHash = requestHash,
        });
        await db.SaveChangesAsync(cancellationToken);
        return alert;
    }

    public static string Version(CustomerAlert alert) => $"alert-{alert.Version}";
}