// Implements: architecture/reference/product/wc085-identity-architecture-decision.md Current Implementable Contract
// constitutional_basis: C-023, C-026, C-059

using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class CustomerIdentityJourneyService(IdentityService identity,
    IDbContextFactory<IdentityDbContext> factory, GoogleWorkspaceProofAdapter proofAdapter,
    IdentityProviderProjectionService providers)
{
    public bool IsAvailable => proofAdapter.IsConfigured && providers.IsAvailable("GOOGLE");

    public VerifiedCustomerActor ValidateActor(ClaimsPrincipal principal)
    {
        if (!IsAvailable) throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable);
        return proofAdapter.ValidateActor(principal);
    }

    public Task<(IdentityRegistrationRecord reg, bool isNew)> StartAsync(ClaimsPrincipal principal,
        Guid key, string language, CancellationToken ct)
    {
        ValidateActor(principal);
        return identity.StartRegistrationAsync(
            proofAdapter.ValidateActor(principal, requireFresh: true), key,
            CanonicalHash("StartRegistration", null, new { languagePreference = language }), language, ct);
    }

    public Task<IdentityRegistrationRecord> GetAsync(ClaimsPrincipal principal, Guid registrationId, CancellationToken ct) =>
        identity.GetRegistrationAsync(registrationId, ValidateActor(principal), ct);

    public Task<(IdentityRegistrationRecord reg, bool isNew)> UpdateAsync(ClaimsPrincipal principal,
        Guid registrationId, Guid key, string displayName, string businessName, string businessDomain,
        string languagePreference, CancellationToken ct) => identity.UpdateProfileAsync(registrationId,
            ValidateActor(principal), key, CanonicalHash("UpdateProfile", registrationId,
                new { displayName, businessName, businessDomain, languagePreference }),
            displayName, businessName, businessDomain, languagePreference, ct);

    public async Task<CustomerWorkspaceCompletion> CompleteAsync(ClaimsPrincipal principal,
        Guid registrationId, Guid key, CancellationToken ct)
    {
        await GetAsync(principal, registrationId, ct);
        var proof = await proofAdapter.ReadAsync(principal, ct);
        return await Provisioning().CompleteAsync(proof, registrationId, key,
            CanonicalHash("CompleteRegistration", registrationId, new { }), ct);
    }

    public Task<CustomerWorkspaceMembership> ResolveAsync(ClaimsPrincipal principal, CancellationToken ct) =>
        Provisioning().ResolveAsync(ValidateActor(principal), ct);

    private CustomerWorkspaceProvisioningService Provisioning() => new(factory, proofAdapter.Trust);

    public static string CanonicalHash(string operation, Guid? registrationId, object input) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(
            new { operation, registrationId = registrationId?.ToString("D"), input })))).ToLowerInvariant();
}