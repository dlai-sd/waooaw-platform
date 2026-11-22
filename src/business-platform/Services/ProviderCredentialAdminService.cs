// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R001, WC148-R003, WC148-R004
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class ProviderAdminException(
    int status,
    string code,
    string detail,
    IReadOnlyDictionary<string, object?>? extras = null
) : Exception(detail)
{
    public int Status { get; } = status;
    public string Code { get; } = code;
    public IReadOnlyDictionary<string, object?> Extras { get; } =
        extras ?? new Dictionary<string, object?>();
}

public sealed record ProviderCredentialSummary(
    string Status,
    int? ActiveVersionNo,
    DateTimeOffset? ActivatedAt,
    string? LastTestOutcome
);

public sealed record ProviderSummary(
    Guid Id,
    string ProviderName,
    string DisplayName,
    string? Category,
    string? AgentTypeId,
    string AuthMethod,
    bool HasTestEndpoint,
    bool Active,
    ProviderCredentialSummary Credential
);

public sealed record CreateProviderRequest(
    string? ProviderName,
    string? DisplayName,
    string? Category,
    string? AgentTypeId,
    string? TestUrl,
    string? TestAuthScheme,
    string? TestAuthHeader
);

public sealed record ProviderCredentialVersionSummary(
    Guid VersionId,
    int VersionNo,
    string Status,
    DateTimeOffset CreatedAt,
    DateTimeOffset? ActivatedAt,
    string TestOutcome
);

public sealed record ProviderCredentialSaved(Guid VersionId, int VersionNo, string Status);

/// <summary>Request body carrying a credential value. ToString is redacted so the value cannot reach a log through it.</summary>
public sealed record ProviderCredentialTestRequest(string? Value)
{
    public override string ToString() => "ProviderCredentialTestRequest { Value = [redacted] }";
}

/// <summary>Request body carrying a credential value. ToString is redacted so the value cannot reach a log through it.</summary>
public sealed record ProviderCredentialConfirmRequest(string? Value, bool AcknowledgeUntested)
{
    public override string ToString() =>
        $"ProviderCredentialConfirmRequest {{ Value = [redacted], AcknowledgeUntested = {AcknowledgeUntested} }}";
}

public interface IProviderCredentialAdminService
{
    Task<IReadOnlyList<ProviderSummary>> ListAsync(CancellationToken ct);

    Task<ProviderSummary> CreateAsync(CreateProviderRequest request, CancellationToken ct);

    Task<IReadOnlyList<ProviderCredentialVersionSummary>> ListVersionsAsync(
        Guid providerId,
        CancellationToken ct
    );

    Task<ProviderCredentialTestResult> TestAsync(
        Guid providerId,
        string? value,
        CancellationToken ct
    );

    Task<ProviderCredentialSaved> ConfirmAsync(
        Guid providerId,
        string? value,
        bool acknowledgeUntested,
        string actorSubject,
        CancellationToken ct
    );

    Task<ProviderCredentialSaved> ActivateAsync(
        Guid providerId,
        Guid versionId,
        CancellationToken ct
    );
}

public sealed partial class ProviderCredentialAdminService(
    IDbContextFactory<ProviderRegistryDbContext> dbFactory,
    IProviderSecretStore secrets,
    IProviderCredentialTester tester,
    TimeProvider clock,
    ILogger<ProviderCredentialAdminService> logger
) : IProviderCredentialAdminService
{
    public const int MaximumValueLength = 16_384;
    private static readonly string[] Categories = ["PLATFORM_LLM", "AGENT_API"];
    private static readonly HashSet<string> ForbiddenHeaders = new(StringComparer.OrdinalIgnoreCase)
    {
        "host",
        "content-length",
        "transfer-encoding",
        "connection",
        "upgrade",
        "te",
        "trailer",
        "expect",
    };

    [GeneratedRegex("^[A-Za-z0-9-]{1,64}$")]
    private static partial Regex HeaderNamePattern();

    [GeneratedRegex("^[A-Za-z0-9._-]{1,64}$")]
    private static partial Regex AgentTypePattern();

    public async Task<IReadOnlyList<ProviderSummary>> ListAsync(CancellationToken ct)
    {
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        var providers = await db
            .ProviderConfigs.AsNoTracking()
            .Where(p => p.TenantId == null && p.AuthMethod == "API_KEY")
            .OrderBy(p => p.Category)
            .ThenBy(p => p.ProviderName)
            .ToListAsync(ct);
        var activeIds = providers
            .Where(p => p.ActiveCredentialVersionId.HasValue)
            .Select(p => p.ActiveCredentialVersionId!.Value)
            .ToList();
        var versions = await db
            .ProviderCredentialVersions.AsNoTracking()
            .Where(v => activeIds.Contains(v.Id))
            .ToListAsync(ct);
        return providers
            .Select(p =>
                Summarize(p, versions.FirstOrDefault(v => v.Id == p.ActiveCredentialVersionId))
            )
            .ToList();
    }

    public async Task<ProviderSummary> CreateAsync(
        CreateProviderRequest request,
        CancellationToken ct
    )
    {
        var config = Validate(request);
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        if (
            await db.ProviderConfigs.AnyAsync(
                p => p.TenantId == null && p.ProviderName == config.ProviderName,
                ct
            )
        )
            throw new ProviderAdminException(
                409,
                "PROVIDER_CONFLICT",
                "A provider with this name already exists."
            );
        db.ProviderConfigs.Add(config);
        try
        {
            await db.SaveChangesAsync(ct);
        }
        catch (DbUpdateException exception)
            when (exception.InnerException is PostgresException { SqlState: "23505" })
        {
            throw new ProviderAdminException(
                409,
                "PROVIDER_CONFLICT",
                "A provider with this name already exists."
            );
        }
        logger.LogInformation(
            "Provider registered: provider={ProviderName} category={Category}",
            config.ProviderName,
            config.Category
        );
        return Summarize(config, null);
    }

    public async Task<IReadOnlyList<ProviderCredentialVersionSummary>> ListVersionsAsync(
        Guid providerId,
        CancellationToken ct
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        await FindAsync(db, providerId, ct);
        return (
            await db
                .ProviderCredentialVersions.AsNoTracking()
                .Where(v => v.ProviderConfigId == providerId)
                .OrderByDescending(v => v.VersionNo)
                .ToListAsync(ct)
        )
            .Select(Summarize)
            .ToList();
    }

    public async Task<ProviderCredentialTestResult> TestAsync(
        Guid providerId,
        string? value,
        CancellationToken ct
    )
    {
        var normalized = NormalizeValue(value);
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        var provider = await FindAsync(db, providerId, ct);
        var result = await tester.TestAsync(TargetOf(provider), normalized, ct);
        logger.LogInformation(
            "Provider credential tested: provider={ProviderName} outcome={Outcome}",
            provider.ProviderName,
            result.Outcome
        );
        return result;
    }

    public async Task<ProviderCredentialSaved> ConfirmAsync(
        Guid providerId,
        string? value,
        bool acknowledgeUntested,
        string actorSubject,
        CancellationToken ct
    )
    {
        var normalized = NormalizeValue(value);
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        var provider = await FindAsync(db, providerId, ct);
        if (!ProviderSecretNames.IsValidProviderName(provider.ProviderName))
            throw new ProviderAdminException(
                400,
                "PROVIDER_INVALID",
                "The provider name cannot be used as a vault secret name."
            );

        var test = await tester.TestAsync(TargetOf(provider), normalized, ct);
        if (test.Outcome == ProviderTestOutcomes.Failed)
            throw Rejected("The provider did not accept the credential. Nothing was saved.", test);
        if (test.Outcome == ProviderTestOutcomes.NotTestable && !acknowledgeUntested)
            throw Rejected(
                "This provider has no test endpoint. Set acknowledgeUntested to save it untested.",
                test
            );

        string secretVersion;
        var secretName = ProviderSecretNames.For(provider.ProviderName);
        try
        {
            secretVersion = await secrets.SetSecretAsync(secretName, normalized, ct);
        }
        catch (ProviderSecretStoreException exception)
        {
            logger.LogWarning(
                "Provider credential vault write failed: provider={ProviderName} reason={Reason}",
                provider.ProviderName,
                exception.Message
            );
            throw VaultUnavailable();
        }

        try
        {
            var saved = await RecordVersionAsync(
                db,
                providerId,
                secretName,
                secretVersion,
                test.Outcome,
                actorSubject,
                ct
            );
            logger.LogInformation(
                "Provider credential saved: provider={ProviderName} versionNo={VersionNo} outcome={Outcome}",
                provider.ProviderName,
                saved.VersionNo,
                test.Outcome
            );
            return saved;
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogError(
                "Provider credential vault write succeeded but recording failed: provider={ProviderName} error={ErrorType}",
                provider.ProviderName,
                exception.GetType().Name
            );
            throw new ProviderAdminException(
                500,
                "PROVIDER_PERSISTENCE_FAILED",
                "The credential reached the vault but could not be recorded. The previous version is still active. Try again."
            );
        }
    }

    public async Task<ProviderCredentialSaved> ActivateAsync(
        Guid providerId,
        Guid versionId,
        CancellationToken ct
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var provider = await LockAsync(db, providerId, ct);
        var target = await db.ProviderCredentialVersions.SingleOrDefaultAsync(
            v => v.Id == versionId && v.ProviderConfigId == providerId,
            ct
        );
        if (target is null)
            throw new ProviderAdminException(
                404,
                "PROVIDER_NOT_FOUND",
                "The credential version was not found."
            );
        if (target.Status != ProviderCredentialStatuses.Active)
        {
            await SupersedeActiveAsync(db, providerId, ct);
            target.Status = ProviderCredentialStatuses.Active;
            target.ActivatedAt = clock.GetUtcNow();
            await db.SaveChangesAsync(ct);
        }
        provider.ActiveCredentialVersionId = target.Id;
        await db.SaveChangesAsync(ct);
        await transaction.CommitAsync(ct);
        logger.LogInformation(
            "Provider credential version activated: provider={ProviderName} versionNo={VersionNo}",
            provider.ProviderName,
            target.VersionNo
        );
        return new(target.Id, target.VersionNo, target.Status);
    }

    private async Task<ProviderCredentialSaved> RecordVersionAsync(
        ProviderRegistryDbContext db,
        Guid providerId,
        string secretName,
        string secretVersion,
        string testOutcome,
        string actorSubject,
        CancellationToken ct
    )
    {
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var provider = await LockAsync(db, providerId, ct);
        var next =
            (
                await db
                    .ProviderCredentialVersions.Where(v => v.ProviderConfigId == providerId)
                    .MaxAsync(v => (int?)v.VersionNo, ct)
                ?? 0
            ) + 1;
        await SupersedeActiveAsync(db, providerId, ct);
        var now = clock.GetUtcNow();
        var version = new ProviderCredentialVersion
        {
            ProviderConfigId = providerId,
            VersionNo = next,
            VaultSecretName = secretName,
            VaultSecretVersion = secretVersion,
            Status = ProviderCredentialStatuses.Active,
            TestOutcome = testOutcome,
            CreatedBySubject = actorSubject,
            CreatedAt = now,
            ActivatedAt = now,
        };
        db.ProviderCredentialVersions.Add(version);
        await db.SaveChangesAsync(ct);
        provider.ActiveCredentialVersionId = version.Id;
        await db.SaveChangesAsync(ct);
        await transaction.CommitAsync(ct);
        return new(version.Id, version.VersionNo, version.Status);
    }

    private static async Task SupersedeActiveAsync(
        ProviderRegistryDbContext db,
        Guid providerId,
        CancellationToken ct
    )
    {
        var current = await db
            .ProviderCredentialVersions.Where(v =>
                v.ProviderConfigId == providerId && v.Status == ProviderCredentialStatuses.Active
            )
            .ToListAsync(ct);
        foreach (var version in current)
            version.Status = ProviderCredentialStatuses.Superseded;
        if (current.Count > 0)
            await db.SaveChangesAsync(ct);
    }

    private static async Task<ProviderConfig> FindAsync(
        ProviderRegistryDbContext db,
        Guid providerId,
        CancellationToken ct
    ) =>
        await db.ProviderConfigs.SingleOrDefaultAsync(
            p => p.Id == providerId && p.TenantId == null && p.AuthMethod == "API_KEY",
            ct
        ) ?? throw NotFound();

    private static async Task<ProviderConfig> LockAsync(
        ProviderRegistryDbContext db,
        Guid providerId,
        CancellationToken ct
    ) =>
        await db
            .ProviderConfigs.FromSql(
                $"SELECT * FROM business.provider_configs WHERE id = {providerId} AND tenant_id IS NULL AND auth_method = 'API_KEY' FOR UPDATE"
            )
            .SingleOrDefaultAsync(ct)
        ?? throw NotFound();

    private static ProviderAdminException NotFound() =>
        new(404, "PROVIDER_NOT_FOUND", "The provider was not found.");

    private static ProviderAdminException VaultUnavailable() =>
        new(
            503,
            "PROVIDER_VAULT_UNAVAILABLE",
            "The credential vault is unavailable. Nothing was saved."
        );

    private static ProviderAdminException Rejected(
        string detail,
        ProviderCredentialTestResult test
    ) =>
        new(
            422,
            "PROVIDER_INVALID",
            detail,
            new Dictionary<string, object?>
            {
                ["testOutcome"] = test.Outcome,
                ["testDetail"] = test.Detail,
            }
        );

    private static ProviderTestTarget TargetOf(ProviderConfig provider) =>
        new(
            provider.ProviderName,
            provider.TestUrl,
            provider.TestAuthScheme,
            provider.TestAuthHeader
        );

    private static string NormalizeValue(string? value)
    {
        var normalized = value?.Trim() ?? string.Empty;
        if (normalized.Length is 0 or > MaximumValueLength)
            throw Invalid($"The credential value must be 1 to {MaximumValueLength} characters.");
        if (normalized.Any(char.IsControl))
            throw Invalid(
                "The credential value must not contain line breaks or control characters."
            );
        return normalized;
    }

    private static ProviderAdminException Invalid(string detail) =>
        new(400, "PROVIDER_INVALID", detail);

    private static ProviderConfig Validate(CreateProviderRequest request)
    {
        var name = request.ProviderName?.Trim();
        if (!ProviderSecretNames.IsValidProviderName(name))
            throw Invalid("providerName must be 2 to 48 lowercase letters, digits or hyphens.");
        var displayName = request.DisplayName?.Trim();
        if (string.IsNullOrEmpty(displayName) || displayName.Length > 80)
            throw Invalid("displayName must be 1 to 80 characters.");
        if (request.Category is null || !Categories.Contains(request.Category))
            throw Invalid("category must be PLATFORM_LLM or AGENT_API.");
        var agentTypeId = string.IsNullOrWhiteSpace(request.AgentTypeId)
            ? null
            : request.AgentTypeId.Trim();
        if (
            agentTypeId is not null
            && (request.Category != "AGENT_API" || !AgentTypePattern().IsMatch(agentTypeId))
        )
            throw Invalid(
                "agentTypeId applies only to AGENT_API providers and must be a short identifier."
            );

        var testUrl = string.IsNullOrWhiteSpace(request.TestUrl) ? null : request.TestUrl.Trim();
        var scheme = string.IsNullOrWhiteSpace(request.TestAuthScheme)
            ? null
            : request.TestAuthScheme.Trim();
        var header = string.IsNullOrWhiteSpace(request.TestAuthHeader)
            ? null
            : request.TestAuthHeader.Trim();
        if (testUrl is null)
        {
            if (scheme is not null || header is not null)
                throw Invalid("testAuthScheme and testAuthHeader need a testUrl.");
        }
        else
        {
            if (
                testUrl.Length > 512
                || !Uri.TryCreate(testUrl, UriKind.Absolute, out var uri)
                || uri.Scheme != Uri.UriSchemeHttps
                || uri.Port != 443
                || uri.HostNameType != UriHostNameType.Dns
                || !string.IsNullOrEmpty(uri.UserInfo)
                || !string.IsNullOrEmpty(uri.Fragment)
            )
                throw Invalid("testUrl must be an https URL for a named host.");
            if (scheme is null || !ProviderAuthSchemes.All.Contains(scheme))
                throw Invalid(
                    "testAuthScheme must be BEARER, X_API_KEY, X_GOOG_API_KEY or HEADER."
                );
            if (scheme == ProviderAuthSchemes.Header)
            {
                if (
                    header is null
                    || !HeaderNamePattern().IsMatch(header)
                    || ForbiddenHeaders.Contains(header)
                )
                    throw Invalid(
                        "testAuthHeader must be a valid header name when testAuthScheme is HEADER."
                    );
            }
            else if (header is not null)
                throw Invalid("testAuthHeader applies only when testAuthScheme is HEADER.");
        }

        return new ProviderConfig
        {
            ProviderName = name!,
            AuthMethod = "API_KEY",
            VaultPathKey = $"providers/platform/{name}",
            DisplayName = displayName,
            Category = request.Category,
            AgentTypeId = agentTypeId,
            TestUrl = testUrl,
            TestAuthScheme = scheme,
            TestAuthHeader = header,
        };
    }

    private static ProviderSummary Summarize(
        ProviderConfig provider,
        ProviderCredentialVersion? active
    ) =>
        new(
            provider.Id,
            provider.ProviderName,
            provider.DisplayName ?? provider.ProviderName,
            provider.Category,
            provider.AgentTypeId,
            provider.AuthMethod,
            !string.IsNullOrEmpty(provider.TestUrl),
            provider.Active,
            active is { Status: ProviderCredentialStatuses.Active }
                ? new("ACTIVE", active.VersionNo, active.ActivatedAt, active.TestOutcome)
                : new("NOT_SET", null, null, null)
        );

    private static ProviderCredentialVersionSummary Summarize(ProviderCredentialVersion version) =>
        new(
            version.Id,
            version.VersionNo,
            version.Status,
            version.CreatedAt,
            version.ActivatedAt,
            version.TestOutcome
        );
}
