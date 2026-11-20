// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-03
// Constitutional basis: C-001, C-009, C-023, C-059, C-063, ADR-051

using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Workbench;

/// <summary>Answers a bound WhatsApp participant's progress request from the workbench projection.</summary>
public interface IWorkbenchWhatsAppResponder
{
    /// <summary>The WhatsApp text for the relationship, or null when the workbench is off or cannot answer.</summary>
    Task<string?> RenderProgressAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        RelationshipParticipantRole role,
        string correlationId,
        CancellationToken ct
    );
}

public sealed class WorkbenchWhatsAppResponder(
    IOptions<WorkbenchOptions> options,
    WorkbenchProjectionService projection,
    WorkbenchHandoffService handoffs,
    ILogger<WorkbenchWhatsAppResponder> logger
) : IWorkbenchWhatsAppResponder
{
    private static readonly ChannelCapabilities WhatsApp = ChannelCapabilities.Default with
    {
        Channel = "WHATSAPP",
    };

    public async Task<string?> RenderProgressAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        RelationshipParticipantRole role,
        string correlationId,
        CancellationToken ct
    )
    {
        if (!options.Value.Enabled)
            return null;
        try
        {
            var context = await projection.NarrowAsync(
                new WorkbenchContext(
                    tenantId,
                    relationshipId,
                    participantId.ToString("D"),
                    participantId,
                    role,
                    WorkbenchAudiences.FromRole(role),
                    correlationId
                ),
                ct
            );
            var view = await projection.BuildAsync(context, WhatsApp, ct);
            var handoff = await handoffs.CreateAsync(context, "WEB_WORKBENCH", null, ct);
            return ExperienceWhatsAppRenderer.Render(
                view.Blocks,
                handoffs.UrlFor(handoff, relationshipId)
            );
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogWarning(
                "workbench_whatsapp_unavailable relationship={RelationshipHash} reason={Reason}",
                WorkbenchProjectionService.Hash(relationshipId),
                exception.GetType().Name
            );
            return null;
        }
    }
}
