// Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §1 Provider Registry API
// constitutional_basis: C-041 (tool authorization), C-059 (traceability), ADR-042

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// Pinned Key Vault secret version of the provider's active credential (WC148-R005). Names a secret; never holds its value.
/// </summary>
public sealed record ProviderCredentialPointer(
    string SecretName,
    string SecretVersion,
    int VersionNo
);

/// <summary>Response DTO — no internal fields (vault_path_key excluded from external response).</summary>
public sealed record ProviderConfigResponse(
    string ProviderName,
    string AuthMethod,
    string? McpServerUrl,
    string[] ScopeSet,
    bool Active,
    ProviderCredentialPointer? Credential = null
);

/// <summary>
/// Provider Registry API — internal-only endpoints (service-to-service JWT required).
/// Called by CTG registry cache (ADR-042 §2) to route tool calls to the correct provider.
/// </summary>
[ApiController, Route("api/v1/providers")]
[Authorize] // service-to-service: validated JWT required (mTLS full auth in ADR-007 future sprint)
public sealed class ProvidersController : ControllerBase
{
    private readonly IDbContextFactory<ProviderRegistryDbContext> _dbFactory;
    private readonly ILogger<ProvidersController> _logger;

    public ProvidersController(
        IDbContextFactory<ProviderRegistryDbContext> dbFactory,
        ILogger<ProvidersController> logger
    )
    {
        _dbFactory = dbFactory;
        _logger = logger;
    }

    /// <summary>
    /// GET /api/v1/providers
    /// Lists all active providers visible to this tenant (tenant-specific rows + platform-level rows).
    /// Called by CTG registry cache with TTL 60s (ADR-042 §2).
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<IReadOnlyList<ProviderConfigResponse>>> GetProviders(
        CancellationToken ct
    )
    {
        var tenantIdClaim = User.FindFirst("tenant_id")?.Value;
        Guid? tenantId = Guid.TryParse(tenantIdClaim, out var tid) ? tid : null;

        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var configs = await db
            .ProviderConfigs.Where(p => p.Active && (p.TenantId == null || p.TenantId == tenantId))
            .OrderBy(p => p.ProviderName)
            .ToListAsync(ct);
        var pointers = await ActivePointersAsync(db, configs, ct);
        var rows = configs.Select(p => ToResponse(p, pointers.GetValueOrDefault(p.Id))).ToList();

        _logger.LogInformation(
            "GetProviders: returned {Count} providers for tenant={TenantId}",
            rows.Count,
            tenantId
        );

        return Ok(rows);
    }

    /// <summary>
    /// GET /api/v1/providers/{providerName}
    /// Gets a single provider config by name. Resolves tenant-specific row first, then platform-level.
    /// </summary>
    [HttpGet("{providerName}")]
    public async Task<ActionResult<ProviderConfigResponse>> GetProvider(
        string providerName,
        CancellationToken ct
    )
    {
        var tenantIdClaim = User.FindFirst("tenant_id")?.Value;
        Guid? tenantId = Guid.TryParse(tenantIdClaim, out var tid) ? tid : null;

        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        // Tenant-specific row takes precedence over platform-level row.
        var row = await db
            .ProviderConfigs.Where(p =>
                p.Active
                && p.ProviderName == providerName
                && (p.TenantId == tenantId || p.TenantId == null)
            )
            .OrderByDescending(p => p.TenantId.HasValue) // tenant-specific first
            .FirstOrDefaultAsync(ct);

        if (row is null)
        {
            _logger.LogWarning(
                "GetProvider: provider_name={ProviderName} not found for tenant={TenantId}",
                providerName,
                tenantId
            );
            return NotFound(new { error = "PROVIDER_NOT_FOUND", provider_name = providerName });
        }

        var pointers = await ActivePointersAsync(db, [row], ct);
        return Ok(ToResponse(row, pointers.GetValueOrDefault(row.Id)));
    }

    private static ProviderConfigResponse ToResponse(
        ProviderConfig row,
        ProviderCredentialPointer? pointer
    ) => new(row.ProviderName, row.AuthMethod, row.McpServerUrl, row.ScopeSet, row.Active, pointer);

    private static async Task<Dictionary<Guid, ProviderCredentialPointer>> ActivePointersAsync(
        ProviderRegistryDbContext db,
        IReadOnlyList<ProviderConfig> configs,
        CancellationToken ct
    )
    {
        var versionIds = configs
            .Where(p => p.ActiveCredentialVersionId.HasValue)
            .Select(p => p.ActiveCredentialVersionId!.Value)
            .ToList();
        if (versionIds.Count == 0)
            return [];
        var versions = await db
            .ProviderCredentialVersions.Where(v =>
                versionIds.Contains(v.Id) && v.Status == ProviderCredentialStatuses.Active
            )
            .ToListAsync(ct);
        return configs
            .Where(p => p.ActiveCredentialVersionId.HasValue)
            .Select(p =>
                (
                    Config: p,
                    Version: versions.FirstOrDefault(v => v.Id == p.ActiveCredentialVersionId)
                )
            )
            .Where(pair => pair.Version is not null)
            .ToDictionary(
                pair => pair.Config.Id,
                pair => new ProviderCredentialPointer(
                    pair.Version!.VaultSecretName,
                    pair.Version.VaultSecretVersion,
                    pair.Version.VersionNo
                )
            );
    }
}
