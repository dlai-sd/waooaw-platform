// Implements: WC-134 durable request-boundary questions.
// constitutional_basis: C-023, C-026, C-059, C-063
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationRequestClarificationPostgresTests
{
    [Fact]
    public async Task QuestionsFreezeAtomicallyWithScopedContiguousImmutableSources()
    {
        await using var postgres = new PostgreSqlBuilder("postgres:16-alpine").Build();
        await postgres.StartAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        await Execute(
            owner,
            """
            CREATE ROLE bp_owner NOBYPASSRLS;
            CREATE ROLE business_app LOGIN PASSWORD 'synthetic-clarification-test' NOBYPASSRLS;
            CREATE SCHEMA business;
            GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            CREATE TABLE business.conversation_messages (
                tenant_id uuid NOT NULL, relationship_id uuid NOT NULL, conversation_id uuid NOT NULL,
                message_id uuid PRIMARY KEY, sequence bigint NOT NULL, environment text NOT NULL,
                actor text NOT NULL, channel text NOT NULL, dialogue_act text,
                evidence_state text NOT NULL DEFAULT 'RECORDED',
                UNIQUE (tenant_id, relationship_id, conversation_id, message_id)
            );
            CREATE TABLE business.conversation_executions (
                tenant_id uuid NOT NULL, execution_id uuid NOT NULL, origin_channel_binding_id uuid,
                origin_recipient_digest text, PRIMARY KEY (tenant_id, execution_id)
            );
            CREATE TABLE business.operational_mandate_snapshots (
                tenant_id uuid NOT NULL, mandate_id uuid NOT NULL, agent_instance_id uuid NOT NULL,
                actor_participant_id uuid NOT NULL,
                deadline timestamptz NOT NULL DEFAULT statement_timestamp() + interval '5 minutes',
                PRIMARY KEY (tenant_id, mandate_id)
            );
            CREATE TABLE business.conversation_pending_starts (
                tenant_id uuid NOT NULL, relationship_id uuid NOT NULL, conversation_id uuid NOT NULL,
                message_id uuid NOT NULL, execution_id uuid NOT NULL, actor_id uuid NOT NULL, mandate_id uuid NOT NULL,
                UNIQUE (tenant_id, relationship_id, conversation_id, message_id)
            );
            CREATE TABLE business.provider_event_claims (
                claim_id uuid PRIMARY KEY, environment text NOT NULL, provider text NOT NULL,
                app_binding_digest text NOT NULL, event_identity text NOT NULL,
                payload_digest text NOT NULL, lease_owner uuid, lease_expires_at timestamptz,
                state text NOT NULL, result_json jsonb NOT NULL DEFAULT '{}'::jsonb,
                terminal_at timestamptz, expires_at timestamptz
            );
            CREATE TABLE business.conversation_delivery_observations (
                observation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), environment text NOT NULL,
                tenant_id uuid NOT NULL, relationship_id uuid NOT NULL, message_id uuid NOT NULL,
                provider text NOT NULL, provider_reference_digest text NOT NULL,
                delivery_state text NOT NULL
            );
            CREATE TABLE business.relationship_emergency_stop_latches (
                environment text NOT NULL, tenant_id uuid NOT NULL,
                relationship_id uuid NOT NULL, state text NOT NULL
            );
            GRANT SELECT ON ALL TABLES IN SCHEMA business TO business_app;
            """
        );
        var migration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/99zzz-wc134-request-clarification.sql"
            )
        );
        await Execute(owner, migration);
        await Execute(owner, migration);

        var tenant = Guid.NewGuid();
        var otherTenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var conversation = Guid.NewGuid();
        var actor = Guid.NewGuid();
        var agent = Guid.NewGuid();
        var binding = Guid.NewGuid();
        var first = Guid.NewGuid();
        var second = Guid.NewGuid();
        var questionMessage = Guid.NewGuid();
        var firstExecution = Guid.NewGuid();
        var secondExecution = Guid.NewGuid();
        var third = Guid.NewGuid();
        var fourth = Guid.NewGuid();
        var thirdExecution = Guid.NewGuid();
        var fourthExecution = Guid.NewGuid();
        var firstMandate = Guid.NewGuid();
        var secondMandate = Guid.NewGuid();
        var thirdMandate = Guid.NewGuid();
        var fourthMandate = Guid.NewGuid();
        var serviceQuestion = Guid.NewGuid();
        var question = Guid.NewGuid();
        await Execute(
            owner,
            $"""
            INSERT INTO business.conversation_messages VALUES
                ('{tenant}', '{relationship}', '{conversation}', '{first}', 1, 'demo', 'CUSTOMER', 'WHATSAPP', NULL),
                ('{tenant}', '{relationship}', '{conversation}', '{second}', 2, 'demo', 'CUSTOMER', 'WHATSAPP', NULL),
                ('{tenant}', '{relationship}', '{conversation}', '{questionMessage}', 3, 'demo', 'SYSTEM', 'WHATSAPP', 'ASK'),
                ('{tenant}', '{relationship}', '{conversation}', '{third}', 4, 'demo', 'CUSTOMER', 'WHATSAPP', NULL),
                ('{tenant}', '{relationship}', '{conversation}', '{fourth}', 5, 'demo', 'CUSTOMER', 'WHATSAPP', NULL),
                ('{tenant}', '{relationship}', '{conversation}', '{serviceQuestion}', 6, 'demo', 'SYSTEM', 'WHATSAPP', 'ASK');
            INSERT INTO business.conversation_executions VALUES
                ('{tenant}', '{firstExecution}', '{binding}', repeat('a', 64)),
                ('{tenant}', '{secondExecution}', '{binding}', repeat('a', 64)),
                ('{tenant}', '{thirdExecution}', '{binding}', repeat('a', 64)),
                ('{tenant}', '{fourthExecution}', '{binding}', repeat('a', 64));
            INSERT INTO business.operational_mandate_snapshots
                (tenant_id, mandate_id, agent_instance_id, actor_participant_id) VALUES
                ('{tenant}', '{firstMandate}', '{agent}', '{actor}'),
                ('{tenant}', '{secondMandate}', '{agent}', '{actor}'),
                ('{tenant}', '{thirdMandate}', '{agent}', '{actor}'),
                ('{tenant}', '{fourthMandate}', '{agent}', '{actor}');
            INSERT INTO business.conversation_pending_starts VALUES
                ('{tenant}', '{relationship}', '{conversation}', '{first}', '{firstExecution}', '{actor}', '{firstMandate}'),
                ('{tenant}', '{relationship}', '{conversation}', '{second}', '{secondExecution}', '{actor}', '{secondMandate}'),
                ('{tenant}', '{relationship}', '{conversation}', '{third}', '{thirdExecution}', '{actor}', '{thirdMandate}'),
                ('{tenant}', '{relationship}', '{conversation}', '{fourth}', '{fourthExecution}', '{actor}', '{fourthMandate}');
            """
        );

        var builder = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = "synthetic-clarification-test",
        };
        await using var app = new NpgsqlConnection(builder.ConnectionString);
        await app.OpenAsync();
        await Execute(app, $"SELECT set_config('app.current_tenant_id', '{tenant}', false)");
        var insertQuestion = $"""
            INSERT INTO business.conversation_request_questions
                (tenant_id, relationship_id, conversation_id, question_id, question_message_id,
                 environment, actor_id, actor_role, relationship_version, agent_instance_id,
                 channel_binding_id, recipient_digest)
            VALUES ('{tenant}', '{relationship}', '{conversation}', '{question}', '{questionMessage}',
                    'demo', '{actor}', 'EMPLOYER', 1, '{agent}', '{binding}', repeat('a', 64))
            """;
        var insertMembers = $"""
            INSERT INTO business.conversation_request_question_members VALUES
                ('{tenant}', '{relationship}', '{conversation}', '{question}', '{first}', 1),
                ('{tenant}', '{relationship}', '{conversation}', '{question}', '{second}', 2)
            """;
        var freeze = $"""
            UPDATE business.conversation_request_questions
            SET frozen_at = statement_timestamp(), member_count = 2
            WHERE tenant_id = '{tenant}' AND question_id = '{question}'
            """;

        await using (var transaction = await app.BeginTransactionAsync())
        {
            await Execute(app, insertQuestion);
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                transaction.CommitAsync()
            );
            Assert.Equal(PostgresErrorCodes.CheckViolation, failure.SqlState);
        }
        Assert.Equal(0L, await Count(app, "business.conversation_request_questions"));

        foreach (
            var invalidQuestion in new[]
            {
                insertQuestion.Replace(agent.ToString(), Guid.NewGuid().ToString()),
                insertQuestion.Replace(binding.ToString(), Guid.NewGuid().ToString()),
                insertQuestion.Replace(actor.ToString(), Guid.NewGuid().ToString()),
                insertQuestion.Replace("'demo'", "'uat'"),
            }
        )
        {
            await using var transaction = await app.BeginTransactionAsync();
            await Execute(app, invalidQuestion);
            await Execute(app, insertMembers);
            var failure = await Assert.ThrowsAsync<PostgresException>(() => Execute(app, freeze));
            Assert.Equal(PostgresErrorCodes.CheckViolation, failure.SqlState);
            await transaction.RollbackAsync();
        }

        await using (var transaction = await app.BeginTransactionAsync())
        {
            await Execute(app, insertQuestion);
            await Execute(
                app,
                $"""
                INSERT INTO business.conversation_request_question_members VALUES
                    ('{tenant}', '{relationship}', '{conversation}', '{question}', '{second}', 1),
                    ('{tenant}', '{relationship}', '{conversation}', '{question}', '{first}', 2)
                """
            );
            var failure = await Assert.ThrowsAsync<PostgresException>(() => Execute(app, freeze));
            Assert.Equal(PostgresErrorCodes.CheckViolation, failure.SqlState);
            await transaction.RollbackAsync();
        }

        await using (var transaction = await app.BeginTransactionAsync())
        {
            await Execute(app, insertQuestion);
            await Execute(app, insertMembers);
            await Execute(app, freeze);
            await transaction.CommitAsync();
        }
        Assert.Equal(1L, await Count(app, "business.conversation_request_questions"));
        Assert.Equal(2L, await Count(app, "business.conversation_request_question_members"));
        var memberFailure = await Assert.ThrowsAsync<PostgresException>(() =>
            Execute(
                app,
                $"""
                INSERT INTO business.conversation_request_question_members VALUES
                    ('{tenant}', '{relationship}', '{conversation}', '{question}', '{first}', 3)
                """
            )
        );
        Assert.Equal(PostgresErrorCodes.CheckViolation, memberFailure.SqlState);
        var freezeFailure = await Assert.ThrowsAsync<PostgresException>(() => Execute(app, freeze));
        Assert.Equal(PostgresErrorCodes.CheckViolation, freezeFailure.SqlState);
        var answerFailure = await Assert.ThrowsAsync<PostgresException>(() =>
            Execute(
                app,
                $"""
                INSERT INTO business.conversation_request_answers
                    (tenant_id, relationship_id, conversation_id, question_id, answer_id, response_claim_id,
                     response_payload_digest, question_provider_digest, decision)
                VALUES ('{tenant}', '{relationship}', '{conversation}', '{question}', '{Guid.NewGuid()}',
                        '{Guid.NewGuid()}', repeat('a', 64), repeat('b', 64), 'ONE')
                """
            )
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, answerFailure.SqlState);
        await Execute(app, $"SELECT set_config('app.current_tenant_id', '{otherTenant}', false)");
        Assert.Equal(0L, await Count(app, "business.conversation_request_questions"));
        Assert.Equal(0L, await Count(app, "business.conversation_request_question_members"));

        var dbOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var db = new ConversationStoreDbContext(dbOptions))
        await using (var transaction = await db.Database.BeginTransactionAsync())
        {
            await ConversationOutboundContributionService.PersistClarificationQuestionAsync(
                db,
                tenant,
                actor,
                relationship,
                conversation,
                serviceQuestion,
                "demo",
                "EMPLOYER",
                1,
                new string('a', 64),
                [third, fourth],
                CancellationToken.None
            );
            await transaction.CommitAsync();
        }
        Assert.Equal(2L, await Count(owner, "business.conversation_request_questions"));
        Assert.Equal(4L, await Count(owner, "business.conversation_request_question_members"));
        Guid serviceQuestionId;
        await using (
            var command = new NpgsqlCommand(
                $"""
                SELECT question_id
                FROM business.conversation_request_questions
                WHERE tenant_id = '{tenant}' AND question_message_id = '{serviceQuestion}'
                """,
                owner
            )
        )
        {
            serviceQuestionId = (Guid)(await command.ExecuteScalarAsync())!;
        }

        var duplicateQuestion = Guid.NewGuid();
        await Execute(
            owner,
            $"""
            INSERT INTO business.conversation_messages VALUES
                ('{tenant}', '{relationship}', '{conversation}', '{duplicateQuestion}', 8,
                 'demo', 'SYSTEM', 'WHATSAPP', 'ASK')
            """
        );
        await using (var db = new ConversationStoreDbContext(dbOptions))
        await using (var transaction = await db.Database.BeginTransactionAsync())
        {
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                ConversationOutboundContributionService.PersistClarificationQuestionAsync(
                    db,
                    tenant,
                    actor,
                    relationship,
                    conversation,
                    duplicateQuestion,
                    "demo",
                    "EMPLOYER",
                    1,
                    new string('a', 64),
                    [third, fourth],
                    CancellationToken.None
                )
            );
            Assert.Equal(PostgresErrorCodes.UniqueViolation, failure.SqlState);
            await transaction.RollbackAsync();
        }
        Assert.Equal(2L, await Count(owner, "business.conversation_request_questions"));
        Assert.Equal(4L, await Count(owner, "business.conversation_request_question_members"));

        var claimId = Guid.NewGuid();
        var claimOwner = Guid.NewGuid();
        const string appDigest = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
        const string responseDigest =
            "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd";
        const string questionDigest =
            "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee";
        var responseEvent = $"reply-{Guid.NewGuid():N}";
        await Execute(
            owner,
            $"""
            INSERT INTO business.conversation_delivery_observations
                (environment, tenant_id, relationship_id, message_id, provider,
                 provider_reference_digest, delivery_state)
            VALUES ('demo', '{tenant}', '{relationship}', '{serviceQuestion}', 'WHATSAPP',
                    '{questionDigest}', 'DELIVERED');
            INSERT INTO business.provider_event_claims
                (claim_id, environment, provider, app_binding_digest, event_identity, payload_digest,
                 lease_owner, lease_expires_at, state)
            VALUES ('{claimId}', 'demo', 'WHATSAPP', '{appDigest}', '{responseEvent}', '{responseDigest}',
                    '{claimOwner}', statement_timestamp() + interval '1 minute', 'CLAIMED');
            """
        );
        await Execute(app, $"SELECT set_config('app.current_tenant_id', '{tenant}', false)");
        await using (
            var command = new NpgsqlCommand(
                $"""
                SELECT question_id, decision, result_status
                FROM business.record_conversation_request_answer(
                    'demo', '{appDigest}', '{responseEvent}', '{responseDigest}', '{claimOwner}',
                    '{tenant}', '{relationship}', '{conversation}', '{actor}', 'EMPLOYER', 1,
                    '{binding}', repeat('a', 64), '{questionDigest}', 'ONE'
                )
                """,
                app
            )
        )
        await using (var reader = await command.ExecuteReaderAsync())
        {
            Assert.True(await reader.ReadAsync());
            Assert.Equal(serviceQuestionId, reader.GetGuid(0));
            Assert.Equal("ONE", reader.GetString(1));
            Assert.Equal("CLARIFICATION_RECORDED", reader.GetString(2));
            Assert.False(await reader.ReadAsync());
        }
        Assert.Equal(1L, await Count(app, "business.conversation_request_answers"));
        Assert.Equal(
            1L,
            await Scalar(
                app,
                $"SELECT count(*) FROM business.provider_event_claims WHERE claim_id = '{claimId}' AND state = 'ACCEPTED' AND lease_owner IS NULL"
            )
        );

        await Execute(
            owner,
            $"""
            INSERT INTO business.conversation_messages VALUES
                ('{tenant}', '{relationship}', '{conversation}', '{Guid.NewGuid()}', 7,
                 'demo', 'SYSTEM', 'WHATSAPP', 'ASK')
            """
        );
        await using (var db = new ConversationStoreDbContext(dbOptions))
        await using (var transaction = await db.Database.BeginTransactionAsync())
        {
            await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                ConversationOutboundContributionService.PersistClarificationQuestionAsync(
                    db,
                    tenant,
                    actor,
                    relationship,
                    conversation,
                    Guid.NewGuid(),
                    "demo",
                    "EMPLOYER",
                    1,
                    new string('a', 64),
                    [fourth, third],
                    CancellationToken.None
                )
            );
            await transaction.RollbackAsync();
        }
        Assert.Equal(2L, await Count(owner, "business.conversation_request_questions"));
        Assert.Equal(4L, await Count(owner, "business.conversation_request_question_members"));
    }

    private static async Task Execute(NpgsqlConnection connection, string sql)
    {
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private static async Task<long> Count(NpgsqlConnection connection, string table)
    {
        await using var command = new NpgsqlCommand($"SELECT count(*) FROM {table}", connection);
        return (long)(await command.ExecuteScalarAsync())!;
    }

    private static async Task<long> Scalar(NpgsqlConnection connection, string sql)
    {
        await using var command = new NpgsqlCommand(sql, connection);
        return (long)(await command.ExecuteScalarAsync())!;
    }
}
