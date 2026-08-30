// Implements: WC-079 AA-03, AA-08, AA-12
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using System.Text.Json;
using Npgsql;
using Testcontainers.PostgreSql;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class Migration25PostgresFixture : IAsyncLifetime
{
    private const string Password = "wc079testpass";
    private PostgreSqlContainer? _container;

    public string OwnerConnectionString { get; private set; } = string.Empty;
    public string BusinessConnectionString { get; private set; } = string.Empty;

    public async Task InitializeAsync()
    {
        _container = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw")
            .WithUsername("waooaw")
            .WithPassword(Password)
            .Build();
        await _container.StartAsync();
        OwnerConnectionString = _container.GetConnectionString();
        await using var connection = await OpenAsync(OwnerConnectionString);
        await ExecuteAsync(connection, "CREATE SCHEMA business; CREATE ROLE business_app LOGIN PASSWORD 'wc079testpass'; GRANT USAGE ON SCHEMA business TO business_app;");
        await ExecuteAsync(connection, await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/25-agent-admission.sql")));
        BusinessConnectionString = new NpgsqlConnectionStringBuilder(OwnerConnectionString)
        {
            Username = "business_app",
            Password = Password,
        }.ConnectionString;
    }

    public async Task DisposeAsync()
    {
        if (_container is not null) await _container.DisposeAsync();
    }

    public static async Task<NpgsqlConnection> OpenAsync(string connectionString)
    {
        var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync();
        return connection;
    }

    public static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = sql;
        await command.ExecuteNonQueryAsync();
    }
}

[CollectionDefinition("Migration25Postgres")]
public sealed class Migration25PostgresCollection : ICollectionFixture<Migration25PostgresFixture>;

[Collection("Migration25Postgres")]
public sealed class Migration25PostgresIntegrationTests(Migration25PostgresFixture fixture)
{
    private const string ContentDigest = "sha256:1111111111111111111111111111111111111111111111111111111111111111";
    private const string ArtifactDigest = "sha256:2222222222222222222222222222222222222222222222222222222222222222";

    [Fact]
    public async Task ForcedRlsHidesOtherTenantAdmission()
    {
        var tenantA = Guid.NewGuid();
        var tenantB = Guid.NewGuid();
        await InsertAdmissionAsync(tenantA);
        await using var business = await Migration25PostgresFixture.OpenAsync(fixture.BusinessConnectionString);
        await Migration25PostgresFixture.ExecuteAsync(business, $"SET app.current_tenant_id = '{tenantB:D}';");
        await using var command = business.CreateCommand();
        command.CommandText = "SELECT count(*) FROM business.agent_admissions WHERE tenant_id = @tenant";
        command.Parameters.AddWithValue("tenant", tenantA);

        Assert.Equal(0L, await command.ExecuteScalarAsync());
    }

    [Fact]
    public async Task RevisionLineageIsAppendOnlyAndCannotCrossAdmission()
    {
        var tenant = Guid.NewGuid();
        var first = await InsertAdmissionAsync(tenant);
        var second = await InsertAdmissionAsync(tenant, "TRADING_FO_CRYPTO", "1.8.0");
        var predecessor = Guid.NewGuid();
        await using var owner = await Migration25PostgresFixture.OpenAsync(fixture.OwnerConnectionString);
        await Migration25PostgresFixture.ExecuteAsync(owner, RevisionSql(tenant, first, predecessor, 1, null));

        var crossAdmission = await Assert.ThrowsAsync<PostgresException>(() => Migration25PostgresFixture.ExecuteAsync(
            owner, RevisionSql(tenant, second, Guid.NewGuid(), 2, predecessor)));
        Assert.Equal(PostgresErrorCodes.ForeignKeyViolation, crossAdmission.SqlState);
        var mutation = await Assert.ThrowsAsync<PostgresException>(() => Migration25PostgresFixture.ExecuteAsync(
            owner, $"UPDATE business.agent_admission_revisions SET revision = 3 WHERE revision_id = '{predecessor:D}';"));
        Assert.Contains("append-only", mutation.MessageText);
    }

    [Fact]
    public async Task OfferableProjectionRequiresCurrentReadinessAndExcludesPrivateFields()
    {
        var tenant = Guid.NewGuid();
        var admission = await InsertAdmissionAsync(tenant, state: "ACTIVE");
        await using var owner = await Migration25PostgresFixture.OpenAsync(fixture.OwnerConnectionString);
        await Migration25PostgresFixture.ExecuteAsync(owner, RevisionSql(tenant, admission, Guid.NewGuid(), 1, null));
        await Migration25PostgresFixture.ExecuteAsync(owner, $"""
            INSERT INTO business.agent_admission_assertions
                (tenant_id, admission_id, assertion_type, subject_digest, environment, status,
                 source_authority, observed_at, valid_until, policy_version, evidence_ref)
            SELECT '{tenant:D}', '{admission:D}', assertion_type,
                CASE WHEN assertion_type = 'ARTIFACT' THEN '{ArtifactDigest}' ELSE '{ContentDigest}' END,
                'demo', 'PASS', assertion_type || '_OWNER', now(), now() + interval '1 hour',
                'WC-079-1.0', 'evidence:' || lower(assertion_type)
            FROM unnest(ARRAY['RUNTIME','ENVIRONMENT','PROVIDER','BILLING','ARTIFACT','CONSTITUTIONAL']) assertion_type;
            """);
        await using var business = await Migration25PostgresFixture.OpenAsync(fixture.BusinessConnectionString);
        await using var command = business.CreateCommand();
        command.CommandText = "SELECT projection::text FROM business.get_offerable_professional_versions('demo')";
        var projection = Assert.IsType<string>(await command.ExecuteScalarAsync());
        using var document = JsonDocument.Parse(projection);

        Assert.Equal("DIGITAL_MARKETING_LOCAL_SERVICE", document.RootElement.GetProperty("professionalTypeId").GetString());
        Assert.True(document.RootElement.TryGetProperty("skills", out _));
        Assert.False(document.RootElement.TryGetProperty("ownerSubjectId", out _));
        Assert.False(document.RootElement.TryGetProperty("artifactDigest", out _));
        Assert.False(document.RootElement.TryGetProperty("evidenceSetDigest", out _));
    }

    private async Task<Guid> InsertAdmissionAsync(
        Guid tenant,
        string professionalType = "DIGITAL_MARKETING_LOCAL_SERVICE",
        string version = "3.1.0",
        string state = "DRAFT")
    {
        var admission = Guid.NewGuid();
        await using var owner = await Migration25PostgresFixture.OpenAsync(fixture.OwnerConnectionString);
        await Migration25PostgresFixture.ExecuteAsync(owner, $"""
            INSERT INTO business.agent_admissions
                (admission_id, tenant_id, professional_type_id, professional_version, owner_subject_id,
                 state, state_version, current_revision, admission_content_digest, evidence_set_digest,
                 artifact_digest, policy_version)
            VALUES ('{admission:D}', '{tenant:D}', '{professionalType}', '{version}', gen_random_uuid(),
                '{state}', 3, 1, '{ContentDigest}', 'sha256:{new string('e', 64)}', '{ArtifactDigest}', 'WC-079-1.0');
            """);
        return admission;
    }

    private static string RevisionSql(Guid tenant, Guid admission, Guid revision, int number, Guid? predecessor) => $"""
        INSERT INTO business.agent_admission_revisions
            (revision_id, tenant_id, admission_id, revision, contract_schema_version,
             admission_content_digest, admission_content, actor_subject_id, predecessor_revision_id)
        VALUES ('{revision:D}', '{tenant:D}', '{admission:D}', {number}, '1.0.0',
            '{ContentDigest}', '{{"professionalIdentity":{{"supportedChannels":["WEB","WHATSAPP"]}},"skillManifest":[{{"skillId":"PRIMARY_SKILL","skillVersion":"1.0.0","capability":"Bounded delivery","businessKpi":"verified outcomes"}}]}}',
            gen_random_uuid(), {(predecessor is null ? "NULL" : $"'{predecessor:D}'")});
        """;
}