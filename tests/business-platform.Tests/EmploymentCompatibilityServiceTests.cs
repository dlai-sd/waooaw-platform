// Implements: WC-115 R020-R022, R072-R075
// Constitutional basis: C-023, C-059, C-063, C-076, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentCompatibilityServiceTests
{
    [Fact(DisplayName = "CEW-FIT-15 missing owner evidence fails closed")]
    public void ExactInventoryStartsUnknownAndCannotActivate()
    {
        var service = new EmploymentCompatibilityService();
        var agents = NeutralAgents();
        var request = new EmploymentCompatibilityRequest(
            "1.0",
            "1.0-candidate",
            "inventory-1",
            EmploymentCompatibilityService.InventoryDigest(agents),
            agents
        );

        var submission = service.Start("platform-admission", Guid.NewGuid(), request);

        Assert.False(submission.Replayed);
        Assert.Equal("UNKNOWN", submission.Result.State);
        Assert.False(submission.Result.InventoryComplete);
        Assert.False(submission.Result.ActivationEligible);
        Assert.All(
            submission.Result.AgentResults,
            item => Assert.Contains("OWNER_UNAVAILABLE", item.ReasonCodes)
        );
    }

    [Fact(DisplayName = "CEW-FIT-16 activation remains separate from compatibility")]
    public void AllAgentPassStillRequiresRollbackEvidence()
    {
        var service = new EmploymentCompatibilityService();
        var agents = NeutralAgents();
        var request = new EmploymentCompatibilityRequest(
            "1.0",
            "1.0-candidate",
            "inventory-1",
            EmploymentCompatibilityService.InventoryDigest(agents),
            agents
        );
        var started = service.Start("platform-admission", Guid.NewGuid(), request);
        var results = agents
            .Select(agent => new EmploymentAgentCompatibilityResult(
                agent.AgentType,
                agent.AgentVersion,
                agent.ManifestVersion,
                agent.DomainAdapterVersion,
                "PASS",
                ["COMPATIBLE"],
                [],
                [$"evidence:{agent.AgentType}"]
            ))
            .ToArray();

        var noRollback = service.Complete(started.Receipt.ScanId, results, false);

        Assert.Equal("PASS", noRollback.State);
        Assert.True(noRollback.InventoryComplete);
        Assert.False(noRollback.ActivationEligible);
        var serviceWithRollback = new EmploymentCompatibilityService();
        var second = serviceWithRollback.Start("platform-admission", Guid.NewGuid(), request);
        Assert.True(
            serviceWithRollback.Complete(second.Receipt.ScanId, results, true).ActivationEligible
        );
    }

    [Fact(DisplayName = "CEW-FIT-01 exact inventory replay preserves one manifest per agent")]
    public void IdenticalScanReplaysAndChangedInventoryConflicts()
    {
        var service = new EmploymentCompatibilityService();
        var agents = NeutralAgents();
        var key = Guid.NewGuid();
        var request = new EmploymentCompatibilityRequest(
            "1.0",
            "1.0-candidate",
            "inventory-1",
            EmploymentCompatibilityService.InventoryDigest(agents),
            agents
        );

        var first = service.Start("platform-admission", key, request);
        var replay = service.Start("platform-admission", key, request);

        Assert.True(replay.Replayed);
        Assert.Equal(first.Receipt.ScanId, replay.Receipt.ScanId);
        var changedAgents = agents.Append(Agent("legal")).ToArray();
        var changed = request with
        {
            Agents = changedAgents,
            OfferedInventoryDigest = EmploymentCompatibilityService.InventoryDigest(changedAgents),
        };
        var error = Assert.Throws<EmploymentProtocolException>(() =>
            service.Start("platform-admission", key, changed)
        );
        Assert.Equal("COMPATIBILITY_CONFLICT", error.Code);
    }

    [Fact(DisplayName = "CEW-NEG-010 mixed mandatory majors fail closed")]
    public void InvalidInventoryDigestAndMixedMajorResultsFailClosed()
    {
        var service = new EmploymentCompatibilityService();
        var agents = NeutralAgents();
        var invalid = new EmploymentCompatibilityRequest(
            "1.0",
            "1.0-candidate",
            "inventory-1",
            new string('f', 64),
            agents
        );
        Assert.Equal(
            "COMPATIBILITY_INVALID",
            Assert
                .Throws<EmploymentProtocolException>(() =>
                    service.Start("platform-admission", Guid.NewGuid(), invalid)
                )
                .Code
        );

        var valid = invalid with
        {
            OfferedInventoryDigest = EmploymentCompatibilityService.InventoryDigest(agents),
        };
        var started = service.Start("platform-admission", Guid.NewGuid(), valid);
        var results = agents
            .Select(
                (agent, index) =>
                    new EmploymentAgentCompatibilityResult(
                        agent.AgentType,
                        agent.AgentVersion,
                        index == 0 ? "2.0.0" : agent.ManifestVersion,
                        agent.DomainAdapterVersion,
                        "PASS",
                        ["COMPATIBLE"],
                        [],
                        [$"evidence:{agent.AgentType}"]
                    )
            )
            .ToArray();

        var completed = service.Complete(started.Receipt.ScanId, results, true);

        Assert.Equal("FAIL", completed.State);
        Assert.False(completed.ActivationEligible);
        Assert.Null(service.Get(Guid.NewGuid()));
    }

    [Theory]
    [InlineData("2.0", "1.0-candidate", "CANDIDATE", "1.0-candidate", false)]
    [InlineData("1.0", "2.0", "CANDIDATE", "2.0", false)]
    [InlineData("1.0", "1.0-candidate", "HIDDEN", "1.0-candidate", false)]
    [InlineData("1.0", "1.0-candidate", "CANDIDATE", "2.0", false)]
    [InlineData("1.0", "1.0-candidate", "CANDIDATE", "1.0-candidate", true)]
    public void InvalidInventoryShapesAreRejected(
        string schemaVersion,
        string protocolVersion,
        string publicationState,
        string declaredProtocolVersion,
        bool emptyInventory
    )
    {
        var service = new EmploymentCompatibilityService();
        var agents = emptyInventory
            ? Array.Empty<OfferedEmploymentAgent>()
            :
            [
                Agent("trading") with
                {
                    PublicationState = publicationState,
                    DeclaredProtocolVersion = declaredProtocolVersion,
                },
            ];
        var request = new EmploymentCompatibilityRequest(
            schemaVersion,
            protocolVersion,
            "inventory-invalid",
            EmploymentCompatibilityService.InventoryDigest(agents),
            agents
        );

        var error = Assert.Throws<EmploymentProtocolException>(() =>
            service.Start("platform-admission", Guid.NewGuid(), request)
        );

        Assert.Equal("COMPATIBILITY_INVALID", error.Code);
    }

    [Fact]
    public void CompletionRequiresKnownScanAndExactInventorySize()
    {
        var service = new EmploymentCompatibilityService();
        var agents = NeutralAgents();
        var request = new EmploymentCompatibilityRequest(
            "1.0",
            "1.0-candidate",
            "inventory-1",
            EmploymentCompatibilityService.InventoryDigest(agents),
            agents
        );
        var started = service.Start("platform-admission", Guid.NewGuid(), request);

        Assert.Equal(
            "COMPATIBILITY_NOT_FOUND",
            Assert
                .Throws<EmploymentProtocolException>(() =>
                    service.Complete(
                        Guid.NewGuid(),
                        Array.Empty<EmploymentAgentCompatibilityResult>(),
                        false
                    )
                )
                .Code
        );
        Assert.Equal(
            "COMPATIBILITY_INVALID",
            Assert
                .Throws<EmploymentProtocolException>(() =>
                    service.Complete(
                        started.Receipt.ScanId,
                        Array.Empty<EmploymentAgentCompatibilityResult>(),
                        false
                    )
                )
                .Code
        );
    }

    private static OfferedEmploymentAgent[] NeutralAgents() =>
        [Agent("digital-marketing"), Agent("trading"), Agent("tutor")];

    private static OfferedEmploymentAgent Agent(string agentType) =>
        new(
            agentType,
            "1.0.0",
            "CANDIDATE",
            "1.0-candidate",
            "1.0.0",
            new string('a', 64),
            "1.0.0",
            new string('b', 64)
        );
}
