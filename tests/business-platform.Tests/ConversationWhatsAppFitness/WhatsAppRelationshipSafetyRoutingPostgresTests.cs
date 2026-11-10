using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
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

public sealed class WhatsAppRelationshipSafetyRoutingPostgresTests
{
    [Theory]
    [InlineData("renew")]
    [InlineData("renew-unknown")]
    [InlineData("renew-exhausted")]
    [InlineData("renew-active-dispatch")]
    [InlineData("renew-rollback")]
    [InlineData("active-old")]
    [InlineData("missing-end-evidence")]
    [InlineData("withdrawn")]
    [InlineData("other-relationship")]
    [InlineData("other-actor")]
    [InlineData("other-account")]
    [InlineData("other-tenant")]
    [InlineData("other-conversation")]
    public async Task SameOwnerRenewalRetainsOriginalOutboxRouteAndNeverTransfersHistory(
        string change
    )
    {
        var renews = change.StartsWith("renew", StringComparison.Ordinal);
        var commitsRenewal = renews && change != "renew-rollback";
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var relationshipOptions = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        var conversationOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var db = new EmploymentRelationshipDbContext(relationshipOptions))
            await db.Database.EnsureCreatedAsync();
        await using (var db = new ConversationStoreDbContext(conversationOptions))
            await db.Database.ExecuteSqlRawAsync(db.Database.GenerateCreateScript());
        var password = Guid.NewGuid().ToString("N");
        await using var admin = new NpgsqlConnection(postgres.GetConnectionString());
        await admin.OpenAsync();
        await using (
            var roles = new NpgsqlCommand(
                $"""
                CREATE ROLE bp_owner NOLOGIN NOBYPASSRLS;
                CREATE ROLE business_app LOGIN NOBYPASSRLS PASSWORD '{password}';
                GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
                GRANT USAGE ON SCHEMA business TO business_app;
                GRANT SELECT ON ALL TABLES IN SCHEMA business TO bp_owner;
                GRANT UPDATE (status) ON business.channel_bindings TO bp_owner;
                GRANT SELECT, INSERT, UPDATE ON business.channel_bindings,
                    business.whatsapp_journey_contacts, business.conversation_outbox TO business_app;
                GRANT SELECT ON business.conversation_delivery_observations TO business_app;
                """,
                admin
            )
        )
            await roles.ExecuteNonQueryAsync();
        foreach (
            var table in new[]
            {
                "channel_bindings",
                "whatsapp_journey_contacts",
                "conversation_outbox",
                "conversation_delivery_observations",
            }
        )
        {
            await using var policy = new NpgsqlCommand(
                $"""
                ALTER TABLE business.{table} ENABLE ROW LEVEL SECURITY;
                ALTER TABLE business.{table} FORCE ROW LEVEL SECURITY;
                CREATE POLICY renewal_scope ON business.{table}
                    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID)
                    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);
                """,
                admin
            );
            await policy.ExecuteNonQueryAsync();
        }
        foreach (
            var path in new[]
            {
                "infrastructure/postgres/init/91-wc134-whatsapp-relationship-route-directory.sql",
                "infrastructure/postgres/init/92-wc134-whatsapp-outbox-work-directory.sql",
                "infrastructure/postgres/init/93-wc134-whatsapp-route-renewal.sql",
            }
        )
        {
            var sql = await File.ReadAllTextAsync(RepositoryPaths.Resolve(path));
            for (var replay = 0; replay < 3; replay++)
            {
                await using var migration = new NpgsqlCommand(sql, admin);
                await migration.ExecuteNonQueryAsync();
            }
        }
        var now = DateTimeOffset.UtcNow;
        var tenant = Guid.NewGuid();
        var service = Guid.NewGuid();
        var actor = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var conversation = Guid.NewGuid();
        var sender = new string('a', 64);
        var old = new Waooaw.BusinessPlatform.Infrastructure.ChannelBinding
        {
            TenantId = tenant,
            RelationshipId = relationship,
            ParticipantId = actor,
            ParticipantRole = "EMPLOYER",
            Channel = "WHATSAPP",
            ExternalSubjectHash = sender,
            ConversationId = conversation.ToString("D"),
            Status = "ACTIVE",
            BoundEvidenceId = Guid.NewGuid(),
            BoundAt = now.AddHours(-2),
            AssuranceLevel = "TIER_4_PORTAL_FRESH",
        };
        var route = new WhatsAppRelationshipRoute
        {
            ServiceTenantId = service,
            TenantId = tenant,
            SenderHash = sender,
            BindingId = old.BindingId,
            ActorId = actor,
            ActorIssuer = "https://identity.test",
            IdentityLinkId = Guid.NewGuid(),
            AccountId = Guid.NewGuid(),
            MembershipId = Guid.NewGuid(),
            BoundEvidenceId = old.BoundEvidenceId!.Value,
            PublishedAt = now.AddHours(-1),
        };
        var target = new Waooaw.BusinessPlatform.Infrastructure.ChannelBinding
        {
            TenantId = change == "other-tenant" ? Guid.NewGuid() : tenant,
            RelationshipId = change is "other-relationship" or "other-tenant"
                ? Guid.NewGuid()
                : relationship,
            ParticipantId = change == "other-actor" ? Guid.NewGuid() : actor,
            ParticipantRole = "EMPLOYER",
            Channel = "WHATSAPP",
            ExternalSubjectHash = sender,
            ConversationId =
                change == "other-conversation"
                    ? Guid.NewGuid().ToString("D")
                    : conversation.ToString("D"),
            Status = "ACTIVE",
            BoundEvidenceId = Guid.NewGuid(),
            BoundAt = now.AddSeconds(-1),
            AssuranceLevel = "TIER_4_PORTAL_FRESH",
        };
        var outbox = new ConversationOutboxRecord
        {
            TenantId = tenant,
            Environment = "demo",
            RelationshipId = relationship,
            ConversationId = conversation,
            Sequence = 1,
            AggregateId = Guid.NewGuid().ToString("D"),
            IdempotencyKey = Guid.NewGuid(),
            RecipientBindingDigest = sender,
            PayloadDigest = new string('b', 64),
            Purpose = "CUSTOMER_REQUEST",
            NextAttemptAt = now.AddMinutes(-1),
        };
        await using (var db = new EmploymentRelationshipDbContext(relationshipOptions))
        {
            db.Add(
                new EmploymentRelationship
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    State = EmploymentRelationshipState.Active,
                }
            );
            if (target.TenantId != tenant || target.RelationshipId != relationship)
                db.Add(
                    new EmploymentRelationship
                    {
                        TenantId = target.TenantId,
                        RelationshipId = target.RelationshipId,
                        InitiatingParticipantId = Guid.NewGuid(),
                        State = EmploymentRelationshipState.Active,
                    }
                );
            db.Add(old);
            db.Add(route);
            db.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = tenant,
                    PhoneHmac = sender,
                    OptedInAt = now.AddDays(-1),
                    OptedOutAt = change == "withdrawn" ? now.AddMinutes(-1) : null,
                }
            );
            await db.SaveChangesAsync();
        }
        await using (var db = new ConversationStoreDbContext(conversationOptions))
        {
            await using var transaction = await db.Database.BeginTransactionAsync();
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT set_config('app.current_tenant_id', {tenant.ToString("D")}, true)"
            );
            db.Add(outbox);
            await db.SaveChangesAsync();
            await transaction.CommitAsync();
        }
        await using (var db = new EmploymentRelationshipDbContext(relationshipOptions))
        {
            var prior = await db.ChannelBindings.SingleAsync();
            prior.Status = change == "active-old" ? "ACTIVE" : "ENDED";
            prior.RevokedAt = change == "active-old" ? null : now.AddMinutes(-1);
            prior.RevokedEvidenceId = change == "missing-end-evidence" ? null : Guid.NewGuid();
            db.Add(target);
            await db.SaveChangesAsync();
        }
        var gate = new Gate(
            new WhatsAppActivationAuthority
            {
                TenantId = service,
                Environment = "demo",
                RecipientBindingDigest = sender,
                ActivationReference = "renewal",
            }
        );
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var app = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = password,
        };
        var interceptor = new TenantDbConnectionInterceptor(
            new HttpContextAccessor(),
            NullLogger<TenantDbConnectionInterceptor>.Instance,
            scope
        );
        var factory = new Factory(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(app.ConnectionString)
                .AddInterceptors(interceptor)
                .Options,
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseNpgsql(app.ConnectionString)
                .AddInterceptors(interceptor)
                .Options
        );
        var proof = new PortalPhoneAttachProof(
            target.ParticipantId,
            "TIER_4_PORTAL_FRESH",
            now,
            Guid.NewGuid(),
            new VerifiedCustomerActor(route.ActorIssuer, target.ParticipantId.ToString("D")),
            new CustomerWorkspaceMembership(
                AccountId: change == "other-account" ? Guid.NewGuid() : route.AccountId,
                TenantId: tenant,
                MembershipId: route.MembershipId,
                Roles: ["OWNER"]
            )
        );
        using (scope.Begin())
        {
            using (scope.BeginRelationshipValidation(route))
            {
                await using var db = (
                    (IDbContextFactory<EmploymentRelationshipDbContext>)factory
                ).CreateDbContext();
                await using var transaction = await db.Database.BeginTransactionAsync();
                Task<WhatsAppRelationshipRoute> Renew() =>
                    WhatsAppRelationshipRoutePublication.PublishAsync(
                        db,
                        service,
                        target,
                        route.IdentityLinkId,
                        proof,
                        DateTimeOffset.UtcNow,
                        CancellationToken.None
                    );
                if (renews)
                {
                    Assert.Equal(target.BindingId, (await Renew()).BindingId);
                    Assert.Equal(target.BindingId, (await Renew()).BindingId);
                    if (commitsRenewal)
                        await transaction.CommitAsync();
                    else
                        await transaction.RollbackAsync();
                }
                else
                {
                    await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(Renew);
                    await transaction.RollbackAsync();
                }
            }
            await using var lookup = (
                (IDbContextFactory<EmploymentRelationshipDbContext>)factory
            ).CreateDbContext();
            var delivery = await WhatsAppRelationshipRouteAuthority.FindDeliveryAsync(
                lookup,
                service,
                sender,
                "demo",
                outbox.OutboxId,
                CancellationToken.None
            );
            Assert.Equal(old.BindingId, delivery!.BindingId);
            var current = await WhatsAppRelationshipRouteAuthority.FindAsync(
                lookup,
                service,
                sender,
                CancellationToken.None
            );
            Assert.Equal(commitsRenewal ? target.BindingId : old.BindingId, current!.BindingId);
            Assert.Null(
                await WhatsAppRelationshipRouteAuthority.FindDeliveryAsync(
                    lookup,
                    service,
                    new string('b', 64),
                    "demo",
                    outbox.OutboxId,
                    CancellationToken.None
                )
            );
            Assert.Null(
                await WhatsAppRelationshipRouteAuthority.FindDeliveryAsync(
                    lookup,
                    service,
                    sender,
                    "other",
                    outbox.OutboxId,
                    CancellationToken.None
                )
            );
            var historyDenied = await Assert.ThrowsAsync<PostgresException>(() =>
                lookup.Database.ExecuteSqlRawAsync(
                    "SELECT binding_id FROM business.whatsapp_relationship_route_history"
                )
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, historyDenied.SqlState);
            using (scope.BeginRelationshipValidation(current))
            {
                var scopeDenied = await Assert.ThrowsAsync<PostgresException>(() =>
                    WhatsAppRelationshipRouteAuthority.FindDeliveryAsync(
                        lookup,
                        service,
                        sender,
                        "demo",
                        outbox.OutboxId,
                        CancellationToken.None
                    )
                );
                Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, scopeDenied.SqlState);
            }
            if (commitsRenewal)
            {
                if (change != "renew")
                {
                    await using var update = new ConversationStoreDbContext(conversationOptions);
                    var attempted = await update.ConversationOutbox.SingleAsync();
                    attempted.State = change switch
                    {
                        "renew-unknown" => "UNRESOLVED",
                        "renew-exhausted" => "LEASED",
                        _ => "DISPATCHING",
                    };
                    attempted.AttemptNumber = change == "renew-exhausted" ? 12 : 1;
                    attempted.LeaseExpiresAt =
                        change == "renew-active-dispatch" ? now.AddMinutes(5) : now.AddMinutes(-1);
                    await update.SaveChangesAsync();
                }
                var historical = new WhatsAppDeliveryObservationRouting(
                    factory,
                    factory,
                    scope,
                    gate,
                    TimeProvider.System
                );
                var callback = new WhatsAppProviderStatusEvent(
                    "original-callback",
                    "original-provider-message",
                    "READ",
                    now,
                    new string('c', 64)
                )
                {
                    OutboxId = outbox.OutboxId,
                    SenderBindingDigest = sender,
                };
                Assert.True(
                    await historical.RecordDeliveryObservationAsync(
                        callback,
                        async (db, ct) =>
                        {
                            Assert.Equal(tenant, scope.CurrentTenantId);
                            Assert.Equal(
                                outbox.OutboxId,
                                (await db.ConversationOutbox.SingleAsync(ct)).OutboxId
                            );
                            return true;
                        },
                        CancellationToken.None
                    )
                );
                Assert.True(
                    await historical.ReconcileHistoricalWorkAsync(
                        new(outbox.OutboxId, sender),
                        CancellationToken.None
                    )
                );
                Assert.True(
                    await historical.ReconcileHistoricalWorkAsync(
                        new(outbox.OutboxId, sender),
                        CancellationToken.None
                    )
                );
                Assert.Equal(service, scope.CurrentTenantId);
                Assert.Null(scope.DatabaseTenantOverrideId);
                var fresh = new ConversationOutboxRecord
                {
                    TenantId = tenant,
                    Environment = "demo",
                    RelationshipId = relationship,
                    ConversationId = conversation,
                    Sequence = 2,
                    AggregateId = Guid.NewGuid().ToString("D"),
                    IdempotencyKey = Guid.NewGuid(),
                    RecipientBindingDigest = sender,
                    PayloadDigest = new string('d', 64),
                    Purpose = "CUSTOMER_REQUEST",
                    NextAttemptAt = now.AddMinutes(-1),
                };
                using (scope.BeginRelationshipValidation(current))
                {
                    await using var db = (
                        (IDbContextFactory<ConversationStoreDbContext>)factory
                    ).CreateDbContext();
                    await using var transaction = await db.Database.BeginTransactionAsync();
                    db.Add(fresh);
                    await db.SaveChangesAsync();
                    await transaction.CommitAsync();
                }
                var freshRoute = await WhatsAppRelationshipRouteAuthority.FindDeliveryAsync(
                    lookup,
                    service,
                    sender,
                    "demo",
                    fresh.OutboxId,
                    CancellationToken.None
                );
                Assert.Equal(target.BindingId, freshRoute!.BindingId);
                using (scope.BeginRelationshipValidation(current))
                {
                    await using var db = (
                        (IDbContextFactory<ConversationStoreDbContext>)factory
                    ).CreateDbContext();
                    Assert.False(
                        await db
                            .Database.SqlQuery<bool>(
                                $"""
                                SELECT business.matches_whatsapp_outbox_route(
                                    {service}, {tenant}, {sender}, {"demo"}, {outbox.OutboxId}, {target.BindingId}) AS "Value"
                                """
                            )
                            .SingleAsync()
                    );
                    Assert.True(
                        await db
                            .Database.SqlQuery<bool>(
                                $"""
                                SELECT business.matches_whatsapp_outbox_route(
                                    {service}, {tenant}, {sender}, {"demo"}, {fresh.OutboxId}, {target.BindingId}) AS "Value"
                                """
                            )
                            .SingleAsync()
                    );
                }
            }
        }
        await using var count = new NpgsqlCommand(
            "SELECT count(*) FROM business.whatsapp_relationship_route_history",
            admin
        );
        Assert.Equal(commitsRenewal ? 1L : 0L, await count.ExecuteScalarAsync());
        await using var verify = new ConversationStoreDbContext(conversationOptions);
        var saved = await verify.ConversationOutbox.SingleAsync(value =>
            value.OutboxId == outbox.OutboxId
        );
        Assert.Equal(
            change switch
            {
                "renew" => "BLOCKED",
                "renew-unknown" => "UNRESOLVED",
                "renew-exhausted" => "LEASED",
                "renew-active-dispatch" => "DISPATCHING",
                _ => "PENDING",
            },
            saved.State
        );
        Assert.Equal(
            change switch
            {
                "renew-exhausted" => 12,
                "renew-unknown" or "renew-active-dispatch" => 1,
                _ => 0,
            },
            saved.AttemptNumber
        );
        Assert.Empty(verify.DeliveryObservations);
    }

    [Theory]
    [InlineData("stop")]
    [InlineData("revoked-participant-stop")]
    [InlineData("revoked-binding-stop")]
    [InlineData("wrong-evidence-stop")]
    [InlineData("emergency")]
    [InlineData("pending-emergency")]
    [InlineData("revoked-participant-emergency")]
    [InlineData("revoked-binding-emergency")]
    [InlineData("no-route-stop")]
    [InlineData("no-route-emergency")]
    public async Task SafetyControlsUseExactForcedRlsOwnersWithoutConsentOrIdentity(string change)
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var relationshipOptions = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        var conversationOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var db = new EmploymentRelationshipDbContext(relationshipOptions))
            await db.Database.EnsureCreatedAsync();
        await using (var db = new ConversationStoreDbContext(conversationOptions))
            await db.Database.ExecuteSqlRawAsync(db.Database.GenerateCreateScript());
        var password = Guid.NewGuid().ToString("N");
        await using var admin = new NpgsqlConnection(postgres.GetConnectionString());
        await admin.OpenAsync();
        await using (
            var setup = new NpgsqlCommand(
                $"""
                CREATE ROLE bp_owner NOLOGIN NOBYPASSRLS;
                CREATE ROLE business_app LOGIN NOBYPASSRLS PASSWORD '{password}';
                GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
                GRANT USAGE ON SCHEMA business TO business_app;
                """,
                admin
            )
        )
            await setup.ExecuteNonQueryAsync();
        foreach (
            var table in new[]
            {
                "employment_relationships",
                "relationship_participants",
                "whatsapp_journey_contacts",
                "channel_bindings",
                "relationship_state_history",
                "whatsapp_guest_sessions",
                "relationship_emergency_stop_latches",
                "conversation_executions",
                "conversation_idempotency_outcomes",
            }
        )
        {
            await using var policy = new NpgsqlCommand(
                $"""
                GRANT SELECT, INSERT, UPDATE ON business.{table} TO business_app;
                ALTER TABLE business.{table} ENABLE ROW LEVEL SECURITY;
                ALTER TABLE business.{table} FORCE ROW LEVEL SECURITY;
                CREATE POLICY safety_tenant ON business.{table} TO business_app
                    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
                    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
                """,
                admin
            );
            await policy.ExecuteNonQueryAsync();
        }
        var directorySql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/91-wc134-whatsapp-relationship-route-directory.sql"
            )
        );
        await using (var migration = new NpgsqlCommand(directorySql, admin))
            await migration.ExecuteNonQueryAsync();
        var now = DateTimeOffset.UtcNow;
        var authority = new WhatsAppActivationAuthority
        {
            TenantId = Guid.NewGuid(),
            Environment = "demo",
            RecipientBindingDigest = new string('a', 64),
            ActivationReference = "safety-fixture",
        };
        var relationship = new EmploymentRelationship
        {
            TenantId = Guid.NewGuid(),
            State = EmploymentRelationshipState.Active,
        };
        var participant = new RelationshipParticipant
        {
            TenantId = relationship.TenantId,
            RelationshipId = relationship.RelationshipId,
            ParticipantId = Guid.NewGuid(),
            Role = RelationshipParticipantRole.Employer,
            BoundEvidenceId = Guid.NewGuid(),
            BoundAt = now.AddMinutes(-10),
            Status = change.StartsWith("revoked-participant", StringComparison.Ordinal)
                ? "REVOKED"
                : "ACTIVE",
            RevokedAt = change.StartsWith("revoked-participant", StringComparison.Ordinal)
                ? now
                : null,
        };
        var channelEvidence = Guid.NewGuid();
        var binding = new Waooaw.BusinessPlatform.Infrastructure.ChannelBinding
        {
            TenantId = relationship.TenantId,
            RelationshipId = relationship.RelationshipId,
            ParticipantId = participant.ParticipantId,
            ParticipantRole = "EMPLOYER",
            Channel = "WHATSAPP",
            ExternalSubjectHash = authority.RecipientBindingDigest,
            ConversationId = Guid.NewGuid().ToString("D"),
            BoundEvidenceId = channelEvidence,
            BoundAt = now.AddMinutes(-10),
            Status = change.StartsWith("revoked-binding", StringComparison.Ordinal)
                ? "REVOKED"
                : "ACTIVE",
            RevokedAt = change.StartsWith("revoked-binding", StringComparison.Ordinal) ? now : null,
        };
        var route = new WhatsAppRelationshipRoute
        {
            ServiceTenantId = authority.TenantId,
            TenantId = relationship.TenantId,
            SenderHash = authority.RecipientBindingDigest,
            BindingId = binding.BindingId,
            ActorId = participant.ParticipantId,
            ActorIssuer = "fixture-no-identity",
            IdentityLinkId = Guid.NewGuid(),
            AccountId = Guid.NewGuid(),
            MembershipId = Guid.NewGuid(),
            BoundEvidenceId = change == "wrong-evidence-stop" ? Guid.NewGuid() : channelEvidence,
            PublishedAt = now.AddMinutes(-5),
        };
        var contact = new WhatsAppJourneyContact
        {
            TenantId = relationship.TenantId,
            PhoneHmac = route.SenderHash,
            OptedInAt = now.AddDays(-1),
        };
        var foreign = new WhatsAppJourneyContact
        {
            TenantId = Guid.NewGuid(),
            PhoneHmac = new string('b', 64),
            OptedInAt = now.AddDays(-1),
        };
        await using (var db = new EmploymentRelationshipDbContext(relationshipOptions))
        {
            db.AddRange(relationship, participant, binding, contact, foreign);
            if (!change.StartsWith("no-route", StringComparison.Ordinal))
                db.Add(route);
            await db.SaveChangesAsync();
        }
        if (change == "emergency")
        {
            await using var db = new ConversationStoreDbContext(conversationOptions);
            db.Add(
                new WhatsAppGuestSession
                {
                    TenantId = authority.TenantId,
                    BindingDigest = route.SenderHash,
                    FirstObservedAt = now.AddDays(-1),
                    LastInboundAt = now.AddDays(-1),
                    StoppedAt = now.AddHours(-1),
                }
            );
            await db.SaveChangesAsync();
        }
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var runtime = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = password,
        };
        var interceptor = new TenantDbConnectionInterceptor(
            new HttpContextAccessor(),
            NullLogger<TenantDbConnectionInterceptor>.Instance,
            scope
        );
        var factory = new Factory(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(runtime.ConnectionString)
                .AddInterceptors(interceptor)
                .Options,
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseNpgsql(runtime.ConnectionString)
                .AddInterceptors(interceptor)
                .Options
        );
        var identityFactory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var routing = new WhatsAppRelationshipRouting(
            factory,
            factory,
            IdentityTestHelpers.CreateService(identityFactory),
            scope,
            gate,
            new ConfigurationBuilder()
                .AddInMemoryCollection(
                    new Dictionary<string, string?>
                    {
                        ["IdentityBrokerRead:ActorIssuer"] = route.ActorIssuer,
                    }
                )
                .Build(),
            TimeProvider.System
        );
        var gateway = new Gateway(scope, relationship.TenantId, change == "pending-emergency");
        var emergencyStops = new RelationshipEmergencyStopService(
            factory,
            new EmploymentRelationshipService(
                factory,
                new RecordingRelationshipConstitutionalGateway(),
                NullLogger<EmploymentRelationshipService>.Instance
            ),
            gateway,
            Options.Create(new Wc120ConversationOptions { Environment = "demo" }),
            NullLogger<RelationshipEmergencyStopService>.Instance
        );
        var stop = change.EndsWith("stop", StringComparison.Ordinal);
        var proof = new VerifiedPhoneIdentityProof(
            "safety-message",
            route.SenderHash,
            stop ? "STOP" : "EMERGENCY STOP",
            null,
            "whatsapp-provider-callback",
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        )
        {
            Environment = "demo",
        };
        using (scope.Begin())
        {
            Task<WhatsAppJourneyReceipt> Receive() =>
                routing.ReceiveSignedSafetyControlAsync(
                    proof,
                    emergencyStops,
                    CancellationToken.None
                );
            if (
                change
                is "wrong-evidence-stop"
                    or "revoked-participant-emergency"
                    or "revoked-binding-emergency"
            )
                await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(Receive);
            else if (change == "pending-emergency")
                await Assert.ThrowsAsync<EmergencyStopReconciliationPendingException>(Receive);
            else if (change == "no-route-emergency")
                await Assert.ThrowsAsync<WhatsAppWebhookException>(Receive);
            else
            {
                var receipt = await Receive();
                Assert.Equal(stop ? "STOPPED" : "ACCEPTED", receipt.Status);
                Assert.Equal(string.Empty, receipt.InternalTenantToken);
                if (stop)
                    Assert.Equal(string.Empty, receipt.Reply);
                await Receive(); // Replays neither renew opt-in nor create another Stop transition.
            }
            Assert.Equal(authority.TenantId, scope.CurrentTenantId);
            Assert.Null(scope.DatabaseTenantOverrideId);
            Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                scope.RequireConfirmedRelationshipRoute()
            );
            if (change == "stop")
            {
                using var customer = scope.BeginRelationshipValidation(route);
                var expected = new WhatsAppCurrentRelationshipRoute(
                    authority.TenantId,
                    authority.Environment,
                    route.SenderHash,
                    route.TenantId,
                    binding.BindingId,
                    binding.RelationshipId,
                    participant.ParticipantId,
                    binding.ParticipantRole,
                    Guid.Parse(binding.ConversationId),
                    0
                );
                scope.ConfirmRelationshipRoute(expected);
                await using var commitDb = (
                    (IDbContextFactory<ConversationStoreDbContext>)factory
                ).CreateDbContext();
                await using var transaction = await commitDb.Database.BeginTransactionAsync();
                await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
                    WhatsAppRelationshipRouting.RequireIngressCommitAsync(
                        scope,
                        routing,
                        commitDb,
                        route.TenantId,
                        participant.ParticipantId,
                        binding.RelationshipId,
                        expected.ConversationId,
                        "WHATSAPP",
                        binding.BindingId,
                        route.SenderHash,
                        CancellationToken.None
                    )
                );
                Assert.Null(scope.DatabaseTenantOverrideId);
                var selected = await commitDb
                    .Database.SqlQuery<string>(
                        $"""SELECT current_setting('app.current_tenant_id') AS "Value" """
                    )
                    .SingleAsync();
                Assert.Equal(route.TenantId.ToString("D"), selected);
                var senderLock = WhatsAppGuestSession.LockKey(authority.TenantId, route.SenderHash);
                await using var tryLock = new NpgsqlCommand(
                    "SELECT pg_try_advisory_xact_lock(hashtextextended(@sender, 0))",
                    admin
                );
                tryLock.Parameters.AddWithValue("sender", senderLock);
                Assert.Equal(false, await tryLock.ExecuteScalarAsync());
                await transaction.RollbackAsync();
                Assert.Equal(true, await tryLock.ExecuteScalarAsync());
                for (var replay = 0; replay < 2; replay++)
                {
                    await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
                        WhatsAppRelationshipRouting.BeginIngressReadAsync(
                            scope,
                            routing,
                            commitDb,
                            authority.Environment,
                            route.TenantId,
                            participant.ParticipantId,
                            binding.RelationshipId,
                            CancellationToken.None
                        )
                    );
                    Assert.Null(commitDb.Database.CurrentTransaction);
                    Assert.Null(scope.DatabaseTenantOverrideId);
                    Assert.Equal(route.TenantId, scope.CurrentTenantId);
                    Assert.Equal(true, await tryLock.ExecuteScalarAsync());
                }
            }
        }
        await using (var db = new ConversationStoreDbContext(conversationOptions))
        {
            var guest = await db.Set<WhatsAppGuestSession>().SingleOrDefaultAsync();
            Assert.Equal(stop || change == "emergency", guest?.StoppedAt is not null);
            if (guest is not null)
            {
                Assert.Null(guest.EvidenceId);
                Assert.Null(guest.ServiceConsentEvidenceId);
            }
            Assert.Empty(db.ConversationOutbox);
            Assert.Empty(db.Messages);
            Assert.Equal(
                change is "emergency" or "pending-emergency" ? 1 : 0,
                await db.EmergencyStopLatches.CountAsync()
            );
        }
        await using (var db = new EmploymentRelationshipDbContext(relationshipOptions))
        {
            var saved = await db.WhatsAppJourneyContacts.SingleAsync(value =>
                value.ContactId == contact.ContactId
            );
            Assert.Equal(
                stop && change is not ("wrong-evidence-stop" or "no-route-stop"),
                saved.OptedOutAt is not null
            );
            Assert.Null(
                (
                    await db.WhatsAppJourneyContacts.SingleAsync(value =>
                        value.ContactId == foreign.ContactId
                    )
                ).OptedOutAt
            );
            Assert.Equal(
                change == "emergency"
                    ? EmploymentRelationshipState.StoppedEmergency
                    : EmploymentRelationshipState.Active,
                (await db.EmploymentRelationships.SingleAsync()).State
            );
        }
        Assert.Equal(change is "emergency" or "pending-emergency" ? 1 : 0, gateway.Calls);
    }

    private sealed class Factory(
        DbContextOptions<EmploymentRelationshipDbContext> relationships,
        DbContextOptions<ConversationStoreDbContext> conversations
    )
        : IDbContextFactory<EmploymentRelationshipDbContext>,
            IDbContextFactory<ConversationStoreDbContext>
    {
        EmploymentRelationshipDbContext IDbContextFactory<EmploymentRelationshipDbContext>.CreateDbContext() =>
            new(relationships);

        ConversationStoreDbContext IDbContextFactory<ConversationStoreDbContext>.CreateDbContext() =>
            new(conversations);
    }

    private sealed class Gate(WhatsAppActivationAuthority authority) : IWhatsAppCapabilityGate
    {
        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) => authority;

        public void RequireRecipient(Guid tenantId, string sender, DateTimeOffset now)
        {
            if (tenantId != authority.TenantId || sender != authority.RecipientBindingDigest)
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        }
    }

    private sealed class Gateway(WhatsAppTenantExecutionScope scope, Guid tenant, bool pending)
        : IRelationshipEmergencyStopGateway
    {
        public int Calls { get; private set; }

        public Task<RelationshipEmergencyStopDispatch> StopAsync(
            Guid tenantId,
            Guid relationshipId,
            Guid participantId,
            IReadOnlyCollection<Guid> executionIds,
            CancellationToken ct
        )
        {
            Calls++;
            Assert.Equal(tenant, tenantId);
            Assert.Equal(tenant, scope.CurrentTenantId);
            Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                scope.RequireConfirmedRelationshipRoute()
            );
            return pending
                ? Task.FromException<RelationshipEmergencyStopDispatch>(
                    new TimeoutException("Synthetic CE delay.")
                )
                : Task.FromResult(
                    new RelationshipEmergencyStopDispatch(Guid.NewGuid(), DateTimeOffset.UtcNow)
                );
        }
    }
}
