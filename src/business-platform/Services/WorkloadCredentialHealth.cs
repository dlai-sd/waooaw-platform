// Implements: ADR-046 sections 5.2, 5.3 and 12.2 D6, D9
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>Non-gating workload credential and owner-link detail; it never reports anything but Healthy.</summary>
public sealed class WorkloadCredentialHealthCheck(
    WorkloadIdentityClient? identity = null,
    OwnerLinkState? owners = null
) : IHealthCheck
{
    public const string DetailTag = "detail";

    public Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default
    )
    {
        var data = new Dictionary<string, object>();
        if (identity is not null)
        {
            var status = identity.GetStatus();
            data["credential_source"] = status.Source;
            data["credential_state"] = status.State;
            if (status.RemainingSeconds is { } remaining)
                data["credential_remaining_seconds"] = remaining;
            if (status.BundleVersion is { } version)
                data["credential_bundle_version"] = version;
            if (status.Source == "keyvault")
                data["owner_links"] = owners?.Snapshot() ?? new Dictionary<string, string>();
        }
        return Task.FromResult(HealthCheckResult.Healthy("non-gating", data));
    }

    public static Task WriteDetailAsync(HttpContext context, HealthReport report)
    {
        var data = report.Entries.TryGetValue("workload-credentials", out var entry)
            ? entry.Data
            : new Dictionary<string, object>();
        return context.Response.WriteAsJsonAsync(
            new { status = report.Status.ToString(), workload_credentials = data }
        );
    }
}
