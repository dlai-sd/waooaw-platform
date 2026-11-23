// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using System.Reflection;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.AcceptanceSynthetic;

internal sealed class ManualTime(DateTimeOffset now) : TimeProvider
{
    public DateTimeOffset Now { get; set; } = now;

    public override DateTimeOffset GetUtcNow() => Now;
}

/// <summary>
/// WC159-R002 (registry writes), R003 (tenant inherits the label), R004 (the label is kept, never deleted) and
/// R005 (suppression is recorded) against the real migration and a real PostgreSQL.
/// </summary>
public sealed class SyntheticAcceptanceRegistryPostgresTests : IAsyncLifetime
{
    private const string Migration = "infrastructure/postgres/init/99zzzzzzzz-wc159-01-synthetic-acceptance-registry.sql";
    private const string Issuer = "https://identity.invalid/realms/waooaw";
    private const string Run = "run-2026-11-23-001";
    private static readonly DateTimeOffset Start = new(2026, 11, 23, 9, 0, 0, TimeSpan.Zero);

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("synthetic_registry")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    private readonly ManualTime _time = new(Start);
    private PostgresSyntheticAcceptanceRegistry _registry = null!;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteAsync("CREATE ROLE business_app; CREATE ROLE bp_owner; CREATE SCHEMA business AUTHORIZATION bp_owner;");
        await ApplyMigrationAsync();
        _registry = NewRegistry();
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    private PostgresSyntheticAcceptanceRegistry NewRegistry() =>
        new(Factory(), new MemoryCache(new MemoryCacheOptions()), _time);

    private PooledDbContextFactory<ConversationStoreDbContext> Factory() =>
        new(new DbContextOptionsBuilder<ConversationStoreDbContext>().UseNpgsql(_postgres.GetConnectionString()).Options);

    private async Task ApplyMigrationAsync() =>
        await ExecuteAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve(Migration)));

    private async Task ExecuteAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private async Task<T> ScalarAsync<T>(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (T)(await command.ExecuteScalarAsync())!;
    }

    private static VerifiedCustomerActor Actor(string subject, string issuer = Issuer) =>
        (VerifiedCustomerActor)Activator.CreateInstance(
            typeof(VerifiedCustomerActor),
            BindingFlags.Instance | BindingFlags.NonPublic,
            null,
            [issuer, subject],
            null
        )!;

    private SyntheticTenantInheritance Inheritance(bool enabled) =>
        new(Options.Create(new AcceptanceSyntheticOptions { Enabled = enabled }), _time, NullLogger<SyntheticTenantInheritance>.Instance);

    private async Task<Guid> InheritAsync(SyntheticTenantInheritance inheritance, string subject, string issuer = Issuer)
    {
        var tenant = Guid.NewGuid();
        await using var db = Factory().CreateDbContext();
        await inheritance.InheritAsync(db, Actor(subject, issuer), tenant, default);
        return tenant;
    }

    [Fact]
    public async Task WC159_R004_MigrationIsIdempotent_AndTheApplicationRoleCanNeverDeleteOrRewriteALabel()
    {
        await ApplyMigrationAsync();
        foreach (var table in new[] { "synthetic_subjects", "synthetic_sandbox_recipients", "synthetic_tenants", "synthetic_delivery_suppressions" })
        {
            Assert.True(await ScalarAsync<bool>($"SELECT has_table_privilege('business_app', 'business.{table}', 'SELECT') AND has_table_privilege('business_app', 'business.{table}', 'INSERT')"));
            Assert.False(await ScalarAsync<bool>($"SELECT has_table_privilege('business_app', 'business.{table}', 'DELETE') OR has_table_privilege('business_app', 'business.{table}', 'TRUNCATE') OR has_table_privilege('business_app', 'business.{table}', 'UPDATE')"));
        }
        foreach (var table in new[] { "synthetic_subjects", "synthetic_sandbox_recipients" })
        {
            Assert.True(await ScalarAsync<bool>($"SELECT has_column_privilege('business_app', 'business.{table}', 'deactivated_at', 'UPDATE') AND NOT has_column_privilege('business_app', 'business.{table}', 'run_id', 'UPDATE')"));
        }
    }

    [Fact]
    public async Task WC159_R002_ARegistrationIsPerRunAndPerSubject_AndNeverRevivedAfterDeactivation()
    {
        Assert.Equal(SyntheticSubjectRegistration.Created, await _registry.RegisterSubjectAsync(Issuer, "subject-aaaa-0001", Run, "provisioner", default));
        Assert.Equal(SyntheticSubjectRegistration.AlreadyRegistered, await _registry.RegisterSubjectAsync(Issuer, "subject-aaaa-0001", Run, "provisioner", default));
        Assert.Equal(SyntheticSubjectRegistration.RunConflict, await _registry.RegisterSubjectAsync(Issuer, "subject-aaaa-0001", "run-2026-11-23-002", "provisioner", default));
        // The same subject under another issuer is a different identity.
        Assert.Equal(SyntheticSubjectRegistration.Created, await _registry.RegisterSubjectAsync("https://other.invalid/realms/x", "subject-aaaa-0001", Run, "provisioner", default));

        var result = await _registry.DeactivateRunAsync(Run, default);
        Assert.Equal(new SyntheticRunDeactivation(2, 0), result);
        Assert.Equal(new SyntheticRunDeactivation(0, 0), await _registry.DeactivateRunAsync(Run, default));
        Assert.Equal(SyntheticSubjectRegistration.RunConflict, await _registry.RegisterSubjectAsync(Issuer, "subject-aaaa-0001", Run, "provisioner", default));
        // Nothing is deleted: both rows remain, deactivated.
        Assert.Equal(2L, await ScalarAsync<long>("SELECT count(*) FROM business.synthetic_subjects WHERE deactivated_at IS NOT NULL"));
    }

    [Fact]
    public async Task WC159_R002_TheNumberOfActiveRegistrationsIsBoundedAndADeactivationFreesASlot()
    {
        for (var index = 0; index < PostgresSyntheticAcceptanceRegistry.MaximumActiveSubjects; index++)
            Assert.Equal(SyntheticSubjectRegistration.Created, await _registry.RegisterSubjectAsync(Issuer, $"subject-bound-{index:D4}", Run, "provisioner", default));
        Assert.Equal(SyntheticSubjectRegistration.LimitReached, await _registry.RegisterSubjectAsync(Issuer, "subject-bound-extra", Run, "provisioner", default));

        // A registration that has expired no longer counts.
        _time.Now = Start.Add(PostgresSyntheticAcceptanceRegistry.RegistrationLifetime).AddMinutes(1);
        Assert.Equal(SyntheticSubjectRegistration.Created, await _registry.RegisterSubjectAsync(Issuer, "subject-bound-after", "run-2026-11-24-001", "provisioner", default));
    }

    [Fact]
    public async Task WC159_R005_ASandboxRecipientIsStoredOnlyAsADigest_BoundedPerRun_AndExpiresOrIsDeactivated()
    {
        Assert.Equal(SandboxRecipientRegistration.Created, await _registry.RegisterSandboxRecipientAsync(Run, "+15550001234", "provisioner", default));
        Assert.Equal(SandboxRecipientRegistration.AlreadyRegistered, await _registry.RegisterSandboxRecipientAsync(Run, "+1 (555) 000-1234", "provisioner", default));
        var digest = SyntheticRecipient.Digest("+15550001234");
        Assert.Equal(digest, SyntheticRecipient.Digest("15550001234"));
        Assert.Equal(0L, await ScalarAsync<long>("SELECT count(*) FROM business.synthetic_sandbox_recipients WHERE recipient_digest LIKE '%5550001234%'"));
        Assert.True(await _registry.IsSandboxRecipientAsync(Run, digest, default));
        Assert.False(await _registry.IsSandboxRecipientAsync("run-2026-11-23-002", digest, default));
        Assert.False(await _registry.IsSandboxRecipientAsync(Run, SyntheticRecipient.Digest("+15550009999"), default));

        for (var index = 1; index < PostgresSyntheticAcceptanceRegistry.MaximumRecipientsPerRun; index++)
            await _registry.RegisterSandboxRecipientAsync(Run, $"+1555000{index:D4}", "provisioner", default);
        Assert.Equal(SandboxRecipientRegistration.LimitReached, await _registry.RegisterSandboxRecipientAsync(Run, "+15550007777", "provisioner", default));

        _time.Now = Start.Add(PostgresSyntheticAcceptanceRegistry.RegistrationLifetime).AddMinutes(1);
        Assert.False(await _registry.IsSandboxRecipientAsync(Run, digest, default));

        _time.Now = Start;
        Assert.True((await _registry.DeactivateRunAsync(Run, default)).Recipients > 0);
        Assert.False(await _registry.IsSandboxRecipientAsync(Run, digest, default));
        // Registering again under the same run reactivates the one row instead of adding another.
        Assert.Equal(SandboxRecipientRegistration.Created, await _registry.RegisterSandboxRecipientAsync(Run, "+15550001234", "provisioner", default));
        Assert.True(await _registry.IsSandboxRecipientAsync(Run, digest, default));
    }

    [Fact]
    public async Task WC159_R003_OnlyARegisteredAndCurrentSubjectLabelsItsTenant_AndTheLabelCarriesTheRun()
    {
        await _registry.RegisterSubjectAsync(Issuer, "subject-label-0001", Run, "provisioner", default);
        await _registry.RegisterSubjectAsync(Issuer, "subject-label-0002", "run-2026-11-23-002", "provisioner", default);
        await _registry.DeactivateRunAsync("run-2026-11-23-002", default);
        var inheritance = Inheritance(enabled: true);

        var labelled = await InheritAsync(inheritance, "subject-label-0001");
        var real = await InheritAsync(inheritance, "subject-real-0001");
        var deactivated = await InheritAsync(inheritance, "subject-label-0002");
        var otherIssuer = await InheritAsync(inheritance, "subject-label-0001", "https://other.invalid/realms/x");

        Assert.Equal(Run, await _registry.FindTenantRunAsync(labelled, default));
        Assert.Null(await _registry.FindTenantRunAsync(real, default));
        Assert.Null(await _registry.FindTenantRunAsync(deactivated, default));
        Assert.Null(await _registry.FindTenantRunAsync(otherIssuer, default));
        Assert.Equal(1L, await ScalarAsync<long>("SELECT count(*) FROM business.synthetic_tenants"));

        // An expired registration labels nothing, and labelling the same tenant twice keeps one row.
        _time.Now = Start.Add(PostgresSyntheticAcceptanceRegistry.RegistrationLifetime).AddMinutes(1);
        Assert.Null(await _registry.FindTenantRunAsync(await InheritAsync(inheritance, "subject-label-0001"), default));
        Assert.Equal(1L, await ScalarAsync<long>("SELECT count(*) FROM business.synthetic_tenants"));
    }

    [Fact]
    public async Task WC159_R001_WithTheSettingOffNoTenantIsLabelledAndTheRegistryIsNotEvenQueried()
    {
        await _registry.RegisterSubjectAsync(Issuer, "subject-off-00001", Run, "provisioner", default);
        // Dropping the tables proves the off path makes no query: a query would fail here.
        await ExecuteAsync("DROP TABLE business.synthetic_tenants, business.synthetic_subjects CASCADE;");
        var tenant = await InheritAsync(Inheritance(enabled: false), "subject-off-00001");
        Assert.NotEqual(Guid.Empty, tenant);
    }

    [Fact]
    public async Task WC159_R003_AnActorIsSyntheticWhenRegistered_AndLookupsAreBrieflyCached()
    {
        await _registry.RegisterSubjectAsync(Issuer, "subject-actor-0001", Run, "provisioner", default);
        Assert.True(await _registry.IsSyntheticActorAsync(Issuer, "subject-actor-0001", default));
        Assert.False(await _registry.IsSyntheticActorAsync(Issuer, "subject-actor-0002", default));
        Assert.False(await _registry.IsSyntheticActorAsync("https://other.invalid/realms/x", "subject-actor-0001", default));

        await _registry.RegisterSubjectAsync(Issuer, "subject-actor-0002", Run, "provisioner", default);
        Assert.False(await _registry.IsSyntheticActorAsync(Issuer, "subject-actor-0002", default));
        Assert.True(await NewRegistry().IsSyntheticActorAsync(Issuer, "subject-actor-0002", default));
    }

    [Fact]
    public async Task WC159_R005_ASuppressionIsRecordedOncePerAttempt_WithoutTheRecipient()
    {
        var tenant = Guid.NewGuid();
        var outbox = Guid.NewGuid();
        var digest = SyntheticRecipient.Digest("+15550001234");
        await _registry.RecordSuppressionAsync(tenant, Run, outbox, 1, digest, default);
        await _registry.RecordSuppressionAsync(tenant, Run, outbox, 1, digest, default);
        await _registry.RecordSuppressionAsync(tenant, Run, outbox, 2, digest, default);
        Assert.Equal(2L, await ScalarAsync<long>($"SELECT count(*) FROM business.synthetic_delivery_suppressions WHERE tenant_id = '{tenant}' AND reason = 'RECIPIENT_NOT_SANDBOX'"));
        Assert.Equal(0L, await ScalarAsync<long>("SELECT count(*) FROM business.synthetic_delivery_suppressions WHERE recipient_digest LIKE '%5550001234%'"));
    }
}
