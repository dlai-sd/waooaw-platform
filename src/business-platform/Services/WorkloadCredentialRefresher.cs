// Implements: ADR-046 sections 5.1, 5.2 and 12.2 D4, D6; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-023, C-059, C-063, C-083, C-084, C-085

namespace Waooaw.BusinessPlatform.Services;

/// <summary>
/// Re-reads the Key Vault bundles on an interval, swaps a fully verified bundle into the identity client and
/// refreshes the owner-link state. A failure keeps the last verified credential and never stops the host.
/// </summary>
internal sealed class WorkloadCredentialRefresher(
    WorkloadIdentityClient identity,
    IWorkloadCredentialReader reader,
    OwnerLinkProber prober,
    WorkloadCredentialOptions options,
    ILogger<WorkloadCredentialRefresher> logger
) : BackgroundService
{
    private bool _wasReady;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            await RefreshOnceAsync(stoppingToken);
            var seconds = identity.IsAvailable
                ? options.RefreshSeconds
                : WorkloadCredentialOptions.MinimumRefreshSeconds;
            try
            {
                await Task.Delay(TimeSpan.FromSeconds(seconds), stoppingToken);
            }
            catch (OperationCanceledException)
            {
                return;
            }
        }
    }

    public async Task RefreshOnceAsync(CancellationToken cancellationToken)
    {
        try
        {
            var documents = await reader.ReadAsync(cancellationToken);
            var result = identity.Apply(documents.Bundle, documents.TrustBundle);
            if (result.Outcome == "rejected")
                Log(result.Reason == "NO_CREDENTIAL" ? "unissued" : "rejected", result.Reason);
            else if (result.Outcome != "unchanged")
                Log(result.Outcome, null);
        }
        catch (WorkloadCredentialReadException exception)
        {
            Log("read_failed", exception.Code);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            Log("read_failed", exception.GetType().Name);
        }
        var ready = identity.GetStatus().State == "READY";
        if (!ready && _wasReady)
            Log("unavailable", "EXPIRED_OR_REVOKED");
        _wasReady = ready;
        try
        {
            await prober.ProbeAllAsync(cancellationToken);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogWarning(
                "workload_credentials owner_link_probe_failed reason={Reason}",
                exception.GetType().Name
            );
        }
    }

    private void Log(string state, string? reason)
    {
        var status = identity.GetStatus();
        if (state is "loaded" or "refreshed")
            logger.LogInformation(
                "workload_credentials state={State} bundle_version={BundleVersion} remaining_seconds={RemainingSeconds}",
                state,
                status.BundleVersion,
                status.RemainingSeconds
            );
        else
            logger.LogWarning(
                "workload_credentials state={State} reason={Reason} credential={Credential}",
                state,
                reason,
                status.State
            );
    }
}
