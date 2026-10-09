// Implements: architecture/reference/components/conversational-employment-solution-contract.md §4.8 Compatibility scan
// Constitutional basis: C-023, C-059, C-063, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public sealed record OfferedEmploymentAgent(
    string AgentType,
    string AgentVersion,
    string PublicationState,
    string DeclaredProtocolVersion,
    string ManifestVersion,
    string ManifestDigest,
    string DomainAdapterVersion,
    string DomainAdapterDigest
);

public sealed record EmploymentCompatibilityRequest(
    string SchemaVersion,
    string RequiredProtocolVersion,
    string OfferedInventoryVersion,
    string OfferedInventoryDigest,
    IReadOnlyList<OfferedEmploymentAgent> Agents
);

public sealed record EmploymentCompatibilityReceipt(
    string SchemaVersion,
    Guid ScanId,
    string State,
    string RequiredProtocolVersion,
    string OfferedInventoryVersion,
    string OfferedInventoryDigest,
    DateTimeOffset AcceptedAt,
    string ReconciliationUri
);

public sealed record EmploymentAgentCompatibilityResult(
    string AgentType,
    string AgentVersion,
    string ManifestVersion,
    string DomainAdapterVersion,
    string State,
    IReadOnlyList<string> ReasonCodes,
    IReadOnlyList<string> UnresolvedRefs,
    IReadOnlyList<string> EvidenceRefs
);

public sealed record EmploymentCompatibilityResult(
    string SchemaVersion,
    Guid ScanId,
    string State,
    string RequiredProtocolVersion,
    string OfferedInventoryVersion,
    string OfferedInventoryDigest,
    IReadOnlyList<EmploymentAgentCompatibilityResult> AgentResults,
    bool InventoryComplete,
    bool ActivationEligible,
    bool RollbackSafe,
    DateTimeOffset? CompletedAt,
    DateTimeOffset ObservedAt
);

public sealed record EmploymentCompatibilitySubmission(
    EmploymentCompatibilityReceipt Receipt,
    EmploymentCompatibilityResult Result,
    bool Replayed
);

public sealed class EmploymentCompatibilityService
{
    private readonly Dictionary<
        (string Caller, Guid IdempotencyKey),
        (string Digest, Guid ScanId)
    > _idempotency = new();
    private readonly Dictionary<Guid, EmploymentCompatibilityResult> _results = new();
    private readonly object _sync = new();

    public EmploymentCompatibilitySubmission Start(
        string caller,
        Guid idempotencyKey,
        EmploymentCompatibilityRequest request
    )
    {
        Validate(request);
        var digest = RequestDigest(request);
        lock (_sync)
        {
            var identity = (caller, idempotencyKey);
            if (_idempotency.TryGetValue(identity, out var existing))
            {
                if (!string.Equals(existing.Digest, digest, StringComparison.Ordinal))
                    throw new EmploymentProtocolException("COMPATIBILITY_CONFLICT");
                var replayed = _results[existing.ScanId];
                return new EmploymentCompatibilitySubmission(
                    Receipt(replayed, replayed.ObservedAt),
                    replayed,
                    true
                );
            }
            var scanId = Guid.NewGuid();
            var acceptedAt = DateTimeOffset.UtcNow;
            var agentResults = request
                .Agents.Select(agent => new EmploymentAgentCompatibilityResult(
                    agent.AgentType,
                    agent.AgentVersion,
                    agent.ManifestVersion,
                    agent.DomainAdapterVersion,
                    "UNKNOWN",
                    ["OWNER_UNAVAILABLE"],
                    [$"manifest:{agent.AgentType}:{agent.AgentVersion}"],
                    []
                ))
                .ToArray();
            var result = new EmploymentCompatibilityResult(
                "1.0",
                scanId,
                "UNKNOWN",
                request.RequiredProtocolVersion,
                request.OfferedInventoryVersion,
                request.OfferedInventoryDigest,
                agentResults,
                false,
                false,
                false,
                null,
                acceptedAt
            );
            _results[scanId] = result;
            _idempotency[identity] = (digest, scanId);
            return new EmploymentCompatibilitySubmission(
                Receipt(result, acceptedAt),
                result,
                false
            );
        }
    }

    public EmploymentCompatibilityResult? Get(Guid scanId)
    {
        lock (_sync)
            return _results.GetValueOrDefault(scanId);
    }

    public EmploymentCompatibilityResult Complete(
        Guid scanId,
        IReadOnlyList<EmploymentAgentCompatibilityResult> agentResults,
        bool rollbackSafe
    )
    {
        lock (_sync)
        {
            if (!_results.TryGetValue(scanId, out var current))
                throw new EmploymentProtocolException("COMPATIBILITY_NOT_FOUND");
            if (agentResults.Count != current.AgentResults.Count)
                throw new EmploymentProtocolException("COMPATIBILITY_INVALID");
            var inventoryComplete = agentResults.All(item => item.State is "PASS" or "FAIL");
            var allPass =
                inventoryComplete
                && agentResults.All(item =>
                    item.State == "PASS"
                    && item.ReasonCodes.SequenceEqual(["COMPATIBLE"])
                    && item.EvidenceRefs.Count > 0
                );
            var majorVersions = agentResults
                .Select(item => item.ManifestVersion.Split('.')[0])
                .ToHashSet(StringComparer.Ordinal);
            if (majorVersions.Count > 1)
                allPass = false;
            var now = DateTimeOffset.UtcNow;
            var completed = current with
            {
                State = allPass ? "PASS" : "FAIL",
                AgentResults = agentResults,
                InventoryComplete = inventoryComplete,
                ActivationEligible = allPass && rollbackSafe,
                RollbackSafe = rollbackSafe,
                CompletedAt = now,
                ObservedAt = now,
            };
            _results[scanId] = completed;
            return completed;
        }
    }

    private static EmploymentCompatibilityReceipt Receipt(
        EmploymentCompatibilityResult result,
        DateTimeOffset acceptedAt
    ) =>
        new(
            "1.0",
            result.ScanId,
            result.State is "PASS" or "FAIL" ? "RUNNING" : "ACCEPTED",
            result.RequiredProtocolVersion,
            result.OfferedInventoryVersion,
            result.OfferedInventoryDigest,
            acceptedAt,
            $"/internal/v1/employment-interface/compatibility-scans/{result.ScanId}"
        );

    private static void Validate(EmploymentCompatibilityRequest request)
    {
        if (
            request.SchemaVersion != "1.0"
            || request.RequiredProtocolVersion != "1.0-candidate"
            || request.Agents.Count == 0
            || request.Agents.Any(agent =>
                agent.DeclaredProtocolVersion != request.RequiredProtocolVersion
                || agent.PublicationState is not ("OFFERED" or "CANDIDATE")
            )
            || !string.Equals(
                request.OfferedInventoryDigest,
                InventoryDigest(request.Agents),
                StringComparison.Ordinal
            )
        )
            throw new EmploymentProtocolException("COMPATIBILITY_INVALID");
    }

    public static string InventoryDigest(IReadOnlyList<OfferedEmploymentAgent> agents)
    {
        var canonical = JsonSerializer.Serialize(
            agents
                .OrderBy(item => item.AgentType, StringComparer.Ordinal)
                .ThenBy(item => item.AgentVersion, StringComparer.Ordinal),
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        return Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(canonical)));
    }

    private static string RequestDigest(EmploymentCompatibilityRequest request)
    {
        var canonical = JsonSerializer.Serialize(
            request,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        return Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(canonical)));
    }
}
