// Implements: work-contracts/WC-133-whatsapp-first-registration-and-web-registration-repair.md R001-R004, R009
// constitutional_basis: C-023, C-026, C-039, C-059, C-063

using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class PhoneOnboardingPostgresTests
{
    [Fact]
    public async Task FirstContactConcurrencyReplayEvidenceFailureStopAndTenantIsolationUseRealPostgres()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var ownerOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var owner = new ConversationStoreDbContext(ownerOptions))
            await owner.Database.EnsureCreatedAsync();
        await using var connection = new NpgsqlConnection(postgres.GetConnectionString());
        await connection.OpenAsync();
        var identityOptions = new DbContextOptionsBuilder<IdentityDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var identity = new IdentityDbContext(identityOptions))
        {
            await using var schema = new NpgsqlCommand(
                identity.Database.GenerateCreateScript(),
                connection
            );
            await schema.ExecuteNonQueryAsync();
        }
        await using (
            var roles = new NpgsqlCommand(
                """
                CREATE ROLE business_app LOGIN PASSWORD 'synthetic-app-password' NOBYPASSRLS;
                GRANT USAGE ON SCHEMA identity, business TO business_app;
                GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA business TO business_app;
                """,
                connection
            )
        )
            await roles.ExecuteNonQueryAsync();
        foreach (
            var name in new[]
            {
                "35-wc096-portal-interactions.sql",
                "67-wc133-phone-onboarding.sql",
                "67-wc133-phone-onboarding.sql",
            }
        )
        {
            await using var migration = new NpgsqlCommand(
                await File.ReadAllTextAsync(
                    RepositoryPaths.Resolve($"infrastructure/postgres/init/{name}")
                ),
                connection
            );
            await migration.ExecuteNonQueryAsync();
        }
        var conversationSchema = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/36-wc120-conversation-whatsapp.sql"
            )
        );
        await using (
            var policies = new NpgsqlCommand(
                conversationSchema[
                    conversationSchema.IndexOf(
                        "ALTER TABLE business.conversation_outbox ENABLE",
                        StringComparison.Ordinal
                    )..
                ],
                connection
            )
        )
            await policies.ExecuteNonQueryAsync();
        var tenant = Guid.NewGuid();
        var digest = new string('a', 64);
        var now = DateTimeOffset.UtcNow;
        var appConnection = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = "synthetic-app-password",
            Options = $"-c app.current_tenant_id={tenant:D}",
        };
        var factory = new Factory(appConnection.ConnectionString);
        var channel = new WhatsAppJourneyOptions
        {
            DispatchEnabled = true,
            CallbackAcceptanceEnabled = true,
            CallbackHost = "whatsapp-demo.example.test",
        };
        static string Hash(string value) =>
            Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
        var settings = new Wc120ConversationOptions
        {
            Enabled = true,
            Environment = "demo",
            AppBindingDigest = Hash("1001"),
            WabaBindingDigest = Hash("1002"),
            RecipientBindingDigest = Hash("1003"),
        };
        var fence = new ConversationStopFence(factory, Options.Create(settings));
        var outbox = new WhatsAppOutboxService(
            factory,
            factory,
            Options.Create(settings),
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(channel),
            fence
        );
        async Task<bool> BeginDispatch(ConversationOutboxRecord queued, DateTimeOffset at)
        {
            await using var db = factory.CreateDbContext();
            var row = await db.ConversationOutbox.SingleAsync(value =>
                value.OutboxId == queued.OutboxId
            );
            row.State = "LEASED";
            row.LeaseOwner = "synthetic-worker";
            row.LeaseExpiresAt = at.AddSeconds(60);
            await db.SaveChangesAsync();
            return await outbox.BeginDispatchAsync(
                row.OutboxId,
                "synthetic-worker",
                at,
                CancellationToken.None
            );
        }
        var cursor = new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = new string('k', 32) })
        );
        var evidence = new Evidence();
        var gate = new Gate(tenant, digest);
        var service = new PhoneOnboardingService(
            factory,
            evidence,
            gate,
            new PortalInteractionService(factory, cursor, new Catalog()),
            outbox,
            TimeProvider.System
        );
        VerifiedPhoneIdentityProof Proof(string messageId, string text = "Hello") =>
            new(
                messageId,
                digest,
                text,
                null,
                "whatsapp",
                "PHONE_VERIFIED",
                now,
                now,
                now.AddMinutes(5),
                Guid.NewGuid()
            )
            {
                Environment = "demo",
                AppBindingDigest = settings.AppBindingDigest,
                PayloadDigest = Convert.ToHexStringLower(
                    SHA256.HashData(Encoding.UTF8.GetBytes(text))
                ),
            };
        await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.ReceiveAsync(Proof("disabled"), CancellationToken.None)
        );
        gate.Allowed = true;
        evidence.Fail = true;
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.ReceiveAsync(Proof("failed"), CancellationToken.None)
        );
        await using (var empty = factory.CreateDbContext())
        {
            var pending = Assert.Single(await empty.Set<PhoneOnboardingIdentity>().ToListAsync());
            Assert.Null(pending.EvidenceId);
            Assert.Null(pending.AdmittedAt);
            Assert.Empty(await empty.PortalInteractionMessages.ToListAsync());
            Assert.Empty(await empty.ConversationOutbox.ToListAsync());
        }
        evidence.Fail = false;
        await using (
            var employment = (
                (IDbContextFactory<EmploymentRelationshipDbContext>)factory
            ).CreateDbContext()
        )
        {
            var schema = employment.Database.GenerateCreateScript();
            var start = schema.IndexOf(
                "CREATE TABLE business.whatsapp_journey_contacts",
                StringComparison.Ordinal
            );
            var end = schema.IndexOf(';', start);
            await using var contacts = new NpgsqlCommand(
                schema[start..(end + 1)]
                    + " GRANT SELECT ON business.whatsapp_journey_contacts TO business_app;",
                connection
            );
            await contacts.ExecuteNonQueryAsync();
        }
        var credentials = new Credentials(digest, now);
        var journey = new WhatsAppJourneyService(
            factory,
            evidence,
            Options.Create(channel),
            conversationDbFactory: factory,
            conversationOptions: Options.Create(settings),
            outboxService: outbox,
            capabilityGate: gate,
            webhookCredentials: credentials,
            onboarding: service
        );
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder
            .Services.AddControllers()
            .AddApplicationPart(typeof(WhatsAppJourneyController).Assembly);
        builder.Services.AddSingleton(journey);
        builder.Services.AddSingleton<IWhatsAppWebhookCredentials>(credentials);
        builder.Services.AddSingleton<IWhatsAppCapabilityGate>(gate);
        builder.Services.AddSingleton(Options.Create(channel));
        builder.Services.AddSingleton(Options.Create(settings));
        await using var host = builder.Build();
        host.MapControllers();
        await host.StartAsync();
        using var client = host.GetTestClient();
        client.BaseAddress = new Uri("https://whatsapp-demo.example.test");
        var envelope = JsonSerializer.Serialize(
            new
            {
                @object = "whatsapp_business_account",
                entry = new[]
                {
                    new
                    {
                        id = "1002",
                        changes = new[]
                        {
                            new
                            {
                                value = new
                                {
                                    metadata = new { phone_number_id = "1003" },
                                    messages = new[]
                                    {
                                        new
                                        {
                                            id = "first",
                                            from = "15550000001",
                                            type = "text",
                                            timestamp = now.ToUnixTimeSeconds().ToString(),
                                            text = new { body = "Hello" },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            }
        );
        for (var delivery = 0; delivery < 2; delivery++)
        {
            using var request = new HttpRequestMessage(
                HttpMethod.Post,
                "/api/v1/channels/whatsapp/webhook"
            );
            request.Content = new StringContent(envelope, Encoding.UTF8, "application/json");
            request.Headers.Add(
                "X-Hub-Signature-256",
                "sha256="
                    + Convert.ToHexStringLower(
                        HMACSHA256.HashData(
                            Encoding.UTF8.GetBytes(Credentials.Secret),
                            Encoding.UTF8.GetBytes(envelope)
                        )
                    )
            );
            using var response = await client.SendAsync(request);
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            Assert.Equal("{\"status\":\"ACCEPTED\"}", await response.Content.ReadAsStringAsync());
        }
        var receipts = await Task.WhenAll(
            Enumerable
                .Range(0, 8)
                .Select(_ => service.ReceiveAsync(Proof("first"), CancellationToken.None))
        );
        Assert.All(receipts, result => Assert.Equal("ONBOARDING", result.JourneyStage));
        Assert.Equal(1, evidence.Admissions);
        await using (var identity = new IdentityDbContext(identityOptions))
        {
            Assert.Empty(await identity.Accounts.ToListAsync());
            Assert.Empty(await identity.LoginMethods.ToListAsync());
            Assert.Empty(await identity.Memberships.ToListAsync());
        }
        await using (var db = factory.CreateDbContext())
        {
            Assert.Single(await db.Set<PhoneOnboardingIdentity>().ToListAsync());
            Assert.Equal(2, await db.PortalInteractionMessages.CountAsync());
            var queued = Assert.Single(await db.ConversationOutbox.ToListAsync());
            Assert.Null(queued.RelationshipId);
            Assert.Null(queued.ConversationId);
            Assert.NotNull(queued.PortalContextId);
            Assert.Null(queued.TemplateName);
            Assert.True(await BeginDispatch(queued, now));
            Assert.False(await BeginDispatch(queued, now.AddHours(25)));
        }
        await Task.WhenAll(
            Enumerable
                .Range(0, 6)
                .Select(i => service.ReceiveAsync(Proof($"turn-{i}"), CancellationToken.None))
        );
        await using (var db = factory.CreateDbContext())
        {
            var timeline = await db
                .PortalInteractionMessages.OrderBy(value => value.Sequence)
                .ToListAsync();
            Assert.Equal(
                Enumerable.Range(1, 14).Select(value => (long)value),
                timeline.Select(value => value.Sequence)
            );
            Assert.Equal(7, await db.ConversationOutbox.CountAsync());
        }
        var stopped = await service.ReceiveAsync(Proof("stop", "STOP"), CancellationToken.None);
        Assert.Equal("STOPPED", stopped.Status);
        Assert.Equal(
            "STOPPED",
            (await service.ReceiveAsync(Proof("after"), CancellationToken.None)).Status
        );
        await using (var db = factory.CreateDbContext())
        {
            Assert.Equal(14, await db.PortalInteractionMessages.CountAsync());
            foreach (var queued in await db.ConversationOutbox.ToListAsync())
                Assert.False(await BeginDispatch(queued, now));
        }
        appConnection.Options = $"-c app.current_tenant_id={Guid.NewGuid():D}";
        await using var denied = new Factory(appConnection.ConnectionString).CreateDbContext();
        Assert.Empty(await denied.Set<PhoneOnboardingIdentity>().ToListAsync());
        Assert.Empty(await denied.PortalInteractionMessages.ToListAsync());
        Assert.Empty(await denied.ConversationOutbox.ToListAsync());
    }

    private sealed class Factory(string connectionString)
        : IDbContextFactory<ConversationStoreDbContext>,
            IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            );

        EmploymentRelationshipDbContext IDbContextFactory<EmploymentRelationshipDbContext>.CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            );
    }

    private sealed class Evidence : IWhatsAppRegistrationEvidenceGateway
    {
        public bool Fail { get; set; }
        public int Admissions { get; private set; }

        public async Task<Guid> RecordProvisionalAsync(
            Guid tenantId,
            string admissionId,
            string bindingDigest,
            DateTimeOffset occurredAt,
            CancellationToken ct
        )
        {
            await RecordAsync(tenantId, admissionId, bindingDigest, occurredAt, ct);
            return Guid.NewGuid();
        }

        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken ct
        )
        {
            if (Fail)
                throw new InvalidOperationException("Synthetic evidence outage");
            Admissions++;
            return Task.CompletedTask;
        }
    }

    private sealed class Gate(Guid tenantId, string digest) : IWhatsAppCapabilityGate
    {
        public bool Allowed { get; set; }

        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) =>
            new()
            {
                TenantId = tenantId,
                RecipientBindingDigest = digest,
                AllowProvisionalOnboarding = Allowed,
            };

        public void RequireRecipient(Guid tenant, string binding, DateTimeOffset now)
        {
            if (tenant != tenantId || binding != digest)
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        }
    }

    private sealed class Catalog : IProfessionalCatalog
    {
        public IReadOnlyList<ProfessionalDiscoveryResult> Discover(string outcome) =>
            [
                new(
                    "fixture",
                    "1",
                    "Fixture professional",
                    ["Synthetic business assistance"],
                    new(true, "Fixture")
                ),
            ];

        public ProfessionalDisclosure? GetDisclosure(string professionalType) => null;
    }

    private sealed class Credentials(string digest, DateTimeOffset now)
        : IWhatsAppWebhookCredentials
    {
        public const string Secret = "synthetic-webhook-secret-at-least-32";

        public Task<string> ReadVerifyTokenAsync(CancellationToken ct) =>
            Task.FromResult("synthetic-token");

        public Task<string> ReadAppSecretAsync(CancellationToken ct) => Task.FromResult(Secret);

        public Task<WhatsAppProviderBinding> ReadSenderBindingAsync(CancellationToken ct) =>
            Task.FromResult(
                new WhatsAppProviderBinding
                {
                    Environment = "demo",
                    BindingVersion = "fixture:binding",
                    AppId = "1001",
                    WabaId = "1002",
                    PhoneNumberId = "1003",
                    RecipientPhoneNumber = "+15550000001",
                    RecipientBindingDigest = digest,
                    ApiVersion = "v25.0",
                    AuthorityReference = "fixture:authority",
                    ValidFrom = now.AddMinutes(-1),
                    ExpiresAt = now.AddMinutes(10),
                }
            );
    }
}
