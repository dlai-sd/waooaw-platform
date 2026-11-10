using System.Data.Common;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppDeliveryRetentionPostgresTests
{
    [Theory]
    [InlineData("success")]
    [InlineData("takeover")]
    [InlineData("accepted")]
    [InlineData("expired")]
    [InlineData("clock-expired")]
    public async Task ProviderClaimCompletionFencesConcurrentLeaseChanges(string scenario)
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var connectionString = postgres.GetConnectionString();
        var leaseOwner = Guid.NewGuid();
        var otherOwner = Guid.NewGuid();
        var appBinding = new string('a', 64);
        var payloadDigest = new string('b', 64);
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync();
        await using (
            var setup = new NpgsqlCommand(
                """
                CREATE SCHEMA business;
                CREATE TABLE business.provider_event_claims (
                    claim_id uuid PRIMARY KEY,
                    environment text NOT NULL,
                    provider text NOT NULL,
                    app_binding_digest text NOT NULL,
                    event_identity text NOT NULL,
                    payload_digest text NOT NULL,
                    state text NOT NULL,
                    result_json jsonb NOT NULL,
                    lease_owner uuid,
                    lease_expires_at timestamptz,
                    received_at timestamptz NOT NULL,
                    terminal_at timestamptz,
                    expires_at timestamptz,
                    legal_hold boolean NOT NULL
                );
                INSERT INTO business.provider_event_claims VALUES (
                    @id, 'demo', 'WHATSAPP', @app, 'event', @digest, 'CLAIMED', '{}'::jsonb,
                    @owner, now() + interval '10 minutes', now(), NULL, NULL, false
                )
                """,
                connection
            )
        )
        {
            setup.Parameters.AddWithValue("id", Guid.NewGuid());
            setup.Parameters.AddWithValue("app", appBinding);
            setup.Parameters.AddWithValue("digest", payloadDigest);
            setup.Parameters.AddWithValue("owner", leaseOwner);
            await setup.ExecuteNonQueryAsync();
        }
        var barrier = new MutationBarrier("FOR UPDATE", "provider_event_claims");
        var factory = new Factory(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseNpgsql(connectionString)
                .AddInterceptors(barrier)
                .Options
        );
        var now = DateTimeOffset.UtcNow;
        var clock = new MutableClock(now);
        var service = new WhatsAppJourneyService(
            new RelationshipFitnessDbFactory(Guid.NewGuid().ToString("N")),
            new NoEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: factory,
            clock: clock
        );
        var proof = new VerifiedPhoneIdentityProof(
            "event",
            new string('c', 64),
            "synthetic",
            null,
            "demo",
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        )
        {
            Environment = "demo",
            AppBindingDigest = appBinding,
            PayloadDigest = payloadDigest,
        };
        var complete = service.CompleteProviderEventAsync(
            proof,
            leaseOwner,
            new WhatsAppJourneyReceipt(
                "event",
                "ACCEPTED",
                "START",
                "synthetic",
                false,
                "secret-token"
            ),
            CancellationToken.None
        );
        try
        {
            await barrier.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
            if (scenario == "clock-expired")
                clock.Now = now.AddMinutes(20);
            else if (scenario != "success")
            {
                var sql = scenario switch
                {
                    "takeover" => "UPDATE business.provider_event_claims SET lease_owner = @other",
                    "accepted" =>
                        "UPDATE business.provider_event_claims SET state = 'ACCEPTED', result_json = '{\"winner\":true}'::jsonb",
                    _ =>
                        "UPDATE business.provider_event_claims SET lease_expires_at = now() - interval '1 minute'",
                };
                await using var mutate = new NpgsqlCommand(sql, connection);
                if (scenario == "takeover")
                    mutate.Parameters.AddWithValue("other", otherOwner);
                Assert.Equal(1, await mutate.ExecuteNonQueryAsync());
            }
        }
        finally
        {
            barrier.Continue.TrySetResult();
        }
        if (scenario == "success")
            await complete.WaitAsync(TimeSpan.FromSeconds(10));
        else
        {
            var failure = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                complete.WaitAsync(TimeSpan.FromSeconds(10))
            );
            Assert.Equal("WHATSAPP_EVENT_LEASE_LOST", failure.Code);
        }
        await using var verify = new NpgsqlCommand(
            "SELECT state, result_json::text, lease_owner FROM business.provider_event_claims",
            connection
        );
        await using var row = await verify.ExecuteReaderAsync();
        Assert.True(await row.ReadAsync());
        var state = row.GetString(0);
        using var result = JsonDocument.Parse(row.GetString(1));
        if (scenario == "success")
        {
            Assert.Equal("ACCEPTED", state);
            Assert.Equal("", result.RootElement.GetProperty("InternalTenantToken").GetString());
            Assert.True(row.IsDBNull(2));
        }
        else if (scenario == "accepted")
            Assert.True(result.RootElement.GetProperty("winner").GetBoolean());
        else
        {
            Assert.Equal("CLAIMED", state);
            Assert.Equal(scenario == "takeover" ? otherOwner : leaseOwner, row.GetGuid(2));
        }
    }

    [Theory]
    [InlineData("hold")]
    [InlineData("purge-extension")]
    [InlineData("closure-extension")]
    public async Task ConcurrentHoldOrExtensionIsPreserved(string scenario)
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var connectionString = postgres.GetConnectionString();
        var observationId = Guid.NewGuid();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using (var connection = new NpgsqlConnection(connectionString))
        {
            await connection.OpenAsync();
            await using var setup = new NpgsqlCommand(
                """
                CREATE SCHEMA business;
                CREATE TABLE business.conversation_delivery_observations (
                    observation_id uuid PRIMARY KEY,
                    environment text NOT NULL,
                    tenant_id uuid NOT NULL,
                    relationship_id uuid,
                    portal_context_id uuid,
                    message_id uuid,
                    portal_message_id uuid,
                    provider text NOT NULL,
                    provider_event_identity text NOT NULL,
                    provider_reference_digest text NOT NULL,
                    delivery_state text NOT NULL,
                    observation_digest text NOT NULL,
                    observed_at timestamptz NOT NULL,
                    retain_until timestamptz NOT NULL,
                    legal_hold boolean NOT NULL
                );
                INSERT INTO business.conversation_delivery_observations VALUES (
                    @id, 'demo', @tenant, @relationship, NULL, NULL, NULL, 'WHATSAPP',
                    'synthetic', repeat('a', 64), 'DELIVERED', repeat('b', 64),
                    now() - interval '8 years', now() - interval '1 year', false
                );
                """,
                connection
            );
            setup.Parameters.AddWithValue("id", observationId);
            setup.Parameters.AddWithValue("tenant", tenantId);
            setup.Parameters.AddWithValue("relationship", relationshipId);
            await setup.ExecuteNonQueryAsync();
        }

        var barrier = new MutationBarrier(
            scenario == "closure-extension" ? "UPDATE" : "DELETE FROM"
        );
        var options = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(connectionString)
            .AddInterceptors(barrier)
            .Options;
        var factory = new Factory(options);
        var conversationOptions = Options.Create(
            new Wc120ConversationOptions { Environment = "demo" }
        );
        var service = new WhatsAppOutboxService(
            factory,
            new RelationshipFitnessDbFactory(Guid.NewGuid().ToString("N")),
            conversationOptions,
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new WhatsAppJourneyOptions()),
            new ConversationStopFence(factory, conversationOptions)
        );
        var now = DateTimeOffset.UtcNow;
        var purge =
            scenario == "closure-extension"
                ? null
                : service.PurgeDeliveryObservationsAsync(now, CancellationToken.None);
        Task operation = purge is null
            ? service.ApplyRelationshipClosureAsync(
                tenantId,
                relationshipId,
                now,
                CancellationToken.None
            )
            : purge;
        try
        {
            await barrier.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await using var connection = new NpgsqlConnection(connectionString);
            await connection.OpenAsync();
            await using var hold = new NpgsqlCommand(
                scenario == "hold"
                    ? "UPDATE business.conversation_delivery_observations SET legal_hold = true WHERE observation_id = @id"
                    : "UPDATE business.conversation_delivery_observations SET retain_until = now() + interval '20 years' WHERE observation_id = @id",
                connection
            );
            hold.Parameters.AddWithValue("id", observationId);
            Assert.Equal(1, await hold.ExecuteNonQueryAsync());
        }
        finally
        {
            barrier.Continue.TrySetResult();
        }

        await operation.WaitAsync(TimeSpan.FromSeconds(10));
        if (purge is not null)
            Assert.Equal(0, await purge);
        await using var verify = new NpgsqlConnection(connectionString);
        await verify.OpenAsync();
        await using var command = new NpgsqlCommand(
            scenario == "hold"
                ? "SELECT legal_hold FROM business.conversation_delivery_observations WHERE observation_id = @id"
                : "SELECT retain_until > now() + interval '19 years' FROM business.conversation_delivery_observations WHERE observation_id = @id",
            verify
        );
        command.Parameters.AddWithValue("id", observationId);
        Assert.Equal(true, await command.ExecuteScalarAsync());
    }

    [Fact]
    public async Task ClaimHoldAndCollisionRecoveryPreserveOtherWriteFailures()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var connectionString = postgres.GetConnectionString();
        var claimId = Guid.NewGuid();
        var binding = new string('a', 64);
        await using (var connection = new NpgsqlConnection(connectionString))
        {
            await connection.OpenAsync();
            await using var setup = new NpgsqlCommand(
                """
                CREATE SCHEMA business;
                CREATE TABLE business.provider_event_claims (
                    claim_id uuid PRIMARY KEY,
                    environment text NOT NULL,
                    provider text NOT NULL,
                    app_binding_digest text NOT NULL,
                    event_identity text NOT NULL,
                    payload_digest text NOT NULL,
                    state text NOT NULL,
                    result_json jsonb NOT NULL,
                    lease_owner uuid,
                    lease_expires_at timestamptz,
                    received_at timestamptz NOT NULL,
                    terminal_at timestamptz,
                    expires_at timestamptz,
                    legal_hold boolean NOT NULL
                );
                INSERT INTO business.provider_event_claims VALUES (
                    @id, 'demo', 'WHATSAPP', @binding, 'synthetic', repeat('b', 64),
                    'ACCEPTED', '{}'::jsonb, NULL, NULL, now() - interval '2 days',
                    now() - interval '2 days', now() - interval '1 day', false
                );
                """,
                connection
            );
            setup.Parameters.AddWithValue("id", claimId);
            setup.Parameters.AddWithValue("binding", binding);
            await setup.ExecuteNonQueryAsync();
        }

        var barrier = new MutationBarrier("DELETE FROM", "provider_event_claims");
        var factory = new Factory(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseNpgsql(connectionString)
                .AddInterceptors(barrier)
                .Options
        );
        var service = new WhatsAppJourneyService(
            new RelationshipFitnessDbFactory(Guid.NewGuid().ToString("N")),
            new NoEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: factory,
            conversationOptions: Options.Create(
                new Wc120ConversationOptions { Environment = "demo", AppBindingDigest = binding }
            )
        );
        var purge = service.PurgeExpiredProviderClaimsAsync(
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        try
        {
            await barrier.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await using var connection = new NpgsqlConnection(connectionString);
            await connection.OpenAsync();
            await using var hold = new NpgsqlCommand(
                "UPDATE business.provider_event_claims SET legal_hold = true WHERE claim_id = @id",
                connection
            );
            hold.Parameters.AddWithValue("id", claimId);
            Assert.Equal(1, await hold.ExecuteNonQueryAsync());
        }
        finally
        {
            barrier.Continue.TrySetResult();
        }

        Assert.Equal(0, await purge.WaitAsync(TimeSpan.FromSeconds(10)));
        await using var verify = new NpgsqlConnection(connectionString);
        await verify.OpenAsync();
        await using var command = new NpgsqlCommand(
            "SELECT legal_hold FROM business.provider_event_claims WHERE claim_id = @id",
            verify
        );
        command.Parameters.AddWithValue("id", claimId);
        Assert.Equal(true, await command.ExecuteScalarAsync());
        await using var uniqueness = new NpgsqlCommand(
            """
            ALTER TABLE business.provider_event_claims
            ADD CONSTRAINT provider_event_claim_identity_unique
            UNIQUE (environment, provider, app_binding_digest, event_identity)
            """,
            verify
        );
        await uniqueness.ExecuteNonQueryAsync();
        var collisionBarrier = new MutationBarrier("INSERT INTO", "provider_event_claims");
        var collisionFactory = new Factory(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseNpgsql(connectionString)
                .AddInterceptors(collisionBarrier)
                .Options
        );
        var collisionOptions = Options.Create(
            new Wc120ConversationOptions { Environment = "demo", AppBindingDigest = binding }
        );
        var collisionService = new WhatsAppOutboxService(
            collisionFactory,
            new RelationshipFitnessDbFactory(Guid.NewGuid().ToString("N")),
            collisionOptions,
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new WhatsAppJourneyOptions()),
            new ConversationStopFence(collisionFactory, collisionOptions)
        );
        var status = new WhatsAppProviderStatusEvent(
            "synthetic-collision",
            "synthetic-provider-message",
            "DELIVERED",
            DateTimeOffset.UtcNow,
            new string('b', 64)
        );
        var pendingStatus = collisionService.RecordProviderStatusAsync(
            status,
            CancellationToken.None
        );
        try
        {
            await collisionBarrier.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await using var concurrent = new NpgsqlCommand(
                """
                INSERT INTO business.provider_event_claims
                    (claim_id, environment, provider, app_binding_digest, event_identity, payload_digest,
                     state, result_json, received_at, terminal_at, expires_at, legal_hold)
                VALUES
                    (@id, 'demo', 'WHATSAPP_STATUS', @binding, @event, @digest, 'ACCEPTED', '{}'::jsonb,
                     now(), now(), now() + interval '30 days', false)
                """,
                verify
            );
            concurrent.Parameters.AddWithValue("id", Guid.NewGuid());
            concurrent.Parameters.AddWithValue("binding", binding);
            concurrent.Parameters.AddWithValue("event", status.EventIdentity);
            concurrent.Parameters.AddWithValue("digest", status.PayloadDigest);
            Assert.Equal(1, await concurrent.ExecuteNonQueryAsync());
        }
        finally
        {
            collisionBarrier.Continue.TrySetResult();
        }
        Assert.True(await pendingStatus.WaitAsync(TimeSpan.FromSeconds(10)));

        await using var rejectClaims = new NpgsqlCommand(
            "ALTER TABLE business.provider_event_claims ADD CONSTRAINT synthetic_claim_rejection CHECK (state <> 'CLAIMED')",
            verify
        );
        await rejectClaims.ExecuteNonQueryAsync();
        var statusService = new WhatsAppOutboxService(
            factory,
            new RelationshipFitnessDbFactory(Guid.NewGuid().ToString("N")),
            Options.Create(
                new Wc120ConversationOptions { Environment = "demo", AppBindingDigest = binding }
            ),
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new WhatsAppJourneyOptions()),
            new ConversationStopFence(
                factory,
                Options.Create(new Wc120ConversationOptions { Environment = "demo" })
            )
        );
        var failure = await Assert.ThrowsAsync<DbUpdateException>(() =>
            statusService.RecordProviderStatusAsync(
                new WhatsAppProviderStatusEvent(
                    "synthetic-status",
                    "synthetic-provider-message",
                    "DELIVERED",
                    DateTimeOffset.UtcNow,
                    new string('b', 64)
                ),
                CancellationToken.None
            )
        );
        Assert.Equal(
            PostgresErrorCodes.CheckViolation,
            Assert.IsType<PostgresException>(failure.InnerException).SqlState
        );
    }

    private sealed class NoEvidence : IWhatsAppRegistrationEvidenceGateway
    {
        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken cancellationToken
        ) => throw new InvalidOperationException("Evidence is not used by retention.");
    }

    private sealed class Factory(DbContextOptions<ConversationStoreDbContext> options)
        : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() => new(options);
    }

    private sealed class MutableClock(DateTimeOffset now) : TimeProvider
    {
        public DateTimeOffset Now { get; set; } = now;

        public override DateTimeOffset GetUtcNow() => Now;
    }

    private sealed class MutationBarrier(
        string operation,
        string table = "conversation_delivery_observations"
    ) : DbCommandInterceptor
    {
        public TaskCompletionSource Entered { get; } =
            new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource Continue { get; } =
            new(TaskCreationOptions.RunContinuationsAsynchronously);

        public override async ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default
        )
        {
            await WaitForMutationAsync(command, cancellationToken);
            return result;
        }

        public override async ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<DbDataReader> result,
            CancellationToken cancellationToken = default
        )
        {
            await WaitForMutationAsync(command, cancellationToken);
            return result;
        }

        private async Task WaitForMutationAsync(
            DbCommand command,
            CancellationToken cancellationToken
        )
        {
            if (
                command.CommandText.Contains(operation, StringComparison.OrdinalIgnoreCase)
                && command.CommandText.Contains(table, StringComparison.OrdinalIgnoreCase)
            )
            {
                Entered.TrySetResult();
                await Continue.Task.WaitAsync(cancellationToken);
            }
        }
    }
}
