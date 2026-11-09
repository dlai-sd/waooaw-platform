// Implements: work-contracts/WC-134-batching-offering-and-spend-work-component.md §9.1
using Waooaw.WorkloadIdentity;

namespace Waooaw.BusinessPlatform.Services;

public sealed record InferenceCaller(
    Guid TenantId,
    Guid RelationshipId,
    Guid ActorId,
    string Role,
    Guid ContributionId,
    Guid ExecutionId,
    Guid IdempotencyKey
);

public sealed class InferenceWorkloadAuthority(InferenceWorkloadValidator validator)
{
    public async Task<InferenceCaller> RequireAsync(
        HttpContext http,
        string route,
        string operation,
        string digest,
        CancellationToken ct,
        string purpose = "CONVERSATION_INFERENCE_OWNER"
    )
    {
        try
        {
            var caller = await validator.RequireAsync(
                http,
                "ai-runtime",
                "business-platform",
                purpose,
                route,
                operation,
                digest,
                ct
            );
            return new(
                caller.TenantId,
                caller.RelationshipId,
                caller.ActorId,
                caller.Role,
                caller.ContributionId,
                caller.ExecutionId,
                caller.IdempotencyKey
            );
        }
        catch (InferenceWorkloadRejectedException)
        {
            throw new ConversationNotAccessibleException();
        }
    }
}
