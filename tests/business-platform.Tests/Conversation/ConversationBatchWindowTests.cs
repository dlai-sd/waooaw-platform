// Implements: WC-134 bounded conversation batching selection.
// constitutional_basis: C-023, C-026, C-059, C-063
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationBatchWindowTests
{
    private static readonly DateTimeOffset Start = DateTimeOffset.Parse("2026-01-01T00:00:00Z");
    private static readonly ConversationBatchScope Scope = new(
        "Demo",
        Guid.NewGuid(),
        Guid.NewGuid(),
        Guid.NewGuid(),
        Guid.NewGuid(),
        "EMPLOYER",
        Guid.NewGuid(),
        new string('a', 64),
        Guid.NewGuid(),
        "skill",
        "1.0",
        "en-IN",
        new string('b', 64),
        new ConversationBatchTaskIdentity(
            "professional-runtime",
            Guid.NewGuid(),
            1,
            Guid.NewGuid()
        )
    );
    private static readonly ConversationBatchLimits Limits = new(
        3,
        10,
        TimeSpan.FromSeconds(5),
        "\n"
    );

    [Fact]
    public void ApprovedBatchingDefaultsAreValidAndBounded()
    {
        var options = new ConversationBatchingOptions();
        var validation = new ConversationBatchingOptionsValidator().Validate(
            Options.DefaultName,
            options
        );

        Assert.True(validation.Succeeded);
        Assert.False(options.Enabled);
        Assert.Equal(10, options.MaximumWaitSeconds);
        Assert.Equal(3, options.MaximumMessages);
        Assert.Equal(2_000, options.MaximumTextLength);
        Assert.Equal("\n", options.Separator);
        Assert.Equal(
            new ConversationBatchLimits(3, 2_000, TimeSpan.FromSeconds(10), "\n"),
            options.ToLimits()
        );
    }

    [Theory]
    [InlineData(11, 3, 2_000)]
    [InlineData(10, 4, 2_000)]
    [InlineData(10, 3, 2_001)]
    public void BatchingOptionsRejectValuesAboveApprovedCeilings(
        int maximumWaitSeconds,
        int maximumMessages,
        int maximumTextLength
    )
    {
        var options = new ConversationBatchingOptions
        {
            MaximumWaitSeconds = maximumWaitSeconds,
            MaximumMessages = maximumMessages,
            MaximumTextLength = maximumTextLength,
        };

        Assert.False(
            new ConversationBatchingOptionsValidator()
                .Validate(Options.DefaultName, options)
                .Succeeded
        );
    }

    [Fact]
    public void BatchingOptionsRejectEveryValueBelowTheApprovedFloor()
    {
        var options = new ConversationBatchingOptions
        {
            MaximumWaitSeconds = 0,
            MaximumMessages = 1,
            MaximumTextLength = 0,
            Separator = " ",
            LeaseSeconds = 4,
        };

        var validation = new ConversationBatchingOptionsValidator().Validate(
            Options.DefaultName,
            options
        );

        Assert.False(validation.Succeeded);
        Assert.NotNull(validation.Failures);
        Assert.Equal(5, validation.Failures.Count());
    }

    [Fact]
    public void BatchingCanBeEnabledAfterDurableCollectorAndDispatcherIntegration()
    {
        var options = new ConversationBatchingOptions { Enabled = true };

        var validation = new ConversationBatchingOptionsValidator().Validate(
            Options.DefaultName,
            options
        );

        Assert.True(validation.Succeeded);
    }

    [Fact]
    public void ApprovedLimitsIncludeExactWaitCountAndCombinedTextBoundaries()
    {
        var limits = new ConversationBatchingOptions().ToLimits();
        var exactText = new[] { Candidate(1, 1_000), Candidate(2, 999) };
        var exactTextResult = ConversationBatchWindow.Select(exactText, limits);
        Assert.Equal(
            2_000,
            string.Join(limits.Separator, exactText.Select(item => item.Text)).Length
        );
        Assert.Equal(exactText, exactTextResult.ReadyMembers);

        var tooLong = new[] { Candidate(1, 1_000), Candidate(2, 1_000) };
        var tooLongResult = ConversationBatchWindow.Select(tooLong, limits);
        Assert.Equal([tooLong[0]], tooLongResult.ReadyMembers);
        Assert.Equal(tooLong[1], tooLongResult.Boundary);

        var exactWait = new[]
        {
            Candidate(1),
            Candidate(2) with
            {
                AcceptedAt = Start.AddSeconds(10),
            },
        };
        Assert.Equal(exactWait, ConversationBatchWindow.Select(exactWait, limits).ReadyMembers);

        var atCountLimit = Enumerable.Range(1, 4).Select(number => Candidate(number)).ToArray();
        var countResult = ConversationBatchWindow.Select(atCountLimit, limits);
        Assert.Equal(atCountLimit.Take(3), countResult.ReadyMembers);
        Assert.Equal(atCountLimit[3], countResult.Boundary);
    }

    private static ConversationBatchCandidate Candidate(long sequence, int length = 2) =>
        new(
            Guid.NewGuid(),
            Guid.NewGuid(),
            sequence,
            Start.AddSeconds(sequence - 1),
            new string('x', length),
            Scope
        );

    private static IReadOnlyList<ConversationBatchCandidate> ReadySelection(
        IReadOnlyList<ConversationBatchCandidate> candidates,
        ConversationBatchLimits limits
    )
    {
        var result = ConversationBatchWindow.Select(candidates, limits);
        Assert.Empty(result.IndividualMembers);
        return result.ReadyMembers;
    }

    [Fact]
    public void CollectsOnlyTheContiguousBoundedPrefix()
    {
        var items = Enumerable.Range(1, 4).Select(number => Candidate(number)).ToArray();
        Assert.Equal(items.Take(3), ReadySelection(items, Limits));
    }

    [Fact]
    public void ExactTimeAndLengthBoundsAreAllowedButNeverSkipped()
    {
        var first = Candidate(1, 4);
        var atLimit = Candidate(2, 5) with { AcceptedAt = Start.AddSeconds(5) };
        var tooMuch = Candidate(3, 1) with { AcceptedAt = Start.AddSeconds(5) };
        Assert.Equal(new[] { first, atLimit }, ReadySelection([first, atLimit, tooMuch], Limits));
        var tooLate = atLimit with { AcceptedAt = Start.AddSeconds(5).AddTicks(1) };
        Assert.Equal([first], ReadySelection([first, tooLate], Limits));
    }

    [Theory]
    [InlineData("environment")]
    [InlineData("tenant")]
    [InlineData("relationship")]
    [InlineData("conversation")]
    [InlineData("actor")]
    [InlineData("role")]
    [InlineData("binding")]
    [InlineData("recipient")]
    [InlineData("agent")]
    [InlineData("skill")]
    [InlineData("version")]
    [InlineData("language")]
    [InlineData("authority")]
    [InlineData("task-reference")]
    [InlineData("task-revision")]
    public void DifferentAuthorityOrRouteEndsTheBatchWithoutSkipping(string changed)
    {
        var first = Candidate(1);
        var other = Candidate(2);
        var scope = changed switch
        {
            "environment" => Scope with { Environment = "Other" },
            "tenant" => Scope with { TenantId = Guid.NewGuid() },
            "relationship" => Scope with { RelationshipId = Guid.NewGuid() },
            "conversation" => Scope with { ConversationId = Guid.NewGuid() },
            "actor" => Scope with { ActorId = Guid.NewGuid() },
            "role" => Scope with { ActorRole = "VIEWER" },
            "binding" => Scope with { ChannelBindingId = Guid.NewGuid() },
            "recipient" => Scope with { RecipientDigest = new string('c', 64) },
            "agent" => Scope with { AgentInstanceId = Guid.NewGuid() },
            "skill" => Scope with { SkillId = "other" },
            "version" => Scope with { SkillVersion = "2.0" },
            "language" => Scope with { Language = "hi-IN" },
            "authority" => Scope with { AuthorityDigest = new string('c', 64) },
            "task-reference" => Scope with
            {
                Task = Scope.Task! with { WorkItemId = Guid.NewGuid() },
            },
            "task-revision" => Scope with { Task = Scope.Task! with { Revision = 2 } },
            _ => throw new InvalidOperationException(changed),
        };
        Assert.Equal(
            [first],
            ReadySelection([first, other with { Scope = scope }, Candidate(3)], Limits)
        );
    }

    [Fact]
    public void RejectsTaskIdentityNotOwnedByProfessionalRuntime()
    {
        var unowned = Candidate(1) with
        {
            Scope = Scope with { Task = Scope.Task! with { Owner = "other" } },
        };
        Assert.Throws<ConversationStateConflictException>(() =>
            ConversationBatchWindow.Select([unowned], Limits)
        );
    }

    [Fact]
    public void RejectsDuplicateOrOutOfOrderSources()
    {
        var first = Candidate(1);
        var second = Candidate(2);
        Assert.Throws<ConversationStateConflictException>(() =>
            ReadySelection([first, second with { Sequence = 1 }], Limits)
        );
        Assert.Throws<ConversationStateConflictException>(() =>
            ReadySelection([first, second with { AcceptedAt = Start.AddTicks(-1) }], Limits)
        );
        Assert.Throws<ConversationStateConflictException>(() =>
            ReadySelection([first, second with { MessageId = first.MessageId }], Limits)
        );
        Assert.Throws<ConversationStateConflictException>(() =>
            ReadySelection([first, second with { ExecutionId = first.ExecutionId }], Limits)
        );
    }

    [Fact]
    public void DoesNotCrossAnUnseenCanonicalSequence()
    {
        var first = Candidate(1);
        Assert.Equal([first], ReadySelection([first, Candidate(3)], Limits));
    }

    [Fact]
    public void MissingTaskKeepsEveryMessageOnTheIndividualDispatchPath()
    {
        var first = Candidate(1) with { Scope = Scope with { Task = null } };
        var second = Candidate(2) with { Scope = first.Scope };
        var result = ConversationBatchWindow.Select([first, second], Limits);
        Assert.Empty(result.ReadyMembers);
        Assert.Equal([first, second], result.IndividualMembers);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void MissingTaskSplitsTheOwnerBoundPrefixFromIndividualDispatch(bool firstTaskMissing)
    {
        var first = Candidate(1) with
        {
            Scope = firstTaskMissing ? Scope with { Task = null } : Scope,
        };
        var second = Candidate(2) with
        {
            Scope = firstTaskMissing ? Scope : Scope with { Task = null },
        };
        var result = ConversationBatchWindow.Select([first, second], Limits);
        if (firstTaskMissing)
        {
            Assert.Empty(result.ReadyMembers);
            Assert.Equal([first], result.IndividualMembers);
        }
        else
        {
            Assert.Equal([first], result.ReadyMembers);
            Assert.Empty(result.IndividualMembers);
        }
        Assert.Equal(second, result.Boundary);
    }

    [Fact]
    public void MissingLaterTaskDoesNotBlockTheOwnerBoundPrefix()
    {
        var first = Candidate(1);
        var second = Candidate(2);
        var third = Candidate(3) with { Scope = Scope with { Task = null } };
        var result = ConversationBatchWindow.Select([first, second, third], Limits);
        Assert.Equal([first, second], result.ReadyMembers);
        Assert.Empty(result.IndividualMembers);
        Assert.Equal(third, result.Boundary);
    }

    [Fact]
    public void IndividualFallbackCoversTheBoundedWindow()
    {
        var first = Candidate(1) with { Scope = Scope with { Task = null } };
        var second = Candidate(2) with { Scope = first.Scope };
        var third = Candidate(3) with { Scope = first.Scope };
        var fourth = Candidate(4) with { Scope = first.Scope };
        var result = ConversationBatchWindow.Select([first, second, third, fourth], Limits);
        Assert.Empty(result.ReadyMembers);
        Assert.Equal([first, second, third], result.IndividualMembers);
        Assert.Equal(fourth, result.Boundary);
    }

    [Fact]
    public void IndividualFallbackDoesNotCrossTheLengthOrTimeBoundary()
    {
        var first = Candidate(1, 4) with { Scope = Scope with { Task = null } };
        var second = Candidate(2, 5) with { Scope = first.Scope };
        var tooLong = Candidate(3, 1) with { Scope = first.Scope };
        var byLength = ConversationBatchWindow.Select([first, second, tooLong], Limits);
        Assert.Equal([first, second], byLength.IndividualMembers);
        Assert.Equal(tooLong, byLength.Boundary);

        var tooLate = Candidate(3) with
        {
            Scope = first.Scope,
            AcceptedAt = Start.AddSeconds(5).AddTicks(1),
        };
        var byTime = ConversationBatchWindow.Select(
            [first, Candidate(2) with { Scope = first.Scope }, tooLate],
            Limits
        );
        Assert.Equal(2, byTime.IndividualMembers.Count);
        Assert.Equal(tooLate, byTime.Boundary);
    }

    [Fact]
    public void IndividualFallbackRejectsDuplicateSourcesInItsEligiblePrefix()
    {
        var first = Candidate(1) with { Scope = Scope with { Task = null } };
        var second = Candidate(2) with { Scope = first.Scope };
        var duplicate = Candidate(3) with { Scope = first.Scope, MessageId = first.MessageId };
        Assert.Throws<ConversationStateConflictException>(() =>
            ConversationBatchWindow.Select([first, second, duplicate], Limits)
        );
    }

    [Fact]
    public void UnknownTaskDoesNotBridgeDifferentKnownTasks()
    {
        var first = Candidate(1);
        var second = Candidate(2) with { Scope = Scope with { Task = null } };
        var third = Candidate(3) with
        {
            Scope = Scope with { Task = Scope.Task! with { WorkItemId = Guid.NewGuid() } },
        };
        var result = ConversationBatchWindow.Select([first, second, third], Limits);
        Assert.Equal([first], result.ReadyMembers);
        Assert.Empty(result.IndividualMembers);
        Assert.Equal(second, result.Boundary);
        var afterBoundary = ConversationBatchWindow.Select([second, third], Limits);
        Assert.Equal([second], afterBoundary.IndividualMembers);
        Assert.Equal(third, afterBoundary.Boundary);
    }

    [Fact]
    public void MissingFirstTaskDoesNotBridgeDifferentLaterKnownTasks()
    {
        var first = Candidate(1) with { Scope = Scope with { Task = null } };
        var second = Candidate(2);
        var third = Candidate(3) with
        {
            Scope = Scope with { Task = Scope.Task! with { Revision = 2 } },
        };
        var result = ConversationBatchWindow.Select([first, second, third], Limits);
        Assert.Empty(result.ReadyMembers);
        Assert.Equal([first], result.IndividualMembers);
        Assert.Equal(second, result.Boundary);
        var afterBoundary = ConversationBatchWindow.Select([second, third], Limits);
        Assert.Equal([second], afterBoundary.ReadyMembers);
        Assert.Equal(third, afterBoundary.Boundary);
    }

    [Fact]
    public void MissingTaskDoesNotOverrideScopeOrWindowBoundaries()
    {
        var first = Candidate(1) with { Scope = Scope with { Task = null } };
        var foreign = Candidate(2) with { Scope = first.Scope with { ActorId = Guid.NewGuid() } };
        var tooLate = Candidate(2) with { Scope = first.Scope, AcceptedAt = Start.AddSeconds(6) };
        Assert.Equal(
            [first],
            ConversationBatchWindow.Select([first, foreign], Limits).IndividualMembers
        );
        Assert.Equal(
            [first],
            ConversationBatchWindow.Select([first, tooLate], Limits).IndividualMembers
        );
        Assert.Equal([first], ConversationBatchWindow.Select([first], Limits).IndividualMembers);
    }

    [Fact]
    public void SeparatorCountsTowardCombinedLength()
    {
        var first = Candidate(1, 5);
        var second = Candidate(2, 5);
        Assert.Equal([first], ReadySelection([first, second], Limits));
        Assert.Equal(
            [first, second],
            ReadySelection([first, second], Limits with { Separator = "" })
        );
    }

    [Fact]
    public void TextAndSeparatorLimitsCountUtf16CodeUnits()
    {
        var first = Candidate(1) with { Text = "a😀" };
        var second = Candidate(2) with { Text = "b😀" };
        Assert.Equal(
            [first, second],
            ReadySelection([first, second], Limits with { MaximumTextLength = 8, Separator = "😀" })
        );
        Assert.Equal(
            [first],
            ReadySelection([first, second], Limits with { MaximumTextLength = 7, Separator = "😀" })
        );
    }

    [Fact]
    public void RejectsInvalidCandidatesAndLimits()
    {
        var first = Candidate(1);
        Assert.Empty(ReadySelection([], Limits));
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            ReadySelection([first], Limits with { MaximumWait = TimeSpan.Zero })
        );
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            ReadySelection([first], Limits with { Separator = null! })
        );
        Assert.Throws<ConversationStateConflictException>(() =>
            ReadySelection([first with { Text = new string('x', 11) }], Limits)
        );
        Assert.Throws<ConversationStateConflictException>(() =>
            ReadySelection(
                [first with { Scope = Scope with { RecipientDigest = "invalid" } }],
                Limits
            )
        );
        Assert.Throws<ConversationStateConflictException>(() =>
            ReadySelection(
                [first with { Scope = Scope with { AuthorityDigest = new string('A', 64) } }],
                Limits
            )
        );
        Assert.Throws<ConversationStateConflictException>(() =>
            ReadySelection(
                [first with { Scope = Scope with { Task = Scope.Task! with { Revision = 0 } } }],
                Limits
            )
        );
    }
}
