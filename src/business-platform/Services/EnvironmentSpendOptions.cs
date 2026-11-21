// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-01
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-06
// Constitutional basis: C-023, C-059, C-063

using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services;

public sealed class EnvironmentSpendOptions
{
    public const string SectionName = "EnvironmentSpend";
    public const string GlobalLockMode = "GLOBAL_LOCK";
    public const string LeasesMode = "LEASES";
    public const decimal DefaultHardMaximumInr = 500;
    public const decimal MaximumConfigurableInr = 999_999_999_999m;
    public const int MinimumLeaseSeconds = 5;
    public const int MaximumLeaseSeconds = 3_600;

    public decimal HardMaximumInr { get; set; } = DefaultHardMaximumInr;
    public decimal LeaseSizeInr { get; set; } = 25;
    public int LeaseSeconds { get; set; } = 120;
    public string Mode { get; set; } = GlobalLockMode;

    public bool UsesLeases => string.Equals(Mode, LeasesMode, StringComparison.Ordinal);

    public long LeaseSizePaise => checked((long)(LeaseSizeInr * 100m));

    public TimeSpan LeaseDuration => TimeSpan.FromSeconds(LeaseSeconds);

    public decimal EffectiveMaximumInr(decimal authorityMaximumSpendInr) =>
        Math.Min(HardMaximumInr, authorityMaximumSpendInr);

    public long EffectiveMaximumPaise(decimal authorityMaximumSpendInr) =>
        checked((long)(EffectiveMaximumInr(authorityMaximumSpendInr) * 100m));
}

public sealed class EnvironmentSpendOptionsValidator : IValidateOptions<EnvironmentSpendOptions>
{
    public ValidateOptionsResult Validate(string? name, EnvironmentSpendOptions options)
    {
        var errors = new List<string>();
        if (!IsPositiveAmount(options.HardMaximumInr, 2))
            errors.Add(
                "EnvironmentSpend:HardMaximumInr must be greater than 0, at most 999999999999 and a whole number of paise."
            );
        if (
            !IsPositiveAmount(options.LeaseSizeInr, 2)
            || options.LeaseSizeInr > options.HardMaximumInr
        )
            errors.Add(
                "EnvironmentSpend:LeaseSizeInr must be greater than 0, a whole number of paise and not above HardMaximumInr."
            );
        if (
            options.LeaseSeconds
            is < EnvironmentSpendOptions.MinimumLeaseSeconds
                or > EnvironmentSpendOptions.MaximumLeaseSeconds
        )
            errors.Add("EnvironmentSpend:LeaseSeconds must be between 5 and 3600.");
        if (
            options.Mode
            is not (EnvironmentSpendOptions.GlobalLockMode or EnvironmentSpendOptions.LeasesMode)
        )
            errors.Add("EnvironmentSpend:Mode must be GLOBAL_LOCK or LEASES.");
        return errors.Count == 0
            ? ValidateOptionsResult.Success
            : ValidateOptionsResult.Fail(errors);
    }

    private static bool IsPositiveAmount(decimal value, int decimalPlaces) =>
        value > 0
        && value <= EnvironmentSpendOptions.MaximumConfigurableInr
        && decimal.Round(value, decimalPlaces) == value;
}
