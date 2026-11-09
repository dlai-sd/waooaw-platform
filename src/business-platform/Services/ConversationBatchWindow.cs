// Implements: WC-134 bounded conversation batching selection.
// constitutional_basis: C-023, C-026, C-059, C-063
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services;

public sealed class ConversationBatchingOptions
{
    public bool Enabled { get; set; }
    public int MaximumWaitSeconds { get; set; } = 10;
    public int MaximumMessages { get; set; } = 3;
    public int MaximumTextLength { get; set; } = 2_000;
    public string Separator { get; set; } = "\n";
    public int LeaseSeconds { get; set; } = 45;

    internal ConversationBatchLimits ToLimits() =>
        new(
            MaximumMessages,
            MaximumTextLength,
            TimeSpan.FromSeconds(MaximumWaitSeconds),
            Separator
        );
}

internal sealed class ConversationBatchingOptionsValidator
    : IValidateOptions<ConversationBatchingOptions>
{
    public ValidateOptionsResult Validate(string? name, ConversationBatchingOptions options)
    {
        var errors = new List<string>();
        if (options.MaximumWaitSeconds is < 1 or > 10)
            errors.Add("ConversationBatching:MaximumWaitSeconds must be between 1 and 10.");
        if (options.MaximumMessages is < 2 or > 3)
            errors.Add("ConversationBatching:MaximumMessages must be between 2 and 3.");
        if (options.MaximumTextLength is < 1 or > 2_000)
            errors.Add("ConversationBatching:MaximumTextLength must be between 1 and 2000.");
        if (options.Separator != "\n")
            errors.Add("ConversationBatching:Separator must be a newline.");
        if (options.LeaseSeconds is < 5 or > 300)
            errors.Add("ConversationBatching:LeaseSeconds must be between 5 and 300.");
        return errors.Count == 0
            ? ValidateOptionsResult.Success
            : ValidateOptionsResult.Fail(errors);
    }
}

public sealed record ConversationBatchTaskIdentity(
    string Owner,
    Guid WorkItemId,
    int Revision,
    Guid InvocationId
);

internal sealed record ConversationBatchScope(
    string Environment,
    Guid TenantId,
    Guid RelationshipId,
    Guid ConversationId,
    Guid ActorId,
    string ActorRole,
    Guid ChannelBindingId,
    string RecipientDigest,
    Guid AgentInstanceId,
    string SkillId,
    string SkillVersion,
    string Language,
    string AuthorityDigest,
    ConversationBatchTaskIdentity? Task
);

internal sealed record ConversationBatchCandidate(
    Guid MessageId,
    Guid ExecutionId,
    long Sequence,
    DateTimeOffset AcceptedAt,
    string Text,
    ConversationBatchScope Scope
);

internal sealed record ConversationBatchLimits(
    int MaximumMessages,
    int MaximumTextLength,
    TimeSpan MaximumWait,
    string Separator
);

internal sealed record ConversationBatchSelection(
    IReadOnlyList<ConversationBatchCandidate> ReadyMembers,
    IReadOnlyList<ConversationBatchCandidate> IndividualMembers,
    ConversationBatchCandidate? Boundary = null
);

internal static class ConversationBatchWindow
{
    // Selection does not confer authority: each source and its current mandate
    // must still be checked by the owner at admission and dispatch.
    internal static ConversationBatchSelection Select(
        IReadOnlyList<ConversationBatchCandidate> ordered,
        ConversationBatchLimits limits
    )
    {
        if (
            limits.MaximumMessages < 1
            || limits.MaximumTextLength < 1
            || limits.MaximumWait <= TimeSpan.Zero
            || limits.Separator is null
        )
            throw new ArgumentOutOfRangeException(nameof(limits));
        if (ordered.Count == 0)
            return new([], []);

        var first = ordered[0];
        RequireCandidate(first);
        if (first.Text.Length > limits.MaximumTextLength)
            throw new ConversationStateConflictException();
        var selected = new List<ConversationBatchCandidate> { first };
        var length = first.Text.Length;
        var lastSequence = first.Sequence;
        var lastAcceptedAt = first.AcceptedAt;
        var messageIds = new HashSet<Guid> { first.MessageId };
        var executionIds = new HashSet<Guid> { first.ExecutionId };
        var knownTask = first.Scope.Task;
        var individualDispatchRequired = knownTask is null;
        for (var index = 1; index < ordered.Count; index++)
        {
            var candidate = ordered[index];
            RequireCandidate(candidate);
            if (
                candidate.Sequence <= lastSequence
                || candidate.AcceptedAt < lastAcceptedAt
                || !messageIds.Add(candidate.MessageId)
                || !executionIds.Add(candidate.ExecutionId)
            )
                throw new ConversationStateConflictException();
            if (
                candidate.Scope with { Task = null } != first.Scope with { Task = null }
                || candidate.Sequence != lastSequence + 1
                || candidate.AcceptedAt - first.AcceptedAt > limits.MaximumWait
                || selected.Count == limits.MaximumMessages
                || limits.Separator.Length > limits.MaximumTextLength - length
                || candidate.Text.Length
                    > limits.MaximumTextLength - length - limits.Separator.Length
            )
                return Result(candidate);
            if (candidate.Scope.Task != knownTask)
                return Result(candidate);
            selected.Add(candidate);
            length += limits.Separator.Length + candidate.Text.Length;
            lastSequence = candidate.Sequence;
            lastAcceptedAt = candidate.AcceptedAt;
        }
        return Result(null);

        ConversationBatchSelection Result(ConversationBatchCandidate? boundary) =>
            individualDispatchRequired ? new([], selected, boundary) : new(selected, [], boundary);
    }

    private static void RequireCandidate(ConversationBatchCandidate candidate)
    {
        var scope = candidate.Scope;
        if (
            candidate.MessageId == Guid.Empty
            || candidate.ExecutionId == Guid.Empty
            || candidate.Sequence < 1
            || candidate.AcceptedAt == default
            || string.IsNullOrEmpty(candidate.Text)
            || scope is null
            || string.IsNullOrWhiteSpace(scope.Environment)
            || scope.TenantId == Guid.Empty
            || scope.RelationshipId == Guid.Empty
            || scope.ConversationId == Guid.Empty
            || scope.ActorId == Guid.Empty
            || string.IsNullOrWhiteSpace(scope.ActorRole)
            || scope.ChannelBindingId == Guid.Empty
            || !Digest(scope.RecipientDigest)
            || scope.AgentInstanceId == Guid.Empty
            || string.IsNullOrWhiteSpace(scope.SkillId)
            || string.IsNullOrWhiteSpace(scope.SkillVersion)
            || !ConversationInputContract.IsLanguageTag(scope.Language)
            || !Digest(scope.AuthorityDigest)
            || (
                scope.Task is not null
                && (
                    scope.Task.Owner != "professional-runtime"
                    || scope.Task.WorkItemId == Guid.Empty
                    || scope.Task.Revision < 1
                    || scope.Task.InvocationId == Guid.Empty
                )
            )
        )
            throw new ConversationStateConflictException();
    }

    private static bool Digest(string? value) =>
        value is { Length: 64 }
        && value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');
}
