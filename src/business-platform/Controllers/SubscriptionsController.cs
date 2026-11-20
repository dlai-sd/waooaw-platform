// Implements: work-contracts/WC-033-goal005-bp-trial-lifecycle.md §WC033-01
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-03
// constitutional_basis: C-023 (Evidence First — phone_verified gate), C-088 (trial is a billing mode), C-059
using System.Net.Http;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Mvc;

namespace Waooaw.BusinessPlatform.Controllers;

// ─── Request / Response ──────────────────────────────────────────────────────

public sealed record TrialStartRequest(
    Guid CustomerId,
    string AgentType,
    bool PhoneVerified,
    string? AgentVersion = null
);

public sealed record TrialStartResponse(
    Guid TrialId,
    DateTimeOffset ExpiresAt,
    Dictionary<string, int> FreeUnitCaps,
    List<Guid> WalletBucketIds
);

// ─── Controller ──────────────────────────────────────────────────────────────

[ApiController, Route("api/v1/subscriptions")]
public sealed class SubscriptionsController : ControllerBase
{
    private const string WbeClientName = "WBE";
    private const string WbeTrialStartPath = "/trial/start";

    private static readonly JsonSerializerOptions _jsonOpts = new(JsonSerializerDefaults.Web);

    private static readonly Regex AgentVersionPattern = new(
        @"\A[0-9]+\.[0-9]+\.[0-9]+\z",
        RegexOptions.CultureInvariant | RegexOptions.Compiled,
        TimeSpan.FromMilliseconds(100)
    );

    private static readonly Regex IdentityHashPattern = new(
        @"\A[0-9a-fA-F]{64}\z",
        RegexOptions.CultureInvariant | RegexOptions.Compiled,
        TimeSpan.FromMilliseconds(100)
    );

    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<SubscriptionsController> _logger;

    public SubscriptionsController(
        IHttpClientFactory httpClientFactory,
        ILogger<SubscriptionsController> logger
    )
    {
        _httpClientFactory = httpClientFactory;
        _logger = logger;
    }

    /// <summary>
    /// POST /api/v1/subscriptions/trial-start
    /// C-023: phone_verified=true is the pre-condition evidence gate; request is rejected
    /// with 422 PHONE_NOT_VERIFIED before any WBE call if the gate is not met.
    /// C-088: trial is a subscription billing mode — WBE TrialService is the authority.
    /// </summary>
    [HttpPost("trial-start")]
    public async Task<IActionResult> TrialStartAsync(
        [FromBody] TrialStartRequest request,
        CancellationToken cancellationToken
    )
    {
        if (request is null)
            return BadRequest(new { error = "Request body is required." });

        // C-023: phone verification is the evidence gate — reject immediately if not met.
        if (!request.PhoneVerified)
        {
            _logger.LogWarning(
                "TrialStart rejected: phone not verified. customer_id={CustomerId} agent_type={AgentType}",
                request.CustomerId,
                request.AgentType
            );
            return UnprocessableEntity(new { error = "PHONE_NOT_VERIFIED" });
        }

        // C3-03: the trial is per exact agent version (matches trial_allocations_agent_version_check).
        if (request.AgentVersion is null || !AgentVersionPattern.IsMatch(request.AgentVersion))
        {
            return BadRequest(new { error = "AGENT_VERSION_INVALID" });
        }

        // Call WBE billing-engine trial/start — WBE is the authoritative source of truth
        // for trial allocation (trial_allocations + wallet_buckets + trial_free_unit_ledger).
        var wbeClient = _httpClientFactory.CreateClient(WbeClientName);

        WbeTrialStartPayload wbePayload = new(
            request.CustomerId.ToString(),
            request.AgentType,
            request.AgentVersion,
            request.PhoneVerified,
            VerifiedIdentitySubjectHash()
        );

        HttpResponseMessage wbeResponse;
        try
        {
            wbeResponse = await wbeClient.PostAsJsonAsync(
                WbeTrialStartPath,
                wbePayload,
                _jsonOpts,
                cancellationToken
            );
        }
        catch (Exception ex)
        {
            _logger.LogError(
                ex,
                "WBE /trial/start request failed: customer_id={CustomerId}",
                request.CustomerId
            );
            return StatusCode(503, new { error = "Billing service unavailable. Please retry." });
        }

        // C-059: log WBE outcome for traceability
        _logger.LogInformation(
            "WBE /trial/start response: status={Status} customer_id={CustomerId}",
            (int)wbeResponse.StatusCode,
            request.CustomerId
        );

        // Propagate 409 TRIAL_ALREADY_USED and TRIAL_ALREADY_USED_BY_IDENTITY directly from WBE
        if (wbeResponse.StatusCode == System.Net.HttpStatusCode.Conflict)
        {
            var errBody = await wbeResponse.Content.ReadAsStringAsync(cancellationToken);
            var code = errBody.Contains("TRIAL_ALREADY_USED_BY_IDENTITY", StringComparison.Ordinal)
                ? "TRIAL_ALREADY_USED_BY_IDENTITY"
                : "TRIAL_ALREADY_USED";
            return Conflict(new { error = code, detail = errBody });
        }

        if (!wbeResponse.IsSuccessStatusCode)
        {
            _logger.LogError(
                "WBE /trial/start returned unexpected status={Status} customer_id={CustomerId}",
                (int)wbeResponse.StatusCode,
                request.CustomerId
            );
            return StatusCode(502, new { error = "Billing service returned an unexpected error." });
        }

        // Deserialize WBE response and map to BP TrialStartResponse
        WbeTrialStartResult? wbeResult;
        try
        {
            wbeResult = await wbeResponse.Content.ReadFromJsonAsync<WbeTrialStartResult>(
                _jsonOpts,
                cancellationToken
            );
        }
        catch (Exception ex)
        {
            _logger.LogError(
                ex,
                "Failed to deserialize WBE /trial/start response: customer_id={CustomerId}",
                request.CustomerId
            );
            return StatusCode(502, new { error = "Billing service response could not be parsed." });
        }

        if (wbeResult is null)
            return StatusCode(502, new { error = "Billing service returned an empty response." });

        var walletIds = (wbeResult.WalletBucketIds ?? [])
            .Select(id => Guid.TryParse(id, out var g) ? g : Guid.Empty)
            .Where(g => g != Guid.Empty)
            .ToList();

        return Ok(
            new TrialStartResponse(
                TrialId: Guid.TryParse(wbeResult.TrialId, out var tid) ? tid : Guid.Empty,
                ExpiresAt: wbeResult.ExpiresAt,
                FreeUnitCaps: wbeResult.FreeUnitCaps ?? [],
                WalletBucketIds: walletIds
            )
        );
    }

    // ─── Verified identity ───────────────────────────────────────────────────

    /// <summary>
    /// The hash of the verified phone subject, taken only from the server-verified token claims
    /// (never from the request body). Absent for sessions that are not WhatsApp-verified.
    /// </summary>
    private string? VerifiedIdentitySubjectHash()
    {
        var channel = User.FindFirst("channel")?.Value;
        var hash = User.FindFirst("external_subject_hash")?.Value;
        if (
            !string.Equals(channel, "WHATSAPP", StringComparison.OrdinalIgnoreCase)
            || hash is null
            || !IdentityHashPattern.IsMatch(hash)
        )
            return null;
        return hash.ToLowerInvariant();
    }

    // ─── WBE wire types (snake_case from billing-engine FastAPI) ─────────────

    private sealed record WbeTrialStartPayload(
        [property: JsonPropertyName("customer_id")] string CustomerId,
        [property: JsonPropertyName("agent_type")] string AgentType,
        [property: JsonPropertyName("agent_version")] string AgentVersion,
        [property: JsonPropertyName("phone_verified")] bool PhoneVerified,
        [property: JsonPropertyName("identity_subject_hash")] string? IdentitySubjectHash
    );

    private sealed record WbeTrialStartResult(
        [property: JsonPropertyName("trial_id")] string? TrialId,
        [property: JsonPropertyName("expires_at")] DateTimeOffset ExpiresAt,
        [property: JsonPropertyName("free_unit_caps")] Dictionary<string, int>? FreeUnitCaps,
        [property: JsonPropertyName("wallet_bucket_ids")] List<string>? WalletBucketIds
    );
}
