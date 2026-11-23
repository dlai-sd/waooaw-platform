// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;

namespace Waooaw.BusinessPlatform.Tests.AcceptanceSynthetic;

internal sealed class FakeSyntheticAcceptanceRegistry : ISyntheticAcceptanceRegistry
{
    public List<(string Issuer, string Subject, string RunId, string RegisteredBy)> Subjects { get; } = [];
    public List<(string RunId, string Recipient, string RegisteredBy)> Recipients { get; } = [];
    public List<string> Deactivated { get; } = [];
    public List<(Guid TenantId, string RunId, Guid OutboxId, int Attempt, string Digest)> Suppressions { get; } = [];
    public Dictionary<Guid, string> TenantRuns { get; } = [];
    public HashSet<(string RunId, string Digest)> SandboxRecipients { get; } = [];
    public HashSet<(string Issuer, string Subject)> Actors { get; } = [];
    public SyntheticSubjectRegistration SubjectResult { get; set; } = SyntheticSubjectRegistration.Created;
    public SandboxRecipientRegistration RecipientResult { get; set; } = SandboxRecipientRegistration.Created;
    public bool Fail { get; set; }

    public int Calls => Subjects.Count + Recipients.Count + Deactivated.Count;

    public Task<SyntheticSubjectRegistration> RegisterSubjectAsync(string issuer, string subject, string runId, string registeredBy, CancellationToken ct)
    {
        Subjects.Add((issuer, subject, runId, registeredBy));
        return Task.FromResult(SubjectResult);
    }

    public Task<SandboxRecipientRegistration> RegisterSandboxRecipientAsync(string runId, string recipient, string registeredBy, CancellationToken ct)
    {
        Recipients.Add((runId, recipient, registeredBy));
        return Task.FromResult(RecipientResult);
    }

    public Task<SyntheticRunDeactivation> DeactivateRunAsync(string runId, CancellationToken ct)
    {
        Deactivated.Add(runId);
        return Task.FromResult(new SyntheticRunDeactivation(2, 1));
    }

    public Task<bool> IsSyntheticActorAsync(string issuer, string subject, CancellationToken ct) =>
        Fail ? throw new InvalidOperationException("registry down") : Task.FromResult(Actors.Contains((issuer, subject)));

    public Task<string?> FindTenantRunAsync(Guid tenantId, CancellationToken ct) =>
        Task.FromResult(TenantRuns.GetValueOrDefault(tenantId));

    public Task<bool> IsSandboxRecipientAsync(string runId, string recipientDigest, CancellationToken ct) =>
        Task.FromResult(SandboxRecipients.Contains((runId, recipientDigest)));

    public Task RecordSuppressionAsync(Guid tenantId, string runId, Guid outboxId, int attemptNumber, string recipientDigest, CancellationToken ct)
    {
        Suppressions.Add((tenantId, runId, outboxId, attemptNumber, recipientDigest));
        return Task.CompletedTask;
    }
}
