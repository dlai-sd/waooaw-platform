// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R011
// Constitutional basis: C-005, C-023, C-026, C-049, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Alerts;

namespace Waooaw.BusinessPlatform.Services;

public sealed class TrialEndOptions
{
    public const string SectionName = "TrialEnd";

    public bool Enabled { get; set; } = true;

    /// <summary>How often the platform looks for trials that have ended.</summary>
    public int PollSeconds { get; set; } = 300;

    /// <summary>
    /// How long the customer is told their work and data are kept after a trial ends without a Hire. The Founder has not
    /// decided this period (WC-176 D6), so the value is conservative and changeable without a release. Nothing is deleted
    /// by the trial ending.
    /// </summary>
    public int RetentionDays { get; set; } = 90;
}

/// <summary>
/// Ends trials that have run out. The billing owner's status decides: only a trial it reports as EXPIRED ends here, so a
/// trial that was hired in the meantime, or whose status cannot be read, is left alone and looked at again next time.
/// Ending a trial raises one alert for the customer (once, whatever number of retries) and moves the relationship out of
/// the trial state, so the agent takes no new work; the customer's next step is to Hire. Nothing is deleted.
/// </summary>
public sealed class TrialEndService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IRelationshipTrialOwnerGateway owners,
    EmploymentRelationshipService relationships,
    AlertPolicyService alerts,
    IOptions<TrialEndOptions> options,
    TimeProvider clock,
    ILogger<TrialEndService> logger
)
{
    public const string AlertCategory = "TRIAL";
    private const int BatchSize = 25;

    public static string AlertMeaning(int retentionDays) =>
        $"Your free trial has ended, so your agent has stopped taking new work. Hire your agent to keep it working. "
        + $"Your work and data are kept for {retentionDays} days.";

    public async Task<int> EndDueTrialsAsync(CancellationToken ct)
    {
        var now = clock.GetUtcNow();
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        var due = await (
            from binding in db.RelationshipTrialBindings.AsNoTracking()
            join relationship in db.EmploymentRelationships.AsNoTracking()
                on new { binding.TenantId, binding.RelationshipId } equals new
                {
                    relationship.TenantId,
                    relationship.RelationshipId,
                }
            where
                binding.Status == "ACTIVE"
                && binding.TrialId != null
                && binding.ExpiresAt != null
                && binding.ExpiresAt <= now
                && relationship.State == EmploymentRelationshipState.TrialActive
            orderby binding.ExpiresAt
            select new
            {
                binding.TenantId,
                binding.RelationshipId,
                binding.CustomerId,
                TrialId = binding.TrialId!.Value,
                relationship.InitiatingParticipantId,
            }
        )
            .Take(BatchSize)
            .ToListAsync(ct);

        var ended = 0;
        foreach (var item in due)
        {
            try
            {
                var status = await owners.GetWbeTrialStatusAsync(item.CustomerId, item.TrialId, ct);
                if (status?.Status != "EXPIRED")
                    continue;
                // Alert first: it is deduplicated, so a retry after a failed transition never repeats it.
                await alerts.RaiseAsync(
                    new AlertEvent(
                        AlertSources.BillingThreshold,
                        item.TenantId,
                        item.RelationshipId,
                        "TRIAL_ENDED",
                        "HIGH",
                        $"trial-{item.TrialId:N}",
                        AlertMeaning(options.Value.RetentionDays),
                        AlertCategory,
                        "RELATIONSHIP"
                    ),
                    whatsAppConsent: false,
                    stopReceived: false,
                    ct
                );
                var participant = await db
                    .RelationshipParticipants.AsNoTracking()
                    .Where(value =>
                        value.TenantId == item.TenantId
                        && value.RelationshipId == item.RelationshipId
                        && value.ParticipantId == item.InitiatingParticipantId
                        && value.Status == "ACTIVE"
                    )
                    .FirstOrDefaultAsync(ct);
                if (participant is null)
                {
                    logger.LogWarning(
                        "Trial {TrialId} ended but the relationship has no active customer participant to record the change.",
                        item.TrialId
                    );
                    continue;
                }
                await relationships.TransitionAsync(
                    item.TenantId,
                    item.RelationshipId,
                    participant.ParticipantId,
                    participant.Role,
                    EmploymentRelationshipState.Configuring,
                    Guid.NewGuid(),
                    explicitEmergencyRelease: false,
                    ct
                );
                ended++;
            }
            catch (Exception exception)
                when (exception
                        is IllegalRelationshipTransitionException
                            or ConstitutionalActionDeniedException
                            or DbUpdateException
                            or HttpRequestException
                )
            {
                logger.LogWarning(
                    exception,
                    "Trial {TrialId} could not be ended yet; it is retried.",
                    item.TrialId
                );
            }
        }
        return ended;
    }
}

public sealed class TrialEndHostedService(
    IServiceScopeFactory scopes,
    IOptions<TrialEndOptions> options,
    ILogger<TrialEndHostedService> logger
) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if (!options.Value.Enabled)
            return;
        using var timer = new PeriodicTimer(
            TimeSpan.FromSeconds(Math.Max(30, options.Value.PollSeconds))
        );
        do
        {
            try
            {
                await using var scope = scopes.CreateAsyncScope();
                await scope
                    .ServiceProvider.GetRequiredService<TrialEndService>()
                    .EndDueTrialsAsync(stoppingToken);
            }
            catch (Exception exception) when (exception is not OperationCanceledException)
            {
                logger.LogError(exception, "Looking for ended trials failed; it is retried.");
            }
        } while (await timer.WaitForNextTickAsync(stoppingToken));
    }
}
