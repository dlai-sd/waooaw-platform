// Implements: WC-134 governed generation source and financial receipt authority.
// constitutional_basis: C-023, C-026, C-059, C-063
using System.Diagnostics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.ConstitutionalEngine.Grpc;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationInferenceOwnerPostgresTests
{
    [Theory]
    [InlineData("SETTLED", 1L, 1L, 2L)]
    [InlineData("SETTLED", 9000L, 2500L, 2L)]
    [InlineData("RELEASED", 0L, 0L, 0L)]
    public async Task GovernedReservationAndSettlementUseSignedMtlsEvidenceAndFullActuals(
        string state,
        long inputTokens,
        long outputTokens,
        long expectedCost
    )
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ConfigureEvidenceAsync();
        var permit = await fixture.Owner.ReserveAsync(
            fixture.Caller,
            fixture.Request,
            CancellationToken.None
        );
        Assert.Equal(2m, permit.MaximumCostPaise);
        Assert.InRange(
            permit.ExpiresAt,
            DateTimeOffset.UtcNow.AddSeconds(20),
            DateTimeOffset.UtcNow.AddSeconds(31)
        );
        Assert.Equal(1, fixture.EvidenceServer!.ValidateCalls);
        Assert.Equal(1, fixture.EvidenceServer.RecordCalls);
        var reserved = await fixture.Owner.ReconcileAsync(
            fixture.Caller,
            fixture.Request,
            CancellationToken.None
        );
        Assert.Equal("RESERVED", reserved.State);
        Assert.Equal(permit.ReservationId, reserved.ReservationId);
        var settlement = fixture.Request with
        {
            ReservationId = permit.ReservationId,
            CommercialReservationId = permit.CommercialReservationId,
            InputTokens = state == "RELEASED" ? null : inputTokens,
            OutputTokens = state == "RELEASED" ? null : outputTokens,
        };
        await fixture.Owner.SettleAsync(
            fixture.Caller,
            settlement,
            state == "RELEASED",
            CancellationToken.None
        );
        await fixture.Owner.SettleAsync(
            fixture.Caller,
            settlement,
            state == "RELEASED",
            CancellationToken.None
        );
        Assert.Equal(2, fixture.EvidenceServer.RecordCalls);
        Assert.Equal(
            state,
            (
                await fixture.Owner.ReconcileAsync(
                    fixture.Caller,
                    fixture.Request,
                    CancellationToken.None
                )
            ).State
        );
        await using var connection = fixture.OwnerConnection();
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            "SELECT actual_paise,overrun,input_tokens,output_tokens FROM business.conversation_model_reservations",
            connection
        );
        await using var reader = await command.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        Assert.Equal(expectedCost, reader.GetDecimal(0));
        Assert.Equal(inputTokens > 8192 || outputTokens > 2048, reader.GetBoolean(1));
        if (state == "RELEASED")
        {
            Assert.True(reader.IsDBNull(2));
            Assert.True(reader.IsDBNull(3));
        }
        else
        {
            Assert.Equal(inputTokens, reader.GetInt64(2));
            Assert.Equal(outputTokens, reader.GetInt64(3));
        }
        await using var db = fixture.Database();
        Assert.Single(await db.Messages.ToListAsync());
        Assert.Empty(await db.Events.ToListAsync());
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
    }

    [Theory]
    [InlineData("denied")]
    [InlineData("invalid-evidence")]
    [InlineData("budget")]
    public async Task ReservationEvidenceAndSharedBudgetFailuresDoNotReleaseAFalsePermit(
        string defect
    )
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ConfigureEvidenceAsync(defect);
        if (defect == "budget")
            fixture.Activation = fixture.Activation with { MaximumSpendInr = 0 };
        var failure = await Record.ExceptionAsync(() =>
            fixture.Owner.ReserveAsync(fixture.Caller, fixture.Request, CancellationToken.None)
        );
        if (defect == "denied")
            Assert.IsType<ConstitutionalActionDeniedException>(failure);
        else if (defect == "invalid-evidence")
            Assert.IsType<IdentityConstitutionalUnavailableException>(failure);
        else
            Assert.Equal(
                "COMBINED_DAILY_COST_EXHAUSTED",
                Assert.IsType<WhatsAppCapabilityUnavailableException>(failure).ReasonCode
            );
        await fixture.AssertNoUsageAsync();
    }

    [Fact]
    public async Task ResolveReadsExactAdmittedSourceWithoutDispatchOrFinancialMutation()
    {
        await using var fixture = await Fixture.CreateAsync();
        var result = await fixture.Owner.ResolveAsync(
            fixture.Caller,
            fixture.Request,
            CancellationToken.None
        );
        Assert.Equal(fixture.BindingId, result.GetProperty("bindingId").GetGuid());
        Assert.Equal(
            fixture.Request.ContributionRef,
            result.GetProperty("conversationContext").GetProperty("originalMessageId").GetGuid()
        );
        Assert.Empty(
            result.GetProperty("conversationContext").GetProperty("turns").EnumerateArray()
        );
        await fixture.AssertNoUsageAsync();
    }

    [Fact]
    public async Task ResolveValidatesEveryFrozenBatchSourceAndExactOrderedDigest()
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ConfigureEvidenceAsync("batch");

        var result = await fixture.Owner.ResolveAsync(
            fixture.Caller,
            fixture.Request,
            CancellationToken.None
        );

        Assert.Equal(fixture.BindingId, result.GetProperty("bindingId").GetGuid());
        Assert.Equal(fixture.Request.Batch!.BatchId, fixture.Caller.IdempotencyKey);
        await fixture.AssertNoUsageAsync(expectedMessages: 2);
    }

    [Fact]
    public async Task BatchWorkerDispatchesSingleReadySourceAndConsumesClaim()
    {
        await using var fixture = await Fixture.CreateAsync();

        await fixture.ProcessSinglePendingSourceAsync();
    }

    [Fact]
    public async Task BatchWorkerReplaysExactFrozenSourcesUnderCurrentAuthority()
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ConfigureEvidenceAsync("batch");

        await fixture.ProcessFrozenBatchAsync();
    }

    [Fact]
    public async Task BatchWorkerMarksLostRecoveryDispatchUnresolved()
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ConfigureEvidenceAsync("batch");

        await fixture.ProcessFrozenBatchAsync(dispatchFails: true);
    }

    [Fact]
    public async Task BindingLockIsTenantScopedReadOnlyAndFencesConcurrentRevocation()
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ExecuteAsync(
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve(
                    "infrastructure/postgres/init/98-wc134-inference-binding-row-lock.sql"
                )
            )
        );
        await using var db = fixture.Database();
        await using var transaction = await db.Database.BeginTransactionAsync();
        Assert.Equal(
            fixture.BindingId,
            await db
                .Database.SqlQuery<Guid>(
                    $"SELECT binding_id AS \"Value\" FROM business.lock_conversation_inference_bindings({fixture.Caller.TenantId}, {fixture.Caller.RelationshipId})"
                )
                .SingleAsync()
        );
        await using var revoke = fixture.OwnerConnection();
        await revoke.OpenAsync();
        await using var command = new NpgsqlCommand(
            "SET lock_timeout='100ms'; UPDATE business.conversation_inference_bindings SET active=false",
            revoke
        );
        var blocked = await Assert.ThrowsAsync<PostgresException>(() =>
            command.ExecuteNonQueryAsync()
        );
        Assert.Equal(PostgresErrorCodes.LockNotAvailable, blocked.SqlState);
        Assert.False(
            await db
                .Database.SqlQuery<bool>(
                    $"SELECT has_table_privilege('business_app','business.conversation_inference_bindings','UPDATE') AS \"Value\""
                )
                .SingleAsync()
        );
        await transaction.RollbackAsync();
        await using var foreignDb = fixture.Database();
        var denied = await Assert.ThrowsAsync<PostgresException>(() =>
            foreignDb
                .Database.SqlQuery<Guid>(
                    $"SELECT binding_id AS \"Value\" FROM business.lock_conversation_inference_bindings({Guid.NewGuid()}, {fixture.Caller.RelationshipId})"
                )
                .ToListAsync()
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
    }

    [Fact]
    public async Task ReservationFailsWithoutConstitutionalEvidenceAndDoesNotSpend()
    {
        await using var fixture = await Fixture.CreateAsync();
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            fixture.Owner.ReserveAsync(fixture.Caller, fixture.Request, CancellationToken.None)
        );
        await fixture.AssertNoUsageAsync();
    }

    [Theory]
    [InlineData("SETTLED", false)]
    [InlineData("RELEASED", true)]
    public async Task FinancialReceiptAndExactSettlementReplaySurviveRevokedExecutionAuthority(
        string state,
        bool release
    )
    {
        await using var fixture = await Fixture.CreateAsync();
        var reservation = await fixture.SeedReservationAsync(state);
        await fixture.ExecuteAsync("UPDATE identity.actor_bindings SET status='REVOKED'");
        await fixture.ExecuteAsync(
            $"INSERT INTO constitutional.employment_dispatch_stops VALUES ('{fixture.Caller.TenantId:D}', '{fixture.Caller.RelationshipId:D}')"
        );
        var receipt = await fixture.Owner.ReconcileAsync(
            fixture.Caller,
            fixture.Request,
            CancellationToken.None
        );
        Assert.Equal(state, receipt.State);
        Assert.Equal(reservation, receipt.ReservationId);
        var settlement = fixture.Request with
        {
            ReservationId = reservation,
            InputTokens = release ? null : 1,
            OutputTokens = release ? null : 1,
        };
        await fixture.Owner.SettleAsync(
            fixture.Caller,
            settlement,
            release,
            CancellationToken.None
        );
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            fixture.Owner.SettleAsync(
                fixture.Caller,
                release
                    ? settlement with
                    {
                        InputTokens = 1,
                    }
                    : settlement with
                    {
                        OutputTokens = 2,
                    },
                release,
                CancellationToken.None
            )
        );
        await using var db = fixture.Database();
        Assert.Single(await db.Messages.ToListAsync());
        Assert.Empty(await db.Events.ToListAsync());
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
    }

    [Theory]
    [InlineData("reservation")]
    [InlineData("request")]
    [InlineData("actor")]
    [InlineData("idempotency")]
    [InlineData("mandate")]
    public async Task FinancialReceiptRejectsForeignOriginalIdentity(string defect)
    {
        await using var fixture = await Fixture.CreateAsync();
        var reservation = await fixture.SeedReservationAsync("RESERVED");
        var request = fixture.Request with { ReservationId = reservation };
        var caller = fixture.Caller;
        if (defect == "reservation")
            request = request with { ReservationId = Guid.NewGuid() };
        if (defect == "request")
            request = request with { RequestDigest = new string('b', 64) };
        if (defect == "actor")
            caller = caller with { ActorId = Guid.NewGuid() };
        if (defect == "idempotency")
        {
            caller = caller with { IdempotencyKey = Guid.NewGuid() };
            request = request with
            {
                OperationalMandate = request.OperationalMandate with
                {
                    IdempotencyIdentity = caller.IdempotencyKey,
                },
            };
        }
        if (defect == "mandate")
            request = request with
            {
                OperationalMandate = request.OperationalMandate with { ConfigurationRevision = 2 },
            };
        await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
            fixture.Owner.ReconcileAsync(caller, request, CancellationToken.None)
        );
    }

    [Fact]
    public async Task UnknownReceiptDoesNotBecomeReservationAndMissingEvidencePreservesFullReservation()
    {
        await using var fixture = await Fixture.CreateAsync();
        Assert.Equal(
            "UNRESOLVED",
            (
                await fixture.Owner.ReconcileAsync(
                    fixture.Caller,
                    fixture.Request,
                    CancellationToken.None
                )
            ).State
        );
        await fixture.AssertNoUsageAsync();
        var reservation = await fixture.SeedReservationAsync("RESERVED");
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            fixture.Owner.SettleAsync(
                fixture.Caller,
                fixture.Request with
                {
                    ReservationId = reservation,
                    InputTokens = 1,
                    OutputTokens = 1,
                },
                false,
                CancellationToken.None
            )
        );
        Assert.Equal(
            "RESERVED",
            (
                await fixture.Owner.ReconcileAsync(
                    fixture.Caller,
                    fixture.Request,
                    CancellationToken.None
                )
            ).State
        );
    }

    [Theory]
    [InlineData("actor", "access")]
    [InlineData("input", "access")]
    [InlineData("language", "access")]
    [InlineData("terminal", "access")]
    [InlineData("cancelled", "access")]
    [InlineData("membership", "access")]
    [InlineData("stop", "stop")]
    [InlineData("participant", "access")]
    [InlineData("mandate", "access")]
    [InlineData("binding-inactive", "unavailable")]
    [InlineData("binding-digest", "conflict")]
    [InlineData("binding-extra-field", "conflict")]
    [InlineData("binding-expired", "conflict")]
    [InlineData("provider-inactive", "unavailable")]
    [InlineData("provider-endpoint", "access")]
    [InlineData("provider-scope", "access")]
    public async Task ResolveDeniesStaleOrForeignAuthorityBeforeAnySpend(
        string defect,
        string expected
    )
    {
        await using var fixture = await Fixture.CreateAsync();
        var request = fixture.Request;
        var caller = fixture.Caller;
        if (defect == "actor")
            caller = caller with { ActorId = Guid.NewGuid() };
        else if (defect == "input")
            request = request with { InputDigest = new string('b', 64) };
        else if (defect == "language")
            request = request with { InputLanguage = "hi" };
        else if (defect == "mandate")
            request = request with
            {
                OperationalMandate = request.OperationalMandate with { ConfigurationRevision = 99 },
            };
        else
            await fixture.ExecuteAsync(
                defect switch
                {
                    "terminal" =>
                        "UPDATE business.conversation_executions SET runtime_terminal=true",
                    "cancelled" =>
                        "UPDATE business.conversation_executions SET processing_state='CANCELLED'",
                    "membership" => "UPDATE identity.actor_bindings SET status='REVOKED'",
                    "stop" =>
                        $"INSERT INTO constitutional.employment_dispatch_stops VALUES ('{caller.TenantId:D}', '{caller.RelationshipId:D}')",
                    "participant" =>
                        "UPDATE business.relationship_participants SET status='REMOVED'",
                    "binding-inactive" =>
                        "UPDATE business.conversation_inference_bindings SET active=false",
                    "binding-digest" =>
                        "UPDATE business.conversation_inference_bindings SET binding_digest='sha256:'||repeat('0',64)",
                    "binding-extra-field" =>
                        """UPDATE business.conversation_inference_bindings SET binding_json=binding_json || '{"unexpected":true}'::jsonb""",
                    "binding-expired" =>
                        """UPDATE business.conversation_inference_bindings SET binding_json=jsonb_set(binding_json,'{expiresAt}',to_jsonb('2000-01-01T00:00:00Z'::text))""",
                    "provider-inactive" => "UPDATE business.provider_configs SET active=false",
                    "provider-endpoint" =>
                        "UPDATE business.provider_configs SET mcp_server_url='https://different.invalid'",
                    _ => "UPDATE business.provider_configs SET scope_set='{}'",
                }
            );
        var failure = await Record.ExceptionAsync(() =>
            fixture.Owner.ResolveAsync(caller, request, CancellationToken.None)
        );
        switch (expected)
        {
            case "access":
                Assert.IsType<ConversationNotAccessibleException>(failure);
                break;
            case "stop":
                Assert.IsType<ConversationStoppedException>(failure);
                break;
            case "conflict":
                Assert.IsType<ConversationStateConflictException>(failure);
                break;
            default:
                Assert.IsType<ConversationExecutionUnavailableException>(failure);
                break;
        }
        await fixture.AssertNoUsageAsync();
    }

    private sealed class Factory<T>(string connection) : IDbContextFactory<T>
        where T : DbContext
    {
        public T CreateDbContext() =>
            (T)
                Activator.CreateInstance(
                    typeof(T),
                    new DbContextOptionsBuilder<T>().UseNpgsql(connection).Options
                )!;
    }

    private sealed class SyntheticOfferingUsageGateway : IAuthenticatedOfferingUsageGateway
    {
        private readonly Dictionary<Guid, OfferingUsageReceipt> _receipts = [];

        public void Seed(
            Guid invocationId,
            Guid reservationId,
            string state
        ) =>
            _receipts[invocationId] = new(
                reservationId,
                state,
                8192 + 2048,
                8192 + 2048,
                8192 + 2048,
                "MODEL_GENERATION",
                Guid.NewGuid(),
                new string('d', 64),
                false
            );

        public Task<OfferingUsageReceipt> ReserveAsync(
            OfferingUsageIdentity identity,
            long maximumUnits,
            CancellationToken ct
        )
        {
            if (!_receipts.TryGetValue(identity.InvocationId, out var receipt))
            {
                receipt = new(
                    Guid.NewGuid(),
                    "RESERVED",
                    maximumUnits,
                    maximumUnits,
                    maximumUnits,
                    identity.ComponentId,
                    Guid.NewGuid(),
                    new string('d', 64),
                    false
                );
                _receipts[identity.InvocationId] = receipt;
            }
            return Task.FromResult(receipt);
        }

        public Task<OfferingUsageReceipt> SettleAsync(
            OfferingUsageIdentity identity,
            Guid reservationId,
            long actualUnits,
            Guid evidenceId,
            CancellationToken ct
        ) => Transition(identity, reservationId, "SETTLED");

        public Task<OfferingUsageReceipt> ReleaseAsync(
            OfferingUsageIdentity identity,
            Guid reservationId,
            Guid nonDispatchEvidenceId,
            CancellationToken ct
        ) => Transition(identity, reservationId, "RELEASED");

        public Task<OfferingUsageReceipt?> ReconcileAsync(
            OfferingUsageIdentity identity,
            Guid? reservationId,
            CancellationToken ct
        ) =>
            Task.FromResult(
                _receipts.TryGetValue(identity.InvocationId, out var receipt)
                    ? receipt
                    : null
            );

        private Task<OfferingUsageReceipt> Transition(
            OfferingUsageIdentity identity,
            Guid reservationId,
            string state
        )
        {
            var current = _receipts[identity.InvocationId];
            Assert.Equal(current.ReservationId, reservationId);
            var next = current with { State = state, Replayed = current.State == state };
            _receipts[identity.InvocationId] = next;
            return Task.FromResult(next);
        }
    }

    private sealed class Fixture(PostgreSqlContainer postgres) : IAsyncDisposable
    {
        private Factory<ConversationStoreDbContext> _conversations = null!;
        private Factory<ConversationStoreDbContext> _ownerConversations = null!;
        private Factory<EmploymentRelationshipDbContext> _relationships = null!;
        private Factory<EmploymentRelationshipDbContext> _ownerRelationships = null!;
        private IConfigurationRoot _configuration = null!;
        private readonly string _credentials = Path.Combine(
            Path.GetTempPath(),
            $"wc134-inference-{Guid.NewGuid():N}"
        );
        private X509Certificate2? _serverCertificate;
        private X509Certificate2? _clientCertificate;
        private readonly X509Certificate2Collection _serverCertificateChain = new();
        private ECDsa? _delegationPublicKey;
        private readonly SyntheticOfferingUsageGateway _offeringUsage = new();
        public RawConstitutionalServer? EvidenceServer { get; private set; }
        public WhatsAppActivationAuthority Activation { get; set; } = new();
        public ConversationInferenceOwner Owner { get; private set; } = null!;
        public InferenceCaller Caller { get; private set; } = null!;
        public ConversationInferenceRequest Request { get; private set; } = null!;
        public Guid BindingId { get; } = Guid.NewGuid();

        public ConversationStoreDbContext Database() => _conversations.CreateDbContext();

        public NpgsqlConnection OwnerConnection() => new(postgres.GetConnectionString());

        public async Task ConfigureEvidenceAsync(string defect = "")
        {
            using var process =
                Process.Start(
                    new ProcessStartInfo
                    {
                        FileName = "python3",
                        ArgumentList =
                        {
                            RepositoryPaths.Resolve("scripts/bootstrap_workload_identity.py"),
                            "--registry",
                            RepositoryPaths.Resolve(
                                "infrastructure/workload-identity/registry.yaml"
                            ),
                            "--environment",
                            "ci",
                            "--output",
                            _credentials,
                        },
                        UseShellExecute = false,
                        RedirectStandardError = true,
                    }
                )
                ?? throw new InvalidOperationException(
                    "Synthetic workload credential bootstrap failed to start"
                );

                    async Task ConfigureBatchAsync()
                    {
                        var first = Request.OperationalMandate;
                        var secondKey = Guid.NewGuid();
                        var secondEvidence = Guid.NewGuid();
                        const string secondText = "Use a festive tone";
                        var second = await new OperationalMandateResolver(_ownerRelationships).ResolveAsync(
                            Caller.TenantId,
                            Caller.ActorId,
                            Caller.RelationshipId,
                            secondKey,
                            secondEvidence,
                            first.SkillId,
                            secondText,
                            CancellationToken.None
                        );
                        var secondMessage = Guid.NewGuid();
                        var secondExecution = ConversationExecutionIdentity.Create(
                            Caller.TenantId,
                            Caller.RelationshipId,
                            Caller.ActorId,
                            Request.ConversationId,
                            secondKey
                        );
                        await using (var db = _ownerConversations.CreateDbContext())
                        {
                            var conversation = await db.Conversations.SingleAsync();
                            var firstExecution = await db.Executions.SingleAsync();
                            conversation.NextMessageSequence = 3;
                            db.Messages.Add(
                                new()
                                {
                                    TenantId = Caller.TenantId,
                                    RelationshipId = Caller.RelationshipId,
                                    ConversationId = Request.ConversationId,
                                    MessageId = secondMessage,
                                    Environment = "demo",
                                    Sequence = 2,
                                    SkillId = second.SkillId,
                                    EvidenceRecordId = secondEvidence,
                                    ContentJson = JsonSerializer.Serialize(
                                        new[]
                                        {
                                            new ConversationTextBlockV1(
                                                "1.0",
                                                "TEXT",
                                                secondText,
                                                "en"
                                            ),
                                        },
                                        ConversationReconciliationBinding.Json
                                    ),
                                }
                            );
                            db.Executions.Add(
                                new()
                                {
                                    ExecutionId = secondExecution,
                                    TenantId = Caller.TenantId,
                                    RelationshipId = Caller.RelationshipId,
                                    ConversationId = Request.ConversationId,
                                    MessageId = secondMessage,
                                    RuntimeActorId = firstExecution.RuntimeActorId,
                                    RuntimeActorIssuer = firstExecution.RuntimeActorIssuer,
                                    RuntimeMembershipId = firstExecution.RuntimeMembershipId,
                                    RuntimeAccountId = firstExecution.RuntimeAccountId,
                                }
                            );
                            await db.SaveChangesAsync();
                        }
                        var workItem = Guid.NewGuid();
                        var invocation = Guid.NewGuid();
                        var batchId = Guid.NewGuid();
                        var runtimeExecution = ConversationExecutionIdentity.Create(
                            Caller.TenantId,
                            Caller.RelationshipId,
                            Caller.ActorId,
                            Request.ConversationId,
                            batchId
                        );
                        var sources = new[]
                        {
                            new ConversationInferenceBatchSourceV1(
                                "1.0",
                                Request.ContributionRef,
                                Request.ExecutionId,
                                1,
                                workItem,
                                1,
                                invocation,
                                first.IdempotencyIdentity,
                                Guid.Parse(first.ConstitutionalEvidenceRef["ce-evidence:".Length..]),
                                "Prepare the profile",
                                "en",
                                first
                            ),
                            new ConversationInferenceBatchSourceV1(
                                "1.0",
                                secondMessage,
                                secondExecution,
                                2,
                                workItem,
                                1,
                                invocation,
                                secondKey,
                                secondEvidence,
                                secondText,
                                "en",
                                second
                            ),
                        };
                        var sourceListDigest = AgentAdmissionCanonicalizer.Digest(
                            JsonSerializer.SerializeToElement(
                                sources.Select(value => new
                                {
                                    value.SchemaVersion,
                                    value.MessageId,
                                    value.ExecutionId,
                                    value.Sequence,
                                    value.WorkItemId,
                                    value.WorkItemRevision,
                                    value.WorkItemInvocationId,
                                    value.IdempotencyKey,
                                    value.EvidenceId,
                                    value.Text,
                                    value.Language,
                                    value.OperationalMandate.MandateId,
                                    value.OperationalMandate.MandateDigest,
                                }),
                                ConversationReconciliationBinding.Json
                            )
                        );
                        var prepared = HttpConversationExecutionGateway.PrepareBatchExecution(
                        batchId,
                        sources
                            .Select(value =>
                                new HttpConversationExecutionGateway.BatchExecutionSource(
                                    value.SchemaVersion,
                                    value.MessageId,
                                    value.ExecutionId,
                                    value.Sequence,
                                    value.WorkItemId,
                                    value.WorkItemRevision,
                                    value.WorkItemInvocationId,
                                    value.IdempotencyKey,
                                    value.EvidenceId,
                                    value.Text,
                                    value.Language,
                                    value.OperationalMandate
                                )
                            )
                            .ToArray()
                        );
                        await using var connection = OwnerConnection();
                        await connection.OpenAsync();
                        await using var transaction = await connection.BeginTransactionAsync();
                        await using var command = new NpgsqlCommand(
                            """
                            CREATE TABLE business.conversation_batch_groups (
                                tenant_id uuid NOT NULL, relationship_id uuid NOT NULL,
                                conversation_id uuid NOT NULL, batch_id uuid NOT NULL,
                                frozen_at timestamptz, member_count integer, dispatch_state text,
                                due_at timestamptz, work_item_id uuid, work_item_revision integer,
                                source_list_digest text, request_digest text, runtime_execution_id uuid,
                                lease_owner uuid, lease_token bigint, lease_expires_at timestamptz,
                                dispatch_intent_at timestamptz, started_at timestamptz,
                                PRIMARY KEY (tenant_id,batch_id)
                            );
                            CREATE TABLE business.conversation_batch_members (
                                tenant_id uuid NOT NULL, relationship_id uuid NOT NULL,
                                conversation_id uuid NOT NULL, batch_id uuid NOT NULL,
                                message_id uuid NOT NULL, ordinal integer NOT NULL,
                                PRIMARY KEY (tenant_id,batch_id,ordinal)
                            );
                            ALTER TABLE business.conversation_batch_groups OWNER TO business_app;
                            ALTER TABLE business.conversation_batch_members OWNER TO business_app;
                            INSERT INTO business.conversation_batch_groups
                                (tenant_id,relationship_id,conversation_id,batch_id)
                            VALUES (@tenant,@relationship,@conversation,@batch);
                            INSERT INTO business.conversation_batch_members
                                (tenant_id,relationship_id,conversation_id,batch_id,message_id,ordinal)
                            VALUES
                                (@tenant,@relationship,@conversation,@batch,@first_message,1),
                                (@tenant,@relationship,@conversation,@batch,@second_message,2);
                            UPDATE business.conversation_batch_groups
                            SET frozen_at=now(),member_count=2,dispatch_state='STARTED',
                                due_at=now(),work_item_id=@work_item,work_item_revision=1,
                                source_list_digest=@source_digest,
                                request_digest=@request_digest,
                                runtime_execution_id=@runtime_execution,
                                lease_owner=gen_random_uuid(),lease_token=1,
                                lease_expires_at=now()+interval '1 minute',
                                dispatch_intent_at=now(),started_at=now()
                            WHERE tenant_id=@tenant AND batch_id=@batch;
                            """,
                            connection,
                            transaction
                        );
                        command.Parameters.AddWithValue("tenant", Caller.TenantId);
                        command.Parameters.AddWithValue("relationship", Caller.RelationshipId);
                        command.Parameters.AddWithValue("conversation", Request.ConversationId);
                        command.Parameters.AddWithValue("first_message", Request.ContributionRef);
                        command.Parameters.AddWithValue("first_execution", Request.ExecutionId);
                        command.Parameters.AddWithValue("first_key", first.IdempotencyIdentity);
                        command.Parameters.AddWithValue(
                            "first_evidence",
                            Guid.Parse(first.ConstitutionalEvidenceRef["ce-evidence:".Length..])
                        );
                        command.Parameters.AddWithValue("first_mandate", first.MandateId);
                        command.Parameters.AddWithValue("second_message", secondMessage);
                        command.Parameters.AddWithValue("second_execution", secondExecution);
                        command.Parameters.AddWithValue("second_key", secondKey);
                        command.Parameters.AddWithValue("second_evidence", secondEvidence);
                        command.Parameters.AddWithValue("second_mandate", second.MandateId);
                        command.Parameters.AddWithValue("actor", Caller.ActorId);
                        command.Parameters.AddWithValue("work_item", workItem);
                        command.Parameters.AddWithValue("invocation", invocation);
                        command.Parameters.AddWithValue("batch", batchId);
                        command.Parameters.AddWithValue("source_digest", sourceListDigest);
                        command.Parameters.AddWithValue("request_digest", prepared.RequestDigest);
                        command.Parameters.AddWithValue("runtime_execution", runtimeExecution);
                        await command.ExecuteNonQueryAsync();
                        await transaction.CommitAsync();
                        var combined = string.Join("\n", sources.Select(value => value.Text));
                        Request = Request with
                        {
                            ExecutionId = runtimeExecution,
                            ContributionRef = batchId,
                            InputDigest = Convert.ToHexStringLower(
                                SHA256.HashData(Encoding.UTF8.GetBytes(combined))
                            ),
                            Batch = new(batchId, sourceListDigest, sources),
                        };
                        Caller = Caller with
                        {
                            ContributionId = batchId,
                            ExecutionId = runtimeExecution,
                            IdempotencyKey = batchId,
                        };
                    }
            var errors = await process.StandardError.ReadToEndAsync();
            await process.WaitForExitAsync();
            Assert.True(process.ExitCode == 0, errors);
            _serverCertificate = X509Certificate2.CreateFromPemFile(
                Path.Combine(_credentials, "workloads", "constitutional-engine", "tls-cert.pem"),
                Path.Combine(_credentials, "workloads", "constitutional-engine", "tls-key.pem")
            );
            _serverCertificateChain.ImportFromPem(
                await File.ReadAllTextAsync(Path.Combine(_credentials, "trust", "intermediate.pem"))
            );
            _clientCertificate = X509Certificate2.CreateFromPem(
                await File.ReadAllTextAsync(
                    Path.Combine(_credentials, "workloads", "business-platform", "tls-cert.pem")
                )
            );
            using var delegationCertificate = X509Certificate2.CreateFromPem(
                await File.ReadAllTextAsync(
                    Path.Combine(
                        _credentials,
                        "workloads",
                        "business-platform",
                        "delegation-cert.pem"
                    )
                )
            );
            var publicKey =
                delegationCertificate.GetECDsaPublicKey()
                ?? throw new InvalidOperationException(
                    "Synthetic delegation certificate lacks ECDSA key"
                );
            _delegationPublicKey = publicKey;
            EvidenceServer = await RawConstitutionalServer.StartAsync(
                request =>
                {
                    Assert.Equal(Caller.RelationshipId.ToString("D"), request.ContractId);
                    Assert.Equal(
                        Request.OperationalMandate.DecisionSpaceRevision,
                        request.DecisionSpaceVersion
                    );
                    Assert.Equal(ApprovalType.CustomerExplicit, request.ApprovalType);
                    Assert.Equal(DcmCategory.DeterministicRequired, request.DcmCategory);
                    return new ValidateActionResponse
                    {
                        Decision =
                            defect == "denied" ? ValidationDecision.Deny : ValidationDecision.Allow,
                        ConstitutionalBasis = "C-023",
                    };
                },
                request =>
                {
                    Assert.Equal(EvidenceState.Approved, request.State);
                    Assert.Equal(
                        Request.OperationalMandate.ProfessionalType,
                        request.ProfessionalId
                    );
                    return new RecordEvidenceResponse
                    {
                        EvidenceRecordId =
                            defect == "invalid-evidence" ? "invalid" : Guid.NewGuid().ToString("D"),
                    };
                },
                serverCertificate: _serverCertificate,
                clientCertificate: _clientCertificate,
                inspect: (context, body) =>
                {
                    var token = context.Request.Headers.Authorization.ToString();
                    Assert.StartsWith("Bearer ", token);
                    var parts = token["Bearer ".Length..].Split('.');
                    Assert.Equal(2, parts.Length);
                    static byte[] Decode(string value) =>
                        Convert.FromBase64String(
                            value.Replace('-', '+').Replace('_', '/')
                                + new string('=', (4 - value.Length % 4) % 4)
                        );
                    var payload = Decode(parts[0]);
                    Assert.True(
                        publicKey.VerifyData(
                            payload,
                            Decode(parts[1]),
                            HashAlgorithmName.SHA256,
                            DSASignatureFormat.Rfc3279DerSequence
                        )
                    );
                    using var envelope = JsonDocument.Parse(payload);
                    var value = envelope.RootElement;
                    Assert.Equal(
                        Caller.TenantId.ToString("D"),
                        value.GetProperty("tenant_id").GetString()
                    );
                    Assert.Equal(
                        Caller.ActorId.ToString("D"),
                        value.GetProperty("actor_subject").GetString()
                    );
                    Assert.Equal(
                        "CONVERSATION_INFERENCE_EVIDENCE",
                        value.GetProperty("purpose").GetString()
                    );
                    Assert.Equal(
                        Caller.ExecutionId.ToString("D"),
                        value.GetProperty("command_id").GetString()
                    );
                    Assert.Equal(
                        Convert.ToHexStringLower(SHA256.HashData(body)),
                        value.GetProperty("request_digest").GetString()
                    );
                    Assert.Equal(
                        60,
                        value.GetProperty("expires_at").GetInt64()
                            - value.GetProperty("issued_at").GetInt64()
                    );
                },
                serverCertificateChain: _serverCertificateChain
            );
            _configuration["WAOOAW_WORKLOAD_CREDENTIALS"] = _credentials;
            _configuration["ConstitutionalEngine:GrpcUrl"] = EvidenceServer.Address.ToString();
            if (defect == "batch")
                await ConfigureBatchAsync();
        }

        public async Task ProcessSinglePendingSourceAsync()
        {
            var bindingId = Guid.NewGuid();
            var recipient = new string('a', 64);
            var workItem = Guid.NewGuid();
            var invocation = Guid.NewGuid();
            var claim = Guid.NewGuid();
            await using (var relationships = _ownerRelationships.CreateDbContext())
            {
                relationships.ChannelBindings.Add(
                    new()
                    {
                        BindingId = bindingId,
                        TenantId = Caller.TenantId,
                        RelationshipId = Caller.RelationshipId,
                        ParticipantId = Caller.ActorId,
                        ParticipantRole = Caller.Role,
                        Channel = "WHATSAPP",
                        ExternalSubjectHash = recipient,
                        ConversationId = Request.ConversationId.ToString("D"),
                        AssuranceLevel = "AAL1_CHANNEL",
                        Status = "ACTIVE",
                        PreparedEvidenceId = Guid.NewGuid(),
                        BoundEvidenceId = Guid.NewGuid(),
                        BoundAt = DateTimeOffset.UtcNow,
                    }
                );
                await relationships.SaveChangesAsync();
            }
            await using (var connection = OwnerConnection())
            {
                await connection.OpenAsync();
                await using var command = new NpgsqlCommand(
                    """
                    UPDATE business.conversation_executions
                    SET origin_channel_binding_id=@binding,origin_recipient_digest=@recipient
                    WHERE execution_id=@execution;
                    DROP TABLE business.conversation_pending_starts;
                    CREATE TABLE business.conversation_pending_starts (
                        tenant_id uuid NOT NULL, relationship_id uuid NOT NULL,
                        conversation_id uuid NOT NULL, message_id uuid NOT NULL,
                        execution_id uuid NOT NULL, actor_id uuid NOT NULL,
                        idempotency_key uuid NOT NULL, evidence_id uuid NOT NULL,
                        mandate_id uuid NOT NULL, admitted_at timestamptz NOT NULL,
                        work_item_id uuid, work_item_revision integer,
                        work_item_invocation_id uuid
                    );
                    ALTER TABLE business.conversation_pending_starts OWNER TO business_app;
                    INSERT INTO business.conversation_pending_starts
                        (tenant_id,relationship_id,conversation_id,message_id,execution_id,
                         actor_id,idempotency_key,evidence_id,mandate_id,admitted_at,
                         work_item_id,work_item_revision,work_item_invocation_id)
                    VALUES (@tenant,@relationship,@conversation,@message,@execution,@actor,
                        @key,@evidence,@mandate,now(),@work_item,1,@invocation);
                    CREATE OR REPLACE FUNCTION business.complete_individual_pending_start(
                        uuid,uuid,bigint
                    ) RETURNS boolean LANGUAGE sql AS 'SELECT true';
                    GRANT EXECUTE ON FUNCTION business.complete_individual_pending_start(
                        uuid,uuid,bigint
                    ) TO business_app;
                    """,
                    connection
                );
                command.Parameters.AddWithValue("binding", bindingId);
                command.Parameters.AddWithValue("recipient", recipient);
                command.Parameters.AddWithValue("execution", Request.ExecutionId);
                command.Parameters.AddWithValue("tenant", Caller.TenantId);
                command.Parameters.AddWithValue("relationship", Caller.RelationshipId);
                command.Parameters.AddWithValue("conversation", Request.ConversationId);
                command.Parameters.AddWithValue("message", Request.ContributionRef);
                command.Parameters.AddWithValue("actor", Caller.ActorId);
                command.Parameters.AddWithValue(
                    "key",
                    Request.OperationalMandate.IdempotencyIdentity
                );
                command.Parameters.AddWithValue(
                    "evidence",
                    Guid.Parse(
                        Request.OperationalMandate.ConstitutionalEvidenceRef[
                            "ce-evidence:".Length..
                        ]
                    )
                );
                command.Parameters.AddWithValue("mandate", Request.OperationalMandate.MandateId);
                command.Parameters.AddWithValue("work_item", workItem);
                command.Parameters.AddWithValue("invocation", invocation);
                await command.ExecuteNonQueryAsync();
            }
            var options = Options.Create(
                new Wc120ConversationOptions { Enabled = true, Environment = "demo" }
            );
            var batching = Options.Create(
                new ConversationBatchingOptions
                {
                    Enabled = true,
                    MaximumWaitSeconds = 10,
                    MaximumMessages = 3,
                    MaximumTextLength = 2000,
                    LeaseSeconds = 45,
                }
            );
            var task = new ConversationBatchTaskIdentity(
                "professional-runtime",
                workItem,
                1,
                invocation
            );
            var taskResolver = new Mock<IConversationBatchTaskResolver>();
            taskResolver
                .Setup(value =>
                    value.ResolveFreshAsync(
                        It.IsAny<ConversationBatchTaskResolutionRequest>(),
                        It.IsAny<CancellationToken>()
                    )
                )
                .ReturnsAsync(task);
            var gateway = new Mock<IConversationExecutionGateway>();
            var batchGateway = new Mock<IConversationBatchExecutionGateway>();
            var directory = new ConversationBatchWorkDirectory(
                _conversations,
                options,
                batching,
                NullLogger<ConversationBatchWorkDirectory>.Instance
            );
            var workScope = new ConversationBatchWorkScope();
            var worker = new ConversationBatchDispatchWorker(
                _conversations,
                _relationships,
                new OperationalMandateResolver(_relationships),
                taskResolver.Object,
                new ConversationRuntimeIdentityAuthority(_configuration),
                new ConversationStopFence(_conversations, options),
                gateway.Object,
                batchGateway.Object,
                directory,
                workScope,
                batching,
                NullLogger<ConversationBatchDispatchWorker>.Instance
            );
            using var capability = workScope.Begin(
                new(
                    claim,
                    Caller.TenantId,
                    Caller.RelationshipId,
                    Request.ConversationId,
                    Request.ContributionRef,
                    1,
                    DateTimeOffset.UtcNow.AddMinutes(1)
                )
            );

            Assert.True(await worker.ProcessOneAsync(CancellationToken.None));
            gateway.Verify(
                value =>
                    value.StartAsync(
                        Request.ConversationId,
                        Request.ExecutionId,
                        Request.ContributionRef,
                        Caller.RelationshipId,
                        "en",
                        It.IsAny<IReadOnlyList<ConversationTextBlockV1>>(),
                        It.IsAny<OperationalMandateV1>(),
                        Request.OperationalMandate.IdempotencyIdentity,
                        It.IsAny<CancellationToken>()
                    ),
                Times.Once
            );
            batchGateway.VerifyNoOtherCalls();
        }

        public async Task ProcessFrozenBatchAsync(bool dispatchFails = false)
        {
            var batch = Request.Batch ?? throw new InvalidOperationException();
            var bindingId = Guid.NewGuid();
            var recipient = new string('b', 64);
            await using (var relationships = _ownerRelationships.CreateDbContext())
            {
                relationships.ChannelBindings.Add(
                    new()
                    {
                        BindingId = bindingId,
                        TenantId = Caller.TenantId,
                        RelationshipId = Caller.RelationshipId,
                        ParticipantId = Caller.ActorId,
                        ParticipantRole = Caller.Role,
                        Channel = "WHATSAPP",
                        ExternalSubjectHash = recipient,
                        ConversationId = Request.ConversationId.ToString("D"),
                        AssuranceLevel = "AAL1_CHANNEL",
                        Status = "ACTIVE",
                        PreparedEvidenceId = Guid.NewGuid(),
                        BoundEvidenceId = Guid.NewGuid(),
                        BoundAt = DateTimeOffset.UtcNow,
                    }
                );
                await relationships.SaveChangesAsync();
            }
            await using (var connection = OwnerConnection())
            {
                await connection.OpenAsync();
                await using var command = new NpgsqlCommand(
                    """
                    UPDATE business.conversation_executions
                    SET origin_channel_binding_id=@binding,origin_recipient_digest=@recipient
                    WHERE execution_id = ANY(@executions);
                    DROP TABLE business.conversation_pending_starts;
                    CREATE TABLE business.conversation_pending_starts (
                        tenant_id uuid NOT NULL, relationship_id uuid NOT NULL,
                        conversation_id uuid NOT NULL, message_id uuid NOT NULL,
                        execution_id uuid NOT NULL, actor_id uuid NOT NULL,
                        idempotency_key uuid NOT NULL, evidence_id uuid NOT NULL,
                        mandate_id uuid NOT NULL, admitted_at timestamptz NOT NULL,
                        work_item_id uuid, work_item_revision integer,
                        work_item_invocation_id uuid
                    );
                    ALTER TABLE business.conversation_pending_starts OWNER TO business_app;
                    INSERT INTO business.conversation_pending_starts
                        (tenant_id,relationship_id,conversation_id,message_id,execution_id,
                         actor_id,idempotency_key,evidence_id,mandate_id,admitted_at,
                         work_item_id,work_item_revision,work_item_invocation_id)
                    SELECT @tenant,@relationship,@conversation,source.message_id,
                        source.execution_id,@actor,source.idempotency_key,source.evidence_id,
                        source.mandate_id,now(),@work_item,1,@invocation
                    FROM (
                        VALUES
                            (@first_message,@first_execution,@first_key,@first_evidence,@first_mandate),
                            (@second_message,@second_execution,@second_key,@second_evidence,@second_mandate)
                    ) AS source(message_id,execution_id,idempotency_key,evidence_id,mandate_id);
                    CREATE OR REPLACE FUNCTION business.transition_conversation_batch(
                        uuid,uuid,uuid,bigint,text,text,text,text,uuid,text
                    ) RETURNS boolean LANGUAGE sql AS 'SELECT true';
                    GRANT EXECUTE ON FUNCTION business.transition_conversation_batch(
                        uuid,uuid,uuid,bigint,text,text,text,text,uuid,text
                    ) TO business_app;
                    """,
                    connection
                );
                var first = batch.Sources[0];
                var second = batch.Sources[1];
                command.Parameters.AddWithValue("binding", bindingId);
                command.Parameters.AddWithValue("recipient", recipient);
                command.Parameters.AddWithValue(
                    "executions",
                    new[] { first.ExecutionId, second.ExecutionId }
                );
                command.Parameters.AddWithValue("tenant", Caller.TenantId);
                command.Parameters.AddWithValue("relationship", Caller.RelationshipId);
                command.Parameters.AddWithValue("conversation", Request.ConversationId);
                command.Parameters.AddWithValue("actor", Caller.ActorId);
                command.Parameters.AddWithValue("work_item", first.WorkItemId);
                command.Parameters.AddWithValue("invocation", first.WorkItemInvocationId);
                command.Parameters.AddWithValue("first_message", first.MessageId);
                command.Parameters.AddWithValue("first_execution", first.ExecutionId);
                command.Parameters.AddWithValue("first_key", first.IdempotencyKey);
                command.Parameters.AddWithValue("first_evidence", first.EvidenceId);
                command.Parameters.AddWithValue("first_mandate", first.OperationalMandate.MandateId);
                command.Parameters.AddWithValue("second_message", second.MessageId);
                command.Parameters.AddWithValue("second_execution", second.ExecutionId);
                command.Parameters.AddWithValue("second_key", second.IdempotencyKey);
                command.Parameters.AddWithValue("second_evidence", second.EvidenceId);
                command.Parameters.AddWithValue("second_mandate", second.OperationalMandate.MandateId);
                await command.ExecuteNonQueryAsync();
            }
            var options = Options.Create(
                new Wc120ConversationOptions { Enabled = true, Environment = "demo" }
            );
            var batching = Options.Create(
                new ConversationBatchingOptions
                {
                    Enabled = true,
                    MaximumWaitSeconds = 10,
                    MaximumMessages = 3,
                    MaximumTextLength = 2000,
                    LeaseSeconds = 45,
                }
            );
            var task = new ConversationBatchTaskIdentity(
                "professional-runtime",
                batch.Sources[0].WorkItemId,
                batch.Sources[0].WorkItemRevision,
                batch.Sources[0].WorkItemInvocationId
            );
            var taskResolver = new Mock<IConversationBatchTaskResolver>();
            taskResolver
                .Setup(value =>
                    value.ResolveFreshAsync(
                        It.IsAny<ConversationBatchTaskResolutionRequest>(),
                        It.IsAny<CancellationToken>()
                    )
                )
                .ReturnsAsync(task);
            var gateway = new Mock<IConversationExecutionGateway>();
            var batchGateway = new Mock<IConversationBatchExecutionGateway>();
            var dispatch = batchGateway.Setup(value =>
                    value.StartBatchAsync(
                        It.IsAny<Guid>(),
                        It.IsAny<Guid>(),
                        It.IsAny<Guid>(),
                        It.IsAny<Guid>(),
                        It.IsAny<IReadOnlyList<HttpConversationExecutionGateway.BatchExecutionSource>>(),
                        It.IsAny<CancellationToken>()
                    )
                );
            if (dispatchFails)
                dispatch.ThrowsAsync(new HttpRequestException("synthetic lost response"));
            else
                dispatch.ReturnsAsync(
                    new HttpConversationExecutionGateway.BatchExecutionReceipt(
                        "1.0",
                        batch.BatchId,
                        Request.ExecutionId,
                        Request.ConversationId,
                        batch.SourceListDigest,
                        new string('f', 64),
                        "ACCEPTED",
                        true,
                        DateTimeOffset.UtcNow
                    )
                );
            var directory = new ConversationBatchWorkDirectory(
                _conversations,
                options,
                batching,
                NullLogger<ConversationBatchWorkDirectory>.Instance
            );
            var workScope = new ConversationBatchWorkScope();
            var worker = new ConversationBatchDispatchWorker(
                _conversations,
                _relationships,
                new OperationalMandateResolver(_relationships),
                taskResolver.Object,
                new ConversationRuntimeIdentityAuthority(_configuration),
                new ConversationStopFence(_conversations, options),
                gateway.Object,
                batchGateway.Object,
                directory,
                workScope,
                batching,
                NullLogger<ConversationBatchDispatchWorker>.Instance
            );
            using var capability = workScope.Begin(
                new(
                    batch.BatchId,
                    Caller.TenantId,
                    Caller.RelationshipId,
                    Request.ConversationId,
                    batch.Sources[0].MessageId,
                    1,
                    DateTimeOffset.UtcNow.AddMinutes(1),
                    batch.BatchId,
                    "STARTED"
                )
            );

            Assert.True(await worker.ProcessOneAsync(CancellationToken.None));
            batchGateway.Verify(
                value =>
                    value.StartBatchAsync(
                        Request.ConversationId,
                        batch.BatchId,
                        Request.ExecutionId,
                        Caller.RelationshipId,
                        It.Is<IReadOnlyList<HttpConversationExecutionGateway.BatchExecutionSource>>(
                            sources => sources.Count == 2
                        ),
                        It.IsAny<CancellationToken>()
                    ),
                Times.Once
            );
            gateway.VerifyNoOtherCalls();
        }

        public async Task<Guid> SeedReservationAsync(string state)
        {
            var reservation = Guid.NewGuid();
            var commercialReservation = Guid.NewGuid();
            var evidence = Guid.NewGuid();
            var budgetTenant = Guid.NewGuid();
            await using var connection = OwnerConnection();
            await connection.OpenAsync();
            await using var command = new NpgsqlCommand(
                """
                INSERT INTO business.environment_spend_attempts
                    (environment,owner_kind,attempt_id,original_tenant_id,activation_digest,
                     request_digest,reservation_reference,reserved_paise,actual_paise,state,
                     reserved_at,usage_at,settlement_evidence_id)
                VALUES ('demo','MODEL',@execution,@tenant,repeat('a',64),@request,@id,100,
                    CASE WHEN @state='RESERVED' THEN NULL WHEN @state='SETTLED' THEN 2 ELSE 0 END,
                    @state,now()-interval '1 hour',
                    CASE WHEN @state='RESERVED' THEN NULL ELSE now() END,
                    CASE WHEN @state='RESERVED' THEN NULL ELSE @evidence END);
                INSERT INTO business.conversation_model_reservations
                    (reservation_id,tenant_id,environment,activation_digest,authority_digest,cost_day,
                    customer_tenant_id,relationship_id,execution_id,actor_id,idempotency_key,mandate_digest,
                    request_digest,binding_id,binding_digest,rate_digest,evidence_id,reserved_paise,
                    input_rate_paise,output_rate_paise,state,reserved_at,expires_at,actual_paise,
                    input_tokens,output_tokens,settlement_evidence_id,settled_at)
                VALUES (@id,@budget,'demo',repeat('a',64),repeat('b',64),CURRENT_DATE,
                    @tenant,@relationship,@execution,@actor,@key,@mandate,@request,@binding,@digest,
                    @digest,@evidence,100,1,1,@state,now()-interval '1 hour',now()-interval '59 minutes',
                    CASE WHEN @state='RESERVED' THEN NULL WHEN @state='SETTLED' THEN 2 ELSE 0 END,
                    CASE WHEN @state='SETTLED' THEN 1 ELSE NULL END,
                    CASE WHEN @state='SETTLED' THEN 1 ELSE NULL END,
                    CASE WHEN @state='RESERVED' THEN NULL ELSE @evidence END,
                    CASE WHEN @state='RESERVED' THEN NULL ELSE now() END);
                INSERT INTO business.conversation_model_budget_receipts
                    (tenant_id,execution_id,reservation_id,budget_tenant_id)
                VALUES (@tenant,@execution,@id,@budget);
                INSERT INTO business.conversation_inference_spend_coordinators
                    (tenant_id,relationship_id,execution_id,request_digest,owner_evidence_id,
                     component_id,invocation_id,wbe_reservation_id,operational_reservation_id,
                     wbe_state,operational_state,provider_dispatch_state,created_at,updated_at)
                VALUES (@tenant,@relationship,@execution,@request,@evidence,
                    'MODEL_GENERATION',@execution,@commercial,@id,@state,@state,
                    'DISPATCHED',now(),now());
                """,
                connection
            );
            command.Parameters.AddWithValue("id", reservation);
            command.Parameters.AddWithValue("commercial", commercialReservation);
            command.Parameters.AddWithValue("budget", budgetTenant);
            command.Parameters.AddWithValue("tenant", Caller.TenantId);
            command.Parameters.AddWithValue("relationship", Caller.RelationshipId);
            command.Parameters.AddWithValue("execution", Request.ExecutionId);
            command.Parameters.AddWithValue("actor", Caller.ActorId);
            command.Parameters.AddWithValue("key", Caller.IdempotencyKey);
            command.Parameters.AddWithValue(
                "mandate",
                ConversationReconciliationBinding.Digest(Request.OperationalMandate)
            );
            command.Parameters.AddWithValue("request", Request.RequestDigest);
            command.Parameters.AddWithValue("binding", BindingId);
            command.Parameters.AddWithValue("digest", "sha256:" + new string('c', 64));
            command.Parameters.AddWithValue("evidence", evidence);
            command.Parameters.AddWithValue("state", state);
            await command.ExecuteNonQueryAsync();
            _offeringUsage.Seed(Request.ExecutionId, commercialReservation, state);
            Request = Request with { CommercialReservationId = commercialReservation };
            return reservation;
        }

        public static async Task<Fixture> CreateAsync()
        {
            var postgres = new PostgreSqlBuilder("postgres:16-alpine").Build();
            await postgres.StartAsync();
            var fixture = new Fixture(postgres);
            try
            {
                await fixture.InitializeAsync();
                return fixture;
            }
            catch
            {
                await postgres.DisposeAsync();
                throw;
            }
        }

        private async Task InitializeAsync()
        {
            var ownerConversations = new Factory<ConversationStoreDbContext>(
                postgres.GetConnectionString()
            );
            _ownerConversations = ownerConversations;
            var ownerRelationships = new Factory<EmploymentRelationshipDbContext>(
                postgres.GetConnectionString()
            );
            _ownerRelationships = ownerRelationships;
            await using var db = ownerConversations.CreateDbContext();
            await using var relationships = ownerRelationships.CreateDbContext();
            await ExecuteAsync(db.Database.GenerateCreateScript());
            await ExecuteAsync(relationships.Database.GenerateCreateScript());
            await ExecuteAsync(
                """
                CREATE ROLE bp_owner NOBYPASSRLS;
                CREATE ROLE air_owner NOBYPASSRLS;
                CREATE ROLE ai_runtime_app NOBYPASSRLS;
                CREATE ROLE identity_resolver_owner NOBYPASSRLS;
                CREATE ROLE business_app LOGIN PASSWORD 'synthetic-inference-test' NOBYPASSRLS;
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
                BEGIN PERFORM pg_advisory_xact_lock(hashtextextended('wc134-dispatch:' || $1::text || ':' || $2, 0)); END $$;
                CREATE FUNCTION ai_runtime.employment_dispatch_relationship_key(text) RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
                CREATE TABLE business.provider_configs (id uuid, tenant_id uuid, provider_name text,
                    auth_method text, mcp_server_url text, provider_identity_uri text, scope_set text[], active boolean);
                GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
                GRANT USAGE, CREATE ON SCHEMA ai_runtime TO air_owner;
                GRANT USAGE ON SCHEMA business, identity TO identity_resolver_owner;
                GRANT SELECT ON ALL TABLES IN SCHEMA business, identity TO identity_resolver_owner;
                GRANT USAGE ON SCHEMA business, identity, ai_runtime, constitutional TO business_app;
                GRANT SELECT ON ALL TABLES IN SCHEMA business, constitutional TO business_app;
                ALTER TABLE business.whatsapp_traffic_reservations OWNER TO bp_owner;
                GRANT SELECT, INSERT ON business.whatsapp_traffic_reservations TO business_app;
                GRANT UPDATE (state) ON business.employment_relationships TO business_app;
                GRANT UPDATE (status) ON business.relationship_participants TO business_app;
                GRANT UPDATE (runtime_sequence) ON business.conversation_executions TO business_app;
                GRANT UPDATE (active) ON business.provider_configs TO business_app;
                """
            );
            foreach (
                var migration in new[]
                {
                    "87-wc134-runtime-event-projection.sql",
                    "88-wc134-runtime-identity-authority.sql",
                    "95-wc134-governed-conversation-generation.sql",
                    "98-wc134-inference-binding-row-lock.sql",
                    "99zzzzzz-wc134-environment-spend.sql",
                }
            )
            {
                try
                {
                    await ExecuteAsync(
                        await File.ReadAllTextAsync(
                            RepositoryPaths.Resolve($"infrastructure/postgres/init/{migration}")
                        )
                    );
                }
                catch (Exception exception)
                {
                    throw new InvalidOperationException(
                        $"Failed to apply {migration}.",
                        exception
                    );
                }
            }
            await ExecuteAsync(
                """
                INSERT INTO business.environment_spend_authorities
                    (environment,authority_version,maximum_paise,active,migration_complete,
                     authority_evidence_id,updated_at)
                VALUES ('demo',1,50000,true,true,gen_random_uuid(),clock_timestamp())
                ON CONFLICT (environment) DO UPDATE
                SET active=true,migration_complete=true,authority_evidence_id=excluded.authority_evidence_id;
                """
            );
            var operation = new ConversationOperationBindingV1(
                "PROFESSIONAL_RESPONSE",
                "PRESENT_PROFILE_PROPOSAL",
                "sha256:" + new string('5', 64),
                "sha256:" + new string('6', 64),
                new("prompt:synthetic", "1.0.0", "sha256:" + new string('7', 64)),
                new("model-policy:synthetic", "1.0.0", "sha256:" + new string('9', 64))
            );
            var seeded = await OperationalMandateResolverTests.CreateFixtureAsync(
                operation: operation,
                database: ownerRelationships
            );
            var account = Guid.NewGuid();
            var membership = Guid.NewGuid();
            var login = Guid.NewGuid();
            const string issuer = "https://identity.test/realms/demo";
            await ExecuteAsync(
                $"""
                INSERT INTO identity.actor_bindings VALUES ('{issuer}', '{seeded.ParticipantId:D}', '{account:D}', '{login:D}', 'ACTIVE');
                INSERT INTO identity.login_methods VALUES ('{login:D}', '{account:D}', 'ACTIVE');
                INSERT INTO identity.accounts VALUES ('{account:D}', 'ACTIVE');
                INSERT INTO identity.memberships VALUES ('{membership:D}', '{account:D}', '{seeded.TenantId:D}', ARRAY['OWNER'], 'ACTIVE');
                INSERT INTO business.organisations VALUES ('{seeded.TenantId:D}', true, 'ACTIVE');
                """
            );
            var idempotency = Guid.NewGuid();
            var evidence = Guid.NewGuid();
            const string text = "Prepare the profile";
            var mandate = await new OperationalMandateResolver(ownerRelationships).ResolveAsync(
                seeded.TenantId,
                seeded.ParticipantId,
                seeded.RelationshipId,
                idempotency,
                evidence,
                "CUSTOMER_PROFILING",
                text,
                CancellationToken.None
            );
            var conversation = Guid.NewGuid();
            var message = Guid.NewGuid();
            var execution = ConversationExecutionIdentity.Create(
                seeded.TenantId,
                seeded.RelationshipId,
                seeded.ParticipantId,
                conversation,
                idempotency
            );
            db.Conversations.Add(
                new()
                {
                    TenantId = seeded.TenantId,
                    RelationshipId = seeded.RelationshipId,
                    ConversationId = conversation,
                    Environment = "demo",
                    NextMessageSequence = 2,
                }
            );
            db.Messages.Add(
                new()
                {
                    TenantId = seeded.TenantId,
                    RelationshipId = seeded.RelationshipId,
                    ConversationId = conversation,
                    MessageId = message,
                    Environment = "demo",
                    Sequence = 1,
                    SkillId = mandate.SkillId,
                    EvidenceRecordId = evidence,
                    ContentJson = JsonSerializer.Serialize(
                        new[] { new ConversationTextBlockV1("1.0", "TEXT", text, "en") },
                        ConversationReconciliationBinding.Json
                    ),
                }
            );
            db.Executions.Add(
                new()
                {
                    ExecutionId = execution,
                    TenantId = seeded.TenantId,
                    RelationshipId = seeded.RelationshipId,
                    ConversationId = conversation,
                    MessageId = message,
                    RuntimeActorId = seeded.ParticipantId,
                    RuntimeActorIssuer = issuer,
                    RuntimeMembershipId = membership,
                    RuntimeAccountId = account,
                }
            );
            db.IdempotencyOutcomes.Add(
                new()
                {
                    TenantId = seeded.TenantId,
                    RelationshipId = seeded.RelationshipId,
                    ActorParticipantId = seeded.ParticipantId,
                    ExecutionId = execution,
                    MessageId = message,
                    IdempotencyKey = idempotency,
                    OperationFamily = "SEND",
                }
            );
            await db.SaveChangesAsync();
            var providerId = Guid.NewGuid();
            var configurationDigest = ConversationReconciliationBinding.Digest(
                new
                {
                    Id = providerId,
                    ProviderName = "synthetic-local",
                    AuthMethod = "INSTITUTIONAL_MTLS",
                    Endpoint = "https://inference.invalid",
                    IdentityUri = "spiffe://test/provider",
                    scopes = new[] { operation.GovernedAction },
                }
            );
            var content = JsonSerializer.SerializeToElement(
                new
                {
                    bindingId = BindingId,
                    providerId = "synthetic-local",
                    providerIdentityUri = "spiffe://test/provider",
                    adapter = "OLLAMA",
                    endpoint = "https://inference.invalid",
                    model = "synthetic:model",
                    modelDigest = new string('a', 64),
                    tokenizerDigest = new string('b', 64),
                    tokenizerVersion = "1",
                    region = "LOCAL",
                    tier = "LOCAL",
                    languages = new[] { "en" },
                    domains = new[] { "DMA" },
                    planTiers = new[] { "TRIAL" },
                    resolvedPlanTier = "TRIAL",
                    mandatoryTiers = new[] { "LOCAL" },
                    residencyRegions = new[] { "LOCAL" },
                    institutionalBoundary = true,
                    configurationDigest,
                    rateDigest = "sha256:" + new string('c', 64),
                    inputPaisePerMillion = 100L,
                    outputPaisePerMillion = 100L,
                    systemPrompt = "Synthetic prompt",
                    promptVersion = mandate.PromptVersion,
                    promptDigest = mandate.PromptDigest,
                    promptWrapper = "RAW_SYSTEM_CANONICAL_HISTORY_V1",
                    modelPolicyDigest = operation.ModelPolicy.Digest,
                    expiresAt = DateTimeOffset.UtcNow.AddHours(1),
                }
            );
            await using (
                var insert = new NpgsqlCommand(
                    """
                    INSERT INTO business.provider_configs VALUES (@provider,@tenant,'synthetic-local',
                        'INSTITUTIONAL_MTLS','https://inference.invalid','spiffe://test/provider',ARRAY['PRESENT_PROFILE_PROPOSAL'],true);
                    INSERT INTO business.conversation_inference_bindings
                        (binding_id,tenant_id,admission_id,relationship_id,accepted_contract_id,configuration_revision,
                        admission_revision,professional_type,professional_version,skill_id,skill_version,prompt_ref,prompt_version,
                        prompt_digest,model_policy_ref,model_policy_version,model_policy_digest,binding_json,binding_digest,
                        approved_evidence_id,active)
                    SELECT @binding,@tenant,professional_admission_id,relationship_id,accepted_contract_id,1,
                        1,professional_type,professional_version,'CUSTOMER_PROFILING','1.0.0','prompt:synthetic','1.0.0',
                        @prompt,'model-policy:synthetic','1.0.0',@policy,@content::jsonb,@digest,@evidence,true
                    FROM business.employment_relationships;
                    """,
                    new NpgsqlConnection(postgres.GetConnectionString())
                )
            )
            {
                insert.Parameters.AddWithValue("provider", providerId);
                insert.Parameters.AddWithValue("tenant", seeded.TenantId);
                insert.Parameters.AddWithValue("binding", BindingId);
                insert.Parameters.AddWithValue("prompt", mandate.PromptDigest);
                insert.Parameters.AddWithValue("policy", operation.ModelPolicy.Digest);
                insert.Parameters.AddWithValue("content", content.GetRawText());
                insert.Parameters.AddWithValue(
                    "digest",
                    AgentAdmissionCanonicalizer.Digest(content)
                );
                insert.Parameters.AddWithValue("evidence", Guid.NewGuid());
                await insert.Connection!.OpenAsync();
                await insert.ExecuteNonQueryAsync();
                await insert.Connection.DisposeAsync();
            }
            var appConnection = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
            {
                Username = "business_app",
                Password = "synthetic-inference-test",
                Options = $"-c app.current_tenant_id={seeded.TenantId:D}",
            }.ConnectionString;
            _conversations = new(appConnection);
            var applicationRelationships = new Factory<EmploymentRelationshipDbContext>(
                appConnection
            );
            _relationships = applicationRelationships;
            var config = new ConfigurationBuilder()
                .AddInMemoryCollection(
                    new Dictionary<string, string?> { ["IdentityBrokerRead:ActorIssuer"] = issuer }
                )
                .Build();
            _configuration = config;
            var identity = new ConversationRuntimeIdentityAuthority(config);
            var ingestion = new ConversationRuntimeEventIngestion(
                _conversations,
                applicationRelationships,
                Options.Create(
                    new Wc120ConversationOptions
                    {
                        Environment = "demo",
                        Enabled = true,
                        RuntimeEventIngestionEnabled = true,
                    }
                ),
                TimeProvider.System,
                new ConversationCursorCodec(
                    Options.Create(
                        new ConversationCursorOptions
                        {
                            HmacKey = new string('c', 32),
                        }
                    )
                ),
                identity
            );
            var capability = new Mock<IWhatsAppCapabilityGate>();
            Activation = new()
            {
                TenantId = Guid.NewGuid(),
                Environment = "demo",
                ActivationReference = "synthetic-activation",
                MaximumSpendInr = 500,
                ExpiresAt = DateTimeOffset.UtcNow.AddHours(1),
            };
            capability
                .Setup(value => value.RequireActive(It.IsAny<DateTimeOffset>()))
                .Returns(() => Activation);
            Caller = new(
                seeded.TenantId,
                seeded.RelationshipId,
                seeded.ParticipantId,
                "EMPLOYER",
                message,
                execution,
                idempotency
            );
            Request = new(
                execution,
                conversation,
                message,
                seeded.RelationshipId,
                new string('a', 64),
                Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(text))),
                "en",
                mandate
            );
            Owner = new(
                _conversations,
                applicationRelationships,
                ingestion,
                null!,
                identity,
                new ConversationInferenceEvidence(config, TimeProvider.System),
                capability.Object,
                config,
                TimeProvider.System,
                _offeringUsage,
                new ConversationEnvironmentSpendOwner()
            );
        }

        public async Task ExecuteAsync(string sql)
        {
            await using var connection = new NpgsqlConnection(postgres.GetConnectionString());
            await connection.OpenAsync();
            await using var command = new NpgsqlCommand(sql, connection);
            await command.ExecuteNonQueryAsync();
        }

        public async Task AssertNoUsageAsync(int expectedMessages = 1)
        {
            await using var db = _conversations.CreateDbContext();
            Assert.Equal(expectedMessages, await db.Messages.CountAsync());
            await using var connection = new NpgsqlConnection(postgres.GetConnectionString());
            await connection.OpenAsync();
            await using var command = new NpgsqlCommand(
                "SELECT count(*) FROM business.conversation_model_reservations",
                connection
            );
            Assert.Equal(0L, await command.ExecuteScalarAsync());
        }

        public async ValueTask DisposeAsync()
        {
            if (EvidenceServer is not null)
                await EvidenceServer.DisposeAsync();
            _serverCertificate?.Dispose();
            _clientCertificate?.Dispose();
            foreach (var certificate in _serverCertificateChain)
                certificate.Dispose();
            _delegationPublicKey?.Dispose();
            if (Directory.Exists(_credentials))
                Directory.Delete(_credentials, recursive: true);
            await postgres.DisposeAsync();
        }
    }
}
