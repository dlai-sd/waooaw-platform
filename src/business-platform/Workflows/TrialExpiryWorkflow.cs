// Implements: work-contracts/WC-033-goal005-bp-trial-lifecycle.md §WC033-02
// constitutional_basis: C-088 (trial billing mode), C-090 (grandfather at conversion), C-059
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Temporalio.Activities;
using Temporalio.Workflows;

namespace Waooaw.BusinessPlatform.Workflows;

// ─── Workflow input ──────────────────────────────────────────────────────────

public sealed record TrialExpiryInput(
    string         TrialId,
    string         CustomerId,
    DateTimeOffset ExpiresAt);

public enum TrialExpiryOutcome
{
    Expired,
    BillingConverted,
    Unresolved,
}

// ─── Workflow ────────────────────────────────────────────────────────────────

/// <summary>
/// Temporal saga that manages the trial expiry lifecycle:
/// 1. Sleep until 48 h before expiry → send WhatsApp reminder
/// 2. Sleep until expiry → reconcile authoritative WBE status
/// 3. Expire only confirmed ACTIVE trials; return UNRESOLVED for owner uncertainty
///
/// C-088: trial is a billing mode; lapse is a billing state transition.
/// C-059: every activity outcome is recorded via structured logging in the activity.
/// </summary>
[Workflow]
public class TrialExpiryWorkflow
{
    private static readonly ActivityOptions ActivityOpts = new()
    {
        StartToCloseTimeout = TimeSpan.FromMinutes(5),
        RetryPolicy = new() { MaximumAttempts = 3 },
    };

    [WorkflowRun]
    public async Task<TrialExpiryOutcome> RunAsync(TrialExpiryInput input)
    {
        var reminderAt = input.ExpiresAt - TimeSpan.FromHours(48);
        var now        = Workflow.UtcNow;

        // Sleep until 48 h before expiry (may be zero if already past)
        if (reminderAt > now)
            await Workflow.DelayAsync(reminderAt - now);

        await Workflow.ExecuteActivityAsync(
            (TrialExpiryActivities a) => a.SendReminderAsync(input.CustomerId, input.TrialId),
            ActivityOpts);

        // Sleep until expiry
        now = Workflow.UtcNow;
        if (input.ExpiresAt > now)
            await Workflow.DelayAsync(input.ExpiresAt - now);

        var status = await Workflow.ExecuteActivityAsync(
            (TrialExpiryActivities a) => a.CheckTrialStatusAsync(input.CustomerId, input.TrialId),
            ActivityOpts);

        if (status == "CONVERTED") return TrialExpiryOutcome.BillingConverted;
        if (status == "EXPIRED") return TrialExpiryOutcome.Expired;
        if (status != "ACTIVE") return TrialExpiryOutcome.Unresolved;

        var expiryStatus = await Workflow.ExecuteActivityAsync(
            (TrialExpiryActivities a) => a.MarkExpiredAsync(input.TrialId, input.CustomerId),
            ActivityOpts);
        return expiryStatus switch
        {
            "EXPIRED" => TrialExpiryOutcome.Expired,
            "CONVERTED" => TrialExpiryOutcome.BillingConverted,
            _ => TrialExpiryOutcome.Unresolved,
        };
    }
}

// ─── Activities ──────────────────────────────────────────────────────────────

/// <summary>
/// Temporal activities for TrialExpiryWorkflow. Injected by DI into the worker.
/// Each activity uses the "WBE" named HttpClient to call billing-engine.
/// C-059: every activity logs its outcome for constitutional traceability.
/// </summary>
public sealed class TrialExpiryActivities
{
    private const string WbeClientName          = "WBE";
    private const string WbeTrialStatusBasePath = "/trial/status/";
    private const string WbeTrialExpirePath     = "/trial/expire";

    private static readonly JsonSerializerOptions _jsonOpts = new(JsonSerializerDefaults.Web);

    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<TrialExpiryActivities> _logger;

    public TrialExpiryActivities(
        IHttpClientFactory              httpClientFactory,
        ILogger<TrialExpiryActivities>  logger)
    {
        _httpClientFactory = httpClientFactory;
        _logger            = logger;
    }

    /// <summary>
    /// Sends a 48-hour expiry reminder via WBE WhatsApp notification stub.
    /// C-059: logs reminder sent with trial_id for audit trail.
    /// </summary>
    [Activity]
    public async Task SendReminderAsync(string customerId, string trialId)
    {
        _logger.LogInformation(
            "TrialExpiry: sending 48h reminder customer_id={CustomerId} trial_id={TrialId}",
            customerId, trialId);

        // WhatsApp reminder via WBE notification stub (full implementation in WC-034 scope)
        var client = _httpClientFactory.CreateClient(WbeClientName);
        try
        {
            var payload = new { customer_id = customerId, trial_id = trialId, type = "TRIAL_EXPIRY_48H" };
            var response = await client.PostAsJsonAsync("/notifications/send", payload, _jsonOpts);
            _logger.LogInformation(
                "TrialExpiry: reminder response={Status} customer_id={CustomerId}",
                (int)response.StatusCode, customerId);
        }
        catch (Exception ex)
        {
            // Non-fatal: log but do not fail the workflow — reminder is best-effort
            _logger.LogWarning(ex,
                "TrialExpiry: reminder send failed (non-fatal) customer_id={CustomerId}",
                customerId);
        }
    }

    /// <summary>
    /// Polls WBE GET /trial/status/{customer_id} and returns the status string.
    /// Returns "UNKNOWN" if WBE is unavailable or the returned trial binding differs.
    /// </summary>
    [Activity]
    public async Task<string> CheckTrialStatusAsync(string customerId, string trialId)
    {
        _logger.LogInformation(
            "TrialExpiry: checking trial status trial_id={TrialId}", trialId);

        var client = _httpClientFactory.CreateClient(WbeClientName);
        try
        {
            var response = await client.GetAsync($"{WbeTrialStatusBasePath}{customerId}");
            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning(
                    "TrialExpiry: status check returned {Status} trial_id={TrialId}",
                    (int)response.StatusCode, trialId);
                return "UNKNOWN";
            }

            var result = await response.Content.ReadFromJsonAsync<WbeTrialStatusResult>(_jsonOpts);
            var status = result?.TrialId == trialId ? result.Status ?? "UNKNOWN" : "UNKNOWN";

            _logger.LogInformation(
                "TrialExpiry: trial status={Status} trial_id={TrialId}", status, trialId);
            return status;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex,
                "TrialExpiry: status check failed, defaulting to UNKNOWN trial_id={TrialId}", trialId);
            return "UNKNOWN";
        }
    }

    /// <summary>
    /// Calls WBE's dedicated expiry command and sends an informational notification.
    /// C-088: expiry is a billing state transition — WBE is authoritative.
    /// </summary>
    [Activity]
    public async Task<string> MarkExpiredAsync(string trialId, string customerId)
    {
        _logger.LogInformation(
            "TrialExpiry: marking trial EXPIRED trial_id={TrialId} customer_id={CustomerId}",
            trialId, customerId);

        var client = _httpClientFactory.CreateClient(WbeClientName);
        try
        {
            var payload = new { trial_id = trialId };
            var response = await client.PostAsJsonAsync(WbeTrialExpirePath, payload, _jsonOpts);
            response.EnsureSuccessStatusCode();
            var result = await response.Content.ReadFromJsonAsync<WbeTrialStatusResult>(_jsonOpts);
            if (result?.TrialId != trialId || result.Status is not ("EXPIRED" or "CONVERTED")) return "UNKNOWN";
            _logger.LogInformation(
                "TrialExpiry: expiry response={Status} trial_id={TrialId}",
                (int)response.StatusCode, trialId);
            return result.Status;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "TrialExpiry: MarkExpired failed trial_id={TrialId}", trialId);
            throw; // re-throw so Temporal retries the activity
        }
    }

    // ─── WBE wire types ──────────────────────────────────────────────────────

    private sealed record WbeTrialStatusResult(
        [property: JsonPropertyName("trial_id")] string? TrialId,
        [property: JsonPropertyName("status")] string? Status);
}
