// Implements: work-contracts/WC-134-requirements.yaml WC134-R002, WC134-R005
// Constitutional basis: C-023, C-026, C-059, C-063

using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Waooaw.BusinessPlatform.Tests.Identity;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppAttachmentPostgresTests(CustomerPhoneChangeSchemaFixture schema)
    : IClassFixture<CustomerPhoneChangeSchemaFixture>
{
    [Fact]
    public async Task ActiveSenderIndexMigrationIsReplayableAndTenantScoped()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        await using var connection = new NpgsqlConnection(postgres.GetConnectionString());
        await connection.OpenAsync();
        await using (
            var setup = new NpgsqlCommand(
                """
                CREATE SCHEMA business;
                CREATE ROLE business_app NOLOGIN;
                CREATE ROLE bp_owner NOLOGIN;
                GRANT USAGE ON SCHEMA business TO business_app;
                GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
                """,
                connection
            )
        )
            await setup.ExecuteNonQueryAsync();
        foreach (
            var path in new[]
            {
                "infrastructure/postgres/init/19-ae01-employment-relationship.sql",
                "infrastructure/postgres/init/22-ae01-continuity-evidence.sql",
            }
        )
        {
            var prerequisite = await File.ReadAllTextAsync(RepositoryPaths.Resolve(path));
            await using var apply = new NpgsqlCommand(prerequisite, connection);
            await apply.ExecuteNonQueryAsync();
        }
        var sql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/81-wc134-whatsapp-active-binding-index.sql"
            )
        );
        for (var attempt = 0; attempt < 2; attempt++)
        {
            await using var migration = new NpgsqlCommand(sql, connection);
            await migration.ExecuteNonQueryAsync();
        }
        var routeSql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/91-wc134-whatsapp-relationship-route-directory.sql"
            )
        );
        for (var attempt = 0; attempt < 2; attempt++)
        {
            await using var migration = new NpgsqlCommand(routeSql, connection);
            await migration.ExecuteNonQueryAsync();
        }
        await using var verify = new NpgsqlCommand(
            """
            SELECT pg_get_indexdef(indexrelid), c.relrowsecurity, c.relforcerowsecurity
            FROM pg_index i
            JOIN pg_class c ON c.oid = i.indrelid
            WHERE i.indexrelid = 'business.channel_bindings_active_whatsapp_sender_idx'::regclass
            """,
            connection
        );
        await using var reader = await verify.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        var definition = reader.GetString(0);
        Assert.Contains("(tenant_id, external_subject_hash)", definition, StringComparison.Ordinal);
        Assert.Contains("channel", definition, StringComparison.Ordinal);
        Assert.Contains("WHATSAPP", definition, StringComparison.Ordinal);
        Assert.Contains("status", definition, StringComparison.Ordinal);
        Assert.Contains("ACTIVE", definition, StringComparison.Ordinal);
        Assert.True(reader.GetBoolean(1));
        Assert.True(reader.GetBoolean(2));
        Assert.False(await reader.ReadAsync());
        await reader.DisposeAsync();

        var tenant = Guid.NewGuid();
        var foreignTenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var foreignRelationship = Guid.NewGuid();
        var participantBinding = Guid.NewGuid();
        var foreignParticipantBinding = Guid.NewGuid();
        var channelBinding = Guid.NewGuid();
        var foreignChannelBinding = Guid.NewGuid();
        await using (
            var seed = new NpgsqlCommand(
                """
                INSERT INTO business.employment_relationships
                    (tenant_id, relationship_id, professional_type, evaluation_intent_id, initiating_participant_id)
                VALUES
                    (@tenant, @relationship, 'DMA', gen_random_uuid(), gen_random_uuid()),
                    (@foreign_tenant, @foreign_relationship, 'DMA', gen_random_uuid(), gen_random_uuid());
                INSERT INTO business.relationship_participants
                    (tenant_id, relationship_id, binding_id, participant_id, role, bound_evidence_id)
                VALUES
                    (@tenant, @relationship, @participant, gen_random_uuid(), 'EVALUATOR', gen_random_uuid()),
                    (@foreign_tenant, @foreign_relationship, @foreign_participant, gen_random_uuid(), 'EVALUATOR', gen_random_uuid());
                INSERT INTO business.channel_bindings
                    (tenant_id, relationship_id, binding_id, participant_id, participant_role, channel,
                     external_subject_hash, conversation_id, assurance_level, status,
                     prepared_evidence_id, bound_evidence_id, bound_at)
                VALUES
                    (@tenant, @relationship, @channel, gen_random_uuid(), 'EVALUATOR', 'WHATSAPP',
                     repeat('a', 64), gen_random_uuid()::text, 'TIER_4_PORTAL_FRESH', 'ACTIVE',
                     gen_random_uuid(), gen_random_uuid(), now()),
                    (@foreign_tenant, @foreign_relationship, @foreign_channel, gen_random_uuid(), 'EVALUATOR', 'WHATSAPP',
                     repeat('b', 64), gen_random_uuid()::text, 'TIER_4_PORTAL_FRESH', 'ACTIVE',
                     gen_random_uuid(), gen_random_uuid(), now());
                """,
                connection
            )
        )
        {
            seed.Parameters.AddWithValue("tenant", tenant);
            seed.Parameters.AddWithValue("foreign_tenant", foreignTenant);
            seed.Parameters.AddWithValue("relationship", relationship);
            seed.Parameters.AddWithValue("foreign_relationship", foreignRelationship);
            seed.Parameters.AddWithValue("participant", participantBinding);
            seed.Parameters.AddWithValue("foreign_participant", foreignParticipantBinding);
            seed.Parameters.AddWithValue("channel", channelBinding);
            seed.Parameters.AddWithValue("foreign_channel", foreignChannelBinding);
            await seed.ExecuteNonQueryAsync();
        }
        await using var transaction = await connection.BeginTransactionAsync();
        await using (
            var scope = new NpgsqlCommand(
                "SELECT set_config('app.current_tenant_id', @tenant, true); SET LOCAL ROLE business_app;",
                connection,
                transaction
            )
        )
        {
            scope.Parameters.AddWithValue("tenant", tenant.ToString("D"));
            await scope.ExecuteNonQueryAsync();
        }
        foreach (
            var (table, column, ownId, foreignId) in new[]
            {
                ("employment_relationships", "relationship_id", relationship, foreignRelationship),
                (
                    "relationship_participants",
                    "binding_id",
                    participantBinding,
                    foreignParticipantBinding
                ),
                ("channel_bindings", "binding_id", channelBinding, foreignChannelBinding),
            }
        )
        {
            await using var locked = new NpgsqlCommand(
                $"SELECT {column} FROM business.{table} WHERE {column} = @id FOR UPDATE",
                connection,
                transaction
            );
            locked.Parameters.AddWithValue("id", ownId);
            Assert.Equal(ownId, await locked.ExecuteScalarAsync());
            locked.Parameters["id"].Value = foreignId;
            Assert.Null(await locked.ExecuteScalarAsync());
        }
        await transaction.RollbackAsync();

        var serviceTenant = Guid.NewGuid();
        await using (
            var seedRoutes = new NpgsqlCommand(
                """
                INSERT INTO business.whatsapp_relationship_routes
                    (service_tenant_id, sender_hash, tenant_id, binding_id, identity_link_id,
                     actor_issuer, actor_id, account_id, membership_id, bound_evidence_id, published_at)
                SELECT @service_tenant, external_subject_hash, tenant_id, binding_id, gen_random_uuid(),
                       'https://identity.test', participant_id, gen_random_uuid(), gen_random_uuid(),
                       bound_evidence_id, now()
                FROM business.channel_bindings WHERE binding_id IN (@channel, @foreign_channel);
                """,
                connection
            )
        )
        {
            seedRoutes.Parameters.AddWithValue("service_tenant", serviceTenant);
            seedRoutes.Parameters.AddWithValue("channel", channelBinding);
            seedRoutes.Parameters.AddWithValue("foreign_channel", foreignChannelBinding);
            await seedRoutes.ExecuteNonQueryAsync();
        }
        foreach (
            var (scopeTenant, expectedCount) in new[]
            {
                (serviceTenant, 2L),
                (tenant, 1L),
                (foreignTenant, 1L),
                (Guid.NewGuid(), 0L),
            }
        )
        {
            await using var scopedTransaction = await connection.BeginTransactionAsync();
            await using (
                var scope = new NpgsqlCommand(
                    "SELECT set_config('app.current_tenant_id', @tenant, true); SET LOCAL ROLE business_app;",
                    connection,
                    scopedTransaction
                )
            )
            {
                scope.Parameters.AddWithValue("tenant", scopeTenant.ToString("D"));
                await scope.ExecuteNonQueryAsync();
            }
            await using var countRoutes = new NpgsqlCommand(
                "SELECT count(*) FROM business.whatsapp_relationship_routes",
                connection,
                scopedTransaction
            );
            Assert.Equal(expectedCount, await countRoutes.ExecuteScalarAsync());
            if (scopeTenant == serviceTenant)
            {
                await using var countBindings = new NpgsqlCommand(
                    "SELECT count(*) FROM business.channel_bindings",
                    connection,
                    scopedTransaction
                );
                Assert.Equal(0L, await countBindings.ExecuteScalarAsync());
                await using var exactRoute = new NpgsqlCommand(
                    """
                    SELECT tenant_id FROM business.whatsapp_relationship_routes
                    WHERE service_tenant_id = @service_tenant AND sender_hash = repeat('b', 64)
                    """,
                    connection,
                    scopedTransaction
                );
                exactRoute.Parameters.AddWithValue("service_tenant", serviceTenant);
                Assert.Equal(foreignTenant, await exactRoute.ExecuteScalarAsync());
                await using var forbiddenUpdate = new NpgsqlCommand(
                    "UPDATE business.whatsapp_relationship_routes SET tenant_id = @tenant",
                    connection,
                    scopedTransaction
                );
                forbiddenUpdate.Parameters.AddWithValue("tenant", serviceTenant);
                var denied = await Assert.ThrowsAsync<PostgresException>(() =>
                    forbiddenUpdate.ExecuteNonQueryAsync()
                );
                Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
            }
            await scopedTransaction.RollbackAsync();
        }
        await using var security = new NpgsqlCommand(
            """
            SELECT c.relrowsecurity, c.relforcerowsecurity, pg_get_userbyid(c.relowner),
                   has_table_privilege('business_app', c.oid, 'DELETE')
            FROM pg_class c WHERE c.oid = 'business.whatsapp_relationship_routes'::regclass
            """,
            connection
        );
        await using var routeSecurity = await security.ExecuteReaderAsync();
        Assert.True(await routeSecurity.ReadAsync());
        Assert.True(routeSecurity.GetBoolean(0));
        Assert.True(routeSecurity.GetBoolean(1));
        Assert.Equal("bp_owner", routeSecurity.GetString(2));
        Assert.False(routeSecurity.GetBoolean(3));
    }

    [Theory]
    [InlineData("none")]
    [InlineData("relationship")]
    [InlineData("participant")]
    [InlineData("withdrawal")]
    [InlineData("guest-stop")]
    [InlineData("competing-binding")]
    [InlineData("sender-reassigned")]
    [InlineData("concurrent")]
    [InlineData("proof-expires-after-save")]
    [InlineData("identity-membership")]
    [InlineData("identity-link")]
    [InlineData("identity-proof")]
    [InlineData("missing-identity")]
    [InlineData("missing-actor")]
    [InlineData("missing-membership")]
    [InlineData("foreign-link")]
    public async Task AttachmentRechecksLateChangesWithDistinctForcedRlsTenants(string change)
    {
        var ownerConnection = schema.OwnerConnection;
        var relationshipOptions = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(ownerConnection)
            .Options;
        var conversationOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(ownerConnection)
            .Options;
        var tenant = Guid.NewGuid();
        var guestTenant = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var digest = participantId.ToString("N") + participantId.ToString("N");
        var actor = new VerifiedCustomerActor(
            "https://synthetic.invalid/attachment-owner",
            participantId.ToString("D")
        );
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            tenant,
            Guid.NewGuid(),
            ["OWNER"]
        );
        var linkId = Guid.NewGuid();
        var concurrentLinkId = Guid.NewGuid();
        await SeedAttachmentIdentityAsync(
            ownerConnection,
            actor,
            membership,
            guestTenant,
            linkId,
            concurrentLinkId,
            digest
        );
        await using (var owner = new EmploymentRelationshipDbContext(relationshipOptions))
        {
            owner.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenant,
                    RelationshipId = relationshipId,
                    ProfessionalType = "DMA",
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = participantId,
                    State = EmploymentRelationshipState.TrialActive,
                }
            );
            owner.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenant,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            owner.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = tenant,
                    PhoneHmac = digest,
                    OptedInAt = DateTimeOffset.UtcNow,
                    LastInboundAt = DateTimeOffset.UtcNow,
                }
            );
            await owner.SaveChangesAsync();
        }
        await using (var owner = new ConversationStoreDbContext(conversationOptions))
        {
            owner.Add(
                new WhatsAppGuestSession
                {
                    TenantId = guestTenant,
                    BindingDigest = digest,
                    FirstObservedAt = DateTimeOffset.UtcNow,
                    LastInboundAt = DateTimeOffset.UtcNow,
                }
            );
            await owner.SaveChangesAsync();
        }
        await using var admin = new NpgsqlConnection(ownerConnection);
        await admin.OpenAsync();
        var connectionString = schema.AppConnection;
        var http = new HttpContextAccessor { HttpContext = new DefaultHttpContext() };
        http.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenant.ToString("D");
        var clock = new AttachmentClock { Now = DateTimeOffset.UtcNow };
        var execution = new WhatsAppTenantExecutionScope(
            new Gate(guestTenant),
            TimeProvider.System
        );
        var interceptor = new TenantDbConnectionInterceptor(
            http,
            NullLogger<TenantDbConnectionInterceptor>.Instance,
            execution
        );
        var relationships = new RelationshipFactory(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(connectionString)
                .AddInterceptors(interceptor)
                .AddInterceptors(
                    new ExpireProofAfterBindingSave(clock, change == "proof-expires-after-save")
                )
                .Options
        );
        var conversations = new ConversationFactory(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseNpgsql(connectionString)
                .AddInterceptors(interceptor)
                .Options
        );
        var arrived = 0;
        var evidenceBarrier = new TaskCompletionSource(
            TaskCreationOptions.RunContinuationsAsynchronously
        );
        var gateway = new MutatingGateway(async () =>
        {
            if (
                change
                is "none"
                    or "proof-expires-after-save"
                    or "missing-identity"
                    or "missing-actor"
                    or "missing-membership"
                    or "foreign-link"
            )
                return;
            if (change == "concurrent")
            {
                if (Interlocked.Increment(ref arrived) == 2)
                    evidenceBarrier.TrySetResult();
                await evidenceBarrier.Task.WaitAsync(TimeSpan.FromSeconds(15));
                return;
            }
            if (change is "competing-binding" or "sender-reassigned")
            {
                await using var owner = new EmploymentRelationshipDbContext(relationshipOptions);
                var boundRelationship = relationshipId;
                if (change == "sender-reassigned")
                {
                    boundRelationship = Guid.NewGuid();
                    owner.EmploymentRelationships.Add(
                        new EmploymentRelationship
                        {
                            TenantId = tenant,
                            RelationshipId = boundRelationship,
                            ProfessionalType = "DMA",
                            EvaluationIntentId = Guid.NewGuid(),
                            InitiatingParticipantId = Guid.NewGuid(),
                            State = EmploymentRelationshipState.Active,
                        }
                    );
                }
                owner.ChannelBindings.Add(
                    new Waooaw.BusinessPlatform.Infrastructure.ChannelBinding
                    {
                        TenantId = tenant,
                        RelationshipId = boundRelationship,
                        ParticipantId = Guid.NewGuid(),
                        ParticipantRole = "EVALUATOR",
                        Channel = "WHATSAPP",
                        ExternalSubjectHash =
                            change == "sender-reassigned" ? digest : new string('d', 64),
                        ConversationId = Guid.NewGuid().ToString("D"),
                        AssuranceLevel = "TIER_4_PORTAL_FRESH",
                        Status = "ACTIVE",
                        PreparedEvidenceId = Guid.NewGuid(),
                        BoundEvidenceId = Guid.NewGuid(),
                        BoundAt = DateTimeOffset.UtcNow,
                    }
                );
                await owner.SaveChangesAsync();
                return;
            }
            var sql = change switch
            {
                "relationship" =>
                    "UPDATE business.employment_relationships SET state = 'STOPPED_EMERGENCY' WHERE relationship_id = @relationship",
                "participant" =>
                    "UPDATE business.relationship_participants SET status = 'REVOKED', revoked_evidence_id = gen_random_uuid(), revoked_at = now() WHERE relationship_id = @relationship",
                "withdrawal" =>
                    "UPDATE business.whatsapp_journey_contacts SET opted_out_at = now() WHERE tenant_id = @tenant",
                "guest-stop" =>
                    "UPDATE business.whatsapp_guest_sessions SET stopped_at = now() WHERE tenant_id = @guest_tenant",
                "identity-membership" =>
                    "UPDATE identity.memberships SET status = 'SUSPENDED' WHERE membership_id = @membership",
                "identity-link" =>
                    "UPDATE identity.account_links SET state = 'Cancelled', cancellation_evidence_id = gen_random_uuid() WHERE link_id = @link",
                "identity-proof" =>
                    "UPDATE identity.verification_challenges SET state = 'Expired' WHERE challenge_id = (SELECT verified_mobile_proof_id FROM identity.account_links WHERE link_id = @link)",
                _ => throw new ArgumentOutOfRangeException(nameof(change)),
            };
            await using var mutation = new NpgsqlCommand(sql, admin);
            mutation.Parameters.AddWithValue("relationship", relationshipId);
            mutation.Parameters.AddWithValue("tenant", tenant);
            mutation.Parameters.AddWithValue("guest_tenant", guestTenant);
            mutation.Parameters.AddWithValue("membership", membership.MembershipId);
            mutation.Parameters.AddWithValue("link", linkId);
            Assert.Equal(1, await mutation.ExecuteNonQueryAsync());
        });
        var environmentOptions = Options.Create(
            new Wc120ConversationOptions { Enabled = true, Environment = "demo" }
        );
        var conversation = new ConversationService(
            conversations,
            relationships,
            new ConversationConstitutionalGatewayStub(),
            new ConversationExecutionGatewayStub(),
            new OperationalMandateResolverStub(),
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('c', 48) })
            ),
            conversationOptions: environmentOptions
        );
        var service = new WhatsAppJourneyService(
            relationships,
            new Evidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            gateway,
            conversationDbFactory: conversations,
            conversationService: conversation,
            tenantExecutionScope: execution,
            clock: clock,
            conversationOptions: environmentOptions,
            identity: change == "missing-identity"
                ? null
                : IdentityTestHelpers.CreateService(new IdentityFactory(connectionString))
        );
        var proof = new PortalPhoneAttachProof(
            participantId,
            "TIER_4_PORTAL_FRESH",
            clock.GetUtcNow(),
            Guid.NewGuid()
        )
        {
            Actor = change == "missing-actor" ? null : actor,
            Membership = change == "missing-membership" ? null : membership,
        };
        var attachment = () =>
            service.AttachLinkedPhoneAsync(
                tenant,
                relationshipId,
                change == "foreign-link" ? Guid.NewGuid() : linkId,
                digest,
                true,
                proof,
                CancellationToken.None
            );
        if (change == "concurrent")
        {
            await conversation.EnsureConversationAsync(
                tenant,
                relationshipId,
                CancellationToken.None
            );
            async Task<bool> AttemptAsync(string sender)
            {
                try
                {
                    await service.AttachLinkedPhoneAsync(
                        tenant,
                        relationshipId,
                        sender == digest ? linkId : concurrentLinkId,
                        sender,
                        true,
                        proof with
                        {
                            CorrelationId = Guid.NewGuid(),
                        },
                        CancellationToken.None
                    );
                    return true;
                }
                catch (ConstitutionalActionDeniedException)
                {
                    return false;
                }
            }
            var outcomes = await Task.WhenAll(
                    AttemptAsync(digest),
                    AttemptAsync(new string('e', 64))
                )
                .WaitAsync(TimeSpan.FromSeconds(30));
            Assert.Equal(1, outcomes.Count(result => result));
        }
        else if (change == "none")
            Assert.Equal(tenant, (await attachment()).TenantId);
        else if (change == "missing-identity")
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(attachment);
        else if (change is "missing-actor" or "missing-membership")
            await Assert.ThrowsAsync<IdentityActionDeniedException>(attachment);
        else if (
            change is "identity-membership" or "identity-link" or "identity-proof" or "foreign-link"
        )
            await Assert.ThrowsAsync<IdentityResourceNotFoundException>(attachment);
        else
            await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(attachment);

        await using (var customer = relationships.CreateDbContext())
        {
            Assert.Equal(
                change is "none" or "competing-binding" or "sender-reassigned" or "concurrent"
                    ? 1
                    : 0,
                await customer.ChannelBindings.CountAsync()
            );
        }
        await using (var customer = conversations.CreateDbContext())
        {
            Assert.Empty(await customer.Set<WhatsAppGuestSession>().ToListAsync());
        }
    }

    [Fact]
    public async Task ContactPolicyReplaysAndDeniesForeignReadsWritesAndRetargeting()
    {
        var migration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/97-wc134-whatsapp-contact-tenant-policy.sql"
            )
        );
        await schema.ExecuteAsync(migration);
        await schema.ExecuteAsync(migration);
        var tenant = Guid.NewGuid();
        var foreignTenant = Guid.NewGuid();
        await using var connection = new NpgsqlConnection(schema.OwnerConnection);
        await connection.OpenAsync();
        await using (
            var seed = new NpgsqlCommand(
                """
                INSERT INTO business.whatsapp_journey_contacts(tenant_id, phone_hmac, opted_in_at, last_inbound_at)
                VALUES (@tenant, @own_hash, now(), now()), (@foreign_tenant, @foreign_hash, now(), now());
                """,
                connection
            )
        )
        {
            seed.Parameters.AddWithValue("tenant", tenant);
            seed.Parameters.AddWithValue("foreign_tenant", foreignTenant);
            seed.Parameters.AddWithValue("own_hash", tenant.ToString("N") + tenant.ToString("N"));
            seed.Parameters.AddWithValue(
                "foreign_hash",
                foreignTenant.ToString("N") + foreignTenant.ToString("N")
            );
            await seed.ExecuteNonQueryAsync();
        }
        foreach (var role in new[] { "business_app", "bp_owner" })
        {
            await using var transaction = await connection.BeginTransactionAsync();
            await using (
                var context = new NpgsqlCommand(
                    $"SET LOCAL ROLE {role}; SELECT set_config('app.current_tenant_id', @tenant, true)",
                    connection,
                    transaction
                )
            )
            {
                context.Parameters.AddWithValue("tenant", tenant.ToString("D"));
                await context.ExecuteNonQueryAsync();
            }
            await using (
                var read = new NpgsqlCommand(
                    "SELECT count(*) FROM business.whatsapp_journey_contacts",
                    connection,
                    transaction
                )
            )
                Assert.Equal(1L, await read.ExecuteScalarAsync());
            await using (
                var update = new NpgsqlCommand(
                    "UPDATE business.whatsapp_journey_contacts SET last_inbound_at = now() WHERE tenant_id = @tenant",
                    connection,
                    transaction
                )
            )
            {
                update.Parameters.AddWithValue("tenant", foreignTenant);
                Assert.Equal(0, await update.ExecuteNonQueryAsync());
            }
            await using (
                var ownUpdate = new NpgsqlCommand(
                    "UPDATE business.whatsapp_journey_contacts SET last_inbound_at = now() WHERE tenant_id = @tenant",
                    connection,
                    transaction
                )
            )
            {
                ownUpdate.Parameters.AddWithValue("tenant", tenant);
                Assert.Equal(1, await ownUpdate.ExecuteNonQueryAsync());
            }
            await using (
                var retarget = new NpgsqlCommand(
                    "UPDATE business.whatsapp_journey_contacts SET tenant_id = @tenant",
                    connection,
                    transaction
                )
            )
            {
                retarget.Parameters.AddWithValue("tenant", foreignTenant);
                var denied = await Assert.ThrowsAsync<PostgresException>(() =>
                    retarget.ExecuteNonQueryAsync()
                );
                Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
            }
            await transaction.RollbackAsync();
        }
        await using var security = new NpgsqlCommand(
            """
            SELECT relrowsecurity AND relforcerowsecurity
            FROM pg_class WHERE oid = 'business.whatsapp_journey_contacts'::regclass
            """,
            connection
        );
        Assert.Equal(true, await security.ExecuteScalarAsync());
    }

    private static async Task SeedAttachmentIdentityAsync(
        string ownerConnection,
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership,
        Guid guestTenant,
        Guid linkId,
        Guid concurrentLinkId,
        string senderDigest
    )
    {
        await using var connection = new NpgsqlConnection(ownerConnection);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            """
            BEGIN;
            INSERT INTO business.organisations(id, tenant_id, name, identity_managed, identity_status)
                VALUES (@tenant, @tenant, 'Synthetic attachment owner', true, 'ACTIVE'),
                    (@guest, @guest, 'Synthetic guest scope', false, 'LEGACY_UNVERIFIED');
            INSERT INTO identity.registrations(registration_id, actor_issuer, actor_subject,
                authentication_path, email_verified, mobile_verified, mobile_hmac_key,
                mobile_hmac_version, mobile_hmac_domain, masked_mobile,
                display_name, business_name, business_domain, language_preference)
                VALUES (@registration, @issuer, @subject, 'Google', true, true, @mobile_key,
                    'v1', 'mobile', '+1******0000', 'Synthetic owner', 'Synthetic business', 'retail', 'en');
            INSERT INTO identity.accounts(account_id, initial_tenant_id, origin_registration_id, status)
                VALUES (@account, @tenant, @registration, 'ACTIVE');
            INSERT INTO identity.login_methods(login_method_id, provider_issuer, broker_alias,
                provider_subject, account_id, status)
                VALUES (@login, 'https://synthetic.invalid/provider', 'google', @subject, @account, 'ACTIVE');
            INSERT INTO identity.actor_bindings(actor_binding_id, actor_issuer, actor_subject,
                login_method_id, account_id, status, proof_source, verified_at, auth_time,
                trust_config_digest, correlation_id)
                VALUES (@binding, @issuer, @subject, @login, @account, 'ACTIVE',
                    'KEYCLOAK_FEDERATED_IDENTITY', now(), now(), repeat('a',64), gen_random_uuid());
            INSERT INTO identity.memberships(membership_id, account_id, tenant_id, roles, status)
                VALUES (@membership, @account, @tenant, ARRAY['OWNER']::text[], 'ACTIVE');
            UPDATE identity.registrations SET state = 'Completed', account_id = @account,
                actor_binding_id = @binding, origin_registration_id = @registration,
                completed_at = now(), completion_outcome = 'ACCOUNT_CREATED',
                completion_profile_snapshot = jsonb_build_object(
                    'displayName', display_name, 'businessName', business_name,
                    'businessDomain', business_domain, 'languagePreference', language_preference,
                    'emailVerified', true, 'mobileVerified', true),
                completion_status_code = 200, completion_response_body = '{}'
                WHERE registration_id = @registration;
            INSERT INTO identity.registration_events(registration_id, actor_issuer, actor_subject,
                event_type, from_state, to_state)
                VALUES (@registration, @issuer, @subject, 'RegistrationCompleted', 'ReadyToComplete', 'Completed');
            INSERT INTO identity.idempotency_ledger(registration_id, actor_issuer, actor_subject,
                idempotency_key, operation_family, canonical_hash, status_code, response_body)
                VALUES (@registration, @issuer, @subject, gen_random_uuid()::text,
                    'CompleteRegistration', repeat('b',64), 200, '{}');
            INSERT INTO identity.verification_challenges(challenge_id, registration_id, actor_subject,
                purpose, state, code_hmac, code_hmac_version, destination_hmac_key,
                destination_hmac_version, destination_hmac_domain, delivery_state,
                verified_at, masked_destination, created_at, resend_after)
                VALUES (@proof, @registration, @subject, 'Mobile', 'Consumed', repeat('a',32), 'v1',
                    @mobile_key, 'v1', 'mobile', 'SUBMITTED', now() - interval '1 hour',
                    '+1******0000', now() - interval '1 hour', now() - interval '59 minutes');
            INSERT INTO identity.account_links(link_id, actor_subject, tenant_id, state,
                masked_mobile, verified_mobile_proof_id, start_evidence_id, approval_evidence_id,
                confirmation_evidence_id, confirmation_message_digest, confirmed_phone_subject_hash, confirmed_at)
                VALUES (@link, @subject, @tenant, 'Linked', '+1******0000', @proof,
                    gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), repeat('b',64), @sender, now()),
                    (@concurrent_link, @subject, @tenant, 'Linked', '+1******0000', @proof,
                    gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), repeat('d',64), repeat('e',64), now());
            COMMIT;
            """,
            connection
        );
        command.Parameters.AddWithValue("tenant", membership.TenantId);
        command.Parameters.AddWithValue("guest", guestTenant);
        command.Parameters.AddWithValue("account", membership.AccountId);
        command.Parameters.AddWithValue("membership", membership.MembershipId);
        command.Parameters.AddWithValue("registration", Guid.NewGuid());
        command.Parameters.AddWithValue("issuer", actor.Issuer);
        command.Parameters.AddWithValue("subject", actor.Subject);
        command.Parameters.AddWithValue("login", Guid.NewGuid());
        command.Parameters.AddWithValue("binding", Guid.NewGuid());
        command.Parameters.AddWithValue("proof", Guid.NewGuid());
        command.Parameters.AddWithValue("link", linkId);
        command.Parameters.AddWithValue("concurrent_link", concurrentLinkId);
        command.Parameters.AddWithValue("sender", senderDigest);
        command.Parameters.AddWithValue("mobile_key", Guid.Parse(actor.Subject).ToString("N"));
        await command.ExecuteNonQueryAsync();
    }

    private sealed class IdentityFactory(string connection) : IDbContextFactory<IdentityDbContext>
    {
        public IdentityDbContext CreateDbContext() =>
            new(new DbContextOptionsBuilder<IdentityDbContext>().UseNpgsql(connection).Options);
    }

    private sealed class AttachmentClock : TimeProvider
    {
        public DateTimeOffset Now { get; set; }

        public override DateTimeOffset GetUtcNow() => Now;
    }

    private sealed class ExpireProofAfterBindingSave(AttachmentClock clock, bool enabled)
        : SaveChangesInterceptor
    {
        public override ValueTask<int> SavedChangesAsync(
            SaveChangesCompletedEventData eventData,
            int result,
            CancellationToken cancellationToken = default
        )
        {
            if (
                enabled
                && eventData
                    .Context!.ChangeTracker.Entries<Waooaw.BusinessPlatform.Infrastructure.ChannelBinding>()
                    .Any(entry => entry.State == EntityState.Unchanged)
            )
                clock.Now = clock.Now.AddMinutes(6);
            return ValueTask.FromResult(result);
        }
    }

    private sealed class RelationshipFactory(
        DbContextOptions<EmploymentRelationshipDbContext> options
    ) : IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public EmploymentRelationshipDbContext CreateDbContext() => new(options);
    }

    private sealed class ConversationFactory(DbContextOptions<ConversationStoreDbContext> options)
        : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() => new(options);
    }

    private sealed class MutatingGateway(Func<Task> mutate) : IRelationshipConstitutionalGateway
    {
        public async Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid relationshipId,
            string professionalType,
            string actionType,
            Guid correlationId,
            object actionParameters,
            CancellationToken cancellationToken
        )
        {
            await mutate();
            return Guid.NewGuid();
        }
    }

    private sealed class Evidence : IWhatsAppRegistrationEvidenceGateway
    {
        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken ct
        ) => Task.CompletedTask;
    }

    private sealed class Gate(Guid tenantId) : IWhatsAppCapabilityGate
    {
        private readonly DateTimeOffset _created = DateTimeOffset.UtcNow;

        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) =>
            new()
            {
                TenantId = tenantId,
                StartsAt = _created.AddMinutes(-1),
                ExpiresAt = _created.AddHours(1),
            };

        public void RequireRecipient(
            Guid tenantId,
            string recipientBindingDigest,
            DateTimeOffset now
        ) { }
    }
}
