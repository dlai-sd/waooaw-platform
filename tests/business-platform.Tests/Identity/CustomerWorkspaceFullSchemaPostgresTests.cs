// Implements: architecture/reference/product/wc085-identity-provisioning-data-contract.md CURRENT Sections 1-7
// constitutional_basis: C-005, C-007, C-026, C-059

using Microsoft.EntityFrameworkCore;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class CustomerWorkspaceFullSchemaPostgresTests
{
    [Fact]
    public async Task FullInitChain_AppliesCustomerWorkspaceMigrationAndResolver()
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

        await using var connection = new NpgsqlConnection(postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            """
            SELECT
                to_regclass('identity.accounts') IS NOT NULL,
                to_regclass('identity.login_methods') IS NOT NULL,
                to_regclass('identity.actor_bindings') IS NOT NULL,
                to_regclass('identity.memberships') IS NOT NULL,
                to_regprocedure('identity.resolve_customer_membership()') IS NOT NULL
            """,
            connection
        );
        await using var reader = await command.ExecuteReaderAsync();

        Assert.True(await reader.ReadAsync());
        Assert.True(reader.GetBoolean(0));
        Assert.True(reader.GetBoolean(1));
        Assert.True(reader.GetBoolean(2));
        Assert.True(reader.GetBoolean(3));
        Assert.True(reader.GetBoolean(4));
        await reader.DisposeAsync();
        await using (
            var outboxDirectory = new NpgsqlCommand(
                """
                SELECT relrowsecurity AND relforcerowsecurity,
                    pg_get_userbyid(relowner) = 'bp_owner',
                    NOT has_table_privilege('business_app', oid, 'SELECT,INSERT,UPDATE,DELETE'),
                    has_function_privilege('business_app',
                        'business.claim_whatsapp_outbox_work(uuid,text)', 'EXECUTE'),
                    NOT has_function_privilege('business_app',
                        'business.sync_whatsapp_outbox_work()', 'EXECUTE')
                FROM pg_class WHERE oid = 'business.whatsapp_outbox_work'::regclass
                """,
                connection
            )
        )
        {
            await using var privileges = await outboxDirectory.ExecuteReaderAsync();
            Assert.True(await privileges.ReadAsync());
            for (var column = 0; column < 5; column++)
                Assert.True(privileges.GetBoolean(column));
        }
        await using (
            var retiredRoutes = new NpgsqlCommand(
                """
                SELECT relrowsecurity AND relforcerowsecurity,
                    pg_get_userbyid(relowner) = 'bp_owner',
                    NOT has_table_privilege('business_app', oid, 'SELECT,INSERT,UPDATE,DELETE'),
                    has_function_privilege('business_app',
                        'business.renew_whatsapp_relationship_route(uuid,text,uuid,uuid,uuid,text,uuid,uuid,uuid,uuid,timestamptz)', 'EXECUTE'),
                    has_function_privilege('business_app',
                        'business.find_whatsapp_delivery_route(uuid,text,text,uuid)', 'EXECUTE'),
                    has_function_privilege('business_app',
                        'business.matches_whatsapp_outbox_route(uuid,uuid,text,text,uuid,uuid)', 'EXECUTE')
                FROM pg_class WHERE oid = 'business.whatsapp_relationship_route_history'::regclass
                """,
                connection
            )
        )
        {
            await using var privileges = await retiredRoutes.ExecuteReaderAsync();
            Assert.True(await privileges.ReadAsync());
            for (var column = 0; column < 6; column++)
                Assert.True(privileges.GetBoolean(column));
            Assert.False(await privileges.ReadAsync());
        }
        await using (
            var routeFunctions = new NpgsqlCommand(
                """
                SELECT p.proname, p.prosecdef, pg_get_userbyid(p.proowner) = 'bp_owner',
                    'search_path=pg_catalog' = ANY(p.proconfig),
                    'row_security=on' = ANY(p.proconfig),
                    NOT EXISTS (
                        SELECT 1 FROM aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
                        WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE')
                FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'business' AND p.proname IN (
                    'renew_whatsapp_relationship_route', 'find_whatsapp_delivery_route', 'matches_whatsapp_outbox_route')
                ORDER BY p.proname
                """,
                connection
            )
        )
        {
            await using var functions = await routeFunctions.ExecuteReaderAsync();
            var checkedFunctions = 0;
            while (await functions.ReadAsync())
            {
                checkedFunctions++;
                for (var column = 1; column < 6; column++)
                    Assert.True(functions.GetBoolean(column), functions.GetString(0));
            }
            Assert.Equal(3, checkedFunctions);
        }

        await using (
            var phoneChange = new NpgsqlCommand(
                """
                SELECT c.relrowsecurity AND c.relforcerowsecurity,
                    pg_get_userbyid(c.relowner) = 'web_session_owner',
                    has_table_privilege('business_app', c.oid, 'SELECT'),
                    has_table_privilege('business_app', c.oid, 'INSERT'),
                    NOT has_table_privilege('business_app', c.oid, 'DELETE'),
                    NOT has_column_privilege('business_app', c.oid, 'destination_candidates', 'UPDATE'),
                    has_column_privilege('business_app', c.oid, 'completed_at', 'UPDATE')
                FROM pg_class c WHERE c.oid = 'identity.phone_changes'::regclass;
                """,
                connection
            )
        )
        {
            await using var columns = await phoneChange.ExecuteReaderAsync();
            Assert.True(await columns.ReadAsync());
            for (var column = 0; column < 7; column++)
                Assert.True(columns.GetBoolean(column));
        }
        await using (
            var phoneFunction = new NpgsqlCommand(
                """
                SELECT p.prosecdef, pg_get_userbyid(p.proowner) = 'identity_whatsapp_recognizer_owner',
                    'search_path=pg_catalog' = ANY(p.proconfig),
                    'row_security=on' = ANY(p.proconfig),
                    has_function_privilege('business_app', p.oid, 'EXECUTE'),
                    NOT EXISTS (
                        SELECT 1 FROM aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
                        WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE')
                FROM pg_proc p WHERE p.oid = 'identity.phone_change_conflicts(uuid,jsonb)'::regprocedure;
                """,
                connection
            )
        )
        {
            await using var function = await phoneFunction.ExecuteReaderAsync();
            Assert.True(await function.ReadAsync());
            for (var column = 0; column < 6; column++)
                Assert.True(function.GetBoolean(column));
        }

        await using (
            var inferenceTables = new NpgsqlCommand(
                """
                SELECT bool_and(c.relrowsecurity AND c.relforcerowsecurity
                    AND pg_get_userbyid(c.relowner) = CASE WHEN n.nspname='ai_runtime' THEN 'air_owner' ELSE 'bp_owner' END),
                    count(*) = 4
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE (n.nspname,c.relname) IN (('ai_runtime','conversation_generations'),
                    ('business','conversation_inference_bindings'),('business','conversation_model_reservations'),
                    ('business','conversation_model_budget_receipts'));
                """,
                connection
            )
        )
        {
            await using var tables = await inferenceTables.ExecuteReaderAsync();
            Assert.True(await tables.ReadAsync());
            Assert.True(tables.GetBoolean(0));
            Assert.True(tables.GetBoolean(1));
        }
        await using (
            var inferenceGrants = new NpgsqlCommand(
                """
                SELECT has_table_privilege('business_app','business.conversation_inference_bindings','SELECT')
                    AND NOT has_table_privilege('business_app','business.conversation_inference_bindings','INSERT')
                    AND NOT has_table_privilege('business_app','business.conversation_inference_bindings','UPDATE')
                    AND NOT has_table_privilege('business_app','business.conversation_inference_bindings','DELETE'),
                    has_column_privilege('business_app','business.conversation_model_reservations','actual_paise','UPDATE')
                    AND NOT has_column_privilege('business_app','business.conversation_model_reservations','reserved_paise','UPDATE')
                    AND NOT has_table_privilege('business_app','business.conversation_model_reservations','DELETE'),
                    has_column_privilege('ai_runtime_app','ai_runtime.conversation_generations','result_json','UPDATE')
                    AND NOT has_column_privilege('ai_runtime_app','ai_runtime.conversation_generations','request_digest','UPDATE')
                    AND NOT has_table_privilege('ai_runtime_app','ai_runtime.conversation_generations','DELETE'),
                    has_table_privilege('business_app','business.conversation_model_budget_receipts','SELECT')
                    AND has_table_privilege('business_app','business.conversation_model_budget_receipts','INSERT')
                    AND NOT has_table_privilege('business_app','business.conversation_model_budget_receipts','UPDATE')
                    AND NOT has_table_privilege('business_app','business.conversation_model_budget_receipts','DELETE');
                """,
                connection
            )
        )
        {
            await using var inferenceGrantReader = await inferenceGrants.ExecuteReaderAsync();
            Assert.True(await inferenceGrantReader.ReadAsync());
            for (var column = 0; column < 4; column++)
                Assert.True(inferenceGrantReader.GetBoolean(column));
        }

        await using var seedCommand = new NpgsqlCommand(
            """
            INSERT INTO business.organisations (tenant_id, name)
            VALUES (
                '20000000-0000-0000-0000-000000000001',
                'Synthetic full-schema organisation'
            );
            ALTER TABLE identity.accounts DISABLE TRIGGER ALL;
            INSERT INTO identity.accounts (
                account_id, initial_tenant_id, origin_registration_id, status
            ) VALUES (
                '10000000-0000-0000-0000-000000000001',
                '20000000-0000-0000-0000-000000000001',
                '30000000-0000-0000-0000-000000000001',
                'ACTIVE'
            );
            ALTER TABLE identity.accounts ENABLE TRIGGER ALL;
            INSERT INTO identity.memberships (
                membership_id, account_id, tenant_id, roles, status
            ) VALUES (
                '40000000-0000-0000-0000-000000000001',
                '10000000-0000-0000-0000-000000000001',
                '20000000-0000-0000-0000-000000000001',
                ARRAY['OWNER']::text[],
                'ACTIVE'
            );
            SELECT count(*),
                   bool_and(admission_content_digest ~ '^sha256:[0-9a-f]{64}$'),
                   bool_and(evidence_set_digest ~ '^sha256:[0-9a-f]{64}$'),
                   bool_and(artifact_digest ~ '^sha256:[0-9a-f]{64}$'),
                   bool_and(policy_version = 'demo-marketplace-admission-v1')
            FROM business.agent_admissions
            WHERE tenant_id = '20000000-0000-0000-0000-000000000001'
              AND professional_type_id = 'DIGITAL_MARKETING_LOCAL_SERVICE'
              AND professional_version = '1.0.0';
            """,
            connection
        );
        await using var seedReader = await seedCommand.ExecuteReaderAsync();

        Assert.True(await seedReader.ReadAsync());
        Assert.Equal(1, seedReader.GetInt64(0));
        Assert.True(seedReader.GetBoolean(1));
        Assert.True(seedReader.GetBoolean(2));
        Assert.True(seedReader.GetBoolean(3));
        Assert.True(seedReader.GetBoolean(4));
        await seedReader.DisposeAsync();

        await using var grants = new NpgsqlCommand(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
                   has_table_privilege('business_app', c.oid, 'SELECT'),
                   has_table_privilege('business_app', c.oid, 'INSERT'),
                   has_table_privilege('business_app', c.oid, 'UPDATE'),
                   has_table_privilege('business_app', c.oid, 'DELETE'),
                   pg_get_userbyid(c.relowner), c.relacl::text
            FROM pg_catalog.pg_class AS c
            WHERE c.oid IN (
                'business.conversation_outbox'::regclass,
                'business.conversation_delivery_observations'::regclass,
                'business.relationship_emergency_stop_latches'::regclass
            )
            ORDER BY c.relname
            """,
            connection
        );
        await using var grantReader = await grants.ExecuteReaderAsync();
        var checkedTables = 0;
        while (await grantReader.ReadAsync())
        {
            checkedTables++;
            var name = grantReader.GetString(0);
            Assert.True(grantReader.GetBoolean(1));
            Assert.True(grantReader.GetBoolean(2));
            Assert.True(grantReader.GetBoolean(3));
            Assert.True(grantReader.GetBoolean(4));
            Assert.True(
                (name == "conversation_outbox") == grantReader.GetBoolean(5),
                $"{name}: unexpected table-level UPDATE privilege; owner={grantReader.GetString(7)}; acl={grantReader.GetString(8)}"
            );
            Assert.False(grantReader.GetBoolean(6));
        }
        Assert.Equal(3, checkedTables);
        await grantReader.DisposeAsync();

        await using (
            var latchGrants = new NpgsqlCommand(
                """
                SELECT has_column_privilege('business_app', 'business.relationship_emergency_stop_latches', 'state', 'UPDATE'),
                       has_column_privilege('business_app', 'business.relationship_emergency_stop_latches', 'evidence_id', 'UPDATE'),
                       has_column_privilege('business_app', 'business.relationship_emergency_stop_latches', 'evidence_confirmed_at', 'UPDATE'),
                       has_column_privilege('business_app', 'business.relationship_emergency_stop_latches', 'tenant_id', 'UPDATE'),
                       has_column_privilege('business_app', 'business.relationship_emergency_stop_latches', 'relationship_id', 'UPDATE'),
                       has_column_privilege('business_app', 'business.relationship_emergency_stop_latches', 'environment', 'UPDATE')
                """,
                connection
            )
        )
        await using (var latchReader = await latchGrants.ExecuteReaderAsync())
        {
            Assert.True(await latchReader.ReadAsync());
            Assert.True(latchReader.GetBoolean(0));
            Assert.True(latchReader.GetBoolean(1));
            Assert.True(latchReader.GetBoolean(2));
            Assert.False(latchReader.GetBoolean(3));
            Assert.False(latchReader.GetBoolean(4));
            Assert.False(latchReader.GetBoolean(5));
        }

        var runtimeGrantMigration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/82-wc134-tenant-conversation-runtime-grants.sql"
            )
        );
        for (var attempt = 0; attempt < 2; attempt++)
        {
            await using var replay = new NpgsqlCommand(runtimeGrantMigration, connection);
            await replay.ExecuteNonQueryAsync();
        }

        await using (
            var disableForcedRls = new NpgsqlCommand(
                "ALTER TABLE business.conversation_outbox NO FORCE ROW LEVEL SECURITY",
                connection
            )
        )
            await disableForcedRls.ExecuteNonQueryAsync();
        await using (var guardedMigration = new NpgsqlCommand(runtimeGrantMigration, connection))
        {
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                guardedMigration.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.RaiseException, failure.SqlState);
        }
        await using var restoreRls = new NpgsqlCommand(
            """
            ROLLBACK;
            ALTER TABLE business.conversation_outbox FORCE ROW LEVEL SECURITY;
            """,
            connection
        );
        await restoreRls.ExecuteNonQueryAsync();

        await using var seedTenantRows = new NpgsqlCommand(
            """
            INSERT INTO business.employment_relationships
                (tenant_id, relationship_id, professional_type, evaluation_intent_id, initiating_participant_id)
            VALUES
                (@tenant_a, @relationship_a, 'DMA', gen_random_uuid(), gen_random_uuid()),
                (@tenant_b, @relationship_b, 'DMA', gen_random_uuid(), gen_random_uuid());
            INSERT INTO business.relationship_participants
                (binding_id, tenant_id, relationship_id, participant_id, role, bound_evidence_id)
            VALUES
                (@binding_a, @tenant_a, @relationship_a, @stop_participant_a, 'EVALUATOR', gen_random_uuid()),
                (@binding_b, @tenant_b, @relationship_b, @stop_participant_b, 'EVALUATOR', gen_random_uuid());
            INSERT INTO business.conversations (tenant_id, relationship_id, conversation_id, environment)
            VALUES
                (@tenant_a, @relationship_a, @conversation_a, 'demo'),
                (@tenant_b, @relationship_b, @conversation_b, 'demo');
            INSERT INTO business.conversation_messages
                (message_id, tenant_id, relationship_id, conversation_id, sequence, actor, channel,
                 content_json, delivery_state, processing_state, evidence_state, environment)
            VALUES
                (@message_a, @tenant_a, @relationship_a, @conversation_a, 1, 'SYSTEM', 'SYSTEM',
                 '[]'::jsonb, 'ACCEPTED', 'COMPLETED', 'NOT_APPLICABLE', 'demo'),
                (@message_b, @tenant_b, @relationship_b, @conversation_b, 1, 'SYSTEM', 'SYSTEM',
                 '[]'::jsonb, 'ACCEPTED', 'COMPLETED', 'NOT_APPLICABLE', 'demo');
            INSERT INTO business.portal_interaction_contexts (tenant_id, context_id, participant_id)
            VALUES
                (@tenant_a, @portal_a, @participant_a),
                (@tenant_b, @portal_b, @participant_b);
            INSERT INTO business.portal_interaction_messages
                (tenant_id, context_id, participant_id, message_id, sequence, actor, content_json, current_surface)
            VALUES
                (@tenant_a, @portal_a, @participant_a, @portal_message_a, 1, 'CUSTOMER', '[]'::jsonb, 'MARKETPLACE'),
                (@tenant_b, @portal_b, @participant_b, @portal_message_b, 1, 'CUSTOMER', '[]'::jsonb, 'MARKETPLACE');
            INSERT INTO business.conversation_delivery_observations
                (environment, tenant_id, relationship_id, message_id, provider, provider_event_identity,
                 provider_reference_digest, delivery_state, observation_digest, retain_until)
            VALUES
                ('demo', @tenant_a, @relationship_a, @message_a, 'WHATSAPP', 'synthetic-a',
                 repeat('a', 64), 'DELIVERED', repeat('b', 64), now() + interval '7 years'),
                ('demo', @tenant_b, @relationship_b, @message_b, 'WHATSAPP', 'synthetic-b',
                 repeat('a', 64), 'DELIVERED', repeat('b', 64), now() + interval '7 years');
            SELECT set_config('app.current_tenant_id', @tenant_a::text, false);
            INSERT INTO business.relationship_emergency_stop_latches
                (environment, tenant_id, relationship_id, stopped_by_participant_id, correlation_id)
            VALUES
                ('demo', @tenant_a, @relationship_a, gen_random_uuid(), gen_random_uuid());
            SELECT set_config('app.current_tenant_id', @tenant_b::text, false);
            INSERT INTO business.relationship_emergency_stop_latches
                (environment, tenant_id, relationship_id, stopped_by_participant_id, correlation_id)
            VALUES
                ('demo', @tenant_b, @relationship_b, gen_random_uuid(), gen_random_uuid());
            SELECT set_config('app.current_tenant_id', '', false);
            INSERT INTO business.conversation_outbox
                (environment, tenant_id, relationship_id, conversation_id, sequence, owner, aggregate_id,
                 operation_family, idempotency_key, payload_digest, payload_reference, purpose, recipient_binding_digest)
            VALUES
                ('demo', @tenant_a, @relationship_a, @conversation_a, 1, 'BP', 'synthetic-a',
                 'REPLY', gen_random_uuid(), repeat('a', 64), 'synthetic', 'CONVERSATION_REPLY', repeat('b', 64)),
                ('demo', @tenant_b, @relationship_b, @conversation_b, 1, 'BP', 'synthetic-b',
                 'REPLY', gen_random_uuid(), repeat('a', 64), 'synthetic', 'CONVERSATION_REPLY', repeat('b', 64));
            """,
            connection
        );
        var tenantA = Guid.NewGuid();
        var tenantB = Guid.NewGuid();
        var relationshipA = Guid.NewGuid();
        var relationshipB = Guid.NewGuid();
        var conversationA = Guid.NewGuid();
        var conversationB = Guid.NewGuid();
        var messageA = Guid.NewGuid();
        var messageB = Guid.NewGuid();
        var portalA = Guid.NewGuid();
        var portalB = Guid.NewGuid();
        var portalMessageA = Guid.NewGuid();
        var portalMessageB = Guid.NewGuid();
        var bindingA = Guid.NewGuid();
        var bindingB = Guid.NewGuid();
        var deliveryBinding = Guid.NewGuid();
        var deliveryActor = Guid.NewGuid();
        var deliveryEvidence = Guid.NewGuid();
        seedTenantRows.Parameters.AddWithValue("tenant_a", tenantA);
        seedTenantRows.Parameters.AddWithValue("tenant_b", tenantB);
        seedTenantRows.Parameters.AddWithValue("relationship_a", relationshipA);
        seedTenantRows.Parameters.AddWithValue("relationship_b", relationshipB);
        seedTenantRows.Parameters.AddWithValue("conversation_a", conversationA);
        seedTenantRows.Parameters.AddWithValue("conversation_b", conversationB);
        seedTenantRows.Parameters.AddWithValue("message_a", messageA);
        seedTenantRows.Parameters.AddWithValue("message_b", messageB);
        seedTenantRows.Parameters.AddWithValue("portal_a", portalA);
        seedTenantRows.Parameters.AddWithValue("portal_b", portalB);
        seedTenantRows.Parameters.AddWithValue("portal_message_a", portalMessageA);
        seedTenantRows.Parameters.AddWithValue("portal_message_b", portalMessageB);
        seedTenantRows.Parameters.AddWithValue("participant_a", Guid.NewGuid());
        seedTenantRows.Parameters.AddWithValue("participant_b", Guid.NewGuid());
        seedTenantRows.Parameters.AddWithValue("binding_a", bindingA);
        seedTenantRows.Parameters.AddWithValue("binding_b", bindingB);
        seedTenantRows.Parameters.AddWithValue("stop_participant_a", Guid.NewGuid());
        seedTenantRows.Parameters.AddWithValue("stop_participant_b", Guid.NewGuid());
        await seedTenantRows.ExecuteNonQueryAsync();
        await using (
            var seedDeliveryBinding = new NpgsqlCommand(
                """
                INSERT INTO business.channel_bindings
                    (binding_id, tenant_id, relationship_id, participant_id, participant_role,
                     channel, external_subject_hash, conversation_id, assurance_level, status,
                     prepared_evidence_id, bound_evidence_id, bound_at, revoked_evidence_id, revoked_at)
                VALUES
                    (@binding, @tenant, @relationship, @actor, 'EVALUATOR',
                     'WHATSAPP', repeat('b', 64), @conversation, 'TIER_4_PORTAL_FRESH', 'REVOKED',
                     gen_random_uuid(), @evidence, now() - interval '1 hour', gen_random_uuid(), now());
                """,
                connection
            )
        )
        {
            seedDeliveryBinding.Parameters.AddWithValue("binding", deliveryBinding);
            seedDeliveryBinding.Parameters.AddWithValue("tenant", tenantA);
            seedDeliveryBinding.Parameters.AddWithValue("relationship", relationshipA);
            seedDeliveryBinding.Parameters.AddWithValue("actor", deliveryActor);
            seedDeliveryBinding.Parameters.AddWithValue(
                "conversation",
                conversationA.ToString("D")
            );
            seedDeliveryBinding.Parameters.AddWithValue("evidence", deliveryEvidence);
            await seedDeliveryBinding.ExecuteNonQueryAsync();
        }

        await using (
            var seedLegacyMismatch = new NpgsqlCommand(
                """
                ALTER TABLE business.conversation_delivery_observations
                    DROP CONSTRAINT conversation_delivery_message_scope_fk;
                INSERT INTO business.conversation_delivery_observations
                    (environment, tenant_id, relationship_id, message_id, provider, provider_event_identity,
                     provider_reference_digest, delivery_state, observation_digest, retain_until)
                VALUES
                    ('demo', @tenant, @relationship, @message, 'WHATSAPP', 'legacy-mismatch',
                     repeat('a', 64), 'DELIVERED', repeat('b', 64), now() + interval '7 years');
                """,
                connection
            )
        )
        {
            seedLegacyMismatch.Parameters.AddWithValue("tenant", tenantA);
            seedLegacyMismatch.Parameters.AddWithValue("relationship", relationshipA);
            seedLegacyMismatch.Parameters.AddWithValue("message", messageB);
            await seedLegacyMismatch.ExecuteNonQueryAsync();
        }
        await using (
            var rejectLegacyMismatch = new NpgsqlCommand(runtimeGrantMigration, connection)
        )
        {
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                rejectLegacyMismatch.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.ForeignKeyViolation, failure.SqlState);
        }
        await using (
            var removeLegacyMismatch = new NpgsqlCommand(
                """
                ROLLBACK;
                DELETE FROM business.conversation_delivery_observations
                WHERE provider_event_identity = 'legacy-mismatch';
                """,
                connection
            )
        )
            await removeLegacyMismatch.ExecuteNonQueryAsync();
        await using (var replayAfterCleanup = new NpgsqlCommand(runtimeGrantMigration, connection))
            await replayAfterCleanup.ExecuteNonQueryAsync();

        await using (
            var seedLegacyOutboxMismatch = new NpgsqlCommand(
                """
                ALTER TABLE business.conversation_outbox
                    DROP CONSTRAINT conversation_outbox_conversation_scope_fk;
                INSERT INTO business.conversation_outbox
                    (environment, tenant_id, relationship_id, conversation_id, sequence, owner, aggregate_id,
                     operation_family, idempotency_key, payload_digest, payload_reference, purpose, recipient_binding_digest)
                VALUES
                    ('demo', @tenant, @relationship, @conversation, 2, 'BP', 'legacy-outbox-mismatch',
                     'REPLY', gen_random_uuid(), repeat('a', 64), 'synthetic', 'CONVERSATION_REPLY', repeat('b', 64));
                """,
                connection
            )
        )
        {
            seedLegacyOutboxMismatch.Parameters.AddWithValue("tenant", tenantA);
            seedLegacyOutboxMismatch.Parameters.AddWithValue("relationship", relationshipA);
            seedLegacyOutboxMismatch.Parameters.AddWithValue("conversation", conversationB);
            await seedLegacyOutboxMismatch.ExecuteNonQueryAsync();
        }
        await using (
            var rejectLegacyOutboxMismatch = new NpgsqlCommand(runtimeGrantMigration, connection)
        )
        {
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                rejectLegacyOutboxMismatch.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.ForeignKeyViolation, failure.SqlState);
        }
        await using (
            var removeLegacyOutboxMismatch = new NpgsqlCommand(
                """
                ROLLBACK;
                DELETE FROM business.conversation_outbox WHERE aggregate_id = 'legacy-outbox-mismatch';
                """,
                connection
            )
        )
            await removeLegacyOutboxMismatch.ExecuteNonQueryAsync();
        await using (
            var replayAfterOutboxCleanup = new NpgsqlCommand(runtimeGrantMigration, connection)
        )
            await replayAfterOutboxCleanup.ExecuteNonQueryAsync();

        await using var appConnection = new NpgsqlConnection(postgres.GetConnectionString());
        await appConnection.OpenAsync();
        await using var scope = new NpgsqlCommand(
            "SET ROLE business_app; SELECT set_config('app.current_tenant_id', @tenant, false)",
            appConnection
        );
        scope.Parameters.AddWithValue("tenant", tenantA.ToString("D"));
        await scope.ExecuteNonQueryAsync();
        await using (
            var routeDb = new EmploymentRelationshipDbContext(
                new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                    .UseNpgsql(appConnection)
                    .Options
            )
        )
        {
            await using var routeTransaction = await routeDb.Database.BeginTransactionAsync();
            await WhatsAppRelationshipRouteAuthority.RequireCanonicalConversationAsync(
                routeDb,
                tenantA,
                relationshipA,
                conversationA,
                "demo",
                CancellationToken.None
            );
            Assert.Same(routeTransaction, routeDb.Database.CurrentTransaction);
            foreach (
                var (tenant, relationship, conversation, environment) in new[]
                {
                    (tenantB, relationshipB, conversationB, "demo"),
                    (tenantA, relationshipB, conversationA, "demo"),
                    (tenantA, relationshipA, conversationB, "demo"),
                    (tenantA, relationshipA, conversationA, "other"),
                    (tenantA, relationshipA, Guid.NewGuid(), "demo"),
                }
            )
                await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
                    WhatsAppRelationshipRouteAuthority.RequireCanonicalConversationAsync(
                        routeDb,
                        tenant,
                        relationship,
                        conversation,
                        environment,
                        CancellationToken.None
                    )
                );
            await using (var revoker = new NpgsqlConnection(postgres.GetConnectionString()))
            {
                await revoker.OpenAsync();
                await using (var timeout = new NpgsqlCommand("SET lock_timeout = '250ms'", revoker))
                    await timeout.ExecuteNonQueryAsync();
                await using var mutation = new NpgsqlCommand(
                    "UPDATE business.conversations SET updated_at = now() WHERE conversation_id = @conversation",
                    revoker
                );
                mutation.Parameters.AddWithValue("conversation", conversationA);
                var blocked = await Assert.ThrowsAsync<PostgresException>(() =>
                    mutation.ExecuteNonQueryAsync()
                );
                Assert.Equal(PostgresErrorCodes.LockNotAvailable, blocked.SqlState);
            }
            await routeTransaction.RollbackAsync();
        }
        await using (
            var deliveryDb = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(appConnection)
                    .Options
            )
        )
        {
            var outboxId = await deliveryDb
                .ConversationOutbox.Where(value =>
                    value.TenantId == tenantA && value.RelationshipId == relationshipA
                )
                .Select(value => value.OutboxId)
                .SingleAsync();
            await using var foreignOutbox = new NpgsqlCommand(
                "SELECT outbox_id FROM business.conversation_outbox WHERE tenant_id = @tenant",
                connection
            );
            foreignOutbox.Parameters.AddWithValue("tenant", tenantB);
            var foreignOutboxId = Assert.IsType<Guid>(await foreignOutbox.ExecuteScalarAsync());
            var route = new WhatsAppRelationshipRoute
            {
                ServiceTenantId = Guid.NewGuid(),
                SenderHash = new string('b', 64),
                TenantId = tenantA,
                BindingId = deliveryBinding,
                ActorId = deliveryActor,
                BoundEvidenceId = deliveryEvidence,
            };
            var status = new WhatsAppProviderStatusEvent(
                "signed-status",
                "provider-message",
                "delivered",
                DateTimeOffset.UtcNow,
                new string('c', 64)
            )
            {
                OutboxId = outboxId,
                SenderBindingDigest = route.SenderHash,
            };
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(() =>
                WhatsAppDeliveryObservationRouting.RequireDeliverySourceAsync(
                    deliveryDb,
                    route,
                    status,
                    "demo",
                    CancellationToken.None
                )
            );
            await using var deliveryTransaction = await deliveryDb.Database.BeginTransactionAsync();
            // Historical delivery evidence remains correlatable after binding revocation and relationship Stop.
            await WhatsAppDeliveryObservationRouting.RequireDeliverySourceAsync(
                deliveryDb,
                route,
                status,
                "demo",
                CancellationToken.None
            );
            await WhatsAppDeliveryObservationRouting.RequireDeliverySourceAsync(
                deliveryDb,
                route,
                status,
                "demo",
                CancellationToken.None
            );
            foreach (
                var changed in new[]
                {
                    status with
                    {
                        OutboxId = null,
                    },
                    status with
                    {
                        OutboxId = Guid.Empty,
                    },
                    status with
                    {
                        OutboxId = Guid.NewGuid(),
                    },
                    status with
                    {
                        OutboxId = foreignOutboxId,
                    },
                    status with
                    {
                        SenderBindingDigest = new string('a', 64),
                    },
                }
            )
                await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
                    WhatsAppDeliveryObservationRouting.RequireDeliverySourceAsync(
                        deliveryDb,
                        route,
                        changed,
                        "demo",
                        CancellationToken.None
                    )
                );
            await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
                WhatsAppDeliveryObservationRouting.RequireDeliverySourceAsync(
                    deliveryDb,
                    route,
                    status,
                    "other",
                    CancellationToken.None
                )
            );
            foreach (var mutation in new[] { "tenant", "binding", "actor", "evidence" })
            {
                var changed = new WhatsAppRelationshipRoute
                {
                    ServiceTenantId = route.ServiceTenantId,
                    SenderHash = route.SenderHash,
                    TenantId = mutation == "tenant" ? tenantB : route.TenantId,
                    BindingId = mutation == "binding" ? Guid.NewGuid() : route.BindingId,
                    ActorId = mutation == "actor" ? Guid.NewGuid() : route.ActorId,
                    BoundEvidenceId =
                        mutation == "evidence" ? Guid.NewGuid() : route.BoundEvidenceId,
                };
                await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
                    WhatsAppDeliveryObservationRouting.RequireDeliverySourceAsync(
                        deliveryDb,
                        changed,
                        status,
                        "demo",
                        CancellationToken.None
                    )
                );
            }
            await using var writer = new NpgsqlConnection(postgres.GetConnectionString());
            await writer.OpenAsync();
            await using (var timeout = new NpgsqlCommand("SET lock_timeout = '250ms'", writer))
                await timeout.ExecuteNonQueryAsync();
            await using (
                var change = new NpgsqlCommand(
                    "UPDATE business.channel_bindings SET external_subject_hash = repeat('d', 64) WHERE binding_id = @binding",
                    writer
                )
            )
            {
                change.Parameters.AddWithValue("binding", deliveryBinding);
                var blocked = await Assert.ThrowsAsync<PostgresException>(() =>
                    change.ExecuteNonQueryAsync()
                );
                Assert.Equal(PostgresErrorCodes.LockNotAvailable, blocked.SqlState);
            }
            await deliveryTransaction.RollbackAsync();
        }
        foreach (
            var (table, column, ownId, foreignId) in new[]
            {
                ("employment_relationships", "relationship_id", relationshipA, relationshipB),
                ("relationship_participants", "binding_id", bindingA, bindingB),
            }
        )
        {
            await using var rowLock = new NpgsqlCommand(
                $"SELECT {column} FROM business.{table} WHERE {column} = @id FOR UPDATE",
                appConnection
            );
            rowLock.Parameters.AddWithValue("id", ownId);
            Assert.Equal(ownId, await rowLock.ExecuteScalarAsync());
            rowLock.Parameters["id"].Value = foreignId;
            Assert.Null(await rowLock.ExecuteScalarAsync());
        }
        await using (
            var confirmLatchEvidence = new NpgsqlCommand(
                """
                UPDATE business.relationship_emergency_stop_latches
                SET state = 'EVIDENCE_CONFIRMED', evidence_id = gen_random_uuid(), evidence_confirmed_at = now()
                WHERE tenant_id = @tenant AND relationship_id = @relationship
                """,
                appConnection
            )
        )
        {
            confirmLatchEvidence.Parameters.AddWithValue("tenant", tenantA);
            confirmLatchEvidence.Parameters.AddWithValue("relationship", relationshipA);
            Assert.Equal(1, await confirmLatchEvidence.ExecuteNonQueryAsync());
        }
        foreach (
            var (environment, conversation) in new[]
            {
                ("demo", conversationB),
                ("other", conversationA),
            }
        )
        {
            await using var invalidOutboxScope = new NpgsqlCommand(
                """
                UPDATE business.conversation_outbox
                SET environment = @environment, conversation_id = @conversation
                WHERE tenant_id = @tenant
                """,
                appConnection
            );
            invalidOutboxScope.Parameters.AddWithValue("environment", environment);
            invalidOutboxScope.Parameters.AddWithValue("conversation", conversation);
            invalidOutboxScope.Parameters.AddWithValue("tenant", tenantA);
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                invalidOutboxScope.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.ForeignKeyViolation, failure.SqlState);
        }
        await using (
            var portalOutbox = new NpgsqlCommand(
                """
                INSERT INTO business.conversation_outbox
                    (environment, tenant_id, portal_context_id, sequence, owner, aggregate_id,
                     operation_family, idempotency_key, payload_digest, payload_reference, purpose, recipient_binding_digest)
                VALUES
                    ('demo', @tenant, @portal, 1, 'BP', 'synthetic-portal',
                     'REPLY', gen_random_uuid(), repeat('a', 64), 'synthetic', 'WHATSAPP_GUEST_DISCOVERY', repeat('b', 64))
                """,
                appConnection
            )
        )
        {
            portalOutbox.Parameters.AddWithValue("tenant", tenantA);
            portalOutbox.Parameters.AddWithValue("portal", portalA);
            Assert.Equal(1, await portalOutbox.ExecuteNonQueryAsync());
        }
        await using (
            var visibleDelivery = new NpgsqlCommand(
                "SELECT count(*) FROM business.conversation_delivery_observations",
                appConnection
            )
        )
            Assert.Equal(1L, await visibleDelivery.ExecuteScalarAsync());
        await using (
            var forbiddenDeliveryUpdate = new NpgsqlCommand(
                "UPDATE business.conversation_delivery_observations SET legal_hold = true",
                appConnection
            )
        )
        {
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                forbiddenDeliveryUpdate.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, failure.SqlState);
        }
        foreach (
            var (environment, tenant, relationship, message, expectedError) in new[]
            {
                (
                    "demo",
                    tenantB,
                    relationshipB,
                    messageB,
                    PostgresErrorCodes.InsufficientPrivilege
                ),
                ("demo", tenantA, relationshipA, messageB, PostgresErrorCodes.ForeignKeyViolation),
                ("other", tenantA, relationshipA, messageA, PostgresErrorCodes.ForeignKeyViolation),
            }
        )
        {
            await using var invalidObservation = new NpgsqlCommand(
                """
                INSERT INTO business.conversation_delivery_observations
                    (environment, tenant_id, relationship_id, message_id, provider, provider_event_identity,
                     provider_reference_digest, delivery_state, observation_digest, retain_until)
                VALUES
                    (@environment, @tenant, @relationship, @message, 'WHATSAPP', gen_random_uuid()::text,
                     repeat('a', 64), 'DELIVERED', repeat('b', 64), now() + interval '7 years')
                """,
                appConnection
            );
            invalidObservation.Parameters.AddWithValue("environment", environment);
            invalidObservation.Parameters.AddWithValue("tenant", tenant);
            invalidObservation.Parameters.AddWithValue("relationship", relationship);
            invalidObservation.Parameters.AddWithValue("message", message);
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                invalidObservation.ExecuteNonQueryAsync()
            );
            Assert.Equal(expectedError, failure.SqlState);
        }
        await using (
            var ownObservation = new NpgsqlCommand(
                """
                INSERT INTO business.conversation_delivery_observations
                    (environment, tenant_id, relationship_id, message_id, provider, provider_event_identity,
                     provider_reference_digest, delivery_state, observation_digest, retain_until)
                VALUES
                    ('demo', @tenant, @relationship, @message, 'WHATSAPP', 'synthetic-own-insert',
                     repeat('a', 64), 'DELIVERED', repeat('b', 64), now() + interval '7 years')
                """,
                appConnection
            )
        )
        {
            ownObservation.Parameters.AddWithValue("tenant", tenantA);
            ownObservation.Parameters.AddWithValue("relationship", relationshipA);
            ownObservation.Parameters.AddWithValue("message", messageA);
            Assert.Equal(1, await ownObservation.ExecuteNonQueryAsync());
        }
        foreach (
            var (portalMessage, succeeds) in new[]
            {
                (portalMessageA, true),
                (portalMessageB, false),
            }
        )
        {
            await using var portalObservation = new NpgsqlCommand(
                """
                INSERT INTO business.conversation_delivery_observations
                    (environment, tenant_id, portal_context_id, portal_message_id, provider, provider_event_identity,
                     provider_reference_digest, delivery_state, observation_digest, retain_until)
                VALUES
                    ('demo', @tenant, @portal, @message, 'WHATSAPP', gen_random_uuid()::text,
                     repeat('a', 64), 'DELIVERED', repeat('b', 64), now() + interval '7 years')
                """,
                appConnection
            );
            portalObservation.Parameters.AddWithValue("tenant", tenantA);
            portalObservation.Parameters.AddWithValue("portal", portalA);
            portalObservation.Parameters.AddWithValue("message", portalMessage);
            if (succeeds)
                Assert.Equal(1, await portalObservation.ExecuteNonQueryAsync());
            else
            {
                var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                    portalObservation.ExecuteNonQueryAsync()
                );
                Assert.Equal(PostgresErrorCodes.ForeignKeyViolation, failure.SqlState);
            }
        }
        foreach (
            var table in new[] { "conversation_outbox", "relationship_emergency_stop_latches" }
        )
        {
            await using var visible = new NpgsqlCommand(
                $"SELECT count(*) FROM business.{table}",
                appConnection
            );
            Assert.Equal(
                table == "conversation_outbox" ? 2L : 1L,
                await visible.ExecuteScalarAsync()
            );
            await using var foreign = new NpgsqlCommand(
                $"UPDATE business.{table} SET {(table == "conversation_outbox" ? "environment = 'demo'" : "state = 'LATCHED'")} WHERE tenant_id = @tenant",
                appConnection
            );
            foreign.Parameters.AddWithValue("tenant", tenantB);
            Assert.Equal(0, await foreign.ExecuteNonQueryAsync());
            await using var reassign = new NpgsqlCommand(
                $"UPDATE business.{table} SET tenant_id = @foreign WHERE tenant_id = @own",
                appConnection
            );
            reassign.Parameters.AddWithValue("foreign", tenantB);
            reassign.Parameters.AddWithValue("own", tenantA);
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                reassign.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, failure.SqlState);
        }
    }
}
