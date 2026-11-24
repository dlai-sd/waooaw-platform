// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R013
// constitutional_basis: C-009, C-023, C-063, C-065

using Microsoft.EntityFrameworkCore;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>
/// Applies the real acquisition_intents init file and the WC-169 quote file, then proves with the application role that
/// the quote is stored whole or not at all, belongs only to a Hire, can never change afterwards, and is never deleted.
/// </summary>
public sealed class AcquisitionHireQuotePostgresTests : IAsyncLifetime
{
    private const string BaseTable =
        "infrastructure/postgres/init/49-wc112-acquisition-intents.sql";
    private const string QuoteMigration =
        "infrastructure/postgres/init/99zzzzzzzz-wc169-02-acquisition-hire-quote.sql";

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("hire_quote")
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
            CREATE ROLE bp_owner NOLOGIN;
            CREATE ROLE bp_runtime LOGIN PASSWORD 'synthetic-runtime-password' IN ROLE business_app;
            GRANT bp_owner TO test_owner;
            CREATE SCHEMA business AUTHORIZATION bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            """
        );
        await ExecuteAsAdminAsync(
            "SET ROLE bp_owner;\n"
                + await File.ReadAllTextAsync(RepositoryPaths.Resolve(BaseTable))
                + "\nRESET ROLE;"
        );
        // Idempotent: applying the file twice must leave the same schema.
        await ExecuteAsAdminAsync(
            await File.ReadAllTextAsync(RepositoryPaths.Resolve(QuoteMigration))
        );
        await ExecuteAsAdminAsync(
            await File.ReadAllTextAsync(RepositoryPaths.Resolve(QuoteMigration))
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

    private async Task<string?> RuntimeSqlStateAsync(string sql)
    {
        try
        {
            await using var connection = new NpgsqlConnection(RuntimeConnectionString);
            await connection.OpenAsync();
            await using var command = new NpgsqlCommand(sql, connection);
            await command.ExecuteNonQueryAsync();
            return null;
        }
        catch (PostgresException failure)
        {
            return failure.SqlState;
        }
    }

    private static string InsertIntent(
        Guid id,
        string mode,
        string quoteColumns,
        string quoteValues
    ) =>
        $"""
            INSERT INTO business.acquisition_intents (
                acquisition_intent_id, actor_identity_hash, idempotency_key, professional_type, professional_version, mode,
                disclosure_revision, contract_version, contract_document_uri, contract_hash, material_request_hash, status,
                contract_accepted_at, expires_at {quoteColumns})
            VALUES ('{id}', '{new string(
                'a',
                64
            )}', '{id}', 'DMA', '1.0.0', '{mode}', '1.0.0', '2026-07-18', '/c',
                '{new string('b', 64)}', '{new string(
                'c',
                64
            )}', 'READY_TO_COMPLETE', now(), now() + interval '1 hour' {quoteValues})
            """;

    private static readonly string FullQuoteColumns =
        ", quote_package_id, quote_package_code, quote_period_days, quote_gross_inr_paise, quote_gst_inr_paise, quote_base_inr_paise, quote_version";

    private static string FullQuoteValues(long gross = 118000) =>
        $", '{Guid.NewGuid()}', 'STARTER', 30, {gross}, 18000, 100000, '{new string('d', 64)}'";

    [Fact]
    public async Task WC169_R013_AHireStoresItsWholeQuoteAndTheEntityMapsTheColumns()
    {
        var id = Guid.NewGuid();
        Assert.Null(
            await RuntimeSqlStateAsync(
                InsertIntent(id, "HIRE", FullQuoteColumns, FullQuoteValues())
            )
        );
        var options = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(RuntimeConnectionString)
            .Options;

        await using var db = new EmploymentRelationshipDbContext(options);
        var stored = await db
            .AcquisitionIntents.AsNoTracking()
            .SingleAsync(item => item.AcquisitionIntentId == id);

        var quote = Assert.IsType<HireQuote>(stored.ToQuote());
        Assert.Equal("STARTER", quote.PackageCode);
        Assert.Equal(118000, quote.GrossAmountInrPaise);
        Assert.Equal(18000, quote.GstAmountInrPaise);
        Assert.Equal(30, quote.BillingPeriodDays);
    }

    [Fact]
    public async Task WC169_R013_TheEntityInsertsAHireQuoteThroughTheApplicationRole()
    {
        var options = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(RuntimeConnectionString)
            .Options;
        var id = Guid.NewGuid();
        await using (var db = new EmploymentRelationshipDbContext(options))
        {
            db.AcquisitionIntents.Add(
                new AcquisitionIntent
                {
                    AcquisitionIntentId = id,
                    ActorIdentityHash = new string('e', 64),
                    IdempotencyKey = id,
                    ProfessionalType = "DMA",
                    ProfessionalVersion = "1.0.0",
                    Mode = "HIRE",
                    DisclosureRevision = "1.0.0",
                    ContractVersion = "2026-07-18",
                    ContractDocumentUri = "/c",
                    ContractHash = new string('b', 64),
                    MaterialRequestHash = new string('c', 64),
                    Status = "READY_TO_COMPLETE",
                    QuotePackageId = Guid.NewGuid(),
                    QuotePackageCode = "STARTER",
                    QuotePeriodDays = 30,
                    QuoteGrossInrPaise = 118000,
                    QuoteGstInrPaise = 18000,
                    QuoteBaseInrPaise = 100000,
                    QuoteVersion = new string('f', 64),
                    ContractAcceptedAt = DateTimeOffset.UtcNow,
                    ExpiresAt = DateTimeOffset.UtcNow.AddHours(1),
                }
            );
            await db.SaveChangesAsync();
        }

        await using var read = new EmploymentRelationshipDbContext(options);
        var stored = await read
            .AcquisitionIntents.AsNoTracking()
            .SingleAsync(item => item.AcquisitionIntentId == id);
        Assert.Equal(118000, stored.ToQuote()!.GrossAmountInrPaise);
    }

    [Fact]
    public async Task WC169_R013_AQuoteIsWholeAndOnlyForAHire()
    {
        // A Trial has no price.
        Assert.Equal(
            "23514",
            await RuntimeSqlStateAsync(
                InsertIntent(Guid.NewGuid(), "TRIAL", FullQuoteColumns, FullQuoteValues())
            )
        );
        // A partial quote is refused.
        Assert.Equal(
            "23514",
            await RuntimeSqlStateAsync(
                InsertIntent(Guid.NewGuid(), "HIRE", ", quote_gross_inr_paise", ", 118000")
            )
        );
        // A zero or GST-above-gross quote is refused.
        Assert.Equal(
            "23514",
            await RuntimeSqlStateAsync(
                InsertIntent(Guid.NewGuid(), "HIRE", FullQuoteColumns, FullQuoteValues(0))
            )
        );
        // A row without a quote (a Trial, or a row from before quotes) stays valid.
        Assert.Null(await RuntimeSqlStateAsync(InsertIntent(Guid.NewGuid(), "TRIAL", "", "")));
    }

    [Fact]
    public async Task WC169_R013_TheQuoteNeverChangesAndNothingIsDeleted()
    {
        var id = Guid.NewGuid();
        Assert.Null(
            await RuntimeSqlStateAsync(
                InsertIntent(id, "HIRE", FullQuoteColumns, FullQuoteValues())
            )
        );

        Assert.Equal(
            "23514",
            await RuntimeSqlStateAsync(
                $"UPDATE business.acquisition_intents SET quote_gross_inr_paise = 100, quote_gst_inr_paise = 15 WHERE acquisition_intent_id = '{id}'"
            )
        );
        Assert.Equal(
            "23514",
            await RuntimeSqlStateAsync(
                $"UPDATE business.acquisition_intents SET quote_version = NULL, quote_package_id = NULL, quote_package_code = NULL, quote_period_days = NULL, quote_gross_inr_paise = NULL, quote_gst_inr_paise = NULL, quote_base_inr_paise = NULL WHERE acquisition_intent_id = '{id}'"
            )
        );
        // The ordinary lifecycle update the application already performs still works.
        Assert.Null(
            await RuntimeSqlStateAsync(
                $"UPDATE business.acquisition_intents SET status = 'COMPLETING', updated_at = now() WHERE acquisition_intent_id = '{id}'"
            )
        );
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                $"DELETE FROM business.acquisition_intents WHERE acquisition_intent_id = '{id}'"
            )
        );
    }
}
