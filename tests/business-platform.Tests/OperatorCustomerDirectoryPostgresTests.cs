// Implements: work-contracts/WC-172-safe-to-charge-real-customers.md (Demo defect repairs: Operations Customers tab)
// constitutional_basis: C-005, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Options;
using Moq;
using Npgsql;
using NpgsqlTypes;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Operations;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>
/// Applies the real operator-directory migration over a registrations table that has forced row security and no
/// policy for the application, then proves the one narrow function returns the latest registration per person, masked
/// contact details only, newest activity first, one page at a time.
/// </summary>
public sealed class OperatorCustomerDirectoryPostgresTests : IAsyncLifetime
{
    private const string Migration =
        "infrastructure/postgres/init/99zzzzzzzz-wc172-03-operator-customer-directory.sql";
    private static readonly string Digest = new('1', 32);

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("directory")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    private string RuntimeConnectionString =>
        new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
        {
            Username = "bp_runtime",
            Password = "synthetic-runtime-password",
        }.ConnectionString;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteAsAdminAsync(
            """
            CREATE ROLE business_app NOLOGIN;
            CREATE ROLE bp_runtime LOGIN PASSWORD 'synthetic-runtime-password' IN ROLE business_app;
            CREATE SCHEMA identity;
            GRANT USAGE ON SCHEMA identity TO business_app;
            CREATE TABLE identity.registrations (
                registration_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                actor_issuer varchar(256),
                actor_subject varchar(256) NOT NULL,
                state varchar(64) NOT NULL,
                display_name varchar(120),
                masked_email varchar(254),
                masked_mobile varchar(32),
                email_hmac_domain varchar(16), email_hmac_version varchar(32), email_hmac_key varchar(128),
                mobile_hmac_domain varchar(16), mobile_hmac_version varchar(32), mobile_hmac_key varchar(128),
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                completed_at timestamptz
            );
            ALTER TABLE identity.registrations ENABLE ROW LEVEL SECURITY;
            ALTER TABLE identity.registrations FORCE ROW LEVEL SECURITY;
            """
        );
        var sql = await File.ReadAllTextAsync(RepositoryPaths.Resolve(Migration));
        // Applying the file twice must leave the same schema.
        await ExecuteAsAdminAsync(sql);
        await ExecuteAsAdminAsync(sql);
        await ExecuteAsAdminAsync(
            """
            INSERT INTO identity.registrations
                (actor_issuer, actor_subject, state, display_name, masked_email, masked_mobile,
                 email_hmac_domain, email_hmac_version, email_hmac_key, created_at, updated_at, completed_at)
            VALUES
                ('iss', 'asha', 'Started', 'Asha Rao', 'a***@x.com', NULL, NULL, NULL, NULL,
                 '2026-11-20 10:00+00', '2026-11-20 10:00+00', NULL),
                ('iss', 'asha', 'Completed', 'Asha Rao', 'a***@x.com', '+91*****210',
                 'email', 'v1', '11111111111111111111111111111111',
                 '2026-11-21 10:00+00', '2026-11-22 10:00+00', '2026-11-22 10:00+00'),
                ('iss', 'ravi', 'ProfileCompletionRequired', 'Ravi Iyer', 'r***@y.com', NULL, NULL, NULL, NULL,
                 '2026-11-23 10:00+00', '2026-11-24 10:00+00', NULL),
                ('iss', 'sam', 'Started', 'Sam Roy', NULL, NULL, NULL, NULL, NULL,
                 '2026-11-25 10:00+00', '2026-11-25 10:00+00', NULL);
            """
        );
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    private async Task ExecuteAsAdminAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private async Task<
        List<(string Name, string Status, DateTimeOffset LastActive, Guid Id)>
    > PageAsync(
        string? name = null,
        string? status = null,
        string[]? domains = null,
        string[]? versions = null,
        string[]? digests = null,
        DateTimeOffset? afterAt = null,
        Guid? afterId = null,
        int limit = 10
    )
    {
        await using var connection = new NpgsqlConnection(RuntimeConnectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            """
            SELECT display_name, status, last_active_at, registration_id
            FROM identity.operator_customer_directory(@name, @domains, @versions, @digests, @status, @at, @id, @limit)
            """,
            connection
        );
        command.Parameters.Add(
            new NpgsqlParameter("name", NpgsqlDbType.Text) { Value = (object?)name ?? DBNull.Value }
        );
        command.Parameters.Add(
            new NpgsqlParameter("domains", NpgsqlDbType.Array | NpgsqlDbType.Text)
            {
                Value = (object?)domains ?? DBNull.Value,
            }
        );
        command.Parameters.Add(
            new NpgsqlParameter("versions", NpgsqlDbType.Array | NpgsqlDbType.Text)
            {
                Value = (object?)versions ?? DBNull.Value,
            }
        );
        command.Parameters.Add(
            new NpgsqlParameter("digests", NpgsqlDbType.Array | NpgsqlDbType.Text)
            {
                Value = (object?)digests ?? DBNull.Value,
            }
        );
        command.Parameters.Add(
            new NpgsqlParameter("status", NpgsqlDbType.Text)
            {
                Value = (object?)status ?? DBNull.Value,
            }
        );
        command.Parameters.Add(
            new NpgsqlParameter("at", NpgsqlDbType.TimestampTz)
            {
                Value = (object?)afterAt?.UtcDateTime ?? DBNull.Value,
            }
        );
        command.Parameters.Add(
            new NpgsqlParameter("id", NpgsqlDbType.Uuid)
            {
                Value = (object?)afterId ?? DBNull.Value,
            }
        );
        command.Parameters.Add(
            new NpgsqlParameter("limit", NpgsqlDbType.Integer) { Value = limit }
        );
        var rows = new List<(string, string, DateTimeOffset, Guid)>();
        await using var reader = await command.ExecuteReaderAsync();
        while (await reader.ReadAsync())
            rows.Add(
                (
                    reader.GetString(0),
                    reader.GetString(1),
                    reader.GetFieldValue<DateTimeOffset>(2),
                    reader.GetGuid(3)
                )
            );
        return rows;
    }

    [Fact]
    public async Task EachPersonAppearsOnceAsTheirLatestRegistrationNewestActivityFirst()
    {
        var rows = await PageAsync();

        Assert.Equal(
            new[]
            {
                ("Sam Roy", "LOGGED_IN_ONLY"),
                ("Ravi Iyer", "REGISTRATION_STARTED"),
                ("Asha Rao", "REGISTERED"),
            },
            rows.Select(row => (row.Name, row.Status)).ToArray()
        );
    }

    [Fact]
    public async Task TheApplicationCannotReadRegistrationsDirectly()
    {
        await using var connection = new NpgsqlConnection(RuntimeConnectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            "SELECT count(*) FROM identity.registrations",
            connection
        );

        var failure = await Assert.ThrowsAsync<PostgresException>(() =>
            command.ExecuteScalarAsync()
        );

        Assert.Equal("42501", failure.SqlState);
    }

    [Fact]
    public async Task NameStatusAndContactFiltersNarrowThePage()
    {
        Assert.Equal(["Ravi Iyer"], (await PageAsync(name: "rav")).Select(row => row.Name));
        Assert.Equal(["Asha Rao"], (await PageAsync(status: "REGISTERED")).Select(row => row.Name));
        Assert.Equal(
            ["Asha Rao"],
            (await PageAsync(domains: ["email"], versions: ["v1"], digests: [Digest])).Select(row =>
                row.Name
            )
        );
        Assert.Empty(await PageAsync(domains: ["email"], versions: ["v2"], digests: [Digest]));
    }

    [Fact]
    public async Task KeysetPagingWalksThePagesWithoutRepeatingOrSkipping()
    {
        var first = await PageAsync(limit: 2);
        var last = first[^1];
        var second = await PageAsync(afterAt: last.LastActive, afterId: last.Id, limit: 2);

        Assert.Equal(["Sam Roy", "Ravi Iyer"], first.Select(row => row.Name));
        Assert.Equal(["Asha Rao"], second.Select(row => row.Name));
    }

    [Fact]
    public async Task AMalformedFilterIsRefusedBeforeAnyRowIsRead()
    {
        var failure = await Assert.ThrowsAsync<PostgresException>(() =>
            PageAsync(status: "EVERYONE")
        );
        Assert.Equal("22023", failure.SqlState);
        failure = await Assert.ThrowsAsync<PostgresException>(() =>
            PageAsync(domains: ["email"], versions: ["v1"], digests: ["not-a-digest"])
        );
        Assert.Equal("22023", failure.SqlState);
    }

    private CustomerDirectoryService Service(out IdentityService identity)
    {
        var options = new DbContextOptionsBuilder<IdentityDbContext>()
            .UseNpgsql(RuntimeConnectionString)
            .Options;
        var factory = new PooledDbContextFactory<IdentityDbContext>(options);
        identity = new IdentityService(
            factory,
            Options.Create(
                new IdentityHmacOptions { Key = new string('k', 64), ActiveVersion = "v1" }
            ),
            Mock.Of<IIdentityVerificationDispatcher>()
        );
        return new CustomerDirectoryService(identity, factory);
    }

    [Fact]
    public async Task TheServiceReadsPagesByCursorAndNeverReturnsAKeyOrARawContact()
    {
        var service = Service(out _);

        var first = await service.ListAsync(null, null, null, null, 2, default);
        var second = await service.ListAsync(null, null, null, first.NextCursor, 2, default);

        Assert.Equal(["Sam Roy", "Ravi Iyer"], first.Items.Select(item => item.DisplayName));
        Assert.NotNull(first.NextCursor);
        Assert.Equal(["Asha Rao"], second.Items.Select(item => item.DisplayName));
        Assert.Null(second.NextCursor);
        var asha = second.Items.Single();
        Assert.Equal("a***@x.com", asha.MaskedEmail);
        Assert.Equal(CustomerStatuses.Registered, asha.Status);
        Assert.NotNull(asha.RegisteredAt);
        Assert.Equal(10, CustomerDirectoryService.DefaultPageSize);
    }

    [Fact]
    public async Task TheServiceFindsAPersonByExactEmailOrMobileWithoutStoringOrReturningIt()
    {
        var service = Service(out var identity);
        var email = identity.ComputeMatchCandidates("email", "kiran@example.com").Single();
        var mobile = identity.ComputeMatchCandidates("mobile", "+919876543210").Single();
        await ExecuteAsAdminAsync(
            $"""
            INSERT INTO identity.registrations
                (actor_issuer, actor_subject, state, display_name, masked_email, masked_mobile,
                 email_hmac_domain, email_hmac_version, email_hmac_key,
                 mobile_hmac_domain, mobile_hmac_version, mobile_hmac_key, created_at, updated_at)
            VALUES ('iss', 'kiran', 'Started', 'Kiran Nair', 'k***@example.com', '+91*****210',
                    'email', '{email.Key}', '{email.Value}',
                    'mobile', '{mobile.Key}', '{mobile.Value}', now(), now())
            """
        );

        var byEmail = await service.ListAsync(
            null,
            "Kiran@Example.com ",
            null,
            null,
            null,
            default
        );
        var byMobile = await service.ListAsync(null, "+91 98765 43210", null, null, null, default);
        var unknown = await service.ListAsync(
            null,
            "nobody@example.com",
            null,
            null,
            null,
            default
        );

        Assert.Equal("Kiran Nair", Assert.Single(byEmail.Items).DisplayName);
        Assert.Equal("Kiran Nair", Assert.Single(byMobile.Items).DisplayName);
        Assert.Equal(CustomerStatuses.LoggedInOnly, byMobile.Items[0].Status);
        Assert.Empty(unknown.Items);
    }

    [Fact]
    public async Task TheServiceFiltersByNameAndStatusAndTreatsLikeSymbolsAsText()
    {
        var service = Service(out _);

        Assert.Equal(
            ["Ravi Iyer"],
            (await service.ListAsync("RAV", null, null, null, null, default)).Items.Select(item =>
                item.DisplayName
            )
        );
        Assert.Equal(
            ["Asha Rao"],
            (
                await service.ListAsync(
                    null,
                    null,
                    CustomerStatuses.Registered,
                    null,
                    null,
                    default
                )
            ).Items.Select(item => item.DisplayName)
        );
        Assert.Empty((await service.ListAsync("%", null, null, null, null, default)).Items);
    }

    [Fact]
    public async Task TheServiceRefusesABadStatusAForgedCursorAndAContactThatCannotMatchAnything()
    {
        var service = Service(out _);

        await Assert.ThrowsAsync<CustomerDirectoryFilterException>(() =>
            service.ListAsync(null, null, "EVERYONE", null, null, default)
        );
        await Assert.ThrowsAsync<CustomerDirectoryFilterException>(() =>
            service.ListAsync(null, null, null, "forged", null, default)
        );
        await Assert.ThrowsAsync<CustomerDirectoryFilterException>(() =>
            service.ListAsync(new string('x', 121), null, null, null, null, default)
        );
        Assert.Empty(
            (await service.ListAsync(null, "not a contact", null, null, null, default)).Items
        );
    }
}
