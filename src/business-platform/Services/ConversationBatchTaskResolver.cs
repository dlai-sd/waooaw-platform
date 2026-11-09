// Implements: WC-134 exact PR-owned source-to-work-item admission.
// constitutional_basis: C-023, C-026, C-059, C-063
namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationBatchTaskResolutionRequest(
    Guid TenantId,
    Guid RelationshipId,
    Guid ActorId,
    string ActorRole,
    int RelationshipVersion,
    Guid AgentInstanceId,
    string SkillId,
    string SkillVersion,
    Guid SourceIdempotencyKey,
    ConversationWorkItemReferenceV1? ClaimedWorkItem
);

public interface IConversationBatchTaskResolver
{
    Task<ConversationBatchTaskIdentity?> ResolveFreshAsync(
        ConversationBatchTaskResolutionRequest request,
        CancellationToken cancellationToken
    );
}

public sealed class ConversationBatchTaskResolver(IRelationshipWorkspaceOwnerGateway ownerGateway)
    : IConversationBatchTaskResolver
{
    public async Task<ConversationBatchTaskIdentity?> ResolveFreshAsync(
        ConversationBatchTaskResolutionRequest request,
        CancellationToken cancellationToken
    )
    {
        if (
            request.TenantId == Guid.Empty
            || request.RelationshipId == Guid.Empty
            || request.ActorId == Guid.Empty
            || request.AgentInstanceId == Guid.Empty
            || request.SourceIdempotencyKey == Guid.Empty
            || request.RelationshipVersion < 1
            || string.IsNullOrWhiteSpace(request.ActorRole)
            || string.IsNullOrWhiteSpace(request.SkillId)
            || string.IsNullOrWhiteSpace(request.SkillVersion)
            || request.ClaimedWorkItem is { } claimed
                && (
                    claimed.Owner != "professional-runtime"
                    || claimed.WorkItemId == Guid.Empty
                    || claimed.Revision < 1
                    || claimed.InvocationId == Guid.Empty
                )
        )
            return null;

        var projection = await ownerGateway.GetExecutionAsync(
            new(
                request.ActorId.ToString("D"),
                request.ActorRole,
                request.TenantId,
                request.RelationshipId,
                request.RelationshipVersion,
                request.SourceIdempotencyKey.ToString("D"),
                request.AgentInstanceId
            ),
            cancellationToken
        );
        if (projection is null || projection.State != "CURRENT" || projection.Items is null)
            return null;
        var matches = projection
            .Items.Where(item =>
                (
                    request.ClaimedWorkItem is { } claim
                        ? item.WorkItemId == claim.WorkItemId
                            && item.Revision == claim.Revision
                            && item.InvocationId == claim.InvocationId
                        : item.InvocationId == request.SourceIdempotencyKey
                )
                && item.AgentInstanceId == request.AgentInstanceId
                && string.Equals(item.SkillId, request.SkillId, StringComparison.Ordinal)
                && string.Equals(item.SkillVersion, request.SkillVersion, StringComparison.Ordinal)
                && item.State is "PENDING" or "RUNNING" or "PARTIAL"
            )
            .ToArray();
        return matches.Length == 1
            ? new(
                "professional-runtime",
                matches[0].WorkItemId,
                matches[0].Revision,
                matches[0].InvocationId
            )
            : null;
    }
}
