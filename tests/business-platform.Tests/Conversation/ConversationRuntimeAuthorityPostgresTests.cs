// Implements: WC-134 R006/R008 current Identity locks and owner work-directory isolation.
// constitutional_basis: C-023, C-026, C-059, C-063
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationRuntimeAuthorityPostgresTests
{
    [Fact]
    public async Task RecoveryAuthorityMigrationReplayPreservesForcedRlsAndImmutableFreshIdentity()
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.SeedExecutionAsync();
        await using var app = fixture.App();
        await app.OpenAsync();
        var id = Guid.NewGuid();
        await using (
            var insert = new NpgsqlCommand(
                """
                INSERT INTO business.conversation_reconciliation_authorities
                    (authority_id, tenant_id, relationship_id, execution_id, requester_id, issuer,
                     account_id, membership_id, role, decision_space_snapshot_id, decision_space_version,
                     evidence_id, source_digest, idempotency_key, request_digest, expected_projection_version,
                     created_at, expires_at)
                VALUES (@authority, @tenant, @relationship, @execution, @actor, @issuer, @account,
                    @membership, 'OWNER', @snapshot, 1, @evidence, @digest, @key, @digest, 0,
                    now(), now() + interval '5 minutes')
                """,
                app
            )
        )
        {
            insert.Parameters.AddWithValue("authority", id);
            insert.Parameters.AddWithValue("tenant", fixture.Tenant);
            insert.Parameters.AddWithValue("relationship", Guid.NewGuid());
            insert.Parameters.AddWithValue("execution", fixture.Execution);
            insert.Parameters.AddWithValue("actor", fixture.Actor);
            insert.Parameters.AddWithValue("issuer", Fixture.Issuer);
            insert.Parameters.AddWithValue("account", fixture.Account);
            insert.Parameters.AddWithValue("membership", fixture.Membership);
            insert.Parameters.AddWithValue("snapshot", Guid.NewGuid());
            insert.Parameters.AddWithValue("evidence", Guid.NewGuid());
            insert.Parameters.AddWithValue("key", Guid.NewGuid());
            insert.Parameters.AddWithValue("digest", "sha256:" + new string('a', 64));
            Assert.Equal(1, await insert.ExecuteNonQueryAsync());
        }
        await using (
            var change = new NpgsqlCommand(
                "UPDATE business.conversation_reconciliation_authorities SET requester_id = gen_random_uuid()",
                app
            )
        )
        {
            var denied = await Assert.ThrowsAsync<PostgresException>(() =>
                change.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
        }
        await using (
            var foreign = new NpgsqlCommand(
                "SELECT set_config('app.current_tenant_id', @tenant, false)",
                app
            )
        )
        {
            foreign.Parameters.AddWithValue("tenant", Guid.NewGuid().ToString("D"));
            await foreign.ExecuteNonQueryAsync();
        }
        await using (
            var invisible = new NpgsqlCommand(
                "SELECT count(*) FROM business.conversation_reconciliation_authorities",
                app
            )
        )
            Assert.Equal(0L, await invisible.ExecuteScalarAsync());
        await using (
            var metadata = new NpgsqlCommand(
                "SELECT relforcerowsecurity AND relrowsecurity FROM pg_class WHERE oid = 'business.conversation_reconciliation_authorities'::regclass",
                app
            )
        )
            Assert.Equal(true, await metadata.ExecuteScalarAsync());
        Assert.Equal(
            1L,
            await fixture.ScalarAsync(
                "SELECT count(*) FROM business.conversation_reconciliation_authorities"
            )
        );
    }

    [Theory]
    [InlineData("OWNER")]
    [InlineData("MANAGER")]
    public async Task CurrentMembershipRoleComesFromLockedIdentityNotOriginalOrJwtRole(string role)
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.ExecuteAsync($"UPDATE identity.memberships SET roles = ARRAY['{role}']");
        await using var app = fixture.App();
        await using var db = new ConversationStoreDbContext(
            new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(app).Options
        );
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["IdentityBrokerRead:ActorIssuer"] = Fixture.Issuer,
                }
            )
            .Build();
        var identity = new ConversationRuntimeIdentityAuthority(configuration);
        var current = await identity.ResolveAsync(
            db,
            fixture.Tenant,
            fixture.Actor,
            CancellationToken.None
        );
        Assert.Equal(role, current.Role);
        Assert.Equal(Fixture.Issuer, current.Issuer);
        Assert.Equal(fixture.Account, current.AccountId);
        Assert.Equal(fixture.Membership, current.MembershipId);
    }

    [Theory]
    [InlineData("identity.actor_bindings", "status", "SUSPENDED")]
    [InlineData("identity.login_methods", "status", "SUSPENDED")]
    [InlineData("identity.accounts", "status", "SUSPENDED")]
    [InlineData("identity.memberships", "status", "REMOVED")]
    [InlineData("business.organisations", "identity_status", "SUSPENDED")]
    public async Task EveryCurrentIdentityOwnerCanFenceOriginalDispatch(
        string table,
        string column,
        string status
    )
    {
        await using var fixture = await Fixture.CreateAsync();
        await using var app = fixture.App();
        await app.OpenAsync();
        Assert.Equal(1L, await fixture.CountMembershipAsync(app));
        await fixture.ExecuteAsync($"UPDATE {table} SET {column} = '{status}'");
        Assert.Equal(0L, await fixture.CountMembershipAsync(app));
    }

    [Fact]
    public async Task MembershipLocksBlockRevocationUntilProjectionTransactionEndsAndRestoreActorContext()
    {
        await using var fixture = await Fixture.CreateAsync();
        await using var app = fixture.App();
        await app.OpenAsync();
        await using var transaction = await app.BeginTransactionAsync();
        await using (
            var context = new NpgsqlCommand(
                "SELECT set_config('app.identity_issuer', 'previous-issuer', true), set_config('app.identity_subject', 'previous-subject', true)",
                app,
                transaction
            )
        )
            await context.ExecuteNonQueryAsync();
        Assert.Equal(1L, await fixture.CountMembershipAsync(app));
        await using (
            var restored = new NpgsqlCommand(
                "SELECT current_setting('app.identity_issuer'), current_setting('app.identity_subject')",
                app,
                transaction
            )
        )
        await using (var reader = await restored.ExecuteReaderAsync())
        {
            Assert.True(await reader.ReadAsync());
            Assert.Equal("previous-issuer", reader.GetString(0));
            Assert.Equal("previous-subject", reader.GetString(1));
        }
        await using var revoker = new NpgsqlConnection(fixture.ConnectionString);
        await revoker.OpenAsync();
        await using (var timeout = new NpgsqlCommand("SET lock_timeout = '250ms'", revoker))
            await timeout.ExecuteNonQueryAsync();
        await using (
            var revoke = new NpgsqlCommand(
                "UPDATE identity.memberships SET status = 'REMOVED'",
                revoker
            )
        )
        {
            var blocked = await Assert.ThrowsAsync<PostgresException>(() =>
                revoke.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.LockNotAvailable, blocked.SqlState);
        }
        await transaction.CommitAsync();
        await fixture.ExecuteAsync("UPDATE identity.memberships SET status = 'REMOVED'");
        Assert.Equal(0L, await fixture.CountMembershipAsync(app));
    }

    [Fact]
    public async Task DirectoryIsPrivateEnvironmentBoundAndRechecksMembershipBeforeClaimingWork()
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.SeedExecutionAsync();
        await using var app = fixture.App();
        await app.OpenAsync();
        await using (
            var directory = new NpgsqlCommand(
                "SELECT * FROM business.conversation_runtime_work",
                app
            )
        )
        {
            var denied = await Assert.ThrowsAsync<PostgresException>(() =>
                directory.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
        }
        await using (
            var foreignEnvironment = new NpgsqlCommand(
                "SELECT count(*) FROM business.claim_conversation_runtime_work('another-environment')",
                app
            )
        )
            Assert.Equal(0L, await foreignEnvironment.ExecuteScalarAsync());
        await using (
            var claim = new NpgsqlCommand(
                "SELECT * FROM business.claim_conversation_runtime_work('demo')",
                app
            )
        )
        await using (var reader = await claim.ExecuteReaderAsync())
        {
            Assert.True(await reader.ReadAsync());
            Assert.Equal(fixture.Execution, reader.GetGuid(0));
            Assert.Equal(fixture.Tenant, reader.GetGuid(1));
            Assert.True(reader.GetBoolean(2));
            Assert.False(await reader.ReadAsync());
        }
        await fixture.ExecuteAsync(
            "UPDATE identity.memberships SET status = 'REMOVED'; UPDATE business.conversation_runtime_work SET due_at = now()"
        );
        await using (
            var revoked = new NpgsqlCommand(
                "SELECT authorized FROM business.claim_conversation_runtime_work('demo')",
                app
            )
        )
            Assert.Equal(false, await revoked.ExecuteScalarAsync());
    }

    [Fact]
    public async Task PendingStartCannotBeClaimedOrStarveStartedWorkAcrossTenantContext()
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.SeedExecutionAsync();
        var started = Guid.NewGuid();
        await fixture.SeedExecutionAsync(started, Guid.NewGuid());
        await fixture.ExecuteAsync(
            $"""
            INSERT INTO business.conversation_pending_starts VALUES ('{fixture.Tenant:D}', '{fixture.Execution:D}');
            UPDATE business.conversation_runtime_work SET due_at = now() - interval '1 minute'
            WHERE execution_id = '{fixture.Execution:D}';
            """
        );
        await using var app = fixture.App();
        await app.OpenAsync();
        var otherTenant = Guid.NewGuid();
        await using (
            var context = new NpgsqlCommand(
                "SELECT set_config('app.current_tenant_id', @tenant, false)",
                app
            )
        )
        {
            context.Parameters.AddWithValue("tenant", otherTenant.ToString("D"));
            await context.ExecuteNonQueryAsync();
        }
        await using (
            var claim = new NpgsqlCommand(
                "SELECT execution_id, authorized FROM business.claim_conversation_runtime_work('demo')",
                app
            )
        )
        await using (var reader = await claim.ExecuteReaderAsync())
        {
            Assert.True(await reader.ReadAsync());
            Assert.Equal(started, reader.GetGuid(0));
            Assert.True(reader.GetBoolean(1));
            Assert.False(await reader.ReadAsync());
        }
        await using (
            var retained = new NpgsqlCommand("SELECT current_setting('app.current_tenant_id')", app)
        )
            Assert.Equal(otherTenant.ToString("D"), await retained.ExecuteScalarAsync());
        await using (
            var pendingOnly = new NpgsqlCommand(
                "SELECT count(*) FROM business.claim_conversation_runtime_work('demo')",
                app
            )
        )
            Assert.Equal(0L, await pendingOnly.ExecuteScalarAsync());
        await using (
            var direct = new NpgsqlCommand(
                "SELECT business.runtime_work_has_pending_start(@tenant, @execution)",
                app
            )
        )
        {
            direct.Parameters.AddWithValue("tenant", fixture.Tenant);
            direct.Parameters.AddWithValue("execution", fixture.Execution);
            var denied = await Assert.ThrowsAsync<PostgresException>(() =>
                direct.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
        }
    }

    [Fact]
    public async Task ViewerForeignTenantAndChangedSourceCannotAcquireRuntimeAuthority()
    {
        await using var fixture = await Fixture.CreateAsync();
        await using var app = fixture.App();
        await app.OpenAsync();
        Assert.Equal(0L, await fixture.CountMembershipAsync(app, Guid.NewGuid()));
        await fixture.ExecuteAsync("UPDATE identity.memberships SET roles = ARRAY['VIEWER']");
        Assert.Equal(0L, await fixture.CountMembershipAsync(app));
        await fixture.ExecuteAsync("UPDATE identity.memberships SET roles = ARRAY['OWNER']");
        await fixture.SeedExecutionAsync();
        await using var changedSource = new NpgsqlCommand(
            "UPDATE business.conversation_executions SET runtime_actor_id = @other WHERE execution_id = @execution",
            app
        );
        changedSource.Parameters.AddWithValue("other", Guid.NewGuid());
        changedSource.Parameters.AddWithValue("execution", fixture.Execution);
        var denied = await Assert.ThrowsAsync<PostgresException>(() =>
            changedSource.ExecuteNonQueryAsync()
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
    }

    [Theory]
    [InlineData("runtime_actor_id", "gen_random_uuid()")]
    [InlineData("runtime_account_id", "gen_random_uuid()")]
    [InlineData("runtime_membership_id", "gen_random_uuid()")]
    [InlineData("runtime_actor_issuer", "'https://another-issuer.test'")]
    [InlineData("message_id", "gen_random_uuid()")]
    [InlineData("relationship_id", "gen_random_uuid()")]
    [InlineData("conversation_id", "gen_random_uuid()")]
    public async Task DeferredTriggerRejectsEveryFrozenAuthorityCoordinate(
        string column,
        string value
    )
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.SeedExecutionAsync();
        var denied = await Assert.ThrowsAsync<PostgresException>(() =>
            fixture.ExecuteAsync($"UPDATE business.conversation_executions SET {column} = {value}")
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
        Assert.Equal(
            1L,
            await fixture.ScalarAsync("SELECT count(*) FROM business.conversation_runtime_work")
        );
    }

    [Fact]
    public async Task DeferredDirectoryInputAndExecutionRollBackAsOneTransaction()
    {
        await using var fixture = await Fixture.CreateAsync();
        await using var transaction = await fixture.BeginAsync();
        await fixture.SeedExecutionAsync();
        Assert.Equal(
            0L,
            await fixture.ScalarAsync("SELECT count(*) FROM business.conversation_runtime_work")
        );
        await fixture.ExecuteAsync(
            "SET CONSTRAINTS business.conversation_runtime_work_sync IMMEDIATE"
        );
        Assert.Equal(
            1L,
            await fixture.ScalarAsync("SELECT count(*) FROM business.conversation_runtime_work")
        );
        await transaction.RollbackAsync();
        Assert.Equal(
            0L,
            await fixture.ScalarAsync("SELECT count(*) FROM business.conversation_runtime_work")
        );
        Assert.Equal(
            0L,
            await fixture.ScalarAsync("SELECT count(*) FROM business.conversation_executions")
        );
        Assert.Equal(
            0L,
            await fixture.ScalarAsync("SELECT count(*) FROM business.conversation_messages")
        );
    }

    [Fact]
    public async Task RevokedMembershipAtDeferredAdmissionLeavesNoDirectoryOrInput()
    {
        await using var fixture = await Fixture.CreateAsync();
        await using var transaction = await fixture.BeginAsync();
        await fixture.SeedExecutionAsync();
        await fixture.ExecuteAsync("UPDATE identity.memberships SET status = 'REMOVED'");
        var denied = await Assert.ThrowsAsync<PostgresException>(() =>
            fixture.ExecuteAsync(
                "SET CONSTRAINTS business.conversation_runtime_work_sync IMMEDIATE"
            )
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
        await transaction.RollbackAsync();
        Assert.Equal(
            0L,
            await fixture.ScalarAsync("SELECT count(*) FROM business.conversation_runtime_work")
        );
        Assert.Equal(
            0L,
            await fixture.ScalarAsync("SELECT count(*) FROM business.conversation_executions")
        );
    }

    [Fact]
    public async Task DueAndTerminalUpdatesRemainAllowedAndTerminalWorkCannotBeClaimed()
    {
        await using var fixture = await Fixture.CreateAsync();
        await fixture.SeedExecutionAsync();
        await fixture.ExecuteAsync(
            "UPDATE business.conversation_executions SET runtime_next_attempt_at = now(), runtime_terminal = true"
        );
        await using var app = fixture.App();
        await app.OpenAsync();
        await using var claim = new NpgsqlCommand(
            "SELECT count(*) FROM business.claim_conversation_runtime_work('demo')",
            app
        );
        Assert.Equal(0L, await claim.ExecuteScalarAsync());
    }

    private sealed class Fixture(PostgreSqlContainer postgres, NpgsqlConnection owner)
        : IAsyncDisposable
    {
        public Guid Tenant { get; } = Guid.NewGuid();
        public Guid Actor { get; } = Guid.NewGuid();
        public Guid Account { get; } = Guid.NewGuid();
        public Guid Membership { get; } = Guid.NewGuid();
        public Guid Execution { get; } = Guid.NewGuid();
        private Guid Message { get; } = Guid.NewGuid();
        public const string Issuer = "https://identity.test/realms/demo";
        public string ConnectionString => postgres.GetConnectionString();

        public NpgsqlConnection App() =>
            new(
                new NpgsqlConnectionStringBuilder(ConnectionString)
                {
                    Username = "business_app",
                    Password = "synthetic-runtime-test",
                    Options = $"-c app.current_tenant_id={Tenant:D}",
                }.ConnectionString
            );

        public static async Task<Fixture> CreateAsync()
        {
            var postgres = new PostgreSqlBuilder("postgres:16-alpine").Build();
            await postgres.StartAsync();
            var owner = new NpgsqlConnection(postgres.GetConnectionString());
            await owner.OpenAsync();
            var fixture = new Fixture(postgres, owner);
            await fixture.ExecuteAsync(
                """
                CREATE ROLE bp_owner NOBYPASSRLS;
                CREATE ROLE identity_resolver_owner NOBYPASSRLS;
                CREATE ROLE business_app LOGIN PASSWORD 'synthetic-runtime-test' NOBYPASSRLS;
                CREATE SCHEMA identity;
                CREATE SCHEMA business;
                CREATE SCHEMA constitutional;
                CREATE SCHEMA ai_runtime;
                GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
                GRANT USAGE ON SCHEMA identity, business TO business_app, identity_resolver_owner, bp_owner;
                CREATE TABLE identity.actor_bindings (
                    actor_issuer text, actor_subject text, account_id uuid, login_method_id uuid, status text
                );
                CREATE TABLE identity.login_methods (login_method_id uuid, account_id uuid, status text);
                CREATE TABLE identity.accounts (account_id uuid, status text);
                CREATE TABLE identity.memberships (
                    membership_id uuid PRIMARY KEY, account_id uuid, tenant_id uuid, roles text[], status text
                );
                CREATE TABLE business.organisations (tenant_id uuid PRIMARY KEY, identity_managed bool, identity_status text);
                GRANT SELECT ON identity.actor_bindings, identity.login_methods, identity.accounts,
                    identity.memberships, business.organisations TO identity_resolver_owner;
                ALTER TABLE identity.actor_bindings ENABLE ROW LEVEL SECURITY;
                ALTER TABLE identity.actor_bindings FORCE ROW LEVEL SECURITY;
                CREATE POLICY actor_scope ON identity.actor_bindings TO identity_resolver_owner
                    USING (actor_issuer = current_setting('app.identity_issuer', true)
                        AND actor_subject = current_setting('app.identity_subject', true));
                ALTER TABLE identity.login_methods ENABLE ROW LEVEL SECURITY;
                ALTER TABLE identity.login_methods FORCE ROW LEVEL SECURITY;
                CREATE POLICY actor_scope ON identity.login_methods TO identity_resolver_owner
                    USING (EXISTS (SELECT 1 FROM identity.actor_bindings a
                        WHERE a.login_method_id = login_methods.login_method_id AND a.account_id = login_methods.account_id));
                ALTER TABLE identity.accounts ENABLE ROW LEVEL SECURITY;
                ALTER TABLE identity.accounts FORCE ROW LEVEL SECURITY;
                CREATE POLICY actor_scope ON identity.accounts TO identity_resolver_owner
                    USING (EXISTS (SELECT 1 FROM identity.actor_bindings a WHERE a.account_id = accounts.account_id));
                ALTER TABLE identity.memberships ENABLE ROW LEVEL SECURITY;
                ALTER TABLE identity.memberships FORCE ROW LEVEL SECURITY;
                CREATE POLICY actor_scope ON identity.memberships TO identity_resolver_owner
                    USING (EXISTS (SELECT 1 FROM identity.actor_bindings a WHERE a.account_id = memberships.account_id));
                ALTER TABLE business.organisations ENABLE ROW LEVEL SECURITY;
                ALTER TABLE business.organisations FORCE ROW LEVEL SECURITY;
                CREATE POLICY resolver_scope ON business.organisations TO identity_resolver_owner
                    USING (EXISTS (SELECT 1 FROM identity.memberships m WHERE m.tenant_id = organisations.tenant_id));
                CREATE TABLE business.conversation_executions (
                    execution_id uuid PRIMARY KEY, tenant_id uuid NOT NULL, message_id uuid,
                    relationship_id uuid, conversation_id uuid,
                    processing_state text NOT NULL DEFAULT 'QUEUED',
                    completion_reason text, created_at timestamptz NOT NULL DEFAULT now()
                );
                CREATE TABLE business.conversation_messages (message_id uuid PRIMARY KEY, tenant_id uuid, environment text);
                CREATE TABLE business.conversation_pending_starts (tenant_id uuid NOT NULL, execution_id uuid NOT NULL);
                ALTER TABLE business.conversation_pending_starts OWNER TO bp_owner;
                ALTER TABLE business.conversation_pending_starts ENABLE ROW LEVEL SECURITY;
                ALTER TABLE business.conversation_pending_starts FORCE ROW LEVEL SECURITY;
                CREATE POLICY pending_tenant ON business.conversation_pending_starts
                    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid);
                GRANT SELECT ON business.conversation_messages TO bp_owner;
                GRANT SELECT, INSERT, UPDATE, DELETE ON business.conversation_executions TO business_app;
                CREATE TABLE constitutional.employment_dispatch_stops (tenant_id uuid, relationship_ref text);
                CREATE FUNCTION ai_runtime.lock_employment_dispatch(uuid, text)
                    RETURNS void LANGUAGE plpgsql AS $$ BEGIN RETURN; END $$;
                CREATE FUNCTION ai_runtime.employment_dispatch_relationship_key(text)
                    RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
                """
            );
            foreach (
                var file in new[]
                {
                    "87-wc134-runtime-event-projection.sql",
                    "88-wc134-runtime-identity-authority.sql",
                    "89-wc134-runtime-work-directory.sql",
                    "90-wc134-conversation-reconciliation-authority.sql",
                    "99zz-wc134-pending-runtime-fence.sql",
                }
            )
            {
                var migration = await File.ReadAllTextAsync(
                    RepositoryPaths.Resolve($"infrastructure/postgres/init/{file}")
                );
                await fixture.ExecuteAsync(migration);
                await fixture.ExecuteAsync(migration);
            }
            await using var seed = new NpgsqlCommand(
                """
                INSERT INTO identity.actor_bindings VALUES (@issuer, @actor, @account, @account, 'ACTIVE');
                INSERT INTO identity.login_methods VALUES (@account, @account, 'ACTIVE');
                INSERT INTO identity.accounts VALUES (@account, 'ACTIVE');
                INSERT INTO identity.memberships VALUES (@membership, @account, @tenant, ARRAY['OWNER'], 'ACTIVE');
                INSERT INTO business.organisations VALUES (@tenant, true, 'ACTIVE');
                """,
                owner
            );
            seed.Parameters.AddWithValue("issuer", Issuer);
            seed.Parameters.AddWithValue("actor", fixture.Actor.ToString("D"));
            seed.Parameters.AddWithValue("account", fixture.Account);
            seed.Parameters.AddWithValue("membership", fixture.Membership);
            seed.Parameters.AddWithValue("tenant", fixture.Tenant);
            await seed.ExecuteNonQueryAsync();
            return fixture;
        }

        public async Task<long> CountMembershipAsync(
            NpgsqlConnection connection,
            Guid? tenant = null
        )
        {
            await using var command = new NpgsqlCommand(
                "SELECT count(*) FROM identity.lock_conversation_runtime_membership(@issuer, @actor, @tenant, @membership)",
                connection
            );
            command.Parameters.AddWithValue("issuer", Issuer);
            command.Parameters.AddWithValue("actor", Actor);
            command.Parameters.AddWithValue("tenant", tenant ?? Tenant);
            command.Parameters.AddWithValue("membership", Membership);
            return (long)(await command.ExecuteScalarAsync())!;
        }

        public async Task SeedExecutionAsync(Guid? execution = null, Guid? message = null)
        {
            await using var context = new NpgsqlCommand(
                "SELECT set_config('app.current_tenant_id', @tenant, false)",
                owner
            );
            context.Parameters.AddWithValue("tenant", Tenant.ToString("D"));
            await context.ExecuteNonQueryAsync();
            await using var seed = new NpgsqlCommand(
                """
                INSERT INTO business.conversation_messages VALUES (@message, @tenant, 'demo');
                INSERT INTO business.conversation_executions
                    (execution_id, tenant_id, message_id, runtime_actor_id, runtime_actor_issuer, runtime_membership_id, runtime_account_id)
                VALUES (@execution, @tenant, @message, @actor, @issuer, @membership, @account);
                """,
                owner
            );
            seed.Parameters.AddWithValue("message", message ?? Message);
            seed.Parameters.AddWithValue("tenant", Tenant);
            seed.Parameters.AddWithValue("execution", execution ?? Execution);
            seed.Parameters.AddWithValue("actor", Actor);
            seed.Parameters.AddWithValue("issuer", Issuer);
            seed.Parameters.AddWithValue("membership", Membership);
            seed.Parameters.AddWithValue("account", Account);
            await seed.ExecuteNonQueryAsync();
        }

        public async Task ExecuteAsync(string sql)
        {
            await using var command = new NpgsqlCommand(sql, owner);
            await command.ExecuteNonQueryAsync();
        }

        public Task<NpgsqlTransaction> BeginAsync() => owner.BeginTransactionAsync().AsTask();

        public async Task<long> ScalarAsync(string sql)
        {
            await using var command = new NpgsqlCommand(sql, owner);
            return (long)(await command.ExecuteScalarAsync())!;
        }

        public async ValueTask DisposeAsync()
        {
            await owner.DisposeAsync();
            await postgres.DisposeAsync();
        }
    }
}
