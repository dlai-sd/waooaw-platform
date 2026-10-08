// Implements: architecture/reference/components/conversational-employment-solution-contract.md §12 Rollout And Rollback
// Constitutional basis: C-001, C-059, C-065, C-076, ADR-051
// IB: N/A - Founder-assigned WC-115

using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentProtocolGateTests
{
    [Fact]
    public void DefaultOptionsKeepCandidateDisabled()
    {
        var gate = new EmploymentProtocolGate(Options.Create(new EmploymentProtocolOptions()));

        var snapshot = gate.Snapshot();

        Assert.Equal(EmploymentProtocolOptions.ExpectedGateId, snapshot.GateId);
        Assert.False(snapshot.Enabled);
        Assert.Equal(0, snapshot.RollbackEpoch);
    }

    [Fact]
    public void ValidatorRejectsUnknownGateIdentity()
    {
        var result = new EmploymentProtocolOptionsValidator().Validate(
            null,
            new EmploymentProtocolOptions { GateId = "unapproved-gate" }
        );

        Assert.True(result.Failed);
    }

    [Fact]
    public void ValidatorRejectsNegativeRollbackEpoch()
    {
        var result = new EmploymentProtocolOptionsValidator().Validate(
            null,
            new EmploymentProtocolOptions { RollbackEpoch = -1 }
        );

        Assert.True(result.Failed);
    }

    [Fact]
    public void ValidatorAcceptsExactEnabledCandidateGate()
    {
        var result = new EmploymentProtocolOptionsValidator().Validate(
            null,
            new EmploymentProtocolOptions
            {
                GateId = EmploymentProtocolOptions.ExpectedGateId,
                Enabled = true,
                RollbackEpoch = 2,
            }
        );
        var gate = new EmploymentProtocolGate(
            Options.Create(new EmploymentProtocolOptions { Enabled = true, RollbackEpoch = 2 })
        );

        Assert.False(result.Failed);
        Assert.True(gate.Snapshot().Enabled);
        Assert.Equal(2, gate.Snapshot().RollbackEpoch);
    }
}
