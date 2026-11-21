// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-06
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-07
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-08
// Constitutional basis: C-023, C-059, C-063, C-088, C-089

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// Pricing and spend administration (pricing-admin-business-platform.openapi.yaml). This is an admin
/// route, not a customer route: it carries no customer identity route attribute. Reads, drafts, simulation,
/// submission, discarding and the safety operations need realm role pricing_admin or founder; authorize and
/// activate-for-sale need founder plus a step-up. Every failure is an RFC 7807 problem with a published code.
/// </summary>
[ApiController]
[Authorize]
[Route(PricingAdminService.PublicRoutePrefix)]
public sealed class PricingAdminController(PricingAdminService pricing) : ControllerBase
{
    private const int MaximumBodyBytes = 262_144;

    [HttpGet("drafts")]
    public Task<IActionResult> ListPricingDraftsAsync(CancellationToken ct) =>
        RunAsync("listPricingDrafts", null, ct);

    [HttpPost("drafts")]
    public Task<IActionResult> CreatePricingDraftAsync(CancellationToken ct) =>
        RunAsync("createPricingDraft", null, ct);

    [HttpGet("drafts/{draftId}")]
    public Task<IActionResult> GetPricingDraftAsync(string draftId, CancellationToken ct) =>
        RunAsync("getPricingDraft", Path("draftId", draftId), ct);

    [HttpPut("drafts/{draftId}")]
    public Task<IActionResult> UpdatePricingDraftAsync(string draftId, CancellationToken ct) =>
        RunAsync("updatePricingDraft", Path("draftId", draftId), ct);

    [HttpPost("drafts/{draftId}/simulate")]
    public Task<IActionResult> SimulatePricingDraftAsync(string draftId, CancellationToken ct) =>
        RunAsync("simulatePricingDraft", Path("draftId", draftId), ct);

    [HttpPost("drafts/{draftId}/submit")]
    public Task<IActionResult> SubmitPricingDraftAsync(string draftId, CancellationToken ct) =>
        RunAsync("submitPricingDraft", Path("draftId", draftId), ct);

    [HttpPost("drafts/{draftId}/authorize")]
    public Task<IActionResult> AuthorizePricingDraftAsync(string draftId, CancellationToken ct) =>
        RunAsync("authorizePricingDraft", Path("draftId", draftId), ct);

    [HttpPost("drafts/{draftId}/discard")]
    public Task<IActionResult> DiscardPricingDraftAsync(string draftId, CancellationToken ct) =>
        RunAsync("discardPricingDraft", Path("draftId", draftId), ct);

    [HttpGet("versions")]
    public Task<IActionResult> ListPricingVersionsAsync(CancellationToken ct) =>
        RunAsync("listPricingVersions", null, ct);

    [HttpGet("versions/export")]
    public Task<IActionResult> ExportPricingVersionsAsync(CancellationToken ct) =>
        RunAsync("exportPricingVersions", null, ct);

    [HttpPost("versions/import")]
    public Task<IActionResult> ImportPricingVersionsAsync(CancellationToken ct) =>
        RunAsync("importPricingVersions", null, ct);

    [HttpPost("packages/{packageId}/activate-for-sale")]
    public Task<IActionResult> ActivatePackageForSaleAsync(
        string packageId,
        CancellationToken ct
    ) => RunAsync("activatePackageForSale", Path("packageId", packageId), ct);

    [HttpPost("safety/lower-ceiling")]
    public Task<IActionResult> LowerPricingCeilingAsync(CancellationToken ct) =>
        RunAsync("lowerPricingCeiling", null, ct);

    [HttpPost("safety/close-package")]
    public Task<IActionResult> ClosePackageToNewCustomersAsync(CancellationToken ct) =>
        RunAsync("closePackageToNewCustomers", null, ct);

    [HttpPost("safety/disable-grant")]
    public Task<IActionResult> DisablePricingGrantAsync(CancellationToken ct) =>
        RunAsync("disablePricingGrant", null, ct);

    [HttpGet("live-margin")]
    public Task<IActionResult> GetPricingLiveMarginAsync(CancellationToken ct) =>
        RunAsync("getPricingLiveMargin", null, ct);

    [HttpGet("dashboard/funding")]
    public Task<IActionResult> GetPricingFundingDashboardAsync(CancellationToken ct) =>
        RunAsync("getPricingFundingDashboard", null, ct);

    [HttpGet("dashboard/margin")]
    public Task<IActionResult> GetPricingMarginDashboardAsync(CancellationToken ct) =>
        RunAsync("getPricingMarginDashboard", null, ct);

    private static IReadOnlyDictionary<string, string> Path(string name, string value) =>
        new Dictionary<string, string> { [name] = value };

    private async Task<IActionResult> RunAsync(
        string operation,
        IReadOnlyDictionary<string, string>? pathValues,
        CancellationToken ct
    )
    {
        Guid? correlation = null;
        try
        {
            var actor = Actor();
            var operationRoute = PricingAdminService.Operations[operation];
            PricingAdminService.Authorize(actor, operationRoute);
            correlation = HeaderGuid("X-Correlation-ID");
            var body = operationRoute.Writes ? await ReadBodyAsync(ct) : null;
            var result = await pricing.ExecuteAsync(
                actor,
                new PricingAdminCommand(
                    operation,
                    pathValues ?? new Dictionary<string, string>(),
                    Request
                        .Query.SelectMany(pair =>
                            pair.Value.Select(value => new KeyValuePair<string, string>(
                                pair.Key,
                                value ?? ""
                            ))
                        )
                        .ToList(),
                    body,
                    HeaderGuid("Idempotency-Key"),
                    correlation
                ),
                ct
            );
            if (result.ETag is { } etag)
                Response.Headers.ETag = etag;
            return new ContentResult
            {
                StatusCode = result.Status,
                ContentType = "application/json",
                Content = result.Body?.GetRawText() ?? "{}",
            };
        }
        catch (PricingAdminProblemException problem)
        {
            return ProblemResult(problem, correlation);
        }
    }

    private PricingAdminActor Actor()
    {
        var subject =
            User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        if (User.Identity?.IsAuthenticated != true || string.IsNullOrWhiteSpace(subject))
            throw new PricingAdminProblemException(
                401,
                "PRICING_FORBIDDEN",
                "A signed-in administrator is required."
            );
        var tenant =
            HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var value)
            && value is string text
            && Guid.TryParse(text, out var parsed)
                ? parsed
                : Guid.Empty;
        return new PricingAdminActor(
            subject,
            tenant,
            IsRole("pricing_admin"),
            IsRole("founder"),
            HasStepUp()
        );
    }

    private Guid? HeaderGuid(string name)
    {
        if (!Request.Headers.TryGetValue(name, out var values) || values.Count == 0)
            return null;
        if (values.Count == 1 && Guid.TryParse(values[0], out var parsed) && parsed != Guid.Empty)
            return parsed;
        throw new PricingAdminProblemException(
            400,
            "PRICING_REQUEST_INVALID",
            $"{name} must be a UUID."
        );
    }

    private async Task<JsonElement?> ReadBodyAsync(CancellationToken ct)
    {
        using var buffer = new MemoryStream();
        var chunk = new byte[8192];
        int read;
        while ((read = await Request.Body.ReadAsync(chunk, ct)) > 0)
        {
            buffer.Write(chunk, 0, read);
            if (buffer.Length > MaximumBodyBytes)
                throw new PricingAdminProblemException(
                    400,
                    "PRICING_REQUEST_INVALID",
                    "The request body is too large."
                );
        }
        if (buffer.Length == 0)
            return null;
        try
        {
            using var document = JsonDocument.Parse(buffer.ToArray());
            return document.RootElement.Clone();
        }
        catch (JsonException)
        {
            throw new PricingAdminProblemException(
                400,
                "PRICING_REQUEST_INVALID",
                "The body is not valid JSON."
            );
        }
    }

    private IActionResult ProblemResult(PricingAdminProblemException problem, Guid? correlation)
    {
        var content = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["type"] =
                $"https://waooaw.com/problems/{problem.Code.ToLowerInvariant().Replace('_', '-')}",
            ["title"] = Title(problem.Code),
            ["status"] = problem.Status,
            ["code"] = problem.Code,
            ["correlationId"] = (correlation ?? Guid.NewGuid()).ToString("D"),
            ["detail"] = problem.Detail,
        };
        foreach (var (name, value) in problem.Extras)
            content[name] = value;
        return new ContentResult
        {
            StatusCode = problem.Status,
            ContentType = "application/problem+json",
            Content = JsonSerializer.Serialize(content),
        };
    }

    private static string Title(string code)
    {
        var words = code.ToLowerInvariant().Replace('_', ' ');
        return char.ToUpperInvariant(words[0]) + words[1..];
    }

    private bool IsRole(string role) =>
        User.IsInRole(role)
        || User.Claims.Where(claim => claim.Type is ClaimTypes.Role or "role" or "participant_role")
            .Any(claim => string.Equals(claim.Value, role, StringComparison.OrdinalIgnoreCase));

    // Same bar as the identity lifecycle step-up (IdentityController.HasLifecycleStepUp): a fresh
    // authentication (auth_time within five minutes) at assurance level 2 or 3 with a multi-factor method.
    private bool HasStepUp() =>
        User.FindFirstValue("auth_time") is string authTime
        && long.TryParse(authTime, out var authenticatedAt)
        && DateTimeOffset.UtcNow - DateTimeOffset.FromUnixTimeSeconds(authenticatedAt) is var age
        && age >= TimeSpan.FromSeconds(-30)
        && age <= TimeSpan.FromMinutes(5)
        && User.FindFirstValue("acr") is "2" or "3" or "urn:waooaw:aal2" or "urn:waooaw:aal3"
        && User.FindAll("amr")
            .SelectMany(claim => claim.Value.Split(' ', StringSplitOptions.RemoveEmptyEntries))
            .Any(method => method is "mfa" or "otp" or "webauthn");
}
