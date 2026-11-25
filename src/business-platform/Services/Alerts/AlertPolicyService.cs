// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R005, WC171-R006
// Constitutional basis: C-001, C-005, C-007, C-023, C-049, C-059, C-063
// IB: IB-171

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Alerts;

/// <summary>Founder-controlled switch for proactive WhatsApp alerts. Off by default; Demo sends to sandbox recipients only.</summary>
public sealed class AlertDeliveryOptions
{
    public const string SectionName = "AlertDelivery";

    public bool ProactiveWhatsAppEnabled { get; init; }
    public bool SandboxRecipientsOnly { get; init; } = true;
}

public enum AllowanceOutcome
{
    Consumed,
    Exhausted,
    Unavailable,
}

/// <summary>The 30 proactive messages a month per subscription, counted in the billing engine. Idempotent on the key.</summary>
public interface IProactiveAllowance
{
    Task<AllowanceOutcome> ConsumeAsync(
        Guid tenantId,
        Guid? relationshipId,
        string idempotencyKey,
        CancellationToken cancellationToken
    );
}

public sealed record AlertSendRequest(
    Guid TenantId,
    Guid? RelationshipId,
    Guid AlertId,
    string AlertClass,
    string Signal,
    bool SandboxOnly
);

/// <summary>Delivers one proactive message. The real adapter needs the authorized thread rate and an approved template.</summary>
public interface IAlertWhatsAppSender
{
    bool Available { get; }

    Task<bool> SendAsync(AlertSendRequest request, CancellationToken cancellationToken);
}

/// <summary>No counted message is sent until the billing engine can count it: the portal still carries the alert.</summary>
public sealed class UnavailableProactiveAllowance : IProactiveAllowance
{
    public Task<AllowanceOutcome> ConsumeAsync(
        Guid tenantId,
        Guid? relationshipId,
        string idempotencyKey,
        CancellationToken cancellationToken
    ) => Task.FromResult(AllowanceOutcome.Unavailable);
}

/// <summary>Closed until the Founder authorizes the thread rate and a WhatsApp utility template is approved.</summary>
public sealed class ClosedAlertWhatsAppSender : IAlertWhatsAppSender
{
    public bool Available => false;

    public Task<bool> SendAsync(AlertSendRequest request, CancellationToken cancellationToken) =>
        Task.FromResult(false);
}

public sealed record AlertOutcome(
    Guid? AlertId,
    bool Folded,
    bool Escalated,
    string AlertClass,
    string WhatsAppDecision
);

/// <summary>
/// The single way an alert enters the platform. It classifies by policy, writes the portal alert once per dedup key,
/// decides the second channel, consumes the allowance on send and records what happened. A second event for the same
/// problem is folded into the first; only a strictly more material class may escalate it, once.
/// </summary>
public sealed class AlertPolicyService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IOptions<AlertDeliveryOptions> options,
    IProactiveAllowance allowance,
    IAlertWhatsAppSender sender,
    TimeProvider clock
)
{
    public static readonly TimeSpan IstOffset = TimeSpan.FromMinutes(330);

    public async Task<AlertOutcome> RaiseAsync(
        AlertEvent alert,
        bool whatsAppConsent,
        bool stopReceived,
        CancellationToken cancellationToken
    )
    {
        var alertClass = AlertPolicy.Classify(alert);
        if (alertClass == AlertClasses.Operations || alert.TenantId is not { } tenantId)
            throw new ArgumentException(
                "Operations alerts are paged to operators, not written to a customer inbox.",
                nameof(alert)
            );
        var dedupKey = AlertPolicy.DedupKey(alert);
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var matches = await db
            .CustomerAlerts.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.DedupKey != null
                && (value.DedupKey == dedupKey || value.DedupKey.StartsWith(dedupKey + ":"))
            )
            .ToListAsync(cancellationToken);
        // The most material alert already raised for this problem decides whether a new event is folded or escalates.
        var existing = matches
            .OrderByDescending(value => AlertClasses.Rank(value.AlertClass))
            .ThenByDescending(value => value.OccurredAt)
            .FirstOrDefault();
        var escalated = false;
        if (existing is not null)
        {
            if (!AlertPolicy.Escalates(existing.AlertClass, alertClass))
                return new AlertOutcome(
                    existing.AlertId,
                    true,
                    false,
                    existing.AlertClass,
                    existing.WhatsAppDecision ?? WhatsAppDecisions.ClassNotEligible
                );
            dedupKey = AlertPolicy.EscalatedKey(dedupKey, alertClass);
            escalated = true;
        }

        var muted =
            AlertPolicy.IsMutable(alertClass)
            && await db
                .AlertCategoryMutes.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.Category == alert.Category
                        && value.Muted,
                    cancellationToken
                );
        var now = clock.GetUtcNow();
        var facts = new DeliveryFacts(
            options.Value.ProactiveWhatsAppEnabled && sender.Available,
            whatsAppConsent,
            stopReceived,
            muted,
            (now + IstOffset).TimeOfDay
        );
        var decision = AlertPolicy.DecideWhatsApp(alertClass, facts);
        var record = new CustomerAlert
        {
            TenantId = tenantId,
            AlertType = alertClass is AlertClasses.Floor or AlertClasses.ActionRequired
                ? "ACTIONABLE"
                : "INFORMATIONAL",
            Severity = alertClass switch
            {
                AlertClasses.Floor => "CRITICAL",
                AlertClasses.ActionRequired => "HIGH",
                AlertClasses.AtRisk => "MEDIUM",
                _ => "LOW",
            },
            Source = alert.Source,
            RelationshipId = alert.RelationshipId,
            OccurredAt = now,
            DueMeaning = alert.DueMeaning.Length > 240 ? alert.DueMeaning[..240] : alert.DueMeaning,
            DestinationSurface = alert.DestinationSurface,
            DestinationSubjectId = alert.DestinationSubjectId,
            AvailableAction = alertClass is AlertClasses.Floor or AlertClasses.ActionRequired
                ? "OPEN"
                : "ACKNOWLEDGE",
            Category = alert.Category,
            AlertClass = alertClass,
            DedupKey = dedupKey,
            WhatsAppDecision = decision,
        };
        db.CustomerAlerts.Add(record);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateException)
        {
            // A concurrent producer raised the same problem first: this event is folded into that alert.
            if (await AlreadyRaisedAsync(tenantId, dedupKey, cancellationToken))
                return new AlertOutcome(null, true, false, alertClass, decision);
            throw;
        }

        if (decision is WhatsAppDecisions.Send or WhatsAppDecisions.SendUncounted)
            decision = await SendAsync(db, record, decision, cancellationToken);
        await RecordAsync(db, record, decision, cancellationToken);
        return new AlertOutcome(record.AlertId, false, escalated, alertClass, decision);
    }

    private async Task<string> SendAsync(
        EmploymentRelationshipDbContext db,
        CustomerAlert record,
        string decision,
        CancellationToken cancellationToken
    )
    {
        if (decision == WhatsAppDecisions.Send)
        {
            var consumed = await allowance.ConsumeAsync(
                record.TenantId,
                record.RelationshipId,
                record.AlertId.ToString("N"),
                cancellationToken
            );
            if (consumed != AllowanceOutcome.Consumed)
                return consumed == AllowanceOutcome.Exhausted
                    ? WhatsAppDecisions.AllowanceExhausted
                    : WhatsAppDecisions.AllowanceUnavailable;
        }
        var sent = await sender.SendAsync(
            new AlertSendRequest(
                record.TenantId,
                record.RelationshipId,
                record.AlertId,
                record.AlertClass,
                record.Category,
                options.Value.SandboxRecipientsOnly
            ),
            cancellationToken
        );
        return sent ? decision : WhatsAppDecisions.SenderUnavailable;
    }

    private async Task RecordAsync(
        EmploymentRelationshipDbContext db,
        CustomerAlert record,
        string decision,
        CancellationToken cancellationToken
    )
    {
        var now = clock.GetUtcNow();
        record.WhatsAppDecision = decision;
        db.AlertDeliveries.Add(
            new AlertDelivery
            {
                TenantId = record.TenantId,
                AlertId = record.AlertId,
                Signal = record.Category,
                AlertClass = record.AlertClass,
                Channel = AlertChannels.Portal,
                Outcome = "DELIVERED",
                Reason = decision,
                RecordedAt = now,
            }
        );
        var attempted = decision is WhatsAppDecisions.Send or WhatsAppDecisions.SendUncounted;
        if (attempted || decision == WhatsAppDecisions.SenderUnavailable)
            db.AlertDeliveries.Add(
                new AlertDelivery
                {
                    TenantId = record.TenantId,
                    AlertId = record.AlertId,
                    Signal = record.Category,
                    AlertClass = record.AlertClass,
                    Channel = AlertChannels.WhatsAppText,
                    Outcome = attempted ? "DELIVERED" : "FAILED",
                    Reason = decision,
                    RecordedAt = now,
                }
            );
        await db.SaveChangesAsync(cancellationToken);
    }

    private async Task<bool> AlreadyRaisedAsync(
        Guid tenantId,
        string dedupKey,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        return await db.CustomerAlerts.AnyAsync(
            value => value.TenantId == tenantId && value.DedupKey == dedupKey,
            cancellationToken
        );
    }
}
