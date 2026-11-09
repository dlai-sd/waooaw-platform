using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppOutboxWorkDirectoryPostgresTests
{
    [Theory]
    [InlineData("DELIVERED")]
    [InlineData("READ")]
    [InlineData("FAILED")]
    [InlineData("UNKNOWN")]
    public async Task OwnerDirectoryPublishesTransactionallyAndOnlyDiscoversActiveServiceScope(
        string receipt
    )
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var adminOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var db = new ConversationStoreDbContext(adminOptions))
            await db.Database.EnsureCreatedAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        var password = Guid.NewGuid().ToString("N");
        await using (
            var setup = new NpgsqlCommand(
                $"""
                CREATE ROLE bp_owner NOLOGIN NOBYPASSRLS;
                CREATE ROLE business_app LOGIN NOBYPASSRLS PASSWORD '{password}';
                GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
                GRANT USAGE ON SCHEMA business TO business_app;
                GRANT SELECT, INSERT, UPDATE ON business.conversation_outbox TO business_app;
                GRANT SELECT ON business.conversation_delivery_observations TO business_app;
                ALTER TABLE business.conversation_delivery_observations ENABLE ROW LEVEL SECURITY;
                ALTER TABLE business.conversation_delivery_observations FORCE ROW LEVEL SECURITY;
                CREATE POLICY delivery_tenant ON business.conversation_delivery_observations
                    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
                ALTER TABLE business.conversation_outbox ENABLE ROW LEVEL SECURITY;
                ALTER TABLE business.conversation_outbox FORCE ROW LEVEL SECURITY;
                CREATE POLICY outbox_tenant ON business.conversation_outbox
                    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
                    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
                CREATE TABLE business.channel_bindings (
                    tenant_id UUID NOT NULL, binding_id UUID NOT NULL, relationship_id UUID NOT NULL,
                    participant_id UUID NOT NULL, channel TEXT NOT NULL, external_subject_hash CHAR(64) NOT NULL,
                    conversation_id TEXT NOT NULL, bound_evidence_id UUID NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    revoked_at TIMESTAMPTZ,
                    PRIMARY KEY (tenant_id, binding_id));
                ALTER TABLE business.channel_bindings OWNER TO bp_owner;
                ALTER TABLE business.channel_bindings ENABLE ROW LEVEL SECURITY;
                ALTER TABLE business.channel_bindings FORCE ROW LEVEL SECURITY;
                CREATE POLICY binding_tenant ON business.channel_bindings
                    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
                GRANT SELECT ON business.channel_bindings TO business_app;
                GRANT UPDATE (status, bound_evidence_id, revoked_at)
                    ON business.channel_bindings TO business_app;
                """,
                owner
            )
        )
            await setup.ExecuteNonQueryAsync();
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
            for (var replay = 0; replay < 2; replay++)
            {
                await using var migration = new NpgsqlCommand(sql, owner);
                await migration.ExecuteNonQueryAsync();
            }
        }
        var service = Guid.NewGuid();
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var conversation = Guid.NewGuid();
        var binding = Guid.NewGuid();
        var actor = Guid.NewGuid();
        var evidence = Guid.NewGuid();
        var sender = new string('a', 64);
        await using (
            var seed = new NpgsqlCommand(
                """
                INSERT INTO business.channel_bindings
                    (tenant_id, binding_id, relationship_id, participant_id, channel,
                     external_subject_hash, conversation_id, bound_evidence_id) VALUES
                    (@tenant, @binding, @relationship, @actor, 'WHATSAPP', @sender, @conversation, @evidence);
                INSERT INTO business.whatsapp_relationship_routes
                    (service_tenant_id, sender_hash, tenant_id, binding_id, identity_link_id, actor_issuer,
                     actor_id, account_id, membership_id, bound_evidence_id, published_at)
                VALUES (@service, @sender, @tenant, @binding, gen_random_uuid(), 'fixture',
                    @actor, gen_random_uuid(), gen_random_uuid(), @evidence, now());
                """,
                owner
            )
        )
        {
            seed.Parameters.AddWithValue("tenant", tenant);
            seed.Parameters.AddWithValue("service", service);
            seed.Parameters.AddWithValue("binding", binding);
            seed.Parameters.AddWithValue("relationship", relationship);
            seed.Parameters.AddWithValue("conversation", conversation.ToString("D"));
            seed.Parameters.AddWithValue("actor", actor);
            seed.Parameters.AddWithValue("sender", sender);
            seed.Parameters.AddWithValue("evidence", evidence);
            await seed.ExecuteNonQueryAsync();
        }
        var connectionString = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = password,
            Options = $"-c app.current_tenant_id={tenant:D}",
        }.ConnectionString;
        var outbox = new ConversationOutboxRecord
        {
            TenantId = tenant,
            Environment = "demo",
            RelationshipId = relationship,
            ConversationId = conversation,
            RecipientBindingDigest = sender,
            Sequence = 1,
            AggregateId = Guid.NewGuid().ToString("D"),
            IdempotencyKey = Guid.NewGuid(),
            PayloadDigest = new string('b', 64),
            Purpose = "CUSTOMER_REQUEST",
            NextAttemptAt = DateTimeOffset.UtcNow.AddMinutes(-1),
        };
        await using (
            var customer = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            )
        )
        {
            await using var transaction = await customer.Database.BeginTransactionAsync();
            customer.Add(outbox);
            await customer.SaveChangesAsync();
            await using (
                var invisible = new NpgsqlCommand(
                    "SELECT count(*) FROM business.whatsapp_outbox_work",
                    owner
                )
            )
                Assert.Equal(0L, await invisible.ExecuteScalarAsync());
            await transaction.CommitAsync();
        }
        await using (
            var indexed = new NpgsqlCommand(
                "SELECT count(*) FROM business.whatsapp_outbox_work",
                owner
            )
        )
            Assert.Equal(1L, await indexed.ExecuteScalarAsync());
        var authority = new WhatsAppActivationAuthority
        {
            TenantId = service,
            Environment = "demo",
            RecipientBindingDigest = sender,
            ActivationReference = "directory-fixture",
        };
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var runtime = new NpgsqlConnectionStringBuilder(connectionString)
        {
            Options = string.Empty,
        };
        var interceptor = new TenantDbConnectionInterceptor(
            new HttpContextAccessor(),
            NullLogger<TenantDbConnectionInterceptor>.Instance,
            scope
        );
        var factory = new Factory(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseNpgsql(runtime.ConnectionString)
                .AddInterceptors(interceptor)
                .Options,
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(runtime.ConnectionString)
                .AddInterceptors(interceptor)
                .Options
        );
        var directory = new WhatsAppOutboxWorkDirectory(
            factory,
            scope,
            gate,
            Options.Create(new Wc120ConversationOptions { Enabled = true, Environment = "demo" }),
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new() { DispatchEnabled = true }),
            TimeProvider.System
        );
        var reconciliation = new WhatsAppDeliveryObservationRouting(
            factory,
            factory,
            scope,
            gate,
            TimeProvider.System
        );
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            directory.ClaimAsync(CancellationToken.None)
        );
        using (scope.Begin())
        {
            using (scope.BeginDatabaseTenantOverride(service))
                await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                    directory.ClaimAsync(CancellationToken.None)
                );
            await using (var empty = factory.CreateDbContext())
                Assert.Empty(await empty.ConversationOutbox.ToListAsync());
            await using (var direct = new NpgsqlConnection(runtime.ConnectionString))
            {
                await direct.OpenAsync();
                await using var forbidden = new NpgsqlCommand(
                    "SELECT * FROM business.whatsapp_outbox_work",
                    direct
                );
                var denied = await Assert.ThrowsAsync<PostgresException>(() =>
                    forbidden.ExecuteNonQueryAsync()
                );
                Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
                await using var foreign = new NpgsqlCommand(
                    "SELECT * FROM business.claim_whatsapp_outbox_work(@service, 'demo')",
                    direct
                );
                foreign.Parameters.AddWithValue("service", service);
                var unscoped = await Assert.ThrowsAsync<PostgresException>(() =>
                    foreign.ExecuteNonQueryAsync()
                );
                Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, unscoped.SqlState);
            }
            await using (var locked = new NpgsqlConnection(postgres.GetConnectionString()))
            {
                await locked.OpenAsync();
                await using var transaction = await locked.BeginTransactionAsync();
                await using var hold = new NpgsqlCommand(
                    "SELECT outbox_id FROM business.whatsapp_outbox_work WHERE outbox_id = @id FOR UPDATE",
                    locked,
                    transaction
                );
                hold.Parameters.AddWithValue("id", outbox.OutboxId);
                Assert.Equal(outbox.OutboxId, await hold.ExecuteScalarAsync());
                Assert.Null(await directory.ClaimAsync(CancellationToken.None));
                await transaction.RollbackAsync();
            }
            gate.DenyRecipient = true;
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                directory.ClaimAsync(CancellationToken.None)
            );
            gate.DenyRecipient = false;
            var work = await directory.ClaimAsync(CancellationToken.None);
            Assert.NotNull(work);
            Assert.Equal(outbox.OutboxId, work.OutboxId);
            Assert.Equal(sender, work.SenderHash);
            Assert.Null(await directory.ClaimAsync(CancellationToken.None));
            Assert.False(
                await reconciliation.ReconcileHistoricalWorkAsync(work, CancellationToken.None)
            );
            var routeCandidate = new WhatsAppRelationshipRoute
            {
                ServiceTenantId = service,
                TenantId = tenant,
                SenderHash = sender,
                BindingId = binding,
                ActorId = actor,
            };
            using (scope.BeginRelationshipValidation(routeCandidate))
            {
                var confirmed = new WhatsAppCurrentRelationshipRoute(
                    service,
                    "demo",
                    sender,
                    tenant,
                    binding,
                    relationship,
                    actor,
                    "EMPLOYER",
                    conversation,
                    1
                );
                scope.ConfirmRelationshipRoute(confirmed);
                var options = Options.Create(
                    new Wc120ConversationOptions { Enabled = true, Environment = "demo" }
                );
                var leases = new WhatsAppOutboxService(
                    factory,
                    new UnusedRelationships(),
                    options,
                    new StaticOptionsMonitor<WhatsAppJourneyOptions>(
                        new() { DispatchEnabled = true }
                    ),
                    new ConversationStopFence(factory, options),
                    execution: scope
                );
                var lease = await leases.LeaseRelationshipAsync(
                    work.OutboxId,
                    confirmed,
                    "indexed-worker",
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                );
                Assert.NotNull(lease);
                Assert.Equal(work.OutboxId, lease.OutboxId);
                await using var scheduled = new NpgsqlCommand(
                    "SELECT due_at >= @expiry FROM business.whatsapp_outbox_work WHERE outbox_id = @id",
                    owner
                );
                scheduled.Parameters.AddWithValue("expiry", lease.LeaseExpiresAt);
                scheduled.Parameters.AddWithValue("id", lease.OutboxId);
                Assert.Equal(true, await scheduled.ExecuteScalarAsync());
            }
            Assert.Equal(service, scope.CurrentTenantId);
            Assert.Null(await directory.ClaimAsync(CancellationToken.None));
            Assert.False(
                await reconciliation.ReconcileHistoricalWorkAsync(work, CancellationToken.None)
            );
        }
        await using (var customer = new NpgsqlConnection(connectionString))
        {
            await customer.OpenAsync();
            await using var immutable = new NpgsqlCommand(
                "UPDATE business.conversation_outbox SET payload_digest = repeat('c',64) WHERE outbox_id = @id",
                customer
            );
            immutable.Parameters.AddWithValue("id", outbox.OutboxId);
            var denied = await Assert.ThrowsAsync<PostgresException>(() =>
                immutable.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
            await using var terminal = new NpgsqlCommand(
                """
                UPDATE business.conversation_outbox SET state = 'DISPATCHING',
                    next_attempt_at = now() - interval '1 minute',
                    lease_expires_at = now() - interval '1 minute'
                WHERE outbox_id = @id
                """,
                customer
            );
            terminal.Parameters.AddWithValue("id", outbox.OutboxId);
            await terminal.ExecuteNonQueryAsync();
        }
        // No guest or Identity tables exist in this fixture: historical receipts require neither.
        await using (var seedReceipt = new ConversationStoreDbContext(adminOptions))
        {
            seedReceipt.DeliveryObservations.Add(
                new ConversationDeliveryObservation
                {
                    TenantId = tenant,
                    Environment = "demo",
                    RelationshipId = relationship,
                    MessageId = Guid.Parse(outbox.AggregateId),
                    Provider = "WHATSAPP",
                    ProviderEventIdentity = "signed-receipt",
                    ProviderReferenceDigest = new string('b', 64),
                    ObservationDigest = new string('c', 64),
                    DeliveryState = receipt,
                    ObservedAt = DateTimeOffset.UtcNow,
                    RetainUntil = DateTimeOffset.UtcNow.AddYears(7),
                }
            );
            seedReceipt.DeliveryObservations.Add(
                new ConversationDeliveryObservation
                {
                    TenantId = Guid.NewGuid(),
                    Environment = "demo",
                    RelationshipId = relationship,
                    MessageId = Guid.Parse(outbox.AggregateId),
                    Provider = "WHATSAPP",
                    ProviderEventIdentity = "foreign-delivery",
                    ProviderReferenceDigest = new string('b', 64),
                    ObservationDigest = new string('d', 64),
                    DeliveryState = "DELIVERED",
                    ObservedAt = DateTimeOffset.UtcNow,
                    RetainUntil = DateTimeOffset.UtcNow.AddYears(7),
                }
            );
            await seedReceipt.SaveChangesAsync();
        }
        using (scope.Begin())
        {
            gate.DenyRecipient = true;
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                reconciliation.ReconcileHistoricalWorkAsync(
                    new(outbox.OutboxId, sender),
                    CancellationToken.None
                )
            );
            gate.DenyRecipient = false;
            await using (var lockConnection = new NpgsqlConnection(postgres.GetConnectionString()))
            {
                await lockConnection.OpenAsync();
                await using var transaction = await lockConnection.BeginTransactionAsync();
                await using var hold = new NpgsqlCommand(
                    "SELECT outbox_id FROM business.conversation_outbox WHERE outbox_id = @id FOR UPDATE",
                    lockConnection,
                    transaction
                );
                hold.Parameters.AddWithValue("id", outbox.OutboxId);
                Assert.Equal(outbox.OutboxId, await hold.ExecuteScalarAsync());
                Assert.True(
                    await reconciliation.ReconcileHistoricalWorkAsync(
                        new(outbox.OutboxId, sender),
                        CancellationToken.None
                    )
                );
                await transaction.RollbackAsync();
            }
            Assert.True(
                await reconciliation.ReconcileHistoricalWorkAsync(
                    new(outbox.OutboxId, sender),
                    CancellationToken.None
                )
            );
            Assert.True(
                await reconciliation.ReconcileHistoricalWorkAsync(
                    new(outbox.OutboxId, sender),
                    CancellationToken.None
                )
            );
            Assert.Equal(service, scope.CurrentTenantId);
            Assert.Null(scope.DatabaseTenantOverrideId);
            Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                scope.RequireConfirmedRelationshipRoute()
            );
        }
        await using (var persisted = new ConversationStoreDbContext(adminOptions))
        {
            var row = await persisted.ConversationOutbox.SingleAsync();
            Assert.Equal(
                receipt switch
                {
                    "DELIVERED" or "READ" => "DELIVERED",
                    "FAILED" => "BLOCKED",
                    _ => "DISPATCHING",
                },
                row.State
            );
            Assert.Equal(1, row.AttemptNumber);
            Assert.Equal(2, await persisted.DeliveryObservations.CountAsync());
        }
        await using (
            var terminal = new NpgsqlCommand(
                "SELECT terminal FROM business.whatsapp_outbox_work WHERE outbox_id = @id",
                owner
            )
        )
        {
            terminal.Parameters.AddWithValue("id", outbox.OutboxId);
            Assert.Equal(receipt != "UNKNOWN", await terminal.ExecuteScalarAsync());
        }
        if (receipt != "UNKNOWN")
            using (scope.Begin())
                Assert.Null(await directory.ClaimAsync(CancellationToken.None));
    }

    private sealed class Factory(
        DbContextOptions<ConversationStoreDbContext> options,
        DbContextOptions<EmploymentRelationshipDbContext> relationshipOptions
    )
        : IDbContextFactory<ConversationStoreDbContext>,
            IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() => new(options);

        EmploymentRelationshipDbContext IDbContextFactory<EmploymentRelationshipDbContext>.CreateDbContext() =>
            new(relationshipOptions);
    }

    private sealed class UnusedRelationships : IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public EmploymentRelationshipDbContext CreateDbContext() =>
            throw new InvalidOperationException(
                "Exact leasing must not read separate relationship authority."
            );
    }

    private sealed class Gate(WhatsAppActivationAuthority authority) : IWhatsAppCapabilityGate
    {
        public bool DenyRecipient { get; set; }

        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) => authority;

        public void RequireRecipient(Guid tenantId, string sender, DateTimeOffset now)
        {
            if (
                DenyRecipient
                || tenantId != authority.TenantId
                || sender != authority.RecipientBindingDigest
            )
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        }
    }
}
