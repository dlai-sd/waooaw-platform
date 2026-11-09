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

public sealed class WhatsAppRelationshipOutboxLeaseTests
{
    [Theory]
    [InlineData("PENDING", 0, false, 1)]
    [InlineData("UNRESOLVED", 2, true, 2)]
    [InlineData("DISPATCHING", 2, true, 2)]
    [InlineData("LEASED", 12, true, 12)]
    public async Task ExactCustomerLeasePreservesRlsOrderingAndUnknownSubmission(
        string state, int attempt, bool reconciliation, int expectedAttempt)
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var ownerOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(postgres.GetConnectionString()).Options;
        await using (var db = new ConversationStoreDbContext(ownerOptions))
            await db.Database.EnsureCreatedAsync();
        var credential = Guid.NewGuid().ToString("N");
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        await using (var setup = new NpgsqlCommand(
            $"""
            CREATE ROLE business_app LOGIN NOBYPASSRLS PASSWORD '{credential}';
            GRANT USAGE ON SCHEMA business TO business_app;
            GRANT SELECT, UPDATE ON business.conversation_outbox TO business_app;
            GRANT SELECT, INSERT ON business.conversation_delivery_observations,
                business.conversation_operational_signals TO business_app;
            ALTER TABLE business.conversation_outbox ENABLE ROW LEVEL SECURITY;
            ALTER TABLE business.conversation_outbox FORCE ROW LEVEL SECURITY;
            CREATE POLICY outbox_customer_scope ON business.conversation_outbox TO business_app
                USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
                WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
            """, owner))
            await setup.ExecuteNonQueryAsync();
        var now = DateTimeOffset.UtcNow;
        var authority = new WhatsAppActivationAuthority
        {
            TenantId = Guid.NewGuid(), Environment = "demo",
            RecipientBindingDigest = new string('a', 64), ActivationReference = "lease-fixture",
        };
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = new WhatsAppRelationshipRoute
        {
            ServiceTenantId = authority.TenantId, TenantId = Guid.NewGuid(),
            BindingId = Guid.NewGuid(), ActorId = Guid.NewGuid(),
            SenderHash = authority.RecipientBindingDigest,
        };
        var route = new WhatsAppCurrentRelationshipRoute(
            authority.TenantId, "demo", candidate.SenderHash, candidate.TenantId,
            candidate.BindingId, Guid.NewGuid(), candidate.ActorId, "EMPLOYER", Guid.NewGuid(), 1);
        await using (var directorySchema = new NpgsqlCommand(
            """
            CREATE ROLE bp_owner NOLOGIN NOBYPASSRLS;
            GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
            CREATE TABLE business.channel_bindings (
                tenant_id UUID NOT NULL, binding_id UUID NOT NULL,
                PRIMARY KEY (tenant_id, binding_id));
            CREATE TABLE business.whatsapp_outbox_work (
                outbox_id UUID PRIMARY KEY, tenant_id UUID NOT NULL, service_tenant_id UUID NOT NULL,
                sender_hash CHAR(64) NOT NULL, environment TEXT NOT NULL, binding_id UUID NOT NULL);
            ALTER TABLE business.whatsapp_outbox_work OWNER TO bp_owner;
            ALTER TABLE business.whatsapp_outbox_work ENABLE ROW LEVEL SECURITY;
            ALTER TABLE business.whatsapp_outbox_work FORCE ROW LEVEL SECURITY;
            CREATE POLICY work_owner ON business.whatsapp_outbox_work TO bp_owner
                USING (true) WITH CHECK (true);
            REVOKE ALL ON business.whatsapp_outbox_work FROM PUBLIC, business_app;
            """, owner))
            await directorySchema.ExecuteNonQueryAsync();
        foreach (var path in new[]
        {
            "infrastructure/postgres/init/91-wc134-whatsapp-relationship-route-directory.sql",
            "infrastructure/postgres/init/93-wc134-whatsapp-route-renewal.sql",
        })
        {
            var sql = await File.ReadAllTextAsync(RepositoryPaths.Resolve(path));
            await using var migration = new NpgsqlCommand(sql, owner);
            await migration.ExecuteNonQueryAsync();
        }
        var options = Options.Create(new Wc120ConversationOptions { Enabled = true, Environment = "demo" });
        var connection = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app", Password = credential,
        };
        var factory = new Factory(new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(connection.ConnectionString)
            .AddInterceptors(new TenantDbConnectionInterceptor(
                new HttpContextAccessor(), NullLogger<TenantDbConnectionInterceptor>.Instance, scope))
            .Options);
        var outbox = new WhatsAppOutboxService(
            factory, new UnusedRelationships(), options,
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new() { DispatchEnabled = true }),
            new ConversationStopFence(factory, options), execution: scope);
        var target = Row(route, 2, state, attempt, now);
        var earlier = Row(route, 1, "PENDING", 0, now);
        var foreign = Row(route with { TenantId = Guid.NewGuid() }, 1, "PENDING", 0, now);
        await using (var db = new ConversationStoreDbContext(ownerOptions))
        {
            db.AddRange(target, earlier, foreign);
            await db.SaveChangesAsync();
        }
        await using (var indexed = new NpgsqlCommand(
            """
            INSERT INTO business.channel_bindings VALUES (@tenant, @binding);
            INSERT INTO business.whatsapp_relationship_routes
                (service_tenant_id, sender_hash, tenant_id, binding_id, identity_link_id, actor_issuer,
                 actor_id, account_id, membership_id, bound_evidence_id, published_at)
                VALUES (@service, @sender, @tenant, @binding, gen_random_uuid(), 'fixture',
                    @actor, gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now());
            INSERT INTO business.whatsapp_outbox_work VALUES (@outbox, @tenant, @service, @sender, 'demo', @binding);
            """, owner))
        {
            indexed.Parameters.AddWithValue("tenant", route.TenantId);
            indexed.Parameters.AddWithValue("binding", route.BindingId);
            indexed.Parameters.AddWithValue("service", route.ServiceTenantId);
            indexed.Parameters.AddWithValue("sender", route.SenderHash);
            indexed.Parameters.AddWithValue("actor", route.ParticipantId);
            indexed.Parameters.AddWithValue("outbox", target.OutboxId);
            await indexed.ExecuteNonQueryAsync();
        }
        using (scope.Begin())
        {
            using (scope.BeginRelationshipValidation(candidate))
            {
                await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                    outbox.LeaseRelationshipAsync(target.OutboxId, route, "worker", now, CancellationToken.None));
                scope.ConfirmRelationshipRoute(route);
                await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                    outbox.LeaseNextAsync("worker", now, CancellationToken.None));
                foreach (var wrong in new[]
                {
                    route with { TenantId = Guid.NewGuid() },
                    route with { RelationshipId = Guid.NewGuid() },
                    route with { BindingId = Guid.NewGuid() },
                    route with { ParticipantId = Guid.NewGuid() },
                    route with { ConversationId = Guid.NewGuid() },
                    route with { RelationshipVersion = 2 },
                    route with { ParticipantRole = "EVALUATOR" },
                    route with { Environment = "other" },
                    route with { SenderHash = new string('b', 64) },
                })
                    await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                        outbox.LeaseRelationshipAsync(target.OutboxId, wrong, "worker", now, CancellationToken.None));
                Assert.Null(await outbox.LeaseRelationshipAsync(
                    foreign.OutboxId, route, "worker", now, CancellationToken.None));
                Assert.Null(await outbox.LeaseRelationshipAsync(
                    target.OutboxId, route, "worker", now, CancellationToken.None));
                await using (var retire = new NpgsqlCommand(
                    "UPDATE business.whatsapp_outbox_work SET binding_id = gen_random_uuid() WHERE outbox_id = @id", owner))
                {
                    retire.Parameters.AddWithValue("id", target.OutboxId);
                    await retire.ExecuteNonQueryAsync();
                }
                await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
                    outbox.LeaseRelationshipAsync(target.OutboxId, route, "worker", now, CancellationToken.None));
                await using (var restoreBinding = new NpgsqlCommand(
                    "UPDATE business.whatsapp_outbox_work SET binding_id = @binding WHERE outbox_id = @id", owner))
                {
                    restoreBinding.Parameters.AddWithValue("binding", route.BindingId);
                    restoreBinding.Parameters.AddWithValue("id", target.OutboxId);
                    await restoreBinding.ExecuteNonQueryAsync();
                }
                foreach (var mismatch in new[] { "environment", "relationship", "conversation", "sender" })
                {
                    await using (var mutation = new NpgsqlCommand(
                        """
                        UPDATE business.conversation_outbox
                        SET environment = @environment, relationship_id = @relationship,
                            conversation_id = @conversation, recipient_binding_digest = @sender
                        WHERE outbox_id = @id
                        """, owner))
                    {
                        mutation.Parameters.AddWithValue("environment", mismatch == "environment" ? "other" : route.Environment);
                        mutation.Parameters.AddWithValue("relationship", mismatch == "relationship" ? Guid.NewGuid() : route.RelationshipId);
                        mutation.Parameters.AddWithValue("conversation", mismatch == "conversation" ? Guid.NewGuid() : route.ConversationId);
                        mutation.Parameters.AddWithValue("sender", mismatch == "sender" ? new string('b', 64) : route.SenderHash);
                        mutation.Parameters.AddWithValue("id", target.OutboxId);
                        await mutation.ExecuteNonQueryAsync();
                    }
                    Assert.Null(await outbox.LeaseRelationshipAsync(
                        target.OutboxId, route, "worker", now, CancellationToken.None));
                }
                await using (var restore = new NpgsqlCommand(
                    """
                    UPDATE business.conversation_outbox
                    SET environment = @environment, relationship_id = @relationship,
                        conversation_id = @conversation, recipient_binding_digest = @sender
                    WHERE outbox_id = @id
                    """, owner))
                {
                    restore.Parameters.AddWithValue("environment", route.Environment);
                    restore.Parameters.AddWithValue("relationship", route.RelationshipId);
                    restore.Parameters.AddWithValue("conversation", route.ConversationId);
                    restore.Parameters.AddWithValue("sender", route.SenderHash);
                    restore.Parameters.AddWithValue("id", target.OutboxId);
                    await restore.ExecuteNonQueryAsync();
                }
                await using (var releaseEarlier = new NpgsqlCommand(
                    "UPDATE business.conversation_outbox SET state = 'DELIVERED' WHERE outbox_id = @id", owner))
                {
                    releaseEarlier.Parameters.AddWithValue("id", earlier.OutboxId);
                    await releaseEarlier.ExecuteNonQueryAsync();
                }
                await using (var locked = new NpgsqlConnection(postgres.GetConnectionString()))
                {
                    await locked.OpenAsync();
                    await using var transaction = await locked.BeginTransactionAsync();
                    await using var hold = new NpgsqlCommand(
                        "SELECT outbox_id FROM business.conversation_outbox WHERE outbox_id = @id FOR UPDATE",
                        locked, transaction);
                    hold.Parameters.AddWithValue("id", target.OutboxId);
                    Assert.Equal(target.OutboxId, await hold.ExecuteScalarAsync());
                    Assert.Null(await outbox.LeaseRelationshipAsync(
                        target.OutboxId, route, "worker", now, CancellationToken.None));
                    await transaction.RollbackAsync();
                }
                var lease = await outbox.LeaseRelationshipAsync(
                    target.OutboxId, route, "worker", now, CancellationToken.None);
                Assert.NotNull(lease);
                Assert.Equal(target.OutboxId, lease.OutboxId);
                Assert.Equal(route.TenantId, lease.TenantId);
                Assert.Equal(expectedAttempt, lease.AttemptNumber);
                Assert.Equal(reconciliation, lease.ReconciliationRequired);
                Assert.Null(await outbox.LeaseRelationshipAsync(
                    target.OutboxId, route, "other-worker", now, CancellationToken.None));
                await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                    outbox.HeartbeatAsync(target.OutboxId, "other-worker", now, CancellationToken.None));
                await outbox.HeartbeatAsync(target.OutboxId, "worker", now.AddSeconds(1), CancellationToken.None);
                await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
                    outbox.RecordResultAsync(target.OutboxId, "other-worker",
                        new("UNKNOWN", new string('d', 64), new string('e', 64), now.AddSeconds(2)),
                        CancellationToken.None));
                await outbox.RecordResultAsync(target.OutboxId, "worker",
                    new("UNKNOWN", new string('d', 64), new string('e', 64), now.AddSeconds(2)),
                    CancellationToken.None);
                gate.Authority = authority with { ActivationReference = "revoked" };
                await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                    outbox.LeaseRelationshipAsync(target.OutboxId, route, "worker", now, CancellationToken.None));
            }
        }
        Assert.Null(scope.CurrentTenantId);
        Assert.Null(scope.DatabaseTenantOverrideId);
        await using var persisted = new ConversationStoreDbContext(ownerOptions);
        var unchanged = await persisted.ConversationOutbox.SingleAsync(value => value.OutboxId == foreign.OutboxId);
        Assert.Equal("PENDING", unchanged.State);
        Assert.Equal(0, unchanged.AttemptNumber);
        var leased = await persisted.ConversationOutbox.SingleAsync(value => value.OutboxId == target.OutboxId);
        Assert.Null(leased.LeaseOwner);
        Assert.Equal("UNRESOLVED", leased.State);
        Assert.Equal(expectedAttempt, leased.AttemptNumber);
        Assert.Single(await persisted.DeliveryObservations.ToListAsync());
    }

    private static ConversationOutboxRecord Row(
        WhatsAppCurrentRelationshipRoute route, long sequence, string state, int attempt, DateTimeOffset now) =>
        new()
        {
            TenantId = route.TenantId, Environment = route.Environment,
            RelationshipId = route.RelationshipId, ConversationId = route.ConversationId,
            RecipientBindingDigest = route.SenderHash, Sequence = sequence,
            AggregateId = Guid.NewGuid().ToString("D"), IdempotencyKey = Guid.NewGuid(),
            PayloadDigest = new string('c', 64), Purpose = "CUSTOMER_REQUEST",
            State = state, AttemptNumber = attempt, NextAttemptAt = now.AddMinutes(-1),
            LeaseExpiresAt = state is "LEASED" or "DISPATCHING" ? now.AddMinutes(-1) : null,
        };

    private sealed class Factory(DbContextOptions<ConversationStoreDbContext> options)
        : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() => new(options);
    }

    private sealed class UnusedRelationships : IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public EmploymentRelationshipDbContext CreateDbContext() =>
            throw new InvalidOperationException("Leasing must not open a separate relationship authority context.");
    }

    private sealed class Gate(WhatsAppActivationAuthority authority) : IWhatsAppCapabilityGate
    {
        public WhatsAppActivationAuthority Authority { get; set; } = authority;
        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");
        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) => Authority;
        public void RequireRecipient(Guid tenantId, string sender, DateTimeOffset now)
        {
            if (tenantId != Authority.TenantId || sender != Authority.RecipientBindingDigest)
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        }
    }
}
