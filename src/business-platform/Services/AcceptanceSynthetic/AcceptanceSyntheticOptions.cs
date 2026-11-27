// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;

/// <summary>
/// Feature setting acceptance_synthetic_tenants_enabled (platform settings policy S5, S6). Absent means off, and the
/// setting exists only for Demo and UAT: the deployment inputs and the workload module refuse it for Production.
/// </summary>
public sealed class AcceptanceSyntheticOptions
{
    public const string SectionName = "AcceptanceSyntheticTenants";

    public bool Enabled { get; set; }

    /// <summary>Six-digit code a synthetic customer's registration accepts instead of a WhatsApp code (a test fixture, not a secret).</summary>
    public const string DefaultTestVerificationCode = "123456";

    public string TestVerificationCode { get; set; } = DefaultTestVerificationCode;
}

/// <summary>Defence in depth: a Business Platform that knows it is Production refuses to start with the registry on.</summary>
public sealed class AcceptanceSyntheticOptionsValidator(IConfiguration configuration)
    : IValidateOptions<AcceptanceSyntheticOptions>
{
    public ValidateOptionsResult Validate(string? name, AcceptanceSyntheticOptions options) =>
        options.TestVerificationCode.Length != 6
        || !options.TestVerificationCode.All(char.IsAsciiDigit)
            ? ValidateOptionsResult.Fail(
                "AcceptanceSyntheticTenants:TestVerificationCode must be six digits."
            )
        : options.Enabled
        && string.Equals(
            configuration["IdentityEnvironment:Environment"],
            "prod",
            StringComparison.Ordinal
        )
            ? ValidateOptionsResult.Fail(
                "AcceptanceSyntheticTenants:Enabled is not permitted in Production."
            )
        : ValidateOptionsResult.Success;
}
