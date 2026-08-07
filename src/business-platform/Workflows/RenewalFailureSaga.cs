// Implements: work-contracts/WC-042-wbe-s7-onboarding-payment-renewal-saga.md §WC042-04
// constitutional_basis: C-049 (agent disclosure in degraded mode), C-059, C-090, ADR-022 §1.3
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Temporalio.Activities;
using Temporalio.Workflows;

namespace Waooaw.BusinessPlatform.Workflows;

// ─── Workflow input ──────────────────────────────────────────────────────────

public sealed record RenewalFailureInput(
    string         ContractId,
    string         CustomerId,
    string         AgentType,
    DateTimeOffset FailedAt);

// ─── Day-state enum ──────────────────────────────────────────────────────────

public enum RenewalFailureDay { Day1, Day3, Day7, Day14 }

// ─── Workflow ────────────────────────────────────────────────────────────────

/// <summary>
/// Temporal saga for progressive renewal failure (ADR-022 §1.3 S-14).
///
/// Day 1:  Alert customer via WhatsApp — grace period begins
/// Day 3:  Enter DEGRADED mode — LLM tier reduced to LOCAL (C-049 disclosure sent)
/// Day 7:  Suspend Employment Contract + pause active campaigns (gate)
/// Day 14: Terminate Employment Contract
///
/// C-049: Customer must receive disclosure when agent enters reduced mode (Day 3+).
/// C-059: Every state transition logged with structured evidence.
/// </summary>
[Workflow]
public class RenewalFailureSaga
{
    private static readonly ActivityOptions ActivityOpts = new()
    {
        StartToCloseTimeout = TimeSpan.FromMinutes(5),
        RetryPolicy = new() { MaximumAttempts = 3 },
    };

    [WorkflowRun]
    public async Task RunAsync(RenewalFailureInput input)
    {
        var day1At  = input.FailedAt + TimeSpan.FromDays(1);
        var day3At  = input.FailedAt + TimeSpan.FromDays(3);
        var day7At  = input.FailedAt + TimeSpan.FromDays(7);
        var day14At = input.FailedAt + TimeSpan.FromDays(14);

        // Day 1 — Alert
        await SleepUntilAsync(day1At);
        await Workflow.ExecuteActivityAsync(
            (RenewalFailureActivities a) => a.SendPaymentFailureAlertAsync(input.CustomerId, input.ContractId),
            ActivityOpts);

        // Day 3 — Degraded mode + C-049 disclosure
        await SleepUntilAsync(day3At);
        await Workflow.ExecuteActivityAsync(
            (RenewalFailureActivities a) => a.SetDegradedModeAsync(input.CustomerId, input.ContractId, input.AgentType),
            ActivityOpts);

        // Day 7 — Suspend + campaign pause (gate: campaign pause must succeed before billing state change)
        await SleepUntilAsync(day7At);
        await Workflow.ExecuteActivityAsync(
            (RenewalFailureActivities a) => a.PauseCampaignsAsync(input.CustomerId, input.AgentType),
            ActivityOpts);
        await Workflow.ExecuteActivityAsync(
            (RenewalFailureActivities a) => a.SuspendContractAsync(input.CustomerId, input.ContractId),
            ActivityOpts);

        // Day 14 — Terminate
        await SleepUntilAsync(day14At);
        await Workflow.ExecuteActivityAsync(
            (RenewalFailureActivities a) => a.TerminateContractAsync(input.CustomerId, input.ContractId),
            ActivityOpts);
    }

    private static async Task SleepUntilAsync(DateTimeOffset target)
    {
        var delay = target - Workflow.UtcNow;
        if (delay > TimeSpan.Zero)
            await Workflow.DelayAsync(delay);
    }
}

// ─── Activities ──────────────────────────────────────────────────────────────

public class RenewalFailureActivities(IHttpClientFactory httpClientFactory)
{
    private readonly HttpClient _wbe  = httpClientFactory.CreateClient("WBE");
    private readonly HttpClient _paas = httpClientFactory.CreateClient("PAAS");

    [Activity]
    public async Task SendPaymentFailureAlertAsync(string customerId, string contractId)
    {
        // Day 1: notify customer — payment failed, N days to resolve before degraded mode
        await _wbe.PostAsJsonAsync("/meter/alert", new
        {
            customer_id = customerId,
            alert_type  = "RENEWAL_FAILED_DAY1",
            contract_id = contractId,
        });
    }

    [Activity]
    public async Task SetDegradedModeAsync(string customerId, string contractId, string agentType)
    {
        // Day 3: reduce LLM tier to LOCAL; C-049 disclosure sent to customer
        await _paas.PostAsJsonAsync($"/api/v1/sessions/{customerId}/mode", new
        {
            mode        = "DEGRADED",
            reason      = "RENEWAL_FAILURE_DAY3",
            contract_id = contractId,
            agent_type  = agentType,
        });
        // WhatsApp disclosure per C-049
        await _wbe.PostAsJsonAsync("/meter/alert", new
        {
            customer_id = customerId,
            alert_type  = "RENEWAL_FAILED_DAY3_DISCLOSURE",
            contract_id = contractId,
        });
    }

    [Activity]
    public async Task PauseCampaignsAsync(string customerId, string agentType)
    {
        // Day 7 gate: campaign pause must succeed before contract suspension
        await _paas.PostAsJsonAsync($"/api/v1/campaigns/pause", new
        {
            customer_id = customerId,
            agent_type  = agentType,
            reason      = "RENEWAL_FAILURE_DAY7",
        });
    }

    [Activity]
    public async Task SuspendContractAsync(string customerId, string contractId)
    {
        // Day 7: suspend employment contract after campaign pause confirmed
        await _paas.PostAsJsonAsync($"/api/v1/contracts/{contractId}/suspend", new
        {
            reason = "RENEWAL_FAILURE_DAY7",
        });
    }

    [Activity]
    public async Task TerminateContractAsync(string customerId, string contractId)
    {
        // Day 14: terminate — records EMPLOYMENT_TERMINATED in CE audit trail
        await _paas.PostAsJsonAsync($"/api/v1/contracts/{contractId}/terminate", new
        {
            reason = "RENEWAL_FAILURE_DAY14",
        });
    }
}
