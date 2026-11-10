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
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    [InlineData(5)]
    [InlineData(6)]
    [InlineData(7)]
    public async Task ActualBudgetServiceSerializesRacesUnderForcedRlsAndKeepsAppendOnlyReservations(
        int trafficMode
    )
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
                GRANT SELECT, UPDATE ON business.conversation_outbox TO business_app;
                ALTER TABLE business.conversation_outbox ENABLE ROW LEVEL SECURITY;
                ALTER TABLE business.conversation_outbox FORCE ROW LEVEL SECURITY;
                CREATE POLICY conversation_outbox_tenant_isolation ON business.conversation_outbox
                    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
                DROP TABLE business.whatsapp_traffic_reservations;
                DROP TABLE business.whatsapp_guest_traffic_events;
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
        var legacyTenant = Guid.NewGuid();
        foreach (
            var path in new[]
            {
                "infrastructure/postgres/init/69-wc134-whatsapp-guest-traffic-budget.sql",
                "infrastructure/postgres/init/71-wc134-whatsapp-session-limit-notice.sql",
                "infrastructure/postgres/init/78-wc134-guest-traffic-replay.sql",
                "infrastructure/postgres/init/79-wc134-activation-traffic-notice.sql",
            }
        )
        {
            if (path.EndsWith("78-wc134-guest-traffic-replay.sql", StringComparison.Ordinal))
            {
                await using var legacy = new NpgsqlCommand(
                    """
                    INSERT INTO business.whatsapp_guest_traffic_events
                        (tenant_id, activation_digest, authority_digest, event_id,
                         binding_digest, event_type, reserved_at)
                    VALUES (@tenant, repeat('a', 64), repeat('b', 64), repeat('c', 64),
                            repeat('d', 64), 'INBOUND', now())
                    """,
                    owner
                );
                legacy.Parameters.AddWithValue("tenant", legacyTenant);
                await legacy.ExecuteNonQueryAsync();
            }
            var guestMigration = await File.ReadAllTextAsync(RepositoryPaths.Resolve(path));
            for (var application = 0; application < 2; application++)
            {
                await using var command = new NpgsqlCommand(guestMigration, owner);
                await command.ExecuteNonQueryAsync();
            }
            if (
                path.EndsWith("78-wc134-guest-traffic-replay.sql", StringComparison.Ordinal)
                || path.EndsWith("79-wc134-activation-traffic-notice.sql", StringComparison.Ordinal)
            )
                await using (
                    var legacyCheck = new NpgsqlCommand(
                        """
                        SELECT inbound_notice IS NULL
                        FROM business.whatsapp_guest_traffic_events WHERE tenant_id = @tenant
                        """,
                        owner
                    )
                )
                {
                    legacyCheck.Parameters.AddWithValue("tenant", legacyTenant);
                    Assert.Equal(true, await legacyCheck.ExecuteScalarAsync());
                }
        }
        await using (
            var activationEvent = new NpgsqlCommand(
                """
                INSERT INTO business.whatsapp_guest_traffic_events
                    (tenant_id, activation_digest, authority_digest, event_id,
                     binding_digest, event_type, inbound_notice, reserved_at)
                VALUES (@tenant, repeat('a', 64), repeat('b', 64), repeat('e', 64),
                        repeat('d', 64), 'INBOUND', 'ACTIVATION_LIMIT', now())
                """,
                owner
            )
        )
        {
            activationEvent.Parameters.AddWithValue("tenant", legacyTenant);
            await activationEvent.ExecuteNonQueryAsync();
        }
        foreach (
            var path in new[]
            {
                "infrastructure/postgres/init/78-wc134-guest-traffic-replay.sql",
                "infrastructure/postgres/init/79-wc134-activation-traffic-notice.sql",
            }
        )
        {
            await using var replay = new NpgsqlCommand(
                await File.ReadAllTextAsync(RepositoryPaths.Resolve(path)),
                owner
            );
            await replay.ExecuteNonQueryAsync();
        }
        var replyCostPolicy = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/70-wc134-whatsapp-reply-cost-policy.sql"
            )
        );
        for (var application = 0; application < 2; application++)
        {
            await using var command = new NpgsqlCommand(replyCostPolicy, owner);
            await command.ExecuteNonQueryAsync();
        }
        await using (var inferencePrerequisites = new NpgsqlCommand(
            """
            CREATE ROLE air_owner NOLOGIN NOBYPASSRLS;
            CREATE ROLE ai_runtime_app NOLOGIN NOBYPASSRLS;
            CREATE SCHEMA ai_runtime AUTHORIZATION air_owner;
            CREATE TABLE business.provider_configs (auth_method TEXT);
            """, owner))
            await inferencePrerequisites.ExecuteNonQueryAsync();
        var inferenceMigration = await File.ReadAllTextAsync(RepositoryPaths.Resolve(
            "infrastructure/postgres/init/95-wc134-governed-conversation-generation.sql"));
        for (var application = 0; application < 2; application++)
        {
            await using var command = new NpgsqlCommand(inferenceMigration, owner);
            await command.ExecuteNonQueryAsync();
        }
        var spendMigration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/99zzzzzz-wc134-environment-spend.sql"
            )
        );
        await using (var command = new NpgsqlCommand(spendMigration, owner))
            await command.ExecuteNonQueryAsync();
        await using (var command = new NpgsqlCommand(
            """
            INSERT INTO business.environment_spend_authorities
                (environment,authority_version,maximum_paise,active,migration_complete,
                 authority_evidence_id,updated_at)
            VALUES ('demo',1,50000,true,true,gen_random_uuid(),clock_timestamp())
            ON CONFLICT (environment) DO UPDATE
            SET active=true,migration_complete=true,
                authority_evidence_id=excluded.authority_evidence_id
            """, owner))
            await command.ExecuteNonQueryAsync();

        var now = DateTimeOffset.UtcNow;
        var tenant = Guid.NewGuid();
        var recipient = new string('b', 64);
        var sender = trafficMode >= 3 ? new string('c', 64) : recipient;
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
            PublicAdmissionIdentityKeyAvailable = trafficMode >= 3,
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
                AllowRegistrationVerification = true,
                AllowPublicAdmission = trafficMode >= 3,
                AllowProvisionalOnboarding = trafficMode >= 3,
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
        var budget = new WhatsAppTrafficBudget(factory, gate, TimeProvider.System, tenantScope);
        var guestBudget = new WhatsAppGuestTrafficBudget(factory, gate, TimeProvider.System);
        var requests = new List<WhatsAppProviderDispatchRequest>();
        var customerRoutes = new Dictionary<Guid, WhatsAppRelationshipRoute>();
        await using (var admin = new ConversationStoreDbContext(adminOptions))
        {
            for (var index = 0; index < 24; index++)
            {
                var candidate = new WhatsAppRelationshipRoute
                {
                    ServiceTenantId = tenant, SenderHash = sender, TenantId = Guid.NewGuid(),
                    BindingId = Guid.NewGuid(), ActorId = Guid.NewGuid(),
                };
                var row = new ConversationOutboxRecord
                {
                    Environment = "demo",
                    TenantId = trafficMode == 7 && index % 3 == 0 ? candidate.TenantId : tenant,
                    RelationshipId = Guid.NewGuid(),
                    ConversationId = Guid.NewGuid(),
                    Sequence = 1,
                    AggregateId = Guid.NewGuid().ToString("D"),
                    IdempotencyKey = Guid.NewGuid(),
                    Purpose = "CUSTOMER_REQUEST",
                    RecipientBindingDigest = sender,
                    PayloadDigest = new string('d', 64),
                    State = "DISPATCHING",
                    AttemptNumber = 1,
                    LeaseExpiresAt = now.AddMinutes(5),
                };
                admin.ConversationOutbox.Add(row);
                customerRoutes.Add(row.OutboxId, candidate);
                requests.Add(
                    new(
                        row.OutboxId,
                        "demo",
                        row.TenantId,
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
        async Task ReserveCustomerOutbound(WhatsAppProviderDispatchRequest request)
        {
            var candidate = customerRoutes[request.OutboxId];
            using var customer = tenantScope.BeginRelationshipValidation(candidate);
            var current = new WhatsAppCurrentRelationshipRoute(
                tenant, "demo", sender, candidate.TenantId, candidate.BindingId,
                Assert.IsType<Guid>(request.RelationshipId), candidate.ActorId, "EVALUATOR",
                Assert.IsType<Guid>(request.ConversationId), 1);
            tenantScope.ConfirmRelationshipRoute(current);
            var mismatch = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                budget.ReserveRelationshipOutboundAsync(
                    request with { PayloadDigest = new string('e', 64) }, current, CancellationToken.None));
            Assert.Equal("OUTBOUND_LEASE_EXPIRED", mismatch.ReasonCode);
            Assert.Null(tenantScope.DatabaseTenantOverrideId);
            await budget.ReserveRelationshipOutboundAsync(request, current, CancellationToken.None);
            Assert.Equal(current.TenantId, tenantScope.CurrentTenantId);
            Assert.Null(tenantScope.DatabaseTenantOverrideId);
            await using var customerDb = factory.CreateDbContext();
            Assert.Empty(await customerDb.WhatsAppGuestTrafficEvents.ToListAsync());
            Assert.Empty(await customerDb.Set<WhatsAppTrafficReservation>().ToListAsync());
            var duplicate = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                budget.ReserveRelationshipOutboundAsync(request, current, CancellationToken.None));
            Assert.Equal("OUTBOUND_ALREADY_RESERVED", duplicate.ReasonCode);
            Assert.Null(tenantScope.DatabaseTenantOverrideId);
            var settings = Options.Create(new Wc120ConversationOptions { Enabled = true, Environment = "demo" });
            var outbox = new WhatsAppOutboxService(
                factory, new UnusedRelationships(), settings,
                new StaticOptionsMonitor<WhatsAppJourneyOptions>(new() { DispatchEnabled = true }),
                new ConversationStopFence(factory, settings), execution: tenantScope);
            var canonical = await customerDb.ConversationOutbox.SingleAsync(value => value.OutboxId == request.OutboxId);
            var status = new WhatsAppProviderStatusEvent(
                "signed-delivery", "provider-reference", "delivered", now, new string('d', 64))
            {
                OutboxId = request.OutboxId, SenderBindingDigest = sender,
            };
            await using var observationTransaction = await customerDb.Database.BeginTransactionAsync();
            Assert.True(await outbox.HasSubmissionReservationAsync(customerDb, canonical, status, CancellationToken.None));
            Assert.Null(tenantScope.DatabaseTenantOverrideId);
            Assert.Equal(current.TenantId, tenantScope.CurrentTenantId);
            await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
                outbox.HasSubmissionReservationAsync(
                    customerDb, canonical, status with { SenderBindingDigest = new string('f', 64) },
                    CancellationToken.None));
            await observationTransaction.RollbackAsync();
        }
        async Task<WhatsAppGuestTrafficNotice> ReserveCustomerInbound(WhatsAppProviderDispatchRequest request)
        {
            var candidate = customerRoutes[request.OutboxId];
            using var customer = tenantScope.BeginRelationshipValidation(candidate);
            var current = new WhatsAppCurrentRelationshipRoute(
                tenant, "demo", sender, candidate.TenantId, candidate.BindingId,
                Assert.IsType<Guid>(request.RelationshipId), candidate.ActorId, "EVALUATOR",
                Assert.IsType<Guid>(request.ConversationId), 1);
            tenantScope.ConfirmRelationshipRoute(current);
            var denied = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                budget.ReserveRelationshipInboundAsync(
                    current.TenantId, current.RelationshipId, current.BindingId, sender,
                    string.Empty, CancellationToken.None));
            Assert.Equal("INBOUND_BUDGET_AUTHORITY_DENIED", denied.ReasonCode);
            Assert.Equal(current.TenantId, tenantScope.CurrentTenantId);
            Assert.Null(tenantScope.DatabaseTenantOverrideId);
            var result = await budget.ReserveRelationshipInboundAsync(
                current.TenantId, current.RelationshipId, current.BindingId, sender,
                request.OutboxId.ToString("D"), CancellationToken.None);
            Assert.Equal(current.TenantId, tenantScope.CurrentTenantId);
            Assert.Null(tenantScope.DatabaseTenantOverrideId);
            await using var customerDb = factory.CreateDbContext();
            Assert.Empty(await customerDb.WhatsAppGuestTrafficEvents.ToListAsync());
            Assert.Empty(await customerDb.Set<WhatsAppTrafficReservation>().ToListAsync());
            return result;
        }
        using (tenantScope.Begin())
        {
            var expectedCosts = requests
                .Select(
                    (request, index) =>
                        new
                        {
                            request.OutboxId,
                            Cost = trafficMode == 1
                            || trafficMode == 2 && index % 2 == 0
                            || trafficMode == 4 && index % 3 == 1
                            || trafficMode == 5 && index % 3 == 1
                                ? 1m
                                : 0m,
                        }
                )
                .ToDictionary(value => value.OutboxId, value => value.Cost);
            var outcomes = await Task.WhenAll(
                requests.Select(
                    async (request, index) =>
                    {
                        try
                        {
                            if (trafficMode == 7 && index % 3 == 0)
                                await ReserveCustomerOutbound(request);
                            else if (trafficMode == 6 && index % 3 == 0)
                                await ReserveCustomerInbound(request);
                            else if (trafficMode == 5 && index % 3 == 0)
                                await budget.ReserveRelationshipInboundAsync(
                                    tenant,
                                    sender,
                                    request.OutboxId.ToString("D"),
                                    CancellationToken.None
                                );
                            else if (trafficMode == 4 && index % 3 == 0
                                || trafficMode is 6 or 7 && index % 3 == 1)
                                await guestBudget.ReserveInboundAsync(
                                    tenant,
                                    sender,
                                    request.OutboxId.ToString("D"),
                                    false,
                                    CancellationToken.None
                                );
                            else if (expectedCosts[request.OutboxId] > 0)
                                await budget.ReserveAsync(request.OutboxId, CancellationToken.None);
                            else
                                await budget.ReserveAsync(request, sender, CancellationToken.None);
                            return true;
                        }
                        catch (WhatsAppCapabilityUnavailableException error)
                            when (error.ReasonCode
                                    is "TRAFFIC_BUDGET_EXHAUSTED"
                                        or "TRAFFIC_BUDGET_CONCURRENT_CHANGE"
                                        or "GUEST_BUDGET_CONCURRENT_CHANGE"
                                        or "GUEST_GLOBAL_RATE_LIMIT_REACHED"
                            )
                        {
                            return false;
                        }
                    }
                )
            );
            Assert.InRange(outcomes.Count(value => value), 1, 3);
            await using var runtime = factory.CreateDbContext();
            var reservations = await runtime.Set<WhatsAppTrafficReservation>().ToListAsync();
            var guestEvents = await runtime.Set<WhatsAppGuestTrafficEvent>().ToListAsync();
            Assert.Equal(outcomes.Count(value => value), reservations.Count + guestEvents.Count);
            Assert.All(
                reservations,
                value => Assert.Equal(expectedCosts[value.OutboxId], value.ReservedCostInr)
            );
            foreach (var guestEvent in guestEvents.Where(value => value.EventType == "INBOUND"))
            {
                var request = requests.Single(value =>
                    WhatsAppGuestTrafficEventIdentity.Inbound(value.OutboxId.ToString("D"))
                    == guestEvent.EventId
                );
                var requestIndex = requests.IndexOf(request);
                var replay = trafficMode == 6 && requestIndex % 3 == 0
                    ? await ReserveCustomerInbound(request)
                    : trafficMode == 5
                    ? await budget.ReserveRelationshipInboundAsync(
                        tenant, sender, request.OutboxId.ToString("D"), CancellationToken.None)
                    : await guestBudget.ReserveInboundAsync(
                        tenant,
                        sender,
                        request.OutboxId.ToString("D"),
                        false,
                        CancellationToken.None
                    );
                Assert.Equal(
                    guestEvent.InboundNotice switch
                    {
                        "NONE" => WhatsAppGuestTrafficNotice.None,
                        "GUEST_MESSAGE_LIMIT" => WhatsAppGuestTrafficNotice.GuestMessageLimit,
                        "GLOBAL_RATE_LIMIT" => WhatsAppGuestTrafficNotice.GlobalRateLimit,
                        "ACTIVATION_LIMIT" => WhatsAppGuestTrafficNotice.ActivationLimit,
                        _ => throw new InvalidOperationException("Unexpected persisted notice."),
                    },
                    replay
                );
            }
            if (trafficMode is 6 or 7)
            {
                await using var exactLedger = new NpgsqlCommand(
                    """
                    SELECT count(*) FROM business.whatsapp_guest_traffic_events
                    WHERE tenant_id != @tenant AND tenant_id != @legacy
                    """, owner);
                exactLedger.Parameters.AddWithValue("tenant", tenant);
                exactLedger.Parameters.AddWithValue("legacy", legacyTenant);
                Assert.Equal(0L, await exactLedger.ExecuteScalarAsync());
                await using var exactReservations = new NpgsqlCommand(
                    "SELECT count(*) FROM business.whatsapp_traffic_reservations WHERE tenant_id != @tenant", owner);
                exactReservations.Parameters.AddWithValue("tenant", tenant);
                Assert.Equal(0L, await exactReservations.ExecuteScalarAsync());
                Assert.Null(tenantScope.DatabaseTenantOverrideId);
                Assert.Equal(tenant, tenantScope.CurrentTenantId);
            }
            // Same activation reference cannot reset a consumed budget by editing its limits.
            capabilityOptions.Authority = capabilityOptions.Authority! with
            {
                MaximumSpendInr = 10,
            };
            var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(
                async () =>
                {
                    if (trafficMode == 1)
                        await budget.ReserveAsync(Guid.NewGuid(), CancellationToken.None);
                    else
                        await budget.ReserveAsync(requests[^1], sender, CancellationToken.None);
                }
            );
            Assert.Equal("ACTIVATION_RECORD_CHANGED", failure.ReasonCode);
            Assert.Equal(
                reservations.Count,
                await runtime.Set<WhatsAppTrafficReservation>().CountAsync()
            );
            var midnight = new DateTimeOffset(now.UtcDateTime.Date, TimeSpan.Zero).AddMinutes(1);
            var modelReservation = Guid.NewGuid();
            var modelCustomer = Guid.NewGuid();
            var modelExecution = Guid.NewGuid();
            await using (var disableFence = new NpgsqlCommand(
                "ALTER TABLE business.conversation_model_reservations DISABLE TRIGGER conversation_model_environment_writer",
                owner
            ))
                await disableFence.ExecuteNonQueryAsync();
            foreach (var entry in new[]
            {
                (Id: modelReservation, Tenant: tenant, At: midnight.AddMinutes(-2), Cost: 100L),
                (Id: Guid.NewGuid(), Tenant: tenant, At: midnight.AddHours(-25), Cost: 999L),
                (Id: Guid.NewGuid(), Tenant: Guid.NewGuid(), At: midnight, Cost: 50000L),
            })
            {
                await using var insertModel = new NpgsqlCommand(
                    """
                    INSERT INTO business.conversation_model_reservations
                        (reservation_id,tenant_id,environment,activation_digest,authority_digest,cost_day,
                        customer_tenant_id,relationship_id,execution_id,actor_id,idempotency_key,mandate_digest,
                        request_digest,binding_id,binding_digest,rate_digest,evidence_id,reserved_paise,
                        input_rate_paise,output_rate_paise,state,reserved_at,expires_at)
                    VALUES (@id,@tenant,'demo',repeat('a',64),repeat('b',64),@day,
                        @customer,@relationship,@execution,@actor,@key,'sha256:'||repeat('c',64),
                        repeat('d',64),@binding,'sha256:'||repeat('e',64),'sha256:'||repeat('f',64),
                        @evidence,@cost,1,1,'RESERVED',@at,@expiry)
                    """, owner);
                insertModel.Parameters.AddWithValue("id", entry.Id);
                insertModel.Parameters.AddWithValue("tenant", entry.Tenant);
                insertModel.Parameters.AddWithValue("day", DateOnly.FromDateTime(entry.At.UtcDateTime));
                insertModel.Parameters.AddWithValue("customer", entry.Id == modelReservation ? modelCustomer : Guid.NewGuid());
                insertModel.Parameters.AddWithValue("relationship", Guid.NewGuid());
                insertModel.Parameters.AddWithValue("execution", entry.Id == modelReservation ? modelExecution : Guid.NewGuid());
                insertModel.Parameters.AddWithValue("actor", Guid.NewGuid());
                insertModel.Parameters.AddWithValue("key", Guid.NewGuid());
                insertModel.Parameters.AddWithValue("binding", Guid.NewGuid());
                insertModel.Parameters.AddWithValue("evidence", Guid.NewGuid());
                insertModel.Parameters.AddWithValue("cost", entry.Cost);
                insertModel.Parameters.AddWithValue("at", entry.At);
                insertModel.Parameters.AddWithValue("expiry", entry.At.AddSeconds(30));
                await insertModel.ExecuteNonQueryAsync();
            }
            await using (var enableFence = new NpgsqlCommand(
                "ALTER TABLE business.conversation_model_reservations ENABLE TRIGGER conversation_model_environment_writer",
                owner
            ))
                await enableFence.ExecuteNonQueryAsync();
            Assert.Equal(1099m, await ConversationInferenceOwner.CommittedModelSpendAsync(
                runtime, tenant, midnight, CancellationToken.None));
            await using (var settleModel = new NpgsqlCommand(
                """
                UPDATE business.conversation_model_reservations SET state='SETTLED',
                    actual_paise=2,input_tokens=1,output_tokens=1,settled_at=now(),settlement_evidence_id=@evidence
                WHERE reservation_id=@id
                """, owner))
            {
                settleModel.Parameters.AddWithValue("id", modelReservation);
                settleModel.Parameters.AddWithValue("evidence", Guid.NewGuid());
                Assert.Equal(1, await settleModel.ExecuteNonQueryAsync());
            }
            Assert.Equal(1001m, await ConversationInferenceOwner.CommittedModelSpendAsync(
                runtime, tenant, midnight, CancellationToken.None));
            await using (var replaceUsage = new NpgsqlCommand(
                "UPDATE business.conversation_model_reservations SET actual_paise=0 WHERE reservation_id=@id", owner))
            {
                replaceUsage.Parameters.AddWithValue("id", modelReservation);
                var rejected = await Assert.ThrowsAsync<PostgresException>(() => replaceUsage.ExecuteNonQueryAsync());
                Assert.Equal("23514", rejected.SqlState);
            }
            // A signed AIR callback does not inherit the original WhatsApp ingress tenant scope.
            await using var receiptDb = new ConversationStoreDbContext(
                new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(runtimeConnection)
                    .AddInterceptors(new TenantDbConnectionInterceptor(new HttpContextAccessor(),
                        NullLogger<TenantDbConnectionInterceptor>.Instance)).Options);
            await using (var receiptTransaction = await receiptDb.Database.BeginTransactionAsync())
            {
                await receiptDb.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT set_config('app.current_tenant_id',{modelCustomer.ToString("D")},true)");
                await receiptDb.Database.ExecuteSqlInterpolatedAsync(
                    $"""
                    INSERT INTO business.conversation_model_budget_receipts
                        (tenant_id,execution_id,reservation_id,budget_tenant_id)
                    VALUES ({modelCustomer},{modelExecution},{modelReservation},{tenant})
                    """);
                capabilityOptions.Authority = capabilityOptions.Authority! with { TenantId = Guid.NewGuid() };
                Assert.Equal(tenant, await ConversationInferenceOwner.OriginalBudgetTenantAsync(
                    receiptDb, modelCustomer, modelExecution, modelReservation, CancellationToken.None));
                capabilityOptions.Authority = null;
                Assert.Equal(tenant, await ConversationInferenceOwner.OriginalBudgetTenantAsync(
                    receiptDb, modelCustomer, modelExecution, modelReservation, CancellationToken.None));
                await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
                    ConversationInferenceOwner.OriginalBudgetTenantAsync(
                        receiptDb, modelCustomer, modelExecution, Guid.NewGuid(), CancellationToken.None));
                await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
                    ConversationInferenceOwner.OriginalBudgetTenantAsync(
                        receiptDb, modelCustomer, Guid.NewGuid(), modelReservation, CancellationToken.None));
                await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
                    ConversationInferenceOwner.OriginalBudgetTenantAsync(
                        receiptDb, Guid.NewGuid(), modelExecution, modelReservation, CancellationToken.None));
                await receiptDb.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT set_config('app.current_tenant_id',{modelCustomer.ToString("D")},true)");
                await receiptTransaction.CreateSavepointAsync("invalid_receipt");
                var invalid = await Assert.ThrowsAsync<PostgresException>(() =>
                    receiptDb.Database.ExecuteSqlInterpolatedAsync(
                        $"""
                        INSERT INTO business.conversation_model_budget_receipts
                            (tenant_id,execution_id,reservation_id,budget_tenant_id)
                        VALUES ({modelCustomer},{Guid.NewGuid()},{modelReservation},{Guid.NewGuid()})
                        """));
                Assert.Equal("23503", invalid.SqlState);
                await receiptTransaction.RollbackToSavepointAsync("invalid_receipt");
                await receiptTransaction.CommitAsync();
            }
        }
        Assert.Null(tenantScope.CurrentTenantId);
        await using (var runtime = factory.CreateDbContext())
        {
            Assert.Empty(await runtime.Set<WhatsAppTrafficReservation>().ToListAsync());
            Assert.Empty(await runtime.Set<WhatsAppGuestTrafficEvent>().ToListAsync());
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
            var guestRead = new NpgsqlCommand(
                "SELECT count(*) FROM business.whatsapp_guest_traffic_events",
                limited,
                isolatedTransaction
            )
        )
            Assert.Equal(0L, await guestRead.ExecuteScalarAsync());
        await using (
            var guestUpdate = new NpgsqlCommand(
                "UPDATE business.whatsapp_guest_traffic_events SET event_type = 'OUTBOUND'",
                limited,
                isolatedTransaction
            )
        )
        {
            var denied = await Assert.ThrowsAsync<PostgresException>(() =>
                guestUpdate.ExecuteNonQueryAsync()
            );
            Assert.Equal("42501", denied.SqlState);
        }
        await isolatedTransaction.RollbackAsync();
        await using var reservationTransaction = await limited.BeginTransactionAsync();
        await using (
            var update = new NpgsqlCommand(
                "UPDATE business.whatsapp_traffic_reservations SET reserved_cost_inr = 0",
                limited,
                reservationTransaction
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

    private sealed class UnusedRelationships : IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public EmploymentRelationshipDbContext CreateDbContext() =>
            throw new InvalidOperationException("Reservation evidence does not read separate relationship authority.");
    }
}
