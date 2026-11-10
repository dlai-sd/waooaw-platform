// Implements: WC-134 canonical pending-start persistence.
// constitutional_basis: C-023, C-026, C-059, C-063
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationPendingStartPostgresTests
{
    private static readonly ConversationBatchLimits BatchLimits = new(
        3,
        32,
        TimeSpan.FromMinutes(5),
        "\n"
    );

    [Fact]
    public async Task FullInitChainInstallsTenantScopedBatchTablesAndAtomicFreeze()
    {
        var initDirectory = Path.GetDirectoryName(
            RepositoryPaths.Resolve("infrastructure/postgres/init/01-schemas.sql")
        )!;
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw")
            .WithUsername("waooaw")
            .WithPassword("synthetic-full-schema-password")
            .WithResourceMapping(new DirectoryInfo(initDirectory), "/docker-entrypoint-initdb.d")
            .Build();
        await postgres.StartAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        await using var command = new NpgsqlCommand(
            """
            SELECT
                (SELECT count(*) = 3 FROM pg_class
                 WHERE oid IN ('business.conversation_pending_starts'::regclass,
                               'business.conversation_batch_groups'::regclass,
                               'business.conversation_batch_members'::regclass)
                   AND relrowsecurity AND relforcerowsecurity AND pg_get_userbyid(relowner) = 'bp_owner'),
                has_column_privilege('business_app', 'business.conversation_batch_groups', 'batch_id', 'INSERT'),
                NOT has_column_privilege('business_app', 'business.conversation_batch_groups', 'frozen_at', 'INSERT'),
                has_column_privilege('business_app', 'business.conversation_batch_groups', 'frozen_at', 'UPDATE'),
                NOT has_table_privilege('business_app', 'business.conversation_batch_members', 'UPDATE,DELETE'),
                EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'business.conversation_batch_groups'::regclass
                        AND tgname = 'conversation_batch_requires_freeze' AND tgdeferrable AND tginitdeferred),
                (SELECT count(*) = 3 FROM pg_class
                 WHERE oid IN ('business.conversation_request_questions'::regclass,
                               'business.conversation_request_question_members'::regclass,
                               'business.conversation_request_answers'::regclass)
                   AND relrowsecurity AND relforcerowsecurity AND pg_get_userbyid(relowner) = 'bp_owner'),
                NOT has_table_privilege('business_app', 'business.conversation_request_answers', 'INSERT,UPDATE,DELETE'),
                EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'business.conversation_request_questions'::regclass
                        AND tgname = 'request_question_requires_freeze' AND tgdeferrable AND tginitdeferred)
            """,
            owner
        );
        await using var reader = await command.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        for (var index = 0; index < 9; index++)
            Assert.True(reader.GetBoolean(index), $"Full-schema invariant {index} failed.");
    }

    [Fact]
    public async Task PendingSourceIsAtomicUniqueAndTenantIsolated()
    {
        await using var postgres = new PostgreSqlBuilder("postgres:16-alpine").Build();
        await postgres.StartAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        await ExecuteAsync(
            owner,
            """
            CREATE ROLE bp_owner NOBYPASSRLS;
            CREATE ROLE business_app LOGIN PASSWORD 'synthetic-batch-test' NOBYPASSRLS;
            CREATE SCHEMA business;
            GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            CREATE TABLE business.conversation_messages (
                tenant_id uuid NOT NULL, relationship_id uuid NOT NULL,
                conversation_id uuid NOT NULL, message_id uuid PRIMARY KEY,
                sequence bigint GENERATED ALWAYS AS IDENTITY,
                environment text NOT NULL DEFAULT 'demo',
                evidence_record_id uuid, actor text DEFAULT 'CUSTOMER',
                channel text DEFAULT 'WHATSAPP', evidence_state text DEFAULT 'RECORDED',
                skill_id text NOT NULL DEFAULT 'skill',
                content_json jsonb NOT NULL DEFAULT '[{"schemaVersion":"1.0","blockType":"TEXT","text":"input","language":"en-IN"}]'
            );
            CREATE TABLE business.conversation_executions (
                tenant_id uuid NOT NULL, relationship_id uuid NOT NULL, conversation_id uuid NOT NULL,
                message_id uuid NOT NULL, execution_id uuid PRIMARY KEY,
                runtime_actor_id uuid, origin_channel_binding_id uuid,
                origin_recipient_digest text NOT NULL DEFAULT repeat('a', 64)
            );
            CREATE TABLE business.operational_mandate_snapshots (
                tenant_id uuid NOT NULL, relationship_id uuid NOT NULL, actor_participant_id uuid NOT NULL,
                idempotency_identity uuid NOT NULL, constitutional_evidence_id uuid NOT NULL, mandate_id uuid PRIMARY KEY,
                deadline timestamptz NOT NULL DEFAULT now() + interval '5 minutes'
            );
            CREATE TABLE business.conversation_idempotency_outcomes (
                tenant_id uuid NOT NULL, relationship_id uuid NOT NULL, actor_participant_id uuid NOT NULL,
                operation_family text NOT NULL, idempotency_key uuid NOT NULL, message_id uuid NOT NULL, execution_id uuid NOT NULL
            );
            GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA business TO business_app;
            GRANT USAGE ON ALL SEQUENCES IN SCHEMA business TO business_app;
            """
        );
        var migration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/99z-wc134-conversation-pending-start.sql"
            )
        );
        await ExecuteAsync(owner, migration);
        await ExecuteAsync(owner, migration);
        var dispatchMigration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/99zzzz-wc134-conversation-batch-dispatch.sql"
            )
        );
        await ExecuteAsync(owner, dispatchMigration);
        await ExecuteAsync(owner, dispatchMigration);

        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var conversation = Guid.NewGuid();
        var message = Guid.NewGuid();
        var execution = Guid.NewGuid();
        var actor = Guid.NewGuid();
        var key = Guid.NewGuid();
        var evidence = Guid.NewGuid();
        var mandate = Guid.NewGuid();
        var parameters = new Dictionary<string, Guid>
        {
            ["tenant"] = tenant,
            ["relationship"] = relationship,
            ["conversation"] = conversation,
            ["message"] = message,
            ["execution"] = execution,
            ["actor"] = actor,
            ["key"] = key,
            ["evidence"] = evidence,
            ["mandate"] = mandate,
        };
        await using var transaction = await owner.BeginTransactionAsync();
        await ExecuteAsync(
            owner,
            """
            INSERT INTO business.conversation_messages (tenant_id, relationship_id, conversation_id, message_id, evidence_record_id) VALUES (@tenant, @relationship, @conversation, @message, @evidence);
            INSERT INTO business.conversation_executions (tenant_id, relationship_id, conversation_id, message_id, execution_id, runtime_actor_id, origin_channel_binding_id) VALUES (@tenant, @relationship, @conversation, @message, @execution, @actor, '00000000-0000-0000-0000-000000000001'::uuid);
            INSERT INTO business.operational_mandate_snapshots (tenant_id, relationship_id, actor_participant_id, idempotency_identity, constitutional_evidence_id, mandate_id) VALUES (@tenant, @relationship, @actor, @key, @evidence, @mandate);
            INSERT INTO business.conversation_idempotency_outcomes VALUES (@tenant, @relationship, @actor, 'SEND', @key, @message, @execution);
            """,
            parameters
        );
        const string insert = """
            INSERT INTO business.conversation_pending_starts
                (tenant_id, relationship_id, conversation_id, message_id, execution_id,
                 actor_id, idempotency_key, evidence_id, mandate_id, due_at)
            VALUES (@tenant, @relationship, @conversation, @message, @execution,
                    @actor, @key, @evidence, @mandate, now() + interval '1 second')
            """;
        await ExecuteAsync(owner, insert, parameters);
        await transaction.RollbackAsync();
        Assert.Equal(
            0L,
            await ScalarAsync(owner, "SELECT count(*) FROM business.conversation_pending_starts")
        );
        Assert.Equal(
            0L,
            await ScalarAsync(owner, "SELECT count(*) FROM business.conversation_messages")
        );

        await ExecuteAsync(
            owner,
            """
            INSERT INTO business.conversation_messages (tenant_id, relationship_id, conversation_id, message_id, evidence_record_id) VALUES (@tenant, @relationship, @conversation, @message, @evidence);
            INSERT INTO business.conversation_executions (tenant_id, relationship_id, conversation_id, message_id, execution_id, runtime_actor_id, origin_channel_binding_id) VALUES (@tenant, @relationship, @conversation, @message, @execution, @actor, '00000000-0000-0000-0000-000000000001'::uuid);
            INSERT INTO business.operational_mandate_snapshots (tenant_id, relationship_id, actor_participant_id, idempotency_identity, constitutional_evidence_id, mandate_id) VALUES (@tenant, @relationship, @actor, @key, @evidence, @mandate);
            INSERT INTO business.conversation_idempotency_outcomes VALUES (@tenant, @relationship, @actor, 'SEND', @key, @message, @execution);
            """,
            parameters
        );
        await ExecuteAsync(owner, insert, parameters);
        var duplicateReplay = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(owner, insert, parameters)
        );
        Assert.Equal(PostgresErrorCodes.UniqueViolation, duplicateReplay.SqlState);

        var intervening = new Dictionary<string, Guid>(parameters) { ["message"] = Guid.NewGuid() };
        await ExecuteAsync(
            owner,
            """
            INSERT INTO business.conversation_messages
                (tenant_id, relationship_id, conversation_id, message_id, evidence_record_id)
            VALUES (@tenant, @relationship, @conversation, @message, @evidence)
            """,
            intervening
        );
        var other = new Dictionary<string, Guid>(parameters)
        {
            ["message"] = Guid.NewGuid(),
            ["execution"] = Guid.NewGuid(),
            ["key"] = Guid.NewGuid(),
            ["mandate"] = Guid.NewGuid(),
            ["evidence"] = Guid.NewGuid(),
        };
        await ExecuteAsync(
            owner,
            """
            INSERT INTO business.conversation_messages (tenant_id, relationship_id, conversation_id, message_id, evidence_record_id) VALUES (@tenant, @relationship, @conversation, @message, @evidence);
            INSERT INTO business.conversation_executions (tenant_id, relationship_id, conversation_id, message_id, execution_id, runtime_actor_id, origin_channel_binding_id) VALUES (@tenant, @relationship, @conversation, @message, @execution, @actor, '00000000-0000-0000-0000-000000000001'::uuid);
            INSERT INTO business.operational_mandate_snapshots (tenant_id, relationship_id, actor_participant_id, idempotency_identity, constitutional_evidence_id, mandate_id) VALUES (@tenant, @relationship, @actor, @key, @evidence, @mandate);
            INSERT INTO business.conversation_idempotency_outcomes VALUES (@tenant, @relationship, @actor, 'SEND', @key, @message, @execution);
            """,
            other
        );
        var wrongEvidence = new Dictionary<string, Guid>(other) { ["evidence"] = Guid.NewGuid() };
        var wrongMandate = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(owner, insert, wrongEvidence)
        );
        Assert.Equal(PostgresErrorCodes.ForeignKeyViolation, wrongMandate.SqlState);

        await using var app = new NpgsqlConnection(
            new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
            {
                Username = "business_app",
                Password = "synthetic-batch-test",
                Options = $"-c app.current_tenant_id={tenant:D}",
            }.ConnectionString
        );
        await app.OpenAsync();
        var atomicTenant = Guid.NewGuid();
        var atomic = new Dictionary<string, Guid>
        {
            ["tenant"] = atomicTenant,
            ["relationship"] = Guid.NewGuid(),
            ["conversation"] = Guid.NewGuid(),
            ["message"] = Guid.NewGuid(),
            ["execution"] = Guid.NewGuid(),
            ["actor"] = Guid.NewGuid(),
            ["key"] = Guid.NewGuid(),
            ["evidence"] = Guid.NewGuid(),
            ["mandate"] = Guid.NewGuid(),
        };
        await ExecuteAsync(
            app,
            $"SELECT set_config('app.current_tenant_id', '{atomicTenant:D}', false)"
        );
        var atomicSource = new ConversationPendingStartSource(
            "demo",
            atomic["tenant"],
            atomic["relationship"],
            atomic["conversation"],
            atomic["message"],
            atomic["execution"],
            atomic["actor"],
            atomic["key"],
            atomic["evidence"],
            atomic["mandate"],
            new("professional-runtime", Guid.NewGuid(), 1, Guid.NewGuid())
        );
        const string atomicCanonical = """
            INSERT INTO business.conversation_messages (tenant_id, relationship_id, conversation_id, message_id, evidence_record_id) VALUES (@tenant, @relationship, @conversation, @message, @evidence);
            INSERT INTO business.conversation_executions (tenant_id, relationship_id, conversation_id, message_id, execution_id, runtime_actor_id, origin_channel_binding_id) VALUES (@tenant, @relationship, @conversation, @message, @execution, @actor, '00000000-0000-0000-0000-000000000001'::uuid);
            INSERT INTO business.operational_mandate_snapshots (tenant_id, relationship_id, actor_participant_id, idempotency_identity, constitutional_evidence_id, mandate_id) VALUES (@tenant, @relationship, @actor, @key, @evidence, @mandate);
            INSERT INTO business.conversation_idempotency_outcomes VALUES (@tenant, @relationship, @actor, 'SEND', @key, @message, @execution);
            """;
        await using (
            var atomicDb = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(app).Options
            )
        )
        {
            await using (var rollback = await atomicDb.Database.BeginTransactionAsync())
            {
                await ExecuteAsync(app, atomicCanonical, atomic);
                await ConversationPendingStartAdmission.InsertAsync(
                    atomicDb,
                    atomicSource,
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                );
                Assert.Equal(
                    1L,
                    await ScalarAsync(
                        app,
                        "SELECT count(*) FROM business.conversation_pending_starts"
                    )
                );
                await rollback.RollbackAsync();
            }
            Assert.Equal(
                0L,
                await ScalarAsync(app, "SELECT count(*) FROM business.conversation_pending_starts")
            );
            Assert.Equal(
                0L,
                await ScalarAsync(
                    app,
                    $"SELECT count(*) FROM business.conversation_messages WHERE tenant_id = '{atomicTenant:D}'"
                )
            );
            await using (var commit = await atomicDb.Database.BeginTransactionAsync())
            {
                await ExecuteAsync(app, atomicCanonical, atomic);
                await ConversationPendingStartAdmission.InsertAsync(
                    atomicDb,
                    atomicSource,
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                );
                await commit.CommitAsync();
            }
            await using (var replay = await atomicDb.Database.BeginTransactionAsync())
            {
                var duplicate = await Assert.ThrowsAsync<PostgresException>(() =>
                    ConversationPendingStartAdmission.InsertAsync(
                        atomicDb,
                        atomicSource,
                        TimeSpan.FromSeconds(1),
                        CancellationToken.None
                    )
                );
                Assert.Equal(PostgresErrorCodes.UniqueViolation, duplicate.SqlState);
                await replay.RollbackAsync();
            }
            Assert.Equal(
                1L,
                await ScalarAsync(app, "SELECT count(*) FROM business.conversation_pending_starts")
            );
        }
        await ExecuteAsync(app, $"SELECT set_config('app.current_tenant_id', '{tenant:D}', false)");
        await using (
            var db = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(app).Options
            )
        )
        {
            var source = new ConversationPendingStartSource(
                "demo",
                tenant,
                relationship,
                conversation,
                other["message"],
                other["execution"],
                actor,
                other["key"],
                other["evidence"],
                other["mandate"],
                new("professional-runtime", Guid.NewGuid(), 1, Guid.NewGuid())
            );
            await Assert.ThrowsAsync<InvalidOperationException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    db,
                    source,
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<InvalidOperationException>(() =>
                ConversationPendingStartAdmission.LockConversationAsync(
                    db,
                    "demo",
                    tenant,
                    relationship,
                    CancellationToken.None
                )
            );
            await using var admission = await db.Database.BeginTransactionAsync();
            await Assert.ThrowsAsync<ArgumentException>(() =>
                ConversationPendingStartAdmission.LockConversationAsync(
                    db,
                    "",
                    tenant,
                    relationship,
                    CancellationToken.None
                )
            );
            await ConversationPendingStartAdmission.LockConversationAsync(
                db,
                "demo",
                tenant,
                relationship,
                CancellationToken.None
            );
            await using var concurrent = new NpgsqlConnection(
                new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
                {
                    Username = "business_app",
                    Password = "synthetic-batch-test",
                    Options = $"-c app.current_tenant_id={tenant:D}",
                }.ConnectionString
            );
            await concurrent.OpenAsync();
            await using var concurrentDb = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(concurrent)
                    .Options
            );
            await using var contender = await concurrentDb.Database.BeginTransactionAsync();
            await ExecuteAsync(concurrent, "SET LOCAL lock_timeout = '250ms'");
            await ConversationPendingStartAdmission.LockConversationAsync(
                concurrentDb,
                "demo",
                tenant,
                Guid.NewGuid(),
                CancellationToken.None
            );
            await ExecuteAsync(concurrent, "SAVEPOINT insert_lock");
            var insertLocked = await Assert.ThrowsAsync<PostgresException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    concurrentDb,
                    source,
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                )
            );
            Assert.Equal(PostgresErrorCodes.LockNotAvailable, insertLocked.SqlState);
            await ExecuteAsync(concurrent, "ROLLBACK TO SAVEPOINT insert_lock");
            var locked = await Assert.ThrowsAsync<PostgresException>(() =>
                ConversationPendingStartAdmission.LockConversationAsync(
                    concurrentDb,
                    "demo",
                    tenant,
                    relationship,
                    CancellationToken.None
                )
            );
            Assert.Equal(PostgresErrorCodes.LockNotAvailable, locked.SqlState);
            await contender.RollbackAsync();
            await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    db,
                    source with
                    {
                        TenantId = Guid.Empty,
                    },
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    db,
                    source,
                    TimeSpan.Zero,
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    db,
                    source with
                    {
                        Environment = "other",
                    },
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    db,
                    source with
                    {
                        EvidenceId = Guid.NewGuid(),
                    },
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    db,
                    source with
                    {
                        ActorId = Guid.NewGuid(),
                    },
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    db,
                    source,
                    TimeSpan.FromHours(1),
                    CancellationToken.None
                )
            );
            await ExecuteAsync(
                owner,
                "UPDATE business.conversation_messages SET channel = 'WEB' WHERE message_id = @message",
                other
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    db,
                    source,
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                )
            );
            await ExecuteAsync(
                owner,
                "UPDATE business.conversation_messages SET channel = 'WHATSAPP', evidence_state = 'PENDING' WHERE message_id = @message",
                other
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.InsertAsync(
                    db,
                    source,
                    TimeSpan.FromSeconds(1),
                    CancellationToken.None
                )
            );
            await ExecuteAsync(
                owner,
                "UPDATE business.conversation_messages SET evidence_state = 'RECORDED' WHERE message_id = @message",
                other
            );
            Assert.Equal(
                other["execution"],
                await ConversationRuntimeEventWorker
                    .StartedCandidates(db)
                    .Where(row => row.TenantId == tenant)
                    .Select(row => row.ExecutionId)
                    .SingleAsync()
            );
            await ConversationPendingStartAdmission.InsertAsync(
                db,
                source,
                TimeSpan.FromSeconds(1),
                CancellationToken.None
            );
            Assert.Empty(
                await ConversationRuntimeEventWorker
                    .StartedCandidates(db)
                    .Where(row => row.TenantId == tenant)
                    .Select(row => row.ExecutionId)
                    .ToListAsync()
            );
            var ordered = await ConversationPendingStartAdmission.ReadOrderedAsync(
                db,
                "demo",
                tenant,
                relationship,
                conversation,
                3,
                CancellationToken.None
            );
            await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() =>
                ConversationPendingStartAdmission.ReadOrderedAsync(
                    db,
                    "demo",
                    tenant,
                    relationship,
                    conversation,
                    0,
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ArgumentException>(() =>
                ConversationPendingStartAdmission.ReadOrderedAsync(
                    db,
                    "demo",
                    tenant,
                    relationship,
                    Guid.Empty,
                    3,
                    CancellationToken.None
                )
            );
            Assert.Equal(
                new[] { message, intervening["message"], other["message"] },
                ordered.Select(row => row.MessageId)
            );
            Assert.Equal(execution, ordered[0].ExecutionId);
            Assert.Null(ordered[1].ExecutionId);
            Assert.Null(ordered[1].AdmittedAt);
            Assert.Equal(other["execution"], ordered[2].ExecutionId);
            var firstMember = BatchCandidate(ordered[0], tenant, relationship, conversation, actor);
            var lastMember = BatchCandidate(ordered[2], tenant, relationship, conversation, actor);
            var bounded = await ConversationPendingStartAdmission.ReadOrderedAsync(
                db,
                "demo",
                tenant,
                relationship,
                conversation,
                2,
                CancellationToken.None
            );
            Assert.Equal(2, bounded.Count);
            Assert.Empty(
                await ConversationPendingStartAdmission.ReadOrderedAsync(
                    db,
                    "other",
                    tenant,
                    relationship,
                    conversation,
                    3,
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.FreezeAsync(
                    db,
                    "demo",
                    tenant,
                    relationship,
                    conversation,
                    Guid.NewGuid(),
                    new([firstMember, lastMember], []),
                    BatchLimits,
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.FreezeAsync(
                    db,
                    "demo",
                    tenant,
                    relationship,
                    conversation,
                    Guid.NewGuid(),
                    new([firstMember], []),
                    BatchLimits with
                    {
                        MaximumTextLength = 4,
                    },
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.FreezeAsync(
                    db,
                    "demo",
                    tenant,
                    relationship,
                    conversation,
                    Guid.NewGuid(),
                    new([firstMember, firstMember], []),
                    BatchLimits,
                    CancellationToken.None
                )
            );
            foreach (
                var invalid in new[]
                {
                    firstMember with
                    {
                        ExecutionId = Guid.NewGuid(),
                    },
                    firstMember with
                    {
                        Sequence = firstMember.Sequence + 1,
                    },
                    firstMember with
                    {
                        AcceptedAt = firstMember.AcceptedAt.AddSeconds(1),
                    },
                    firstMember with
                    {
                        Scope = firstMember.Scope with { TenantId = Guid.NewGuid() },
                    },
                    firstMember with
                    {
                        Text = "different input",
                    },
                    firstMember with
                    {
                        Scope = firstMember.Scope with { Language = "hi-IN" },
                    },
                    firstMember with
                    {
                        Scope = firstMember.Scope with { ActorId = Guid.NewGuid() },
                    },
                    firstMember with
                    {
                        Scope = firstMember.Scope with { SkillId = "other" },
                    },
                    firstMember with
                    {
                        Scope = firstMember.Scope with { ChannelBindingId = Guid.NewGuid() },
                    },
                    firstMember with
                    {
                        Scope = firstMember.Scope with { RecipientDigest = new string('b', 64) },
                    },
                }
            )
                await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                    ConversationPendingStartAdmission.FreezeAsync(
                        db,
                        "demo",
                        tenant,
                        relationship,
                        conversation,
                        Guid.NewGuid(),
                        new([invalid], []),
                        BatchLimits,
                        CancellationToken.None
                    )
                );
            var unclearFirst = firstMember with { Scope = firstMember.Scope with { Task = null } };
            var unclearSecond = lastMember with
            {
                Sequence = firstMember.Sequence + 1,
                Scope = unclearFirst.Scope,
            };
            var individualFallback = ConversationBatchWindow.Select(
                [unclearFirst, unclearSecond],
                new(2, 32, TimeSpan.FromMinutes(5), "\n")
            );
            Assert.Empty(individualFallback.ReadyMembers);
            Assert.Equal(
                new[] { unclearFirst, unclearSecond },
                individualFallback.IndividualMembers
            );
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.FreezeAsync(
                    db,
                    "demo",
                    tenant,
                    relationship,
                    conversation,
                    Guid.NewGuid(),
                    individualFallback,
                    BatchLimits,
                    CancellationToken.None
                )
            );
            var group = new Dictionary<string, Guid>(parameters) { ["batch"] = Guid.NewGuid() };
            await ExecuteAsync(
                app,
                """
                INSERT INTO business.conversation_batch_groups
                    (tenant_id, relationship_id, conversation_id, batch_id)
                VALUES (@tenant, @relationship, @conversation, @batch);
                INSERT INTO business.conversation_batch_members
                    (tenant_id, relationship_id, conversation_id, batch_id, message_id, ordinal)
                VALUES (@tenant, @relationship, @conversation, @batch, @message, 1)
                """,
                group
            );
            var beforeFreeze = await ConversationPendingStartAdmission.ReadOrderedAsync(
                db,
                "demo",
                tenant,
                relationship,
                conversation,
                3,
                CancellationToken.None
            );
            Assert.Equal(3, beforeFreeze.Count);
            Assert.Equal(message, beforeFreeze[0].MessageId);
            await ExecuteAsync(app, "SAVEPOINT incomplete_group");
            var incomplete = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    app,
                    "SET CONSTRAINTS business.conversation_batch_requires_freeze IMMEDIATE"
                )
            );
            Assert.Equal(PostgresErrorCodes.CheckViolation, incomplete.SqlState);
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT incomplete_group");
            await ExecuteAsync(app, "SAVEPOINT direct_freeze");
            var directFreeze = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    app,
                    """
                    INSERT INTO business.conversation_batch_groups
                        (tenant_id, relationship_id, conversation_id, batch_id, frozen_at, member_count)
                    VALUES (@tenant, @relationship, @conversation, gen_random_uuid(), now(), 1)
                    """,
                    group
                )
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, directFreeze.SqlState);
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT direct_freeze");
            await ExecuteAsync(app, "SAVEPOINT duplicate_member");
            var duplicateMember = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    app,
                    """
                    INSERT INTO business.conversation_batch_members
                        (tenant_id, relationship_id, conversation_id, batch_id, message_id, ordinal)
                    VALUES (@tenant, @relationship, @conversation, @batch, @message, 2)
                    """,
                    group
                )
            );
            Assert.Equal(PostgresErrorCodes.UniqueViolation, duplicateMember.SqlState);
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT duplicate_member");
            await ExecuteAsync(app, "SAVEPOINT wrong_scope");
            var wrongScope = new Dictionary<string, Guid>(group)
            {
                ["message"] = other["message"],
                ["conversation"] = Guid.NewGuid(),
            };
            var wrongGroup = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    app,
                    """
                    INSERT INTO business.conversation_batch_members
                        (tenant_id, relationship_id, conversation_id, batch_id, message_id, ordinal)
                    VALUES (@tenant, @relationship, @conversation, @batch, @message, 2)
                    """,
                    wrongScope
                )
            );
            Assert.Equal(PostgresErrorCodes.CheckViolation, wrongGroup.SqlState);
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT wrong_scope");
            await ExecuteAsync(app, "SAVEPOINT incorrect_count");
            var badCount = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    app,
                    """
                    UPDATE business.conversation_batch_groups
                    SET frozen_at = statement_timestamp(), member_count = 2 WHERE batch_id = @batch
                    """,
                    group
                )
            );
            Assert.Equal(PostgresErrorCodes.CheckViolation, badCount.SqlState);
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT incorrect_count");
            await ExecuteAsync(app, "SAVEPOINT missing_count");
            var missingCount = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    app,
                    """
                    UPDATE business.conversation_batch_groups
                    SET frozen_at = statement_timestamp() WHERE batch_id = @batch
                    """,
                    group
                )
            );
            Assert.Equal(PostgresErrorCodes.CheckViolation, missingCount.SqlState);
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT missing_count");
            await ExecuteAsync(app, "SAVEPOINT gapped_members");
            var gappedMember = new Dictionary<string, Guid>(group)
            {
                ["message"] = other["message"],
            };
            await ExecuteAsync(
                app,
                """
                INSERT INTO business.conversation_batch_members
                    (tenant_id, relationship_id, conversation_id, batch_id, message_id, ordinal)
                VALUES (@tenant, @relationship, @conversation, @batch, @message, 2)
                """,
                gappedMember
            );
            var gap = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    app,
                    """
                    UPDATE business.conversation_batch_groups
                    SET frozen_at = statement_timestamp(), member_count = 2 WHERE batch_id = @batch
                    """,
                    group
                )
            );
            Assert.Equal(PostgresErrorCodes.CheckViolation, gap.SqlState);
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT gapped_members");
            await ExecuteAsync(
                app,
                """
                UPDATE business.conversation_batch_groups
                SET frozen_at = statement_timestamp(), member_count = 1 WHERE batch_id = @batch
                """,
                group
            );
            var remaining = await ConversationPendingStartAdmission.ReadOrderedAsync(
                db,
                "demo",
                tenant,
                relationship,
                conversation,
                3,
                CancellationToken.None
            );
            Assert.Single(remaining);
            Assert.Equal(other["message"], remaining[0].MessageId);
            await ExecuteAsync(app, "SAVEPOINT frozen_member");
            var laterMember = new Dictionary<string, Guid>(group)
            {
                ["message"] = other["message"],
            };
            var frozen = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    app,
                    """
                    INSERT INTO business.conversation_batch_members
                        (tenant_id, relationship_id, conversation_id, batch_id, message_id, ordinal)
                    VALUES (@tenant, @relationship, @conversation, @batch, @message, 2)
                    """,
                    laterMember
                )
            );
            Assert.Equal(PostgresErrorCodes.CheckViolation, frozen.SqlState);
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT frozen_member");
            await ExecuteAsync(app, "SAVEPOINT refreeze");
            var refreeze = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    app,
                    "UPDATE business.conversation_batch_groups SET frozen_at = statement_timestamp() WHERE batch_id = @batch",
                    group
                )
            );
            Assert.Equal(PostgresErrorCodes.CheckViolation, refreeze.SqlState);
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT refreeze");
            Assert.Equal(
                2L,
                await ScalarAsync(app, "SELECT count(*) FROM business.conversation_pending_starts")
            );
            Assert.Equal(
                2L,
                await ScalarAsync(
                    app,
                    "SELECT count(*) FROM business.conversation_pending_starts WHERE due_at - admitted_at = interval '1 second'"
                )
            );
            await admission.RollbackAsync();
            await using var resumed = await concurrentDb.Database.BeginTransactionAsync();
            await ConversationPendingStartAdmission.LockConversationAsync(
                concurrentDb,
                "demo",
                tenant,
                relationship,
                CancellationToken.None
            );
            await resumed.RollbackAsync();
        }
        Assert.Equal(
            1L,
            await ScalarAsync(app, "SELECT count(*) FROM business.conversation_pending_starts")
        );
        var committedGroup = new Dictionary<string, Guid>(parameters)
        {
            ["batch"] = Guid.NewGuid(),
        };
        await using (var freeze = await app.BeginTransactionAsync())
        {
            await ExecuteAsync(
                app,
                """
                SELECT pg_sleep(greatest(0, extract(epoch FROM (due_at - statement_timestamp()))) + 0.01)
                FROM business.conversation_pending_starts WHERE message_id = @message
                """,
                parameters
            );
            await using var db = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(app).Options
            );
            await db.Database.UseTransactionAsync(freeze);
            var ready = await ConversationPendingStartAdmission.ReadOrderedAsync(
                db,
                "demo",
                tenant,
                relationship,
                conversation,
                1,
                CancellationToken.None
            );
            var selection = ConversationBatchWindow.Select(
                [BatchCandidate(Assert.Single(ready), tenant, relationship, conversation, actor)],
                new(2, 32, TimeSpan.FromMinutes(5), "\n")
            );
            await ConversationPendingStartAdmission.FreezeAsync(
                db,
                "demo",
                tenant,
                relationship,
                conversation,
                committedGroup["batch"],
                selection,
                BatchLimits,
                CancellationToken.None
            );
            await freeze.CommitAsync();
        }
        var persistedFreeze = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(
                app,
                """
                INSERT INTO business.conversation_batch_members
                    (tenant_id, relationship_id, conversation_id, batch_id, message_id, ordinal)
                VALUES (@tenant, @relationship, @conversation, @batch, @message, 2)
                """,
                committedGroup
            )
        );
        Assert.Equal(PostgresErrorCodes.CheckViolation, persistedFreeze.SqlState);
        var pairedRelationship = Guid.NewGuid();
        var pairedConversation = Guid.NewGuid();
        var pairedMessages = new List<Guid>();
        foreach (var index in Enumerable.Range(0, 2))
        {
            var pair = new Dictionary<string, Guid>
            {
                ["tenant"] = tenant,
                ["relationship"] = pairedRelationship,
                ["conversation"] = pairedConversation,
                ["message"] = Guid.NewGuid(),
                ["execution"] = Guid.NewGuid(),
                ["actor"] = actor,
                ["key"] = Guid.NewGuid(),
                ["evidence"] = Guid.NewGuid(),
                ["mandate"] = Guid.NewGuid(),
            };
            pairedMessages.Add(pair["message"]);
            await ExecuteAsync(
                owner,
                """
                INSERT INTO business.conversation_messages (tenant_id, relationship_id, conversation_id, message_id, evidence_record_id) VALUES (@tenant, @relationship, @conversation, @message, @evidence);
                INSERT INTO business.conversation_executions (tenant_id, relationship_id, conversation_id, message_id, execution_id, runtime_actor_id, origin_channel_binding_id) VALUES (@tenant, @relationship, @conversation, @message, @execution, @actor, '00000000-0000-0000-0000-000000000001'::uuid);
                INSERT INTO business.operational_mandate_snapshots (tenant_id, relationship_id, actor_participant_id, idempotency_identity, constitutional_evidence_id, mandate_id) VALUES (@tenant, @relationship, @actor, @key, @evidence, @mandate);
                INSERT INTO business.conversation_idempotency_outcomes VALUES (@tenant, @relationship, @actor, 'SEND', @key, @message, @execution);
                """,
                pair
            );
            await ExecuteAsync(
                owner,
                index == 0
                    ? """UPDATE business.conversation_messages SET content_json = jsonb_set(content_json, '{0,text}', '"Make a post"') WHERE message_id = @message"""
                    : """UPDATE business.conversation_messages SET content_json = jsonb_set(content_json, '{0,text}', '"for Diwali \ud83d\ude00"') WHERE message_id = @message""",
                pair
            );
            await ExecuteAsync(owner, insert, pair);
        }
        var pairedBatch = Guid.NewGuid();
        await ExecuteAsync(
            owner,
            $"""
            UPDATE business.conversation_pending_starts
            SET due_at = statement_timestamp() + interval '1 minute'
            WHERE tenant_id = '{tenant:D}' AND conversation_id = '{pairedConversation:D}'
            """
        );
        await using (var early = await app.BeginTransactionAsync())
        {
            await using var db = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(app).Options
            );
            await db.Database.UseTransactionAsync(early);
            var rows = await ConversationPendingStartAdmission.ReadOrderedAsync(
                db,
                "demo",
                tenant,
                pairedRelationship,
                pairedConversation,
                2,
                CancellationToken.None
            );
            var first = BatchCandidate(
                rows[0],
                tenant,
                pairedRelationship,
                pairedConversation,
                actor
            ) with
            {
                Text = "Make a post",
            };
            var second = BatchCandidate(
                rows[1],
                tenant,
                pairedRelationship,
                pairedConversation,
                actor
            ) with
            {
                Scope = first.Scope,
                Text = "for Diwali \U0001F600",
            };
            var selection = ConversationBatchWindow.Select([first, second], BatchLimits);
            Assert.Equal(2, selection.ReadyMembers.Count);
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.FreezeAsync(
                    db,
                    "demo",
                    tenant,
                    pairedRelationship,
                    pairedConversation,
                    pairedBatch,
                    selection,
                    BatchLimits,
                    CancellationToken.None
                )
            );
            await early.RollbackAsync();
        }
        await ExecuteAsync(
            owner,
            $"""
            UPDATE business.conversation_pending_starts
            SET admitted_at = statement_timestamp() - interval '3 seconds',
                due_at = statement_timestamp() - interval '2 seconds'
            WHERE tenant_id = '{tenant:D}' AND message_id = '{pairedMessages[0]:D}';
            UPDATE business.conversation_pending_starts
            SET admitted_at = statement_timestamp() - interval '1 second',
                due_at = statement_timestamp() + interval '1 second'
            WHERE tenant_id = '{tenant:D}' AND message_id = '{pairedMessages[1]:D}';
            """
        );
        await using (var late = await app.BeginTransactionAsync())
        {
            await using var db = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(app).Options
            );
            await db.Database.UseTransactionAsync(late);
            var rows = await ConversationPendingStartAdmission.ReadOrderedAsync(
                db,
                "demo",
                tenant,
                pairedRelationship,
                pairedConversation,
                2,
                CancellationToken.None
            );
            var first = BatchCandidate(
                rows[0],
                tenant,
                pairedRelationship,
                pairedConversation,
                actor
            ) with
            {
                Text = "Make a post",
            };
            var second = BatchCandidate(
                rows[1],
                tenant,
                pairedRelationship,
                pairedConversation,
                actor
            ) with
            {
                Scope = first.Scope,
                Text = "for Diwali \U0001F600",
            };
            var selection = ConversationBatchWindow.Select([first, second], BatchLimits);
            Assert.Equal(2, selection.ReadyMembers.Count);
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.FreezeAsync(
                    db,
                    "demo",
                    tenant,
                    pairedRelationship,
                    pairedConversation,
                    pairedBatch,
                    selection,
                    BatchLimits,
                    CancellationToken.None
                )
            );
            await late.RollbackAsync();
        }
        await ExecuteAsync(
            owner,
            $"""
            UPDATE business.conversation_pending_starts
            SET admitted_at = statement_timestamp() - interval '2 seconds',
                due_at = statement_timestamp() - interval '1 second'
            WHERE tenant_id = '{tenant:D}' AND conversation_id = '{pairedConversation:D}'
            """
        );
        await using (var freeze = await app.BeginTransactionAsync())
        {
            await using var db = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(app).Options
            );
            await db.Database.UseTransactionAsync(freeze);
            var rows = await ConversationPendingStartAdmission.ReadOrderedAsync(
                db,
                "demo",
                tenant,
                pairedRelationship,
                pairedConversation,
                2,
                CancellationToken.None
            );
            Assert.Equal(2, rows.Count);
            var first = BatchCandidate(
                rows[0],
                tenant,
                pairedRelationship,
                pairedConversation,
                actor
            ) with
            {
                Text = "Make a post",
            };
            var second = BatchCandidate(
                rows[1],
                tenant,
                pairedRelationship,
                pairedConversation,
                actor
            ) with
            {
                Scope = first.Scope,
                Text = "for Diwali \U0001F600",
            };
            Assert.Single(
                ConversationBatchWindow
                    .Select([first, second], BatchLimits with { MaximumTextLength = 24 })
                    .ReadyMembers
            );
            Assert.Equal(
                2,
                ConversationBatchWindow
                    .Select([first, second], BatchLimits with { MaximumTextLength = 25 })
                    .ReadyMembers.Count
            );
            var incomplete = ConversationBatchWindow.Select([first], BatchLimits);
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.FreezeAsync(
                    db,
                    "demo",
                    tenant,
                    pairedRelationship,
                    pairedConversation,
                    Guid.NewGuid(),
                    incomplete,
                    BatchLimits,
                    CancellationToken.None
                )
            );
            var boundedSelection = ConversationBatchWindow.Select(
                [first, second],
                BatchLimits with
                {
                    MaximumTextLength = 24,
                }
            );
            Assert.Equal(second, boundedSelection.Boundary);
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationPendingStartAdmission.FreezeAsync(
                    db,
                    "demo",
                    tenant,
                    pairedRelationship,
                    pairedConversation,
                    Guid.NewGuid(),
                    boundedSelection with
                    {
                        Boundary = second with { Text = "changed content" },
                    },
                    BatchLimits with
                    {
                        MaximumTextLength = 24,
                    },
                    CancellationToken.None
                )
            );
            var unclear = second with { Scope = second.Scope with { Task = null } };
            var unassignedBoundary = ConversationBatchWindow.Select([first, unclear], BatchLimits);
            Assert.Equal([first], unassignedBoundary.ReadyMembers);
            Assert.Equal(unclear, unassignedBoundary.Boundary);
            await ExecuteAsync(app, "SAVEPOINT bounded_freeze");
            await ConversationPendingStartAdmission.FreezeAsync(
                db,
                "demo",
                tenant,
                pairedRelationship,
                pairedConversation,
                Guid.NewGuid(),
                boundedSelection,
                BatchLimits with
                {
                    MaximumTextLength = 24,
                },
                CancellationToken.None
            );
            await ExecuteAsync(app, "ROLLBACK TO SAVEPOINT bounded_freeze");
            var selected = ConversationBatchWindow.Select([first, second], BatchLimits);
            Assert.Equal(2, selected.ReadyMembers.Count);
            await ConversationPendingStartAdmission.FreezeAsync(
                db,
                "demo",
                tenant,
                pairedRelationship,
                pairedConversation,
                pairedBatch,
                selected,
                BatchLimits,
                CancellationToken.None
            );
            await freeze.CommitAsync();
        }
        Assert.Equal(
            2L,
            await ScalarAsync(
                app,
                $"SELECT count(*) FROM business.conversation_batch_members WHERE batch_id = '{pairedBatch:D}'"
            )
        );
        await ExecuteAsync(
            app,
            $"SELECT set_config('app.current_tenant_id', '{Guid.NewGuid():D}', false)"
        );
        Assert.Equal(
            0L,
            await ScalarAsync(app, "SELECT count(*) FROM business.conversation_pending_starts")
        );
        var denied = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(app, "UPDATE business.conversation_pending_starts SET due_at = now()")
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
    }

    private static ConversationBatchCandidate BatchCandidate(
        ConversationPendingStartCandidate row,
        Guid tenant,
        Guid relationship,
        Guid conversation,
        Guid actor
    ) =>
        new(
            row.MessageId,
            row.ExecutionId!.Value,
            row.Sequence,
            row.AdmittedAt!.Value,
            "input",
            new(
                "demo",
                tenant,
                relationship,
                conversation,
                actor,
                "EMPLOYER",
                Guid.Parse("00000000-0000-0000-0000-000000000001"),
                new string('a', 64),
                Guid.NewGuid(),
                "skill",
                "1.0",
                "en-IN",
                new string('b', 64),
                new("professional-runtime", Guid.NewGuid(), 1, Guid.NewGuid())
            )
        );

    private static async Task ExecuteAsync(
        NpgsqlConnection connection,
        string sql,
        IReadOnlyDictionary<string, Guid>? parameters = null
    )
    {
        await using var command = new NpgsqlCommand(sql, connection);
        if (parameters is not null)
            foreach (var (name, value) in parameters)
                command.Parameters.AddWithValue(name, value);
        await command.ExecuteNonQueryAsync();
    }

    private static async Task<long> ScalarAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = new NpgsqlCommand(sql, connection);
        return (long)(await command.ExecuteScalarAsync())!;
    }
}
