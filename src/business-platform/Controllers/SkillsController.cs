// Implements: work-contracts/WC-040-skill-architecture-s1-catalog.md §WC040-02
// constitutional_basis: C-036 (skills are constitutional units), C-059 (traceability), ADR-043 §2

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Net.Client;

namespace Waooaw.BusinessPlatform.Controllers;

// ─── Request / Response DTOs ─────────────────────────────────────────────────

public sealed record SkillResponse(
    string SkillId,
    string Version,
    string DisplayName,
    JsonElement Definition,
    string[] CctSuite,
    string Status,
    DateTimeOffset? PublishedAt);

public sealed record PublishSkillRequest(
    string SkillId,
    string Version,
    string DisplayName,
    JsonElement Definition,
    string[] CctSuite);

// ─── Controller ──────────────────────────────────────────────────────────────

/// <summary>
/// Skill Catalog API — ADR-043 §2.
/// GET endpoints: public (customer JWT sufficient).
/// POST endpoint: Founder role only (C-066 Tier 3 — catalog is platform configuration).
/// </summary>
[ApiController, Route("api/v1/skills")]
[Authorize]
public sealed class SkillsController : ControllerBase
{
    private readonly IDbContextFactory<SkillCatalogDbContext> _dbFactory;
    private readonly IConfiguration _config;
    private readonly ILogger<SkillsController> _logger;

    public SkillsController(
        IDbContextFactory<SkillCatalogDbContext> dbFactory,
        IConfiguration config,
        ILogger<SkillsController> logger)
    {
        _dbFactory = dbFactory;
        _config    = config;
        _logger    = logger;
    }

    // ── GET /api/v1/skills ────────────────────────────────────────────────────
    // Lists all PUBLISHED skills. Used by hiring UX to show available capabilities.

    [HttpGet]
    public async Task<ActionResult<IReadOnlyList<SkillResponse>>> ListSkillsAsync(
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var skills = await db.Skills
            .Where(s => s.Status == "PUBLISHED")
            .OrderBy(s => s.SkillId).ThenBy(s => s.Version)
            .ToListAsync(ct);

        return Ok(skills.Select(ToResponse).ToList());
    }

    // ── GET /api/v1/skills/{skillId} ──────────────────────────────────────────
    // Returns the latest PUBLISHED version of the skill. Hiring UX default.

    [HttpGet("{skillId}")]
    public async Task<ActionResult<SkillResponse>> GetLatestSkillAsync(
        string skillId,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var skill = await db.Skills
            .Where(s => s.SkillId == skillId && s.Status == "PUBLISHED")
            .OrderByDescending(s => s.PublishedAt)
            .FirstOrDefaultAsync(ct);

        if (skill is null)
        {
            _logger.LogInformation("Skill not found or not published: {SkillId}", skillId);
            return NotFound(new { error = "SKILL_NOT_FOUND", skill_id = skillId });
        }

        return Ok(ToResponse(skill));
    }

    // ── GET /api/v1/skills/{skillId}/{version} ────────────────────────────────
    // Pinned-version resolution — called by PR Skill Runtime at session open (ADR-043 §3).

    [HttpGet("{skillId}/{version}")]
    public async Task<ActionResult<SkillResponse>> GetPinnedSkillAsync(
        string skillId,
        string version,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var skill = await db.Skills
            .FirstOrDefaultAsync(
                s => s.SkillId == skillId && s.Version == version && s.Status == "PUBLISHED",
                ct);

        if (skill is null)
        {
            _logger.LogInformation(
                "Skill not found at pinned version: {SkillId}@{Version}", skillId, version);
            return NotFound(new
            {
                error   = "SKILL_NOT_FOUND",
                skill_id = skillId,
                version
            });
        }

        return Ok(ToResponse(skill));
    }

    // ── POST /api/v1/skills ───────────────────────────────────────────────────
    // Publish a new skill or version. Founder role only (C-066 Tier 3).
    // C-023: CE.ValidateAction SKILL_PUBLISH called before any DB write.

    [HttpPost]
    public async Task<IActionResult> PublishSkillAsync(
        [FromBody] PublishSkillRequest request,
        CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new { error = "Request body is required." });

        // C-066 Tier 3: catalog writes require Founder role claim.
        var role = User.FindFirst("role")?.Value ?? User.FindFirst("roles")?.Value ?? string.Empty;
        if (!role.Contains("founder", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "Skill publish rejected: caller does not have Founder role. SkillId={SkillId} Version={Version}",
                request.SkillId, request.Version);
            return StatusCode(403, new { error = "FOUNDER_ROLE_REQUIRED" });
        }

        // C-023: CE.ValidateAction before any DB write.
        var ceGrpcUrl = _config["ConstitutionalEngine:GrpcUrl"];
        if (string.IsNullOrWhiteSpace(ceGrpcUrl))
        {
            _logger.LogError("ConstitutionalEngine:GrpcUrl missing. SkillId={SkillId}", request.SkillId);
            return StatusCode(503, new { error = "Constitutional Engine address is not configured." });
        }

        ValidateActionResponse ceResponse;
        try
        {
            using var channel  = GrpcChannel.ForAddress(ceGrpcUrl);
            var ceClient       = new ConstitutionalService.ConstitutionalServiceClient(channel);
            using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            linkedCts.CancelAfter(TimeSpan.FromSeconds(5));

            ceResponse = await ceClient.ValidateActionAsync(
                new ValidateActionRequest
                {
                    ContractId             = "platform",
                    ActionType             = "SKILL_PUBLISH",
                    ActionParameters       = $"{{\"skill_id\":\"{request.SkillId}\",\"version\":\"{request.Version}\"}}",
                    DecisionSpaceVersion   = 1,
                },
                cancellationToken: linkedCts.Token);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "CE.ValidateAction failed for SKILL_PUBLISH. SkillId={SkillId}", request.SkillId);
            return StatusCode(503, new { error = "Constitutional Engine unavailable. Publish cannot proceed (C-023)." });
        }

        if (ceResponse.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied SKILL_PUBLISH. SkillId={SkillId} Decision={Decision}",
                request.SkillId, ceResponse.Decision);
            return StatusCode(403, new
            {
                error                = "Constitutional Engine denied the publish action.",
                decision             = ceResponse.Decision.ToString(),
                reason               = ceResponse.Reason,
                constitutional_basis = ceResponse.ConstitutionalBasis,
            });
        }

        await using var db  = await _dbFactory.CreateDbContextAsync(ct);

        // Idempotent: if this version already exists as PUBLISHED, return 409.
        var existing = await db.Skills
            .FirstOrDefaultAsync(s => s.SkillId == request.SkillId && s.Version == request.Version, ct);

        if (existing is not null)
        {
            _logger.LogWarning(
                "Skill version already exists: {SkillId}@{Version}", request.SkillId, request.Version);
            return Conflict(new
            {
                error    = "SKILL_VERSION_EXISTS",
                skill_id = request.SkillId,
                version  = request.Version,
            });
        }

        var entry = new SkillEntry
        {
            SkillId      = request.SkillId,
            Version      = request.Version,
            DisplayName  = request.DisplayName,
            Definition   = request.Definition.GetRawText(),
            CctSuite     = request.CctSuite,
            Status       = "PUBLISHED",
            PublishedAt  = DateTimeOffset.UtcNow,
        };

        db.Skills.Add(entry);
        await db.SaveChangesAsync(ct);

        _logger.LogInformation(
            "Skill published: {SkillId}@{Version}", request.SkillId, request.Version);

        return CreatedAtAction(
            nameof(GetPinnedSkillAsync),
            new { skillId = entry.SkillId, version = entry.Version },
            ToResponse(entry));
    }

    // ─── Helper ──────────────────────────────────────────────────────────────

    private static SkillResponse ToResponse(SkillEntry s)
    {
        JsonElement def;
        try
        {
            def = JsonDocument.Parse(s.Definition).RootElement;
        }
        catch
        {
            def = JsonDocument.Parse("{}").RootElement;
        }
        return new SkillResponse(s.SkillId, s.Version, s.DisplayName, def, s.CctSuite, s.Status, s.PublishedAt);
    }
}
