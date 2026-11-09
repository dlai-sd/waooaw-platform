// Implements: conversation-core.md section 4.2; WC-134 atomic fresh-owner recovery.
// constitutional_basis: C-001, C-023, C-026, C-059, C-063
using System.Data.Common;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Moq;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationReconciliationPostgresTests
{
    [Theory]
    [InlineData("COMPLETED")]
    [InlineData("UNKNOWN")]
    public async Task PublicRecoveryAdmitsCurrentReaderAndReplaysWithoutRenewingEvidence(
        string state
    )
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ExecuteAsync("DELETE FROM business.conversation_reconciliation_authorities");
        var constitutional = new Mock<IRelationshipConstitutionalGateway>(MockBehavior.Strict);
        var evidence = Guid.NewGuid();
        constitutional
            .Setup(value =>
                value.AuthorizeAndRecordAsync(
                    fixture.Source.TenantId,
                    fixture.Source.RelationshipId,
                    It.IsAny<string>(),
                    "READ_EXISTING_RUNTIME_RESULT",
                    It.IsAny<Guid>(),
                    It.IsAny<object>(),
                    1,
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(evidence);
        var runtime = new Mock<IConversationExecutionReconciliationGateway>(MockBehavior.Strict);
        runtime
            .Setup(value =>
                value.ReadTerminalAsync(
                    It.IsAny<ConversationOriginalSourceV1>(),
                    It.IsAny<ConversationReconciliationAuthority>(),
                    0,
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(
                (
                    ConversationOriginalSourceV1 source,
                    ConversationReconciliationAuthority permission,
                    long afterSequence,
                    CancellationToken ct
                ) =>
                {
                    Assert.Equal(fixture.Source.MessageId, source.OriginalMessageId);
                    Assert.Equal(fixture.Source.Caller.ActorId, source.OriginalActorId);
                    Assert.NotEqual(source.OriginalActorId, permission.RequesterId);
                    Assert.Equal(fixture.Permission.RequesterId, permission.RequesterId);
                    Assert.Equal(evidence, permission.EvidenceId);
                    Assert.Equal(
                        TimeSpan.FromMinutes(5),
                        permission.ExpiresAt - permission.CreatedAt
                    );
                    return fixture.Result() with
                    {
                        ReconciliationAuthorityId = permission.AuthorityId,
                        State = state,
                        Events = state == "UNKNOWN" ? [] : fixture.Result().Events,
                        OriginalRequestDigest =
                            state == "UNKNOWN" ? null : fixture.Result().OriginalRequestDigest,
                        ResultDigest = state == "UNKNOWN" ? null : fixture.Result().ResultDigest,
                        NextAction =
                            state == "UNKNOWN"
                                ? "OPERATOR_RECONCILIATION_REQUIRED"
                                : "RECONCILE_CANONICAL_PROJECTION",
                    };
                }
            );
        var service = fixture.RecoveryService(constitutional.Object, runtime.Object);
        var request = new ReconcileConversationExecutionRequestV1(
            "1.0",
            fixture.Source.MessageId,
            0
        );
        var key = Guid.NewGuid();
        var first = await service.ReconcileAsync(
            fixture.Source.TenantId,
            fixture.Permission.RequesterId,
            fixture.Source.RelationshipId,
            fixture.Source.ExecutionId,
            key,
            Guid.NewGuid(),
            request,
            CancellationToken.None
        );
        var replay = await service.ReconcileAsync(
            fixture.Source.TenantId,
            fixture.Permission.RequesterId,
            fixture.Source.RelationshipId,
            fixture.Source.ExecutionId,
            key,
            Guid.NewGuid(),
            request,
            CancellationToken.None
        );
        Assert.Equal(state == "UNKNOWN" ? "UNRESOLVED" : "COMPLETED", first.State);
        Assert.Equal(first.State, replay.State);
        Assert.Equal(state == "COMPLETED", replay.Replayed);
        Assert.Equal(state == "COMPLETED" ? 2 : 0, first.ProjectionVersion);
        constitutional.Verify(
            value =>
                value.AuthorizeAndRecordAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<Guid>(),
                    It.IsAny<string>(),
                    It.IsAny<string>(),
                    It.IsAny<Guid>(),
                    It.IsAny<object>(),
                    It.IsAny<int>(),
                    It.IsAny<CancellationToken>()
                ),
            Times.Once
        );
        runtime.Verify(
            value =>
                value.ReadTerminalAsync(
                    It.IsAny<ConversationOriginalSourceV1>(),
                    It.IsAny<ConversationReconciliationAuthority>(),
                    0,
                    It.IsAny<CancellationToken>()
                ),
            Times.Exactly(state == "COMPLETED" ? 1 : 2)
        );
        await using var db = fixture.Conversations.CreateDbContext();
        var permission = await db.ReconciliationAuthorities.SingleAsync();
        Assert.Equal(state == "COMPLETED", permission.ResponseJson is not null);
        Assert.Equal(state == "COMPLETED" ? 2 : 1, await db.Messages.CountAsync());
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
        await using var relationships = fixture.Relationships.CreateDbContext();
        var originalMandate = await relationships.OperationalMandateSnapshots.SingleAsync();
        Assert.True(originalMandate.Deadline < DateTimeOffset.UtcNow);
        using var expectedMandate = JsonDocument.Parse(fixture.OriginalMandateJson);
        using var persistedMandate = JsonDocument.Parse(originalMandate.MandateJson);
        Assert.Equal(
            AgentAdmissionCanonicalizer.Digest(expectedMandate.RootElement),
            AgentAdmissionCanonicalizer.Digest(persistedMandate.RootElement)
        );
        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            service.ReconcileAsync(
                fixture.Source.TenantId,
                fixture.Permission.RequesterId,
                fixture.Source.RelationshipId,
                fixture.Source.ExecutionId,
                key,
                Guid.NewGuid(),
                request with
                {
                    ExpectedProjectionVersion = 1,
                },
                CancellationToken.None
            )
        );
    }

    [Theory]
    [InlineData("empty-evidence")]
    [InlineData("ce-unavailable")]
    [InlineData("ce-denied")]
    [InlineData("projection-after-ce")]
    [InlineData("participant-after-ce")]
    [InlineData("projection-after-read")]
    [InlineData("stop-after-read")]
    [InlineData("source-after-read")]
    [InlineData("invalid-result")]
    public async Task PublicRecoveryFailsClosedOnEvidenceAndOwnerDrift(string defect)
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ExecuteAsync("DELETE FROM business.conversation_reconciliation_authorities");
        var constitutional = new Mock<IRelationshipConstitutionalGateway>(MockBehavior.Strict);
        constitutional
            .Setup(value =>
                value.AuthorizeAndRecordAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<Guid>(),
                    It.IsAny<string>(),
                    "READ_EXISTING_RUNTIME_RESULT",
                    It.IsAny<Guid>(),
                    It.IsAny<object>(),
                    1,
                    It.IsAny<CancellationToken>()
                )
            )
            .Returns(async () =>
            {
                if (defect == "ce-unavailable")
                    throw new InvalidOperationException("Synthetic CE outage");
                if (defect == "ce-denied")
                    throw new ConstitutionalActionDeniedException("Synthetic denial");
                if (defect == "projection-after-ce")
                    await fixture.ExecuteAsync(
                        "UPDATE business.conversation_executions SET projection_version=1"
                    );
                if (defect == "participant-after-ce")
                    await fixture.ExecuteAsync(
                        $"UPDATE business.relationship_participants SET status='REMOVED' WHERE participant_id='{fixture.Permission.RequesterId:D}'"
                    );
                return defect == "empty-evidence" ? Guid.Empty : Guid.NewGuid();
            });
        var runtime = new Mock<IConversationExecutionReconciliationGateway>(MockBehavior.Strict);
        runtime
            .Setup(value =>
                value.ReadTerminalAsync(
                    It.IsAny<ConversationOriginalSourceV1>(),
                    It.IsAny<ConversationReconciliationAuthority>(),
                    0,
                    It.IsAny<CancellationToken>()
                )
            )
            .Returns(
                async (
                    ConversationOriginalSourceV1 source,
                    ConversationReconciliationAuthority permission,
                    long afterSequence,
                    CancellationToken ct
                ) =>
                {
                    if (defect == "projection-after-read")
                        await fixture.ExecuteAsync(
                            "UPDATE business.conversation_executions SET projection_version=1"
                        );
                    if (defect == "stop-after-read")
                        await fixture.ExecuteAsync(
                            $"INSERT INTO constitutional.employment_dispatch_stops VALUES ('{fixture.Source.TenantId:D}', '{fixture.Source.RelationshipId:D}')"
                        );
                    if (defect == "source-after-read")
                        await fixture.ExecuteAsync(
                            """UPDATE business.conversation_messages SET evidence_record_id=NULL"""
                        );
                    return fixture.Result() with
                    {
                        ReconciliationAuthorityId = permission.AuthorityId,
                        State = "UNKNOWN",
                        Events = [],
                        OriginalRequestDigest = null,
                        ResultDigest = null,
                        OriginalMessageId =
                            defect == "invalid-result" ? Guid.NewGuid() : source.OriginalMessageId,
                        NextAction = "OPERATOR_RECONCILIATION_REQUIRED",
                    };
                }
            );
        var service = fixture.RecoveryService(constitutional.Object, runtime.Object);
        var failure = await Record.ExceptionAsync(() =>
            service.ReconcileAsync(
                fixture.Source.TenantId,
                fixture.Permission.RequesterId,
                fixture.Source.RelationshipId,
                fixture.Source.ExecutionId,
                Guid.NewGuid(),
                Guid.NewGuid(),
                new("1.0", fixture.Source.MessageId, 0),
                CancellationToken.None
            )
        );
        if (defect == "ce-denied")
            Assert.IsType<ConstitutionalActionDeniedException>(failure);
        else if (defect == "participant-after-ce")
            Assert.IsType<ConversationNotAccessibleException>(failure);
        else if (defect == "stop-after-read")
            Assert.IsType<ConversationStoppedException>(failure);
        else if (
            defect
            is "projection-after-ce"
                or "projection-after-read"
                or "source-after-read"
                or "invalid-result"
        )
            Assert.IsType<ConversationStateConflictException>(failure);
        else
            Assert.IsType<ConversationExecutionUnavailableException>(failure);
        runtime.Verify(
            value =>
                value.ReadTerminalAsync(
                    It.IsAny<ConversationOriginalSourceV1>(),
                    It.IsAny<ConversationReconciliationAuthority>(),
                    0,
                    It.IsAny<CancellationToken>()
                ),
            defect.EndsWith("-after-read", StringComparison.Ordinal) || defect == "invalid-result"
                ? Times.Once()
                : Times.Never()
        );
        await using var db = fixture.Conversations.CreateDbContext();
        Assert.Single(await db.Messages.ToListAsync());
        Assert.Empty(await db.Events.ToListAsync());
        Assert.Empty(await db.RuntimeEventReceipts.ToListAsync());
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
        Assert.All(
            await db.ReconciliationAuthorities.ToListAsync(),
            permission => Assert.Null(permission.ResponseJson)
        );
    }

    [Theory]
    [InlineData("none")]
    [InlineData("requester")]
    [InlineData("original-membership")]
    [InlineData("participant")]
    [InlineData("projection")]
    [InlineData("stop")]
    [InlineData("source")]
    [InlineData("schema")]
    [InlineData("authority")]
    [InlineData("message")]
    [InlineData("relationship")]
    [InlineData("reservation")]
    [InlineData("input-usage")]
    [InlineData("output-usage")]
    [InlineData("idempotency")]
    [InlineData("role")]
    [InlineData("source-digest")]
    [InlineData("permission-expiry")]
    [InlineData("permission-version")]
    [InlineData("sequence")]
    public async Task AirContentReadUsesPersistedFreshPermissionAndCurrentOriginalOwner(
        string defect
    )
    {
        await using var fixture = await Fixture.CreateAsync(contentRecovery: true);
        var config = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["IdentityBrokerRead:ActorIssuer"] = fixture.Permission.Issuer,
                }
            )
            .Build();
        var identity = new ConversationRuntimeIdentityAuthority(config);
        var owner = new ConversationInferenceOwner(
            fixture.Conversations,
            fixture.Relationships,
            fixture.Ingestion,
            null!,
            identity,
            new ConversationInferenceEvidence(config, fixture.Clock),
            Mock.Of<IWhatsAppCapabilityGate>(),
            config,
            fixture.Clock
        );
        var mandate = JsonSerializer.Deserialize<OperationalMandateV1>(
            fixture.OriginalMandateJson,
            ConversationReconciliationBinding.Json
        )!;
        var original = new ConversationInferenceRequest(
            fixture.Source.Caller.RuntimeExecutionId,
            fixture.Source.ConversationId,
            fixture.Source.MessageId,
            fixture.Source.RelationshipId,
            new string('a', 64),
            Convert.ToHexStringLower(
                SHA256.HashData(Encoding.UTF8.GetBytes("original customer text"))
            ),
            "en",
            mandate
        );
        var permission = new RuntimeReconciliationRequestV1(
            "1.0",
            fixture.Source.MessageId,
            fixture.Permission.SourceDigest,
            0,
            fixture.Permission.AuthorityId,
            fixture.Permission.ExpiresAt,
            fixture.Permission.ExpectedProjectionVersion
        );
        var caller = new InferenceCaller(
            fixture.Source.TenantId,
            fixture.Source.RelationshipId,
            fixture.Permission.RequesterId,
            fixture.Permission.Role,
            fixture.Source.MessageId,
            fixture.Permission.AuthorityId,
            fixture.Permission.IdempotencyKey
        );
        if (defect == "requester")
            caller = caller with { ActorId = Guid.NewGuid() };
        else if (defect == "source")
            original = original with { InputDigest = new string('b', 64) };
        else if (defect == "schema")
            permission = permission with { SchemaVersion = "2.0" };
        else if (defect == "authority")
            caller = caller with { ExecutionId = Guid.NewGuid() };
        else if (defect == "message")
            original = original with { ContributionRef = Guid.NewGuid() };
        else if (defect == "relationship")
            original = original with { RelationshipRef = Guid.NewGuid() };
        else if (defect == "reservation")
            original = original with { ReservationId = Guid.NewGuid() };
        else if (defect == "input-usage")
            original = original with { InputTokens = 1 };
        else if (defect == "output-usage")
            original = original with { OutputTokens = 1 };
        else if (defect == "idempotency")
            caller = caller with { IdempotencyKey = Guid.NewGuid() };
        else if (defect == "role")
            caller = caller with { Role = "MANAGER" };
        else if (defect == "source-digest")
            permission = permission with { OriginalSourceDigest = new string('b', 64) };
        else if (defect == "permission-expiry")
            permission = permission with
            {
                PermissionExpiresAt = permission.PermissionExpiresAt.AddSeconds(1),
            };
        else if (defect == "permission-version")
            permission = permission with
            {
                ExpectedProjectionVersion = permission.ExpectedProjectionVersion + 1,
            };
        else if (defect == "sequence")
            permission = permission with { AfterSequence = 1 };
        else if (defect != "none")
            await fixture.ExecuteAsync(
                defect switch
                {
                    "original-membership" =>
                        $"UPDATE identity.actor_bindings SET status='REVOKED' WHERE actor_subject='{fixture.Source.Caller.ActorId:D}'",
                    "participant" =>
                        $"UPDATE business.relationship_participants SET status='REMOVED' WHERE participant_id='{fixture.Source.Caller.ActorId:D}'",
                    "projection" =>
                        "UPDATE business.conversation_executions SET projection_version=projection_version+1",
                    _ =>
                        $"INSERT INTO constitutional.employment_dispatch_stops VALUES ('{fixture.Source.TenantId:D}', '{fixture.Source.RelationshipId:D}')",
                }
            );
        if (defect == "none")
        {
            Assert.Equal(
                "READ_ALLOWED",
                (
                    await owner.ReadContentAsync(
                        caller,
                        new(original, permission),
                        CancellationToken.None
                    )
                ).State
            );
            Assert.True(mandate.Deadline < DateTimeOffset.UtcNow);
        }
        else if (defect == "stop")
            await Assert.ThrowsAsync<ConversationStoppedException>(() =>
                owner.ReadContentAsync(caller, new(original, permission), CancellationToken.None)
            );
        else
            await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
                owner.ReadContentAsync(caller, new(original, permission), CancellationToken.None)
            );
        await using var db = fixture.Conversations.CreateDbContext();
        Assert.Single(await db.Messages.ToListAsync());
        Assert.Empty(await db.Events.ToListAsync());
        Assert.Empty(await db.RuntimeEventReceipts.ToListAsync());
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
        Assert.Null((await db.ReconciliationAuthorities.SingleAsync()).ResponseJson);
    }

    [Fact]
    public async Task FreshOwnerRecoversExpiredOriginalMandateWithoutRenewingOriginalAuthority()
    {
        await using var fixture = await Fixture.CreateAsync();
        var outcome = await fixture.Ingestion.ApplyReconciliationAsync(
            fixture.Source,
            fixture.Permission.AuthorityId,
            fixture.Result(),
            CancellationToken.None
        );
        Assert.Equal("COMPLETED", outcome.State);
        Assert.Equal(2, outcome.ProjectionVersion);
        await using var db = fixture.Conversations.CreateDbContext();
        var execution = await db.Executions.SingleAsync();
        Assert.True(execution.RuntimeTerminal);
        Assert.Null(execution.RuntimeAccountId);
        Assert.Null(execution.RuntimeActorId);
        Assert.Equal(2, await db.RuntimeEventReceipts.CountAsync());
        Assert.Equal(2, await db.Events.CountAsync());
        var input = await db.Messages.SingleAsync(value =>
            value.MessageId == fixture.Source.MessageId
        );
        using var originalInput = JsonDocument.Parse(input.ContentJson);
        Assert.Equal(
            "original customer text",
            originalInput.RootElement[0].GetProperty("text").GetString()
        );
        Assert.Equal("1.0", originalInput.RootElement[0].GetProperty("schemaVersion").GetString());
        Assert.Equal("TEXT", originalInput.RootElement[0].GetProperty("blockType").GetString());
        var reply = await db.Messages.SingleAsync(value => value.Actor == "PROFESSIONAL");
        Assert.Contains("Recovered professional answer", reply.ContentJson);
        Assert.NotNull((await db.ReconciliationAuthorities.SingleAsync()).ResponseJson);
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
        await using var authority = fixture.Relationships.CreateDbContext();
        using var originalMandate = JsonDocument.Parse(fixture.OriginalMandateJson);
        using var persistedMandate = JsonDocument.Parse(
            (await authority.OperationalMandateSnapshots.SingleAsync()).MandateJson
        );
        Assert.Equal(
            AgentAdmissionCanonicalizer.Digest(originalMandate.RootElement),
            AgentAdmissionCanonicalizer.Digest(persistedMandate.RootElement)
        );
        Assert.True(
            (await authority.OperationalMandateSnapshots.SingleAsync()).Deadline
                < DateTimeOffset.UtcNow
        );
    }

    [Theory]
    [InlineData("FAILED", "execution.failed", "PARTIAL_FAILURE")]
    [InlineData("CANCELLED", "execution.cancelled", "CANCELLED")]
    public async Task RecoveryPreservesNonSuccessTerminalMeaning(
        string state,
        string eventType,
        string reason
    )
    {
        await using var fixture = await Fixture.CreateAsync();
        var result = fixture.Result();
        result = result with
        {
            State = state,
            Events =
            [
                result.Events[0],
                result.Events[1] with
                {
                    EventType = eventType,
                    Data = JsonSerializer.SerializeToElement(
                        new
                        {
                            state,
                            partial = true,
                            completionReason = reason,
                        }
                    ),
                },
            ],
        };
        var outcome = await fixture.Ingestion.ApplyReconciliationAsync(
            fixture.Source,
            fixture.Permission.AuthorityId,
            result,
            CancellationToken.None
        );
        Assert.Equal(state, outcome.State);
        await using var db = fixture.Conversations.CreateDbContext();
        var execution = await db.Executions.SingleAsync();
        Assert.Equal(state, execution.ProcessingState);
        Assert.Equal(reason, execution.CompletionReason);
        Assert.True(execution.Partial);
        Assert.True(execution.RuntimeTerminal);
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
    }

    [Fact]
    public async Task RecoveryReplayCannotDuplicateMessagesReceiptsOrProjectionVersion()
    {
        await using var fixture = await Fixture.CreateAsync();
        var first = await fixture.Ingestion.ApplyReconciliationAsync(
            fixture.Source,
            fixture.Permission.AuthorityId,
            fixture.Result(),
            CancellationToken.None
        );
        var replay = await fixture.Ingestion.ApplyReconciliationAsync(
            fixture.Source,
            fixture.Permission.AuthorityId,
            fixture.Result(),
            CancellationToken.None
        );
        Assert.True(replay.Replayed);
        Assert.Equal(first.ProjectionVersion, replay.ProjectionVersion);
        await using var db = fixture.Conversations.CreateDbContext();
        Assert.Equal(2, await db.Messages.CountAsync());
        Assert.Equal(2, await db.RuntimeEventReceipts.CountAsync());
        Assert.Equal(2, await db.Events.CountAsync());
    }

    [Fact]
    public async Task DivergentReplayCannotHideChangedEventsBehindARepeatedReceiptDigest()
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.Ingestion.ApplyReconciliationAsync(
            fixture.Source,
            fixture.Permission.AuthorityId,
            fixture.Result(),
            CancellationToken.None
        );
        var changed = fixture.Result();
        changed = changed with
        {
            Events =
            [
                changed.Events[0] with
                {
                    Data = JsonSerializer.SerializeToElement(
                        new
                        {
                            contentIndex = 0,
                            appendText = "changed",
                            partial = true,
                        }
                    ),
                },
                changed.Events[1],
            ],
        };
        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            fixture.Ingestion.ApplyReconciliationAsync(
                fixture.Source,
                fixture.Permission.AuthorityId,
                changed,
                CancellationToken.None
            )
        );
        await using var db = fixture.Conversations.CreateDbContext();
        Assert.Contains(
            "Recovered professional answer",
            (await db.Messages.SingleAsync(value => value.Actor == "PROFESSIONAL")).ContentJson
        );
        Assert.Equal(2, await db.RuntimeEventReceipts.CountAsync());
    }

    [Theory]
    [InlineData("invalid-terminal")]
    [InlineData("sequence-gap")]
    [InlineData("expiry-during-tail")]
    [InlineData("wrong-next-action")]
    [InlineData("invalid-digest")]
    public async Task TailFailureRollsBackAllEarlierEventsOutputAndAuthorityResult(string defect)
    {
        await using var fixture = await Fixture.CreateAsync();
        var result = fixture.Result();
        if (defect == "invalid-terminal")
            result = result with
            {
                Events =
                [
                    result.Events[0],
                    result.Events[1] with
                    {
                        Data = JsonSerializer.SerializeToElement(
                            new
                            {
                                state = "COMPLETED",
                                partial = false,
                                completionReason = "PARTIAL_FAILURE",
                            }
                        ),
                    },
                ],
            };
        if (defect == "sequence-gap")
            result = result with
            {
                Events =
                [
                    result.Events[0],
                    result.Events[1] with
                    {
                        Sequence = 3,
                        EventId = $"{fixture.Source.Caller.RuntimeExecutionId:D}:3",
                    },
                ],
            };
        if (defect == "expiry-during-tail")
            fixture.Clock.ExpireAfterFirstReceipt = true;
        if (defect == "wrong-next-action")
            result = result with { NextAction = "OPERATOR_RECONCILIATION_REQUIRED" };
        if (defect == "invalid-digest")
            result = result with { ResultDigest = "not-a-digest" };
        var failure = await Record.ExceptionAsync(() =>
            fixture.Ingestion.ApplyReconciliationAsync(
                fixture.Source,
                fixture.Permission.AuthorityId,
                result,
                CancellationToken.None
            )
        );
        Assert.NotNull(failure);
        Assert.True(
            failure
                is JsonException
                    or ConversationStateConflictException
                    or ConversationNotAccessibleException
        );
        await fixture.AssertUnchangedAsync();
    }

    [Theory]
    [InlineData("membership")]
    [InlineData("stop")]
    [InlineData("projection")]
    public async Task RevokedOrChangedAuthorityCannotProjectRetainedContent(string defect)
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ExecuteAsync(
            defect switch
            {
                "membership" => "UPDATE identity.memberships SET status = 'REMOVED'",
                "stop" =>
                    $"INSERT INTO constitutional.employment_dispatch_stops VALUES ('{fixture.Source.TenantId:D}', '{fixture.Source.RelationshipId:D}')",
                _ => "UPDATE business.conversation_executions SET projection_version = 1",
            }
        );
        var failure = await Record.ExceptionAsync(() =>
            fixture.Ingestion.ApplyReconciliationAsync(
                fixture.Source,
                fixture.Permission.AuthorityId,
                fixture.Result(),
                CancellationToken.None
            )
        );
        Assert.NotNull(failure);
        Assert.True(
            failure
                is ConversationNotAccessibleException
                    or ConversationStoppedException
                    or ConversationStateConflictException
        );
        await fixture.AssertUnchangedAsync(expectedVersion: defect == "projection" ? 1 : 0);
    }

    [Theory]
    [InlineData("none", true)]
    [InlineData("membership", false)]
    [InlineData("consent", false)]
    [InlineData("binding", false)]
    [InlineData("stop", false)]
    [InlineData("stopped-at", false)]
    [InlineData("cancelled-execution", false)]
    [InlineData("expired-permission", false)]
    [InlineData("cancelled-outbox", false)]
    [InlineData("erased-message", false)]
    [InlineData("changed-content", false)]
    public async Task FinalEgressAdmissionRechecksCommittedRecoveryAndCurrentRecipient(
        string defect,
        bool allowed
    )
    {
        await using var fixture = await Fixture.CreateAsync(whatsApp: true);
        await fixture.Ingestion.ApplyReconciliationAsync(
            fixture.Source,
            fixture.Permission.AuthorityId,
            fixture.Result(),
            CancellationToken.None
        );
        await using var db = fixture.Conversations.CreateDbContext();
        var record = await db.ConversationOutbox.SingleAsync();
        record.State = "DISPATCHING";
        record.LeaseOwner = "recovery-test-worker";
        record.LeaseExpiresAt = DateTimeOffset.UtcNow.AddMinutes(1);
        await db.SaveChangesAsync();
        if (defect != "none")
            await fixture.ExecuteAsync(
                defect switch
                {
                    "membership" => "UPDATE identity.memberships SET status = 'REMOVED'",
                    "consent" =>
                        "UPDATE business.whatsapp_journey_contacts SET opted_out_at = now()",
                    "binding" => "UPDATE business.channel_bindings SET status = 'WITHDRAWN'",
                    "stop" =>
                        $"INSERT INTO constitutional.employment_dispatch_stops VALUES ('{fixture.Source.TenantId:D}', '{fixture.Source.RelationshipId:D}')",
                    "stopped-at" =>
                        "UPDATE business.employment_relationships SET stopped_at = now()",
                    "cancelled-execution" =>
                        "UPDATE business.conversation_executions SET processing_state = 'CANCELLED'",
                    "expired-permission" =>
                        "UPDATE business.conversation_reconciliation_authorities SET created_at = now() - interval '10 minutes', expires_at = now() - interval '5 minutes'",
                    "erased-message" =>
                        "DELETE FROM business.conversation_messages WHERE actor = 'PROFESSIONAL'",
                    "changed-content" =>
                        """UPDATE business.conversation_messages SET content_json = '[{"schemaVersion":"1.0","blockType":"TEXT","text":"different output"}]' WHERE actor = 'PROFESSIONAL'""",
                    _ => "UPDATE business.conversation_outbox SET state = 'BLOCKED'",
                }
            );
        Assert.Equal(
            allowed,
            await fixture.Outbox.AuthorizeRuntimeEgressAsync(
                record,
                fixture.Clock,
                CancellationToken.None
            )
        );
        var current = await db.Executions.AsNoTracking().SingleAsync();
        Assert.True(current.RuntimeTerminal);
        Assert.Equal(
            defect == "cancelled-execution" ? "CANCELLED" : "COMPLETED",
            current.ProcessingState
        );
        Assert.Equal(2, await db.RuntimeEventReceipts.CountAsync());
    }

    private sealed class ReceiptClock : TimeProvider
    {
        private DateTimeOffset _now = DateTimeOffset.UtcNow;
        public bool ExpireAfterFirstReceipt { get; set; }

        public override DateTimeOffset GetUtcNow() => _now;

        public void ReceiptInserted(DbCommand command)
        {
            if (
                ExpireAfterFirstReceipt
                && command.CommandText.Contains("INSERT INTO", StringComparison.Ordinal)
                && command.CommandText.Contains(
                    "conversation_runtime_event_receipts",
                    StringComparison.Ordinal
                )
            )
            {
                _now = _now.AddMinutes(6);
                ExpireAfterFirstReceipt = false;
            }
        }
    }

    private sealed class ReceiptInterceptor(ReceiptClock clock) : DbCommandInterceptor
    {
        public override ValueTask<DbDataReader> ReaderExecutedAsync(
            DbCommand command,
            CommandExecutedEventData eventData,
            DbDataReader result,
            CancellationToken cancellationToken = default
        )
        {
            clock.ReceiptInserted(command);
            return ValueTask.FromResult(result);
        }

        public override ValueTask<int> NonQueryExecutedAsync(
            DbCommand command,
            CommandExecutedEventData eventData,
            int result,
            CancellationToken cancellationToken = default
        )
        {
            clock.ReceiptInserted(command);
            return ValueTask.FromResult(result);
        }
    }

    private sealed class ConversationFactory(string connectionString, ReceiptClock? clock = null)
        : IDbContextFactory<ConversationStoreDbContext>
    {
        private readonly DbContextOptions<ConversationStoreDbContext> _options = CreateOptions(
            connectionString,
            clock
        );

        public ConversationStoreDbContext CreateDbContext() => new(_options);

        private static DbContextOptions<ConversationStoreDbContext> CreateOptions(
            string connectionString,
            ReceiptClock? clock
        )
        {
            var builder = new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(
                connectionString
            );
            if (clock is not null)
                builder.AddInterceptors(new ReceiptInterceptor(clock));
            return builder.Options;
        }
    }

    private sealed class RelationshipFactory(string connectionString)
        : IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public EmploymentRelationshipDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            );
    }

    private sealed class Fixture(PostgreSqlContainer postgres) : IAsyncDisposable
    {
        public ConversationFactory Conversations { get; private set; } = null!;
        public RelationshipFactory Relationships { get; private set; } = null!;
        public ConversationRuntimeEventIngestion Ingestion { get; private set; } = null!;
        public WhatsAppOutboxService Outbox { get; private set; } = null!;
        public ConversationRuntimeSource Source { get; private set; } = null!;
        public ConversationReconciliationAuthority Permission { get; private set; } = null!;
        public ReceiptClock Clock { get; private set; } = null!;
        public string OriginalMandateJson { get; private set; } = "";

        public ConversationReconciliationService RecoveryService(
            IRelationshipConstitutionalGateway constitutional,
            IConversationExecutionReconciliationGateway runtime
        ) =>
            new(
                Conversations,
                Relationships,
                constitutional,
                runtime,
                new ConversationRuntimeIdentityAuthority(
                    new ConfigurationBuilder()
                        .AddInMemoryCollection(
                            new Dictionary<string, string?>
                            {
                                ["IdentityBrokerRead:ActorIssuer"] = Permission.Issuer,
                            }
                        )
                        .Build()
                ),
                Ingestion,
                Options.Create(
                    new Wc120ConversationOptions
                    {
                        Environment = "demo",
                        Enabled = true,
                        RuntimeEventIngestionEnabled = true,
                    }
                ),
                Clock
            );

        public static async Task<Fixture> CreateAsync(
            bool whatsApp = false,
            bool contentRecovery = false
        )
        {
            var postgres = new PostgreSqlBuilder("postgres:16-alpine").Build();
            await postgres.StartAsync();
            var fixture = new Fixture(postgres);
            try
            {
                await fixture.InitializeAsync(whatsApp, contentRecovery);
                return fixture;
            }
            catch
            {
                await postgres.DisposeAsync();
                throw;
            }
        }

        private async Task InitializeAsync(bool whatsApp, bool contentRecovery)
        {
            var tenant = Guid.NewGuid();
            var requester = Guid.NewGuid();
            var originalActor = Guid.NewGuid();
            var relationship = Guid.NewGuid();
            var conversation = Guid.NewGuid();
            var message = Guid.NewGuid();
            var execution = Guid.NewGuid();
            var key = Guid.NewGuid();
            var account = Guid.NewGuid();
            var membership = Guid.NewGuid();
            var snapshot = Guid.NewGuid();
            var binding = Guid.NewGuid();
            var recipient = new string('a', 64);
            const string issuer = "https://identity.test/realms/demo";
            var ownerConversations = new ConversationFactory(postgres.GetConnectionString());
            var ownerRelationships = new RelationshipFactory(postgres.GetConnectionString());
            await using var db = ownerConversations.CreateDbContext();
            await using var authority = ownerRelationships.CreateDbContext();
            await ExecuteAsync(db.Database.GenerateCreateScript());
            await ExecuteAsync(authority.Database.GenerateCreateScript());
            await ExecuteAsync(
                """
                CREATE ROLE bp_owner NOBYPASSRLS;
                CREATE ROLE identity_resolver_owner NOBYPASSRLS;
                CREATE ROLE business_app LOGIN PASSWORD 'synthetic-recovery-test' NOBYPASSRLS;
                CREATE SCHEMA identity;
                CREATE SCHEMA constitutional;
                CREATE SCHEMA ai_runtime;
                CREATE TABLE identity.actor_bindings (actor_issuer text, actor_subject text, account_id uuid, login_method_id uuid, status text);
                CREATE TABLE identity.login_methods (login_method_id uuid, account_id uuid, status text);
                CREATE TABLE identity.accounts (account_id uuid, status text);
                CREATE TABLE identity.memberships (membership_id uuid, account_id uuid, tenant_id uuid, roles text[], status text);
                CREATE TABLE business.organisations (tenant_id uuid, identity_managed bool, identity_status text);
                CREATE TABLE constitutional.employment_dispatch_stops (tenant_id uuid, relationship_ref text);
                CREATE FUNCTION ai_runtime.lock_employment_dispatch(uuid, text) RETURNS void LANGUAGE plpgsql AS $$
                BEGIN
                    PERFORM pg_advisory_xact_lock(hashtextextended('wc134-dispatch:' || $1::text || ':' || $2, 0));
                END $$;
                CREATE FUNCTION ai_runtime.employment_dispatch_relationship_key(text) RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
                GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
                GRANT SELECT ON business.conversation_messages TO bp_owner;
                GRANT USAGE ON SCHEMA business, identity TO identity_resolver_owner;
                GRANT SELECT ON ALL TABLES IN SCHEMA business, identity TO identity_resolver_owner;
                GRANT USAGE ON SCHEMA business, identity, ai_runtime, constitutional TO business_app;
                GRANT SELECT ON ALL TABLES IN SCHEMA business, constitutional TO business_app;
                GRANT INSERT, UPDATE ON business.conversation_messages, business.conversation_executions,
                    business.conversations, business.conversation_events, business.conversation_operational_signals,
                    business.conversation_outbox TO business_app;
                GRANT UPDATE (state) ON business.employment_relationships TO business_app;
                GRANT UPDATE (status) ON business.relationship_participants TO business_app;
                GRANT UPDATE (opted_out_at) ON business.whatsapp_journey_contacts TO business_app;
                GRANT UPDATE (status) ON business.channel_bindings TO business_app;
                """
            );
            var login = Guid.NewGuid();
            await ExecuteAsync(
                $"""
                INSERT INTO identity.actor_bindings VALUES ('{issuer}', '{requester:D}', '{account:D}', '{login:D}', 'ACTIVE');
                INSERT INTO identity.login_methods VALUES ('{login:D}', '{account:D}', 'ACTIVE');
                INSERT INTO identity.accounts VALUES ('{account:D}', 'ACTIVE');
                INSERT INTO identity.memberships VALUES ('{membership:D}', '{account:D}', '{tenant:D}', ARRAY['OWNER'], 'ACTIVE');
                INSERT INTO business.organisations VALUES ('{tenant:D}', true, 'ACTIVE');
                """
            );
            if (contentRecovery)
                await ExecuteAsync(
                    $"""
                    INSERT INTO identity.actor_bindings VALUES ('{issuer}', '{originalActor:D}', '{account:D}', '{login:D}', 'ACTIVE');
                    """
                );
            foreach (
                var migration in new[]
                {
                    "87-wc134-runtime-event-projection.sql",
                    "88-wc134-runtime-identity-authority.sql",
                    "89-wc134-runtime-work-directory.sql",
                    "90-wc134-conversation-reconciliation-authority.sql",
                }
            )
                await ExecuteAsync(
                    await File.ReadAllTextAsync(
                        RepositoryPaths.Resolve($"infrastructure/postgres/init/{migration}")
                    )
                );
            var mandate = await new OperationalMandateResolverStub().ResolveAsync(
                tenant,
                originalActor,
                relationship,
                key,
                Guid.NewGuid(),
                "skill",
                "original purpose",
                CancellationToken.None
            );
            mandate = mandate with { Deadline = DateTimeOffset.UtcNow.AddMinutes(-10) };
            if (contentRecovery)
                mandate = mandate with
                {
                    ConversationOperation = new(
                        "PROFESSIONAL_RESPONSE",
                        "RESPOND",
                        "sha256:" + new string('a', 64),
                        "sha256:" + new string('b', 64),
                        new("prompt:synthetic", "1", "sha256:" + new string('c', 64)),
                        new("model:synthetic", "1", "sha256:" + new string('d', 64))
                    ),
                };
            using var material = JsonDocument.Parse(
                JsonSerializer.Serialize(mandate, ConversationReconciliationBinding.Json)
            );
            var unsigned = material
                .RootElement.EnumerateObject()
                .Where(value => value.Name != "mandateDigest")
                .ToDictionary(value => value.Name, value => value.Value);
            mandate = mandate with
            {
                MandateDigest = ConversationReconciliationBinding.Digest(unsigned),
            };
            OriginalMandateJson = JsonSerializer.Serialize(
                mandate,
                ConversationReconciliationBinding.Json
            );
            db.Conversations.Add(
                new()
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    ConversationId = conversation,
                    Environment = "demo",
                    NextMessageSequence = 2,
                }
            );
            db.Messages.Add(
                new()
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    ConversationId = conversation,
                    MessageId = message,
                    Environment = "demo",
                    Sequence = 1,
                    EvidenceRecordId = Guid.NewGuid(),
                    Channel = whatsApp ? "WHATSAPP" : "WEB",
                    ContentJson = contentRecovery
                        ? """[{"schemaVersion":"1.0","blockType":"TEXT","text":"original customer text","language":"en"}]"""
                        : """[{"schemaVersion":"1.0","blockType":"TEXT","text":"original customer text"}]""",
                }
            );
            db.Executions.Add(
                new()
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    ConversationId = conversation,
                    MessageId = message,
                    ExecutionId = execution,
                    RuntimeActorId = contentRecovery ? originalActor : null,
                    RuntimeActorIssuer = contentRecovery ? issuer : null,
                    RuntimeAccountId = contentRecovery ? account : null,
                    RuntimeMembershipId = contentRecovery ? membership : null,
                    OriginChannelBindingId = whatsApp ? binding : null,
                    OriginRecipientDigest = whatsApp ? recipient : null,
                }
            );
            db.IdempotencyOutcomes.Add(
                new()
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    ActorParticipantId = originalActor,
                    ExecutionId = execution,
                    MessageId = message,
                    IdempotencyKey = key,
                    OperationFamily = "SEND",
                }
            );
            await db.SaveChangesAsync();
            authority.EmploymentRelationships.Add(
                new()
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    AuthoritySnapshotId = snapshot,
                    State = EmploymentRelationshipState.Active,
                }
            );
            authority.RelationshipParticipants.Add(
                new()
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    ParticipantId = requester,
                    Role = RelationshipParticipantRole.Employer,
                }
            );
            if (contentRecovery && !whatsApp)
                authority.RelationshipParticipants.Add(
                    new()
                    {
                        TenantId = tenant,
                        RelationshipId = relationship,
                        ParticipantId = originalActor,
                        Role = RelationshipParticipantRole.Employer,
                    }
                );
            if (whatsApp)
            {
                authority.RelationshipParticipants.Add(
                    new()
                    {
                        TenantId = tenant,
                        RelationshipId = relationship,
                        ParticipantId = originalActor,
                        Role = RelationshipParticipantRole.Employer,
                    }
                );
                authority.ChannelBindings.Add(
                    new()
                    {
                        BindingId = binding,
                        TenantId = tenant,
                        RelationshipId = relationship,
                        ParticipantId = originalActor,
                        ParticipantRole = "EMPLOYER",
                        Channel = "WHATSAPP",
                        ExternalSubjectHash = recipient,
                        ConversationId = conversation.ToString("D"),
                        Status = "ACTIVE",
                    }
                );
                authority.WhatsAppJourneyContacts.Add(
                    new()
                    {
                        TenantId = tenant,
                        PhoneHmac = recipient,
                        OptedInAt = DateTimeOffset.UtcNow.AddMinutes(-5),
                        LastInboundAt = DateTimeOffset.UtcNow.AddMinutes(-1),
                    }
                );
            }
            authority.DecisionSpaceSnapshots.Add(
                new()
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    SnapshotId = snapshot,
                    Version = 1,
                }
            );
            authority.OperationalMandateSnapshots.Add(
                new()
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    ActorParticipantId = originalActor,
                    IdempotencyIdentity = key,
                    MandateId = mandate.MandateId,
                    MandateDigest = mandate.MandateDigest,
                    MandateJson = OriginalMandateJson,
                    Deadline = mandate.Deadline,
                }
            );
            await authority.SaveChangesAsync();
            var bound = await ConversationReconciliationBinding.SourceAsync(
                db,
                authority,
                await db.Executions.SingleAsync(),
                "demo",
                CancellationToken.None
            );
            Source = bound.Source;
            var now = DateTimeOffset.UtcNow;
            Permission = new()
            {
                AuthorityId = Guid.NewGuid(),
                TenantId = tenant,
                RelationshipId = relationship,
                ExecutionId = execution,
                RequesterId = requester,
                Issuer = issuer,
                AccountId = account,
                MembershipId = membership,
                Role = "OWNER",
                DecisionSpaceSnapshotId = snapshot,
                DecisionSpaceVersion = 1,
                EvidenceId = Guid.NewGuid(),
                SourceDigest = ConversationReconciliationBinding.Digest(bound.Original),
                IdempotencyKey = Guid.NewGuid(),
                RequestDigest = "sha256:" + new string('a', 64),
                CreatedAt = now,
                ExpiresAt = now.AddMinutes(5),
            };
            db.ReconciliationAuthorities.Add(Permission);
            await db.SaveChangesAsync();
            var app = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
            {
                Username = "business_app",
                Password = "synthetic-recovery-test",
                Options = $"-c app.current_tenant_id={tenant:D}",
            }.ConnectionString;
            Clock = new();
            Conversations = new(app, Clock);
            Relationships = new(app);
            var identity = new ConversationRuntimeIdentityAuthority(
                new ConfigurationBuilder()
                    .AddInMemoryCollection(
                        new Dictionary<string, string?>
                        {
                            ["IdentityBrokerRead:ActorIssuer"] = issuer,
                        }
                    )
                    .Build()
            );
            var options = Options.Create(
                new Wc120ConversationOptions
                {
                    Environment = "demo",
                    Enabled = true,
                    DispatchEnabled = true,
                    RuntimeEventIngestionEnabled = true,
                }
            );
            Ingestion = new(
                Conversations,
                Relationships,
                options,
                Clock,
                new ConversationCursorCodec(
                    Options.Create(
                        new ConversationCursorOptions
                        {
                            HmacKey = "synthetic-recovery-cursor-key-at-least-32-characters",
                        }
                    )
                ),
                identity
            );
            Outbox = new(
                Conversations,
                Relationships,
                options,
                Mock.Of<Microsoft.Extensions.Options.IOptionsMonitor<WhatsAppJourneyOptions>>(),
                new ConversationStopFence(Conversations, options),
                identity
            );
        }

        public RuntimeReconciliationResultV1 Result() =>
            new(
                "1.0",
                Source.ConversationId,
                Source.Caller.RuntimeExecutionId,
                Source.MessageId,
                Permission.SourceDigest,
                Permission.AuthorityId,
                "COMPLETED",
                [
                    Event(
                        1,
                        "response.delta",
                        new
                        {
                            contentIndex = 0,
                            appendText = "Recovered professional answer",
                            partial = true,
                        }
                    ),
                    Event(
                        2,
                        "execution.completed",
                        new
                        {
                            state = "COMPLETED",
                            partial = false,
                            completionReason = "COMPLETE",
                        }
                    ),
                ],
                "RECONCILE_CANONICAL_PROJECTION",
                "sha256:" + new string('b', 64),
                "sha256:" + new string('c', 64)
            );

        private RuntimeExecutionEventV1 Event(long sequence, string type, object data) =>
            new(
                "1.0",
                $"{Source.Caller.RuntimeExecutionId:D}:{sequence}",
                type,
                Source.ConversationId,
                Source.Caller.RuntimeExecutionId,
                Source.MessageId,
                sequence,
                Permission.CreatedAt,
                JsonSerializer.SerializeToElement(data)
            );

        public async Task AssertUnchangedAsync(long expectedVersion = 0)
        {
            await using var db = Conversations.CreateDbContext();
            Assert.Single(await db.Messages.ToListAsync());
            Assert.Empty(await db.RuntimeEventReceipts.ToListAsync());
            Assert.Empty(await db.Events.ToListAsync());
            Assert.Empty(await db.ConversationOutbox.ToListAsync());
            var execution = await db.Executions.SingleAsync();
            Assert.False(execution.RuntimeTerminal);
            Assert.Equal(0, execution.RuntimeSequence);
            Assert.Equal(expectedVersion, execution.ProjectionVersion);
            var permission = await db.ReconciliationAuthorities.SingleAsync();
            Assert.Null(permission.ResultDigest);
            Assert.Null(permission.ResponseJson);
        }

        public async Task ExecuteAsync(string sql)
        {
            await using var connection = new NpgsqlConnection(postgres.GetConnectionString());
            await connection.OpenAsync();
            await using var command = new NpgsqlCommand(sql, connection);
            await command.ExecuteNonQueryAsync();
        }

        public async ValueTask DisposeAsync() => await postgres.DisposeAsync();
    }
}
