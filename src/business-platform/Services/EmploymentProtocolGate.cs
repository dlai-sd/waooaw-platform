// Implements: architecture/reference/components/conversational-employment-solution-contract.md §12 Rollout And Rollback
// Constitutional basis: C-001, C-023, C-059, C-065, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services;

public sealed class EmploymentProtocolOptions
{
    public const string ExpectedGateId = "conversational-employment-candidate-v1";

    public string GateId { get; init; } = ExpectedGateId;
    public bool Enabled { get; init; }
    public long RollbackEpoch { get; init; }
}

public sealed record EmploymentProtocolGateSnapshot(
    string GateId,
    bool Enabled,
    long RollbackEpoch
);

public interface IEmploymentProtocolGate
{
    EmploymentProtocolGateSnapshot Snapshot();
}

public sealed class EmploymentProtocolOptionsValidator : IValidateOptions<EmploymentProtocolOptions>
{
    public ValidateOptionsResult Validate(string? name, EmploymentProtocolOptions options)
    {
        if (
            !string.Equals(
                options.GateId,
                EmploymentProtocolOptions.ExpectedGateId,
                StringComparison.Ordinal
            )
        )
            return ValidateOptionsResult.Fail(
                "Employment protocol gate identifier is not approved."
            );
        if (options.RollbackEpoch < 0)
            return ValidateOptionsResult.Fail(
                "Employment protocol rollback epoch cannot be negative."
            );
        return ValidateOptionsResult.Success;
    }
}

public sealed class EmploymentProtocolGate(IOptions<EmploymentProtocolOptions> options)
    : IEmploymentProtocolGate
{
    private readonly EmploymentProtocolGateSnapshot _snapshot = new(
        options.Value.GateId,
        options.Value.Enabled,
        options.Value.RollbackEpoch
    );

    public EmploymentProtocolGateSnapshot Snapshot() => _snapshot;
}
