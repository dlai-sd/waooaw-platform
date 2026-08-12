// Implements: work-contracts/WC-060-goal005-ae01-continuity-evidence-stop.md § WC060-07
// constitutional_basis: C-001, C-005, C-023, C-024, C-059

using Grpc.Core;
using Grpc.Net.Client;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.BusinessPlatform.Services;

public sealed record RelationshipEmergencyStopDispatch(Guid EvidenceId, DateTimeOffset ConfirmedAt);

public interface IRelationshipEmergencyStopGateway
{
    Task<RelationshipEmergencyStopDispatch> StopAsync(
        Guid tenantId, Guid relationshipId, Guid participantId,
        IReadOnlyCollection<Guid> executionIds, CancellationToken cancellationToken);
}

public sealed class GrpcRelationshipEmergencyStopGateway(
    IConfiguration configuration) : IRelationshipEmergencyStopGateway
{
    public async Task<RelationshipEmergencyStopDispatch> StopAsync(
        Guid tenantId, Guid relationshipId, Guid participantId,
        IReadOnlyCollection<Guid> executionIds, CancellationToken cancellationToken)
    {
        var endpoint = configuration["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");
        using var channel = GrpcChannel.ForAddress(endpoint);
        var client = new ConstitutionalService.ConstitutionalServiceClient(channel);
        var request = new EmergencyStopRequest
        {
            ContractId = relationshipId.ToString("D"),
            StoppedBy = participantId.ToString("D"),
        };
        request.ActiveSessionIds.Add(executionIds.Select(value => value.ToString("D")));
        var response = await client.TriggerEmergencyStopAsync(
            request,
            new Metadata { { "x-tenant-id", tenantId.ToString("D") } },
            deadline: DateTime.UtcNow.AddMilliseconds(200),
            cancellationToken: cancellationToken);
        if (!Guid.TryParse(response.EmergencyStopRecordId, out var evidenceId))
            throw new InvalidOperationException("Constitutional Engine returned an invalid Stop evidence identifier.");
        return new RelationshipEmergencyStopDispatch(evidenceId, response.RecordedAt.ToDateTimeOffset());
    }
}

public sealed class RelationshipEmergencyStopService(
    IDbContextFactory<ConversationStoreDbContext> conversationFactory,
    EmploymentRelationshipService relationships,
    IRelationshipEmergencyStopGateway gateway)
{
    public async Task<EmploymentRelationship?> StopAsync(
        Guid tenantId, Guid relationshipId, Guid participantId,
        RelationshipParticipantRole participantRole, Guid correlationId,
        CancellationToken cancellationToken)
    {
        var existing = await relationships.GetAsync(tenantId, relationshipId, cancellationToken);
        if (existing is null || existing.State == EmploymentRelationshipState.StoppedEmergency) return existing;
        await using var conversations = await conversationFactory.CreateDbContextAsync(cancellationToken);
        var terminalStates = new[] { "COMPLETED", "FAILED", "CANCELLED", "STOPPED" };
        var executionIds = await conversations.Executions.AsNoTracking()
            .Where(value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && !terminalStates.Contains(value.ProcessingState))
            .Select(value => value.ExecutionId)
            .ToListAsync(cancellationToken);
        var dispatch = await gateway.StopAsync(
            tenantId, relationshipId, participantId, executionIds, cancellationToken);
        return await relationships.CommitEmergencyStopAsync(
            tenantId, relationshipId, participantId, participantRole,
            correlationId, dispatch.EvidenceId, cancellationToken);
    }
}