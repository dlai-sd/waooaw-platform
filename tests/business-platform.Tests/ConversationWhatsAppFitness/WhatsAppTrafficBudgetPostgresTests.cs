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

public sealed class WhatsAppTrafficBudgetPostgresTests
{
    [Fact]
    public async Task ActualBudgetServiceSerializesRacesUnderForcedRlsAndKeepsAppendOnlyReservations()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw")
            .WithUsername("waooaw")
            .WithPassword(Guid.NewGuid().ToString("N"))
            .Build();
        await postgres.StartAsync();
        var adminOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var admin = new ConversationStoreDbContext(adminOptions))
        {
            await admin.Database.EnsureCreatedAsync();
        }
        var credential = Guid.NewGuid().ToString("N");
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        await using (
            var setup = new NpgsqlCommand(
                $"""
                CREATE ROLE bp_owner NOLOGIN NOBYPASSRLS;
                CREATE ROLE bp_runtime NOLOGIN NOBYPASSRLS;
                CREATE ROLE business_app LOGIN NOBYPASSRLS PASSWORD '{credential}';
                GRANT USAGE ON SCHEMA business TO business_app, bp_runtime, bp_owner;
                GRANT CREATE ON SCHEMA business TO bp_owner;
                GRANT SELECT ON business.conversation_outbox TO business_app;
                ALTER TABLE business.conversation_outbox ENABLE ROW LEVEL SECURITY;
                ALTER TABLE business.conversation_outbox FORCE ROW LEVEL SECURITY;
                CREATE POLICY conversation_outbox_tenant_isolation ON business.conversation_outbox
                    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
                DROP TABLE business.whatsapp_traffic_reservations;
                """,
                owner
            )
        )
            await setup.ExecuteNonQueryAsync();
        var migration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/61-wc120-whatsapp-traffic-reservations.sql"
            )
        );
        for (var application = 0; application < 2; application++)
        {
            await using var command = new NpgsqlCommand(migration, owner);
            await command.ExecuteNonQueryAsync();
        }

        var now = DateTimeOffset.UtcNow;
        var tenant = Guid.NewGuid();
        var recipient = new string('b', 64);
        var digest = "sha256:" + new string('a', 64);
        var capabilityOptions = new WhatsAppCapabilityOptions
        {
            Configured = true,
            ProviderAvailable = true,
            Environment = "demo",
            ReleaseDigest = digest,
            ConfigurationDigest = digest,
            CatalogDigest = digest,
            RollbackDigest = digest,
            Authority = new()
            {
                ActivationReference = "FA:postgres-concurrency",
                ExternalTrafficReference = "FA:traffic",
                ConsentReference = "consent:fixture",
                IncidentOwnerReference = "office:operations",
                AlertRouteReference = "alerts:fixture",
                Environment = "demo",
                ReleaseDigest = digest,
                ConfigurationDigest = digest,
                CatalogDigest = digest,
                RollbackDigest = digest,
                TenantId = tenant,
                RecipientBindingDigest = recipient,
                StartsAt = now.AddSeconds(-1),
                ExpiresAt = now.AddMinutes(5),
                MaximumMessages = 3,
                MaximumMessagesPerMinute = 3,
                MaximumSpendInr = 3,
                MaximumCostPerMessageInr = 1,
            },
        };
        var gate = new WhatsAppCapabilityGate(
            new StaticOptionsMonitor<WhatsAppCapabilityOptions>(capabilityOptions)
        );
        var tenantScope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var interceptor = new TenantDbConnectionInterceptor(
            new HttpContextAccessor(),
            NullLogger<TenantDbConnectionInterceptor>.Instance,
            tenantScope
        );
        var runtimeConnection = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = credential,
        }.ConnectionString;
        var runtimeOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(runtimeConnection)
            .AddInterceptors(interceptor)
            .Options;
        var factory = new Factory(runtimeOptions);
        var budget = new WhatsAppTrafficBudget(factory, gate, TimeProvider.System);
        var requests = new List<WhatsAppProviderDispatchRequest>();
        await using (var admin = new ConversationStoreDbContext(adminOptions))
        {
            for (var index = 0; index < 24; index++)
            {
                var row = new ConversationOutboxRecord
                {
                    Environment = "demo",
                    TenantId = tenant,
                    RelationshipId = Guid.NewGuid(),
                    ConversationId = Guid.NewGuid(),
                    Sequence = 1,
                    AggregateId = Guid.NewGuid().ToString("D"),
                    IdempotencyKey = Guid.NewGuid(),
                    State = "DISPATCHING",
                    AttemptNumber = 1,
                    LeaseExpiresAt = now.AddMinutes(5),
                };
                admin.ConversationOutbox.Add(row);
                requests.Add(
                    new(
                        row.OutboxId,
                        "demo",
                        tenant,
                        row.RelationshipId,
                        row.ConversationId,
                        row.Sequence,
                        row.PayloadReference,
                        row.PayloadDigest,
                        1
                    )
                );
            }
            await admin.SaveChangesAsync();
        }
        using (tenantScope.Begin())
        {
            var outcomes = await Task.WhenAll(
                requests.Select(async request =>
                {
                    try
                    {
                        await budget.ReserveAsync(request, recipient, CancellationToken.None);
                        return true;
                    }
                    catch (WhatsAppCapabilityUnavailableException error)
                        when (error.ReasonCode
                                is "TRAFFIC_BUDGET_EXHAUSTED"
                                    or "TRAFFIC_BUDGET_CONCURRENT_CHANGE"
                        )
                    {
                        return false;
                    }
                })
            );
            Assert.InRange(outcomes.Count(value => value), 1, 3);
            await using var runtime = factory.CreateDbContext();
            var reservations = await runtime.Set<WhatsAppTrafficReservation>().ToListAsync();
            Assert.Equal(outcomes.Count(value => value), reservations.Count);
            Assert.True(reservations.Sum(value => value.ReservedCostInr) <= 3);
            // Same activation reference cannot reset a consumed budget by editing its limits.
            capabilityOptions.Authority = capabilityOptions.Authority! with
            {
                MaximumSpendInr = 10,
            };
            var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                budget.ReserveAsync(requests[^1], recipient, CancellationToken.None)
            );
            Assert.Equal("ACTIVATION_RECORD_CHANGED", failure.ReasonCode);
            Assert.Equal(
                reservations.Count,
                await runtime.Set<WhatsAppTrafficReservation>().CountAsync()
            );
        }
        Assert.Null(tenantScope.CurrentTenantId);
        await using (var runtime = factory.CreateDbContext())
        {
            Assert.Empty(await runtime.Set<WhatsAppTrafficReservation>().ToListAsync());
        }
        await using var limited = new NpgsqlConnection(runtimeConnection);
        await limited.OpenAsync();
        await using var isolatedTransaction = await limited.BeginTransactionAsync();
        await using (
            var otherTenant = new NpgsqlCommand(
                "SELECT set_config('app.current_tenant_id', @tenant, true)",
                limited,
                isolatedTransaction
            )
        )
        {
            otherTenant.Parameters.AddWithValue("tenant", Guid.NewGuid().ToString("D"));
            await otherTenant.ExecuteNonQueryAsync();
        }
        await using (
            var read = new NpgsqlCommand(
                "SELECT count(*) FROM business.whatsapp_traffic_reservations",
                limited,
                isolatedTransaction
            )
        )
            Assert.Equal(0L, await read.ExecuteScalarAsync());
        await using (
            var update = new NpgsqlCommand(
                "UPDATE business.whatsapp_traffic_reservations SET reserved_cost_inr = 0",
                limited,
                isolatedTransaction
            )
        )
        {
            var denied = await Assert.ThrowsAsync<PostgresException>(() =>
                update.ExecuteNonQueryAsync()
            );
            Assert.Equal("42501", denied.SqlState);
        }
    }

    private sealed class Factory(DbContextOptions<ConversationStoreDbContext> options)
        : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() => new(options);
    }
}
