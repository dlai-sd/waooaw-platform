// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R021
// Constitutional basis: C-023, C-059 (Implementation Traceability), C-063 (Data Minimisation)

using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;

/// <summary>
/// The test code for a synthetic customer's registration. A customer is synthetic only when the server-side registry
/// (written by the role-guarded provisioner route) holds its subject, and only where the synthetic feature is on, which
/// Production refuses. For such a customer no WhatsApp message is sent and no message budget is used; every other
/// customer always gets a real, random, delivered code.
/// </summary>
public interface ISyntheticVerificationCode
{
    Task<string?> CodeForAsync(string issuer, string subject, CancellationToken ct);
}

public sealed class SyntheticVerificationCode(
    ISyntheticAcceptanceRegistry registry,
    IOptions<AcceptanceSyntheticOptions> options
) : ISyntheticVerificationCode
{
    public async Task<string?> CodeForAsync(string issuer, string subject, CancellationToken ct) =>
        options.Value.Enabled && await registry.IsSyntheticActorAsync(issuer, subject, ct)
            ? options.Value.TestVerificationCode
            : null;
}
