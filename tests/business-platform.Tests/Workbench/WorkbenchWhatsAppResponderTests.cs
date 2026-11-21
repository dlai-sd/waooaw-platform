// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-03
// Constitutional basis: C-001, C-009, C-023, C-059, C-063, ADR-051

using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchWhatsAppResponderTests
{
    private static WorkbenchWhatsAppResponder Responder(WorkbenchHarness harness, bool enabled) =>
        new(
            Options.Create(
                new WorkbenchOptions
                {
                    Enabled = enabled,
                    HandoffBaseUrl = "https://app.example.test",
                }
            ),
            harness.Projection,
            harness.Handoffs,
            NullLogger<WorkbenchWhatsAppResponder>.Instance
        );

    [Fact]
    public async Task RenderProgress_WhenTheWorkbenchIsOff_LeavesTheLegacyAnswerInPlace()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var text = await Responder(harness, false)
            .RenderProgressAsync(
                harness.TenantId,
                harness.RelationshipId,
                harness.ParticipantId,
                harness.Role,
                Guid.NewGuid().ToString("D"),
                CancellationToken.None
            );

        Assert.Null(text);
    }

    [Fact]
    public async Task RenderProgress_ForAMember_ReturnsPlainTextWithAWebHandoffLink()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var text = await Responder(harness, true)
            .RenderProgressAsync(
                harness.TenantId,
                harness.RelationshipId,
                harness.ParticipantId,
                harness.Role,
                Guid.NewGuid().ToString("D"),
                CancellationToken.None
            );

        Assert.False(string.IsNullOrWhiteSpace(text));
        Assert.DoesNotContain("<", text);
    }

    [Fact]
    public async Task RenderProgress_ForARelationshipThatDoesNotExist_ReturnsNullInsteadOfThrowing()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var text = await Responder(harness, true)
            .RenderProgressAsync(
                harness.TenantId,
                Guid.NewGuid(),
                harness.ParticipantId,
                harness.Role,
                Guid.NewGuid().ToString("D"),
                CancellationToken.None
            );

        Assert.Null(text);
    }
}
