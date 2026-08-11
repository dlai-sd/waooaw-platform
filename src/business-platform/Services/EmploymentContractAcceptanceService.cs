// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-03
// constitutional_basis: C-009, C-010, C-011, C-023, C-026, C-059

using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public static class ContractScopeConfirmation
{
    public const string ExplicitStatement = "I_CONFIRM_THE_ACCEPTED_DECISION_SPACE_AND_AUTHORITY_SCOPE";
}

public sealed record ContractPortalAssurance(bool IsKeycloakPortal, DateTimeOffset AuthenticatedAt);

public sealed record ContractAcceptanceResult(ContractAcceptance Acceptance, bool Created);

public sealed class ContractStepUpRequiredException(string reason) : Exception(reason);
public sealed class ContractScopeConfirmationRequiredException()
    : Exception("Separate authority-scope confirmation is required.");
public sealed class ContractIdentityMismatchException()
    : Exception("The presented contract identity does not match.");

public sealed class EmploymentContractAcceptanceService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IRelationshipConstitutionalGateway constitutionalGateway)
{
    private static readonly TimeSpan FreshnessWindow = TimeSpan.FromMinutes(5);
    private static readonly TimeSpan FutureClockSkew = TimeSpan.FromSeconds(30);

    public async Task<ContractAcceptanceResult> AcceptAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        Guid contractId,
        int contractVersion,
        string contractHash,
        string scopeConfirmation,
        ContractPortalAssurance assurance,
        Guid correlationId,
        CancellationToken cancellationToken)
    {
        EnforcePortalAssurance(assurance);
        if (!string.Equals(
                scopeConfirmation,
                ContractScopeConfirmation.ExplicitStatement,
                StringComparison.Ordinal))
        {
            throw new ContractScopeConfirmationRequiredException();
        }

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Relationship not found.");
        var hasEmployerAuthority = await db.RelationshipParticipants.AnyAsync(
            item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && item.ParticipantId == participantId
                && item.Role == RelationshipParticipantRole.Employer
                && item.Status == "ACTIVE",
            cancellationToken);
        if (!hasEmployerAuthority)
        {
            throw new ConstitutionalActionDeniedException(
                "Contract acceptance requires an active same-tenant EMPLOYER binding.");
        }

        var contract = await db.EmploymentContractVersions.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && item.ContractId == contractId
                && item.Version == contractVersion
                && item.ContractHash == contractHash
                && item.State == "PRESENTED",
            cancellationToken) ?? throw new ContractIdentityMismatchException();
        var authoritySnapshot = await db.DecisionSpaceSnapshots.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .OrderByDescending(item => item.Version)
            .FirstOrDefaultAsync(cancellationToken)
            ?? throw new InvalidOperationException("Accepted authority scope is unavailable.");
        var scopeConfirmationHash = Hash(
            $"{contract.ContractId:D}|{contract.Version}|{contract.ContractHash}|{authoritySnapshot.SnapshotId:D}|{ContractScopeConfirmation.ExplicitStatement}");
        var existing = await db.ContractAcceptances.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && item.ContractId == contractId,
            cancellationToken);
        if (existing is not null)
        {
            if (existing.ParticipantId != participantId
                || existing.ContractVersion != contractVersion
                || existing.ContractHash != contractHash
                || existing.AuthoritySnapshotId != authoritySnapshot.SnapshotId
                || existing.ScopeConfirmationHash != scopeConfirmationHash)
            {
                throw new ConstitutionalActionDeniedException("The contract already has a different effective acceptance.");
            }

            return new ContractAcceptanceResult(existing, false);
        }

        if (relationship.State != EmploymentRelationshipState.ContractPendingAcceptance)
        {
            throw new IllegalRelationshipTransitionException(
                relationship.State,
                EmploymentRelationshipState.ContractAcceptedPendingPayment);
        }

        var evidenceId = await constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "ACCEPT_EMPLOYMENT_CONTRACT",
            correlationId,
            new
            {
                contract_id = contract.ContractId,
                contract_version = contract.Version,
                contract_hash = contract.ContractHash,
                participant_id = participantId,
                participant_role = "EMPLOYER",
                authentication_assurance = "AAL3_FRESH",
                authority_snapshot_id = authoritySnapshot.SnapshotId,
                scope_confirmation_hash = scopeConfirmationHash,
            },
            cancellationToken);
        var acceptedAt = DateTimeOffset.UtcNow;
        var acceptance = new ContractAcceptance
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ContractId = contract.ContractId,
            ContractVersion = contract.Version,
            ContractHash = contract.ContractHash,
            ParticipantId = participantId,
            ParticipantRole = RelationshipParticipantRole.Employer,
            AuthenticationAssurance = "AAL3_FRESH",
            AuthoritySnapshotId = authoritySnapshot.SnapshotId,
            ScopeConfirmationHash = scopeConfirmationHash,
            AcceptanceEvidenceId = evidenceId,
            AcceptedAt = acceptedAt,
        };
        relationship.State = EmploymentRelationshipState.ContractAcceptedPendingPayment;
        relationship.StateVersion += 1;
        relationship.AcceptedContractId = contract.ContractId;
        relationship.AuthoritySnapshotId = authoritySnapshot.SnapshotId;
        relationship.UpdatedAt = acceptedAt;
        db.ContractAcceptances.Add(acceptance);
        db.RelationshipStateHistory.Add(new RelationshipStateHistory
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            StateVersion = relationship.StateVersion,
            FromState = EmploymentRelationshipState.ContractPendingAcceptance,
            ToState = EmploymentRelationshipState.ContractAcceptedPendingPayment,
            ActorParticipantId = participantId,
            ActorRole = RelationshipParticipantRole.Employer,
            AuthoritySnapshotId = authoritySnapshot.SnapshotId,
            CorrelationId = correlationId,
            EvidenceId = evidenceId,
            OccurredAt = acceptedAt,
        });
        await db.SaveChangesAsync(cancellationToken);
        return new ContractAcceptanceResult(acceptance, true);
    }

    private static void EnforcePortalAssurance(ContractPortalAssurance assurance)
    {
        var age = DateTimeOffset.UtcNow - assurance.AuthenticatedAt;
        if (!assurance.IsKeycloakPortal || age > FreshnessWindow || age < -FutureClockSkew)
        {
            throw new ContractStepUpRequiredException(
                "Fresh Keycloak portal authentication is required for contract acceptance.");
        }
    }

    private static string Hash(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}