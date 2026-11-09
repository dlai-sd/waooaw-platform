using Moq;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationBatchTaskResolverTests
{
    [Theory]
    [InlineData("tenant")]
    [InlineData("relationship")]
    [InlineData("actor")]
    [InlineData("agent")]
    [InlineData("idempotency")]
    [InlineData("version")]
    [InlineData("role")]
    [InlineData("skill")]
    [InlineData("skill-version")]
    [InlineData("claim-owner")]
    [InlineData("claim-id")]
    [InlineData("claim-revision")]
    [InlineData("claim-invocation")]
    public async Task RejectsEveryInvalidResolutionAuthorityBeforeOwnerLookup(string defect)
    {
        var claim = new ConversationWorkItemReferenceV1(
            defect == "claim-owner" ? "other" : "professional-runtime",
            defect == "claim-id" ? Guid.Empty : Guid.NewGuid(),
            defect == "claim-revision" ? 0 : 1,
            defect == "claim-invocation" ? Guid.Empty : Guid.NewGuid()
        );
        var request = new ConversationBatchTaskResolutionRequest(
            defect == "tenant" ? Guid.Empty : Guid.NewGuid(),
            defect == "relationship" ? Guid.Empty : Guid.NewGuid(),
            defect == "actor" ? Guid.Empty : Guid.NewGuid(),
            defect == "role" ? " " : "OWNER",
            defect == "version" ? 0 : 1,
            defect == "agent" ? Guid.Empty : Guid.NewGuid(),
            defect == "skill" ? " " : "publish",
            defect == "skill-version" ? " " : "1.0.0",
            defect == "idempotency" ? Guid.Empty : Guid.NewGuid(),
            claim
        );
        var owner = new Mock<IRelationshipWorkspaceOwnerGateway>(MockBehavior.Strict);
        var resolver = new ConversationBatchTaskResolver(owner.Object);

        var resolved = await resolver.ResolveFreshAsync(request, CancellationToken.None);

        Assert.Null(resolved);
        owner.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task ResolvesUnclaimedSourceByItsIdempotencyKey()
    {
        var sourceIdempotencyKey = Guid.NewGuid();
        var agent = Guid.NewGuid();
        var item = new ExecutionOwnerWorkItem(
            Guid.NewGuid(),
            agent,
            "publish",
            "1.0.0",
            sourceIdempotencyKey,
            1,
            "PENDING",
            "publish",
            null,
            DateTimeOffset.UtcNow
        );
        var owner = new Mock<IRelationshipWorkspaceOwnerGateway>(MockBehavior.Strict);
        owner
            .Setup(value =>
                value.GetExecutionAsync(
                    It.IsAny<RelationshipOwnerContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(
                new ExecutionOwnerProjection(
                    "work-1",
                    "CURRENT",
                    DateTimeOffset.UtcNow,
                    [item]
                )
            );
        var resolver = new ConversationBatchTaskResolver(owner.Object);

        var resolved = await resolver.ResolveFreshAsync(
            new(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                "OWNER",
                1,
                agent,
                "publish",
                "1.0.0",
                sourceIdempotencyKey,
                null
            ),
            CancellationToken.None
        );

        Assert.Equal(
            new ConversationBatchTaskIdentity(
                "professional-runtime",
                item.WorkItemId,
                item.Revision,
                item.InvocationId
            ),
            resolved
        );
    }

    [Theory]
    [InlineData("work-item")]
    [InlineData("revision")]
    [InlineData("invocation")]
    [InlineData("agent")]
    [InlineData("skill")]
    [InlineData("skill-version")]
    [InlineData("state")]
    public async Task RefusesEveryNonExactClaimedProjectionBinding(string defect)
    {
        var claim = new ConversationWorkItemReferenceV1(
            "professional-runtime",
            Guid.NewGuid(),
            2,
            Guid.NewGuid()
        );
        var agent = Guid.NewGuid();
        var item = new ExecutionOwnerWorkItem(
            defect == "work-item" ? Guid.NewGuid() : claim.WorkItemId,
            defect == "agent" ? Guid.NewGuid() : agent,
            defect == "skill" ? "other" : "publish",
            defect == "skill-version" ? "2.0.0" : "1.0.0",
            defect == "invocation" ? Guid.NewGuid() : claim.InvocationId,
            defect == "revision" ? 3 : claim.Revision,
            defect == "state" ? "COMPLETED" : "PARTIAL",
            "publish",
            null,
            DateTimeOffset.UtcNow
        );
        var owner = new Mock<IRelationshipWorkspaceOwnerGateway>(MockBehavior.Strict);
        owner
            .Setup(value =>
                value.GetExecutionAsync(
                    It.IsAny<RelationshipOwnerContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(
                new ExecutionOwnerProjection(
                    "work-2",
                    "CURRENT",
                    DateTimeOffset.UtcNow,
                    [item]
                )
            );
        var resolver = new ConversationBatchTaskResolver(owner.Object);

        var resolved = await resolver.ResolveFreshAsync(
            new(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                "OWNER",
                1,
                agent,
                "publish",
                "1.0.0",
                Guid.NewGuid(),
                claim
            ),
            CancellationToken.None
        );

        Assert.Null(resolved);
    }

    [Fact]
    public async Task ResolvesOnlyExactCurrentPrOwnedSourceBinding()
    {
        var claim = new ConversationWorkItemReferenceV1(
            "professional-runtime",
            Guid.NewGuid(),
            7,
            Guid.NewGuid()
        );
        var agent = Guid.NewGuid();
        var item = new ExecutionOwnerWorkItem(
            claim.WorkItemId,
            agent,
            "publish",
            "1.0.0",
            claim.InvocationId,
            claim.Revision,
            "RUNNING",
            "publish",
            null,
            DateTimeOffset.UtcNow
        );
        var owner = new Mock<IRelationshipWorkspaceOwnerGateway>(MockBehavior.Strict);
        owner
            .Setup(value =>
                value.GetExecutionAsync(
                    It.IsAny<RelationshipOwnerContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(
                new ExecutionOwnerProjection(
                    "work-7",
                    "CURRENT",
                    DateTimeOffset.UtcNow,
                    [item]
                )
            );
        var resolver = new ConversationBatchTaskResolver(owner.Object);
        var request = new ConversationBatchTaskResolutionRequest(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            "OWNER",
            3,
            agent,
            "publish",
            "1.0.0",
            Guid.NewGuid(),
            claim
        );

        var resolved = await resolver.ResolveFreshAsync(request, CancellationToken.None);

        Assert.Equal(
            new ConversationBatchTaskIdentity(
                "professional-runtime",
                claim.WorkItemId,
                claim.Revision,
                claim.InvocationId
            ),
            resolved
        );
    }

    [Fact]
    public async Task RefusesStaleRevisionAndPreservesIndividualFallback()
    {
        var claim = new ConversationWorkItemReferenceV1(
            "professional-runtime",
            Guid.NewGuid(),
            2,
            Guid.NewGuid()
        );
        var owner = new Mock<IRelationshipWorkspaceOwnerGateway>(MockBehavior.Strict);
        owner
            .Setup(value =>
                value.GetExecutionAsync(
                    It.IsAny<RelationshipOwnerContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(
                new ExecutionOwnerProjection(
                    "work-3",
                    "CURRENT",
                    DateTimeOffset.UtcNow,
                    [
                        new(
                            claim.WorkItemId,
                            Guid.NewGuid(),
                            "publish",
                            "1.0.0",
                            claim.InvocationId,
                            3,
                            "RUNNING",
                            "publish",
                            null,
                            DateTimeOffset.UtcNow
                        ),
                    ]
                )
            );
        var resolver = new ConversationBatchTaskResolver(owner.Object);

        var resolved = await resolver.ResolveFreshAsync(
            new(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                "OWNER",
                1,
                Guid.NewGuid(),
                "publish",
                "1.0.0",
                Guid.NewGuid(),
                claim
            ),
            CancellationToken.None
        );

        Assert.Null(resolved);
    }
}
