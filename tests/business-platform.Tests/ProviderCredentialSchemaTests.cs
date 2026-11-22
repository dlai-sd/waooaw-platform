// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R001
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using FluentAssertions;
using Npgsql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ProviderCredentialSchemaTests
{
    private static string Insert(Guid provider, int versionNo, string status) =>
        $"""
            INSERT INTO business.provider_credential_versions
                (provider_config_id, version_no, vault_secret_name, vault_secret_version, status, test_outcome, created_by_subject)
            VALUES ('{provider}', {versionNo}, 'provider-openai', 'a1b2c3d4e5f60718293a4b5c6d7e8f90', '{status}', 'PASSED', 'founder-1')
            """;

    private static Task<Guid> ProviderIdAsync(
        ProviderRegistryDatabase db,
        string name = "openai"
    ) =>
        db.ScalarAsync<Guid>(
            $"SELECT id FROM business.provider_configs WHERE provider_name = '{name}' AND tenant_id IS NULL"
        );

    [Fact]
    public async Task SeedsAreFourPlatformRowsWithTestSettingsAndNoCredential()
    {
        await using var db = await ProviderRegistryDatabase.CreateAsync();

        var rows =
            new List<(
                string Name,
                string Category,
                string? Url,
                string? Scheme,
                bool HasCredential
            )>();
        await using (var connection = new NpgsqlConnection(db.ConnectionString))
        {
            await connection.OpenAsync();
            await using var command = new NpgsqlCommand(
                """
                SELECT provider_name, category, test_url, test_auth_scheme, active_credential_version_id IS NOT NULL
                FROM business.provider_configs
                WHERE tenant_id IS NULL AND auth_method = 'API_KEY'
                ORDER BY provider_name
                """,
                connection
            );
            await using var reader = await command.ExecuteReaderAsync();
            while (await reader.ReadAsync())
                rows.Add(
                    (
                        reader.GetString(0),
                        reader.GetString(1),
                        reader.IsDBNull(2) ? null : reader.GetString(2),
                        reader.IsDBNull(3) ? null : reader.GetString(3),
                        reader.GetBoolean(4)
                    )
                );
        }

        rows.Should()
            .Equal(
                (
                    "anthropic",
                    "PLATFORM_LLM",
                    "https://api.anthropic.com/v1/models",
                    "X_API_KEY",
                    false
                ),
                (
                    "google",
                    "PLATFORM_LLM",
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    "X_GOOG_API_KEY",
                    false
                ),
                ("openai", "PLATFORM_LLM", "https://api.openai.com/v1/models", "BEARER", false),
                (
                    "sarvam",
                    "PLATFORM_LLM",
                    "https://api.sarvam.ai/v1/chat/completions",
                    "SUBSCRIPTION_KEY",
                    false
                )
            );
        (await db.ScalarAsync<long>("SELECT count(*) FROM business.provider_credential_versions"))
            .Should()
            .Be(0);
    }

    [Fact]
    public async Task ReapplyingTheInitFileKeepsRowsAndRecordedVersions()
    {
        await using var db = await ProviderRegistryDatabase.CreateAsync();
        var openai = await ProviderIdAsync(db);
        await db.ExecuteAsync(Insert(openai, 1, "ACTIVE"));

        await db.ApplyAsync(ProviderRegistryDatabase.CredentialsInit);
        await db.ApplyAsync(ProviderRegistryDatabase.ConnectionsInit);
        await db.ApplyAsync(ProviderRegistryDatabase.RegistryInit);
        await db.ApplyAsync(ProviderRegistryDatabase.CredentialsInit);
        await db.ApplyAsync(ProviderRegistryDatabase.ConnectionsInit);

        (
            await db.ScalarAsync<long>(
                "SELECT count(*) FROM business.provider_configs WHERE tenant_id IS NULL AND provider_name IN ('openai','anthropic','google','sarvam')"
            )
        )
            .Should()
            .Be(4);
        (await db.ScalarAsync<long>("SELECT count(*) FROM business.provider_credential_versions"))
            .Should()
            .Be(1);
    }

    [Fact]
    public async Task AProviderCanHaveAtMostOneActiveVersion()
    {
        await using var db = await ProviderRegistryDatabase.CreateAsync();
        var openai = await ProviderIdAsync(db);
        var anthropic = await ProviderIdAsync(db, "anthropic");
        await db.ExecuteAsync(Insert(openai, 1, "ACTIVE"));
        await db.ExecuteAsync(Insert(openai, 2, "SUPERSEDED"));
        await db.ExecuteAsync(Insert(openai, 3, "SUPERSEDED"));
        await db.ExecuteAsync(Insert(anthropic, 1, "ACTIVE"));

        var second = async () => await db.ExecuteAsync(Insert(openai, 4, "ACTIVE"));

        (await second.Should().ThrowAsync<PostgresException>()).Which.SqlState.Should().Be("23505");
    }

    [Fact]
    public async Task VersionNumbersAreUniquePerProvider()
    {
        await using var db = await ProviderRegistryDatabase.CreateAsync();
        var openai = await ProviderIdAsync(db);
        await db.ExecuteAsync(Insert(openai, 1, "SUPERSEDED"));

        var duplicate = async () => await db.ExecuteAsync(Insert(openai, 1, "SUPERSEDED"));

        (await duplicate.Should().ThrowAsync<PostgresException>())
            .Which.SqlState.Should()
            .Be("23505");
    }

    [Fact]
    public async Task ARecordedVersionOnlyChangesStatusAndIsNeverDeleted()
    {
        await using var db = await ProviderRegistryDatabase.CreateAsync();
        var openai = await ProviderIdAsync(db);
        await db.ExecuteAsync(Insert(openai, 1, "ACTIVE"));

        await db.ExecuteAsync(
            "UPDATE business.provider_credential_versions SET status = 'SUPERSEDED', activated_at = now()"
        );
        var rewrite = async () =>
            await db.ExecuteAsync(
                "UPDATE business.provider_credential_versions SET vault_secret_version = 'ffffffffffffffffffffffffffffffff'"
            );
        var delete = async () =>
            await db.ExecuteAsync("DELETE FROM business.provider_credential_versions");

        (await rewrite.Should().ThrowAsync<PostgresException>())
            .Which.SqlState.Should()
            .Be("23514");
        (await delete.Should().ThrowAsync<PostgresException>()).Which.SqlState.Should().Be("23514");
    }

    [Fact]
    public async Task TheVersionTableHasNoColumnThatCanHoldASecretValue()
    {
        await using var db = await ProviderRegistryDatabase.CreateAsync();

        var columns = await db.ScalarAsync<string>(
            "SELECT string_agg(column_name, ',' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema = 'business' AND table_name = 'provider_credential_versions'"
        );

        columns
            .Should()
            .Be(
                "id,provider_config_id,version_no,vault_secret_name,vault_secret_version,status,test_outcome,created_by_subject,created_at,activated_at"
            );
    }

    [Theory]
    [InlineData("category = 'OTHER'")]
    [InlineData("test_auth_scheme = 'BASIC'")]
    [InlineData("test_url = 'http://api.example.com/ping'")]
    public async Task RegistrySettingsAreConstrained(string assignment)
    {
        await using var db = await ProviderRegistryDatabase.CreateAsync();

        var update = async () =>
            await db.ExecuteAsync(
                $"UPDATE business.provider_configs SET {assignment} WHERE provider_name = 'sarvam'"
            );

        (await update.Should().ThrowAsync<PostgresException>()).Which.SqlState.Should().Be("23514");
    }

    [Fact]
    public async Task ActiveVersionPointerMustReferenceARecordedVersion()
    {
        await using var db = await ProviderRegistryDatabase.CreateAsync();

        var update = async () =>
            await db.ExecuteAsync(
                $"UPDATE business.provider_configs SET active_credential_version_id = '{Guid.NewGuid()}' WHERE provider_name = 'openai'"
            );

        (await update.Should().ThrowAsync<PostgresException>()).Which.SqlState.Should().Be("23503");
    }
}
