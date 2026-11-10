// Implements: WC-134 R005; recognition never grants account or relationship authority.
// constitutional_basis: C-023, C-026, C-059, C-063

using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public interface IWhatsAppRegistrationRecognition
{
    Task<bool> IsVerifiedRegistrationAsync(string phoneNumber, CancellationToken ct);
}

public sealed partial class WhatsAppRegistrationRecognition(
    IdentityService identity,
    IDbContextFactory<IdentityDbContext> factory
) : IWhatsAppRegistrationRecognition
{
    public async Task<bool> IsVerifiedRegistrationAsync(string phoneNumber, CancellationToken ct)
    {
        if (!Phone().IsMatch(phoneNumber))
            throw new WhatsAppWebhookException(403, "PHONE_IDENTITY_PROOF_INVALID");
        var candidates = identity.ComputeMatchCandidates("mobile", phoneNumber);
        var versions = candidates.Keys.ToArray();
        var digests = candidates.Values.ToArray();
        await using var db = await factory.CreateDbContextAsync(ct);
        return await db
            .Database.SqlQuery<bool>(
                $"SELECT identity.has_verified_whatsapp_registration({versions}, {digests}) AS \"Value\""
            )
            .SingleAsync(ct);
    }

    [GeneratedRegex("\\A\\+[1-9][0-9]{7,14}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Phone();
}
