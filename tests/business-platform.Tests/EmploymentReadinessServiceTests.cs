// Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R001, WC170-R002
// Constitutional basis: C-023, C-049, C-059, C-076
// IB: IB-170

using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentReadinessServiceTests
{
    private static readonly OfferableProfessionalVersion Dma = new(
        "digital-marketing",
        "1.0.0",
        "sha256:abc",
        "Digital Marketing",
        [],
        []
    );

    [Fact]
    public async Task EveryFactReadyMeansReady()
    {
        var report = await Service(new Sources()).ReportAsync(CancellationToken.None);

        Assert.True(report.Ready);
        Assert.All(report.Checks, check => Assert.Equal("READY", check.State));
        Assert.Equal(6, report.Checks.Count);
    }

    [Fact]
    public async Task EveryMissIsANamedBlockedByFlagReason()
    {
        var sources = new Sources
        {
            Offerable = [],
            ModelKey = false,
            Replicas = { ["ai-runtime"] = false },
        };

        var report = await Service(sources, enabled: false).ReportAsync(CancellationToken.None);

        Assert.False(report.Ready);
        var reasons = report.Checks.ToDictionary(check => check.Id, check => check.Reason);
        Assert.Equal("EMPLOYMENT_PROTOCOL_DISABLED", reasons["PROTOCOL_GATE"]);
        Assert.Equal("AGENT_NOT_ADMITTED", reasons["AGENT_ADMISSION"]);
        Assert.Equal("MODEL_KEY_NOT_CONFIGURED", reasons["MODEL_KEY"]);
        Assert.Equal("AI_CAPACITY_NOT_READY", reasons["AI_CAPACITY"]);
        Assert.All(
            report.Checks.Where(check => check.Reason is not null),
            check => Assert.Equal("BLOCKED-BY-FLAG", check.State)
        );
    }

    [Fact]
    public async Task AFactThatCannotBeReadIsBlockedNeverAssumedReady()
    {
        var sources = new Sources { Throw = true };

        var report = await Service(sources).ReportAsync(CancellationToken.None);

        Assert.False(report.Ready);
        Assert.Equal(
            "MODEL_KEY_UNREADABLE",
            report.Checks.Single(check => check.Id == "MODEL_KEY").Reason
        );
        Assert.Equal(
            "RUNTIME_CAPACITY_UNREADABLE",
            report.Checks.Single(check => check.Id == "RUNTIME_CAPACITY").Reason
        );
    }

    [Fact]
    public async Task TheReportCarriesTheEpochAndNoCredentialValue()
    {
        var report = await Service(new Sources(), epoch: 7).ReportAsync(CancellationToken.None);

        Assert.Equal(7, report.RollbackEpoch);
        Assert.DoesNotContain(
            "key",
            System.Text.Json.JsonSerializer.Serialize(report.Checks.Select(c => c.Reason)),
            StringComparison.OrdinalIgnoreCase
        );
    }

    private static EmploymentReadinessService Service(
        Sources sources,
        bool enabled = true,
        long epoch = 0
    ) => new(new Gate(enabled, epoch), sources, Options.Create(new EmploymentReadinessOptions()));

    private sealed class Gate(bool enabled, long epoch) : IEmploymentProtocolGate
    {
        public EmploymentProtocolGateSnapshot Snapshot() =>
            new(EmploymentProtocolOptions.ExpectedGateId, enabled, epoch);
    }

    private sealed class Sources : IEmploymentReadinessSources
    {
        public IReadOnlyList<OfferableProfessionalVersion> Offerable { get; init; } = [Dma];
        public bool ModelKey { get; init; } = true;
        public bool Throw { get; init; }
        public Dictionary<string, bool> Replicas { get; } = new();

        public Task<IReadOnlyList<OfferableProfessionalVersion>> OfferableAsync(
            string environment,
            CancellationToken cancellationToken
        ) => Throw ? throw new InvalidOperationException("down") : Task.FromResult(Offerable);

        public Task<bool> ModelKeyConfiguredAsync(CancellationToken cancellationToken) =>
            Throw ? throw new InvalidOperationException("down") : Task.FromResult(ModelKey);

        public Task<bool> ReplicaReadyAsync(
            string component,
            CancellationToken cancellationToken
        ) =>
            Throw
                ? throw new InvalidOperationException("down")
                : Task.FromResult(Replicas.GetValueOrDefault(component, true));
    }
}
