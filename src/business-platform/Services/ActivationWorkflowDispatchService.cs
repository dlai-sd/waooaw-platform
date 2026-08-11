// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-05
// constitutional_basis: C-002, C-023, C-026, C-059, C-088

using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Temporalio.Client;
using Temporalio.Exceptions;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Workflows;

namespace Waooaw.BusinessPlatform.Services;

public sealed record StartPaidActivationRequest(string PaymentReference, Guid PaymentEvidenceId);

public interface IActivationWorkflowStarter
{
    Task<ActivationOutcome> StartOrJoinAsync(ActivationRequest request, CancellationToken cancellationToken);
}

public sealed class TemporalActivationWorkflowStarter(ITemporalClient temporalClient) : IActivationWorkflowStarter
{
    public async Task<ActivationOutcome> StartOrJoinAsync(
        ActivationRequest request, CancellationToken cancellationToken)
    {
        var workflowId = ActivationWorkflow.WorkflowIdFor(request);
        try
        {
            var handle = await temporalClient.StartWorkflowAsync(
                (ActivationWorkflow workflow) => workflow.RunAsync(request),
                new WorkflowOptions(workflowId, "bp-trial-worker"));
            return await handle.GetResultAsync<ActivationOutcome>();
        }
        catch (WorkflowAlreadyStartedException)
        {
            return await temporalClient.GetWorkflowHandle(workflowId).GetResultAsync<ActivationOutcome>();
        }
    }
}

public sealed class ActivationWorkflowDispatchService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IActivationWorkflowStarter workflowStarter)
{
    public async Task<ActivationOutcome> StartAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        StartPaidActivationRequest request,
        ContractPortalAssurance assurance,
        CancellationToken cancellationToken)
    {
        var authenticationAge = DateTimeOffset.UtcNow - assurance.AuthenticatedAt;
        if (!assurance.IsKeycloakPortal || authenticationAge > TimeSpan.FromMinutes(5)
            || authenticationAge < TimeSpan.FromSeconds(-30))
            throw new PaymentStepUpRequiredException();
        if (string.IsNullOrWhiteSpace(request.PaymentReference) || request.PaymentEvidenceId == Guid.Empty)
            throw new ActivationEligibilityException("Captured payment evidence is required for activation.");

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken) ?? throw new ActivationEligibilityException("Relationship not found.");
        if (relationship.State is not (EmploymentRelationshipState.ContractAcceptedPendingPayment
                or EmploymentRelationshipState.ActivationPending)
            || !relationship.AcceptedContractId.HasValue || !relationship.AuthoritySnapshotId.HasValue)
            throw new ActivationEligibilityException("Relationship is not eligible for paid activation.");
        var employer = await db.RelationshipParticipants.AsNoTracking().AnyAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ParticipantId == participantId && item.Role == RelationshipParticipantRole.Employer
                && item.Status == "ACTIVE", cancellationToken);
        if (!employer)
            throw new ConstitutionalActionDeniedException("Activation requires an active same-tenant EMPLOYER binding.");
        var acceptance = await db.ContractAcceptances.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ContractId == relationship.AcceptedContractId,
            cancellationToken) ?? throw new ActivationEligibilityException("Exact contract acceptance is required for activation.");

        var activation = new ActivationRequest(
            tenantId,
            relationshipId,
            participantId,
            relationship.AcceptedContractId.Value,
            acceptance.AcceptanceId,
            request.PaymentReference.Trim(),
            request.PaymentEvidenceId,
            relationship.AuthoritySnapshotId.Value,
            StableCorrelation(tenantId, relationshipId, relationship.AcceptedContractId.Value, request.PaymentReference));
        return await workflowStarter.StartOrJoinAsync(activation, cancellationToken);
    }

    private static Guid StableCorrelation(
        Guid tenantId, Guid relationshipId, Guid contractId, string paymentReference)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(
            $"{tenantId:D}|{relationshipId:D}|{contractId:D}|{paymentReference.Trim()}"));
        bytes[6] = (byte)((bytes[6] & 0x0f) | 0x40);
        bytes[8] = (byte)((bytes[8] & 0x3f) | 0x80);
        return new Guid(bytes[..16]);
    }
}