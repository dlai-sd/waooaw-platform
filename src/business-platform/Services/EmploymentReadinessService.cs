// Implements: architecture/reference/product/ae02-real-work-solution-contract.md section 2 Activation contract (WC170-R001, WC170-R002)
// Constitutional basis: C-023, C-049, C-059, C-063
// IB: IB-170

using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services;

public sealed class EmploymentReadinessOptions
{
    public const string SectionName = "EmploymentReadiness";

    public string Environment { get; init; } = "demo";
    public string ProfessionalTypeId { get; init; } = "digital-marketing";
    public string ProfessionalRuntimeUrl { get; init; } = "";
    public string AiRuntimeUrl { get; init; } = "";
    public string DomainAdapterUrl { get; init; } = "";
}

/// <summary>One readiness fact. State is READY or BLOCKED-BY-FLAG; a fact that cannot be read is BLOCKED-BY-FLAG, never READY.</summary>
public sealed record EmploymentReadinessCheck(string Id, string State, string? Reason);

public sealed record EmploymentReadinessReport(
    string SchemaVersion,
    string GateId,
    bool Enabled,
    long RollbackEpoch,
    bool Ready,
    IReadOnlyList<EmploymentReadinessCheck> Checks,
    DateTimeOffset ObservedAt
);

public interface IEmploymentReadinessSources
{
    Task<IReadOnlyList<OfferableProfessionalVersion>> OfferableAsync(
        string environment,
        CancellationToken cancellationToken
    );

    /// <summary>True when an active credential exists for a platform model provider. The value is never read.</summary>
    Task<bool> ModelKeyConfiguredAsync(CancellationToken cancellationToken);

    Task<bool> ReplicaReadyAsync(string component, CancellationToken cancellationToken);
}

public sealed class EmploymentReadinessService(
    IEmploymentProtocolGate gate,
    IEmploymentReadinessSources sources,
    IOptions<EmploymentReadinessOptions> options,
    TimeProvider? clock = null
)
{
    public const string Ready = "READY";
    public const string Blocked = "BLOCKED-BY-FLAG";

    public async Task<EmploymentReadinessReport> ReportAsync(CancellationToken cancellationToken)
    {
        var settings = options.Value;
        var snapshot = gate.Snapshot();
        var checks = new List<EmploymentReadinessCheck>
        {
            snapshot.Enabled
                ? new("PROTOCOL_GATE", Ready, null)
                : new("PROTOCOL_GATE", Blocked, "EMPLOYMENT_PROTOCOL_DISABLED"),
            await Guard(
                "AGENT_ADMISSION",
                "AGENT_ADMISSION_UNREADABLE",
                async () =>
                {
                    var offerable = await sources.OfferableAsync(
                        settings.Environment,
                        cancellationToken
                    );
                    return offerable.Any(item =>
                        string.Equals(
                            item.ProfessionalTypeId,
                            settings.ProfessionalTypeId,
                            StringComparison.Ordinal
                        ) && !string.IsNullOrWhiteSpace(item.AdmissionContentDigest)
                    )
                        ? null
                        : "AGENT_NOT_ADMITTED";
                }
            ),
            await Guard(
                "MODEL_KEY",
                "MODEL_KEY_UNREADABLE",
                async () =>
                    await sources.ModelKeyConfiguredAsync(cancellationToken)
                        ? null
                        : "MODEL_KEY_NOT_CONFIGURED"
            ),
        };
        foreach (
            var (id, component) in new[]
            {
                ("RUNTIME_CAPACITY", "professional-runtime"),
                ("AI_CAPACITY", "ai-runtime"),
                ("AGENT_CAPACITY", "domain-adapter"),
            }
        )
            checks.Add(
                await Guard(
                    id,
                    $"{id}_UNREADABLE",
                    async () =>
                        await sources.ReplicaReadyAsync(component, cancellationToken)
                            ? null
                            : $"{id}_NOT_READY"
                )
            );
        return new EmploymentReadinessReport(
            "1.0",
            snapshot.GateId,
            snapshot.Enabled,
            snapshot.RollbackEpoch,
            checks.All(check => check.State == Ready),
            checks,
            (clock ?? TimeProvider.System).GetUtcNow()
        );
    }

    private static async Task<EmploymentReadinessCheck> Guard(
        string id,
        string unreadableReason,
        Func<Task<string?>> reasonOrNull
    )
    {
        try
        {
            var reason = await reasonOrNull();
            return reason is null ? new(id, Ready, null) : new(id, Blocked, reason);
        }
        catch (Exception error) when (error is not OperationCanceledException)
        {
            return new(id, Blocked, unreadableReason);
        }
    }
}

public sealed class EmploymentReadinessSources(
    AgentAdmissionService admissions,
    IProviderCredentialAdminService providers,
    IHttpClientFactory httpClients,
    IOptions<EmploymentReadinessOptions> options
) : IEmploymentReadinessSources
{
    public Task<IReadOnlyList<OfferableProfessionalVersion>> OfferableAsync(
        string environment,
        CancellationToken cancellationToken
    ) => admissions.GetOfferableAsync(environment, cancellationToken);

    public async Task<bool> ModelKeyConfiguredAsync(CancellationToken cancellationToken)
    {
        var all = await providers.ListAsync(cancellationToken);
        return all.Any(provider =>
            provider.Active
            && provider.Category == "PLATFORM_LLM"
            && provider.Credential.ActiveVersionNo is not null
        );
    }

    public async Task<bool> ReplicaReadyAsync(string component, CancellationToken cancellationToken)
    {
        var settings = options.Value;
        var baseUrl = component switch
        {
            "professional-runtime" => settings.ProfessionalRuntimeUrl,
            "ai-runtime" => settings.AiRuntimeUrl,
            "domain-adapter" => settings.DomainAdapterUrl,
            _ => "",
        };
        if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri))
            return false;
        using var client = httpClients.CreateClient("employment-readiness");
        client.Timeout = TimeSpan.FromSeconds(3);
        using var response = await client.GetAsync(new Uri(uri, "/health"), cancellationToken);
        return response.IsSuccessStatusCode;
    }
}
