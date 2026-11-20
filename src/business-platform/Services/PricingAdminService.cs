// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-04
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-06
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-07
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-08
// Constitutional basis: C-023, C-059, C-063, C-088, C-089
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services;

public sealed class PricingAdminOptions
{
    public const string SectionName = "PricingAdmin";

    public int WriteLimitPerMinute { get; set; } = 30;
}

/// <summary>The caller as the controller resolved it from the session; roles are never taken from a body.</summary>
public sealed record PricingAdminActor(
    string Subject,
    Guid TenantId,
    bool IsPricingAdmin,
    bool IsFounder,
    bool HasStepUp
)
{
    public bool CanOperate => IsPricingAdmin || IsFounder;

    public string EffectiveRole => IsFounder ? "FOUNDER" : "PRICING_ADMIN";
}

public sealed record PricingAdminOperation(
    string Id,
    string WbeOperation,
    string Method,
    string PublicRoute,
    string WbeRoute,
    bool Writes,
    bool FounderOnly,
    bool DeployMaximum,
    IReadOnlyList<string> QueryNames
);

public sealed record PricingAdminCommand(
    string Operation,
    IReadOnlyDictionary<string, string> PathValues,
    IReadOnlyList<KeyValuePair<string, string>> Query,
    JsonElement? Body,
    Guid? IdempotencyKey,
    Guid? CorrelationId
);

public sealed record PricingAdminResult(int Status, JsonElement? Body, string? ETag);

/// <summary>A published Appendix B.5 problem; extras carry violations, blockingPaise and similar members.</summary>
public sealed class PricingAdminProblemException(
    int status,
    string code,
    string detail,
    IReadOnlyDictionary<string, JsonElement>? extras = null
) : Exception(code)
{
    public int Status { get; } = status;

    public string Code { get; } = code;

    public string Detail { get; } = detail;

    public IReadOnlyDictionary<string, JsonElement> Extras { get; } =
        extras ?? new Dictionary<string, JsonElement>();
}

/// <summary>Sliding one-minute window per subject for state-changing admin calls.</summary>
public sealed class PricingAdminWriteLimiter(
    IOptions<PricingAdminOptions> options,
    TimeProvider clock
)
{
    private static readonly TimeSpan Window = TimeSpan.FromMinutes(1);
    private readonly Dictionary<string, Queue<DateTimeOffset>> _calls = new(StringComparer.Ordinal);
    private readonly object _gate = new();

    public bool TryAcquire(string subject)
    {
        var now = clock.GetUtcNow();
        lock (_gate)
        {
            if (!_calls.TryGetValue(subject, out var queue))
                _calls[subject] = queue = new Queue<DateTimeOffset>();
            while (queue.Count > 0 && now - queue.Peek() >= Window)
                queue.Dequeue();
            if (queue.Count >= options.Value.WriteLimitPerMinute)
                return false;
            queue.Enqueue(now);
            return true;
        }
    }
}

/// <summary>
/// The Business Platform facade of the pricing admin API. It decides who may do what (administrators
/// draft, simulate, submit and lower; only the Founder with a step-up authorizes or activates), signs the
/// call to the Billing Engine, keeps the environment spend authority in step with an authorized
/// ENVIRONMENT_CEILING budget, and turns every owner failure into a published problem code.
/// </summary>
public sealed class PricingAdminService(
    IPricingAdminGateway gateway,
    IEnvironmentSpendCeilingStore ceilings,
    EnvironmentSpendOptions spend,
    PricingAdminWriteLimiter limiter,
    TimeProvider clock,
    ILogger<PricingAdminService> logger
)
{
    public const string WbeRoutePrefix = "/internal/v1/pricing";
    public const string PublicRoutePrefix = "api/v1/admin/pricing";
    public const string SchemaVersion = "1.0";
    private const string EnvironmentCeilingScope = "ENVIRONMENT_CEILING";

    private static readonly string[] ListQuery = ["kind", "state", "subjectKey", "limit", "cursor"];
    private static readonly string[] PeriodQuery = ["from", "to"];
    private static readonly string[] NoQuery = [];

    private static readonly HashSet<string> PublishedCodes =
    [
        "PRICING_FORBIDDEN",
        "PRICING_STEP_UP_REQUIRED",
        "PRICING_DRAFT_INVALID",
        "PRICING_BELOW_FLOOR",
        "PRICING_NEEDS_SECOND_CONFIRMATION",
        "PRICING_ILLEGAL_TRANSITION",
        "PRICING_CEILING_ABOVE_MAXIMUM",
        "PRICING_CEILING_BELOW_OPEN_RESERVATIONS",
        "PACKAGE_COMPONENT_NOT_AVAILABLE",
        "RECIPE_THREAD_NOT_AUTHORIZED",
        "PRICING_REQUEST_INVALID",
        "PRICING_NOT_FOUND",
        "PRICING_VERSION_CONFLICT",
        "PRICING_IDEMPOTENCY_CONFLICT",
        "PRICING_RATE_LIMITED",
        "PRICING_UNAVAILABLE",
    ];

    private static readonly HashSet<int> PassThroughStatuses = [400, 403, 404, 409, 422, 429, 503];
    private static readonly string[] ExtraMembers =
    [
        "violations",
        "minimumCompliantPricePaise",
        "blockingPaise",
        "componentId",
    ];

    public static IReadOnlyDictionary<string, PricingAdminOperation> Operations { get; } =
        new PricingAdminOperation[]
        {
            Op(
                "listPricingDrafts",
                "wbeListPricingDrafts",
                "GET",
                "drafts",
                false,
                false,
                false,
                ListQuery
            ),
            Op(
                "createPricingDraft",
                "wbeCreatePricingDraft",
                "POST",
                "drafts",
                true,
                false,
                true,
                NoQuery
            ),
            Op(
                "getPricingDraft",
                "wbeGetPricingDraft",
                "GET",
                "drafts/{draftId}",
                false,
                false,
                false,
                NoQuery
            ),
            Op(
                "updatePricingDraft",
                "wbeUpdatePricingDraft",
                "PUT",
                "drafts/{draftId}",
                true,
                false,
                true,
                NoQuery
            ),
            Op(
                "simulatePricingDraft",
                "wbeSimulatePricingDraft",
                "POST",
                "drafts/{draftId}/simulate",
                true,
                false,
                false,
                NoQuery
            ),
            Op(
                "submitPricingDraft",
                "wbeSubmitPricingDraft",
                "POST",
                "drafts/{draftId}/submit",
                true,
                false,
                false,
                NoQuery
            ),
            Op(
                "authorizePricingDraft",
                "wbeAuthorizePricingDraft",
                "POST",
                "drafts/{draftId}/authorize",
                true,
                true,
                true,
                NoQuery
            ),
            Op(
                "discardPricingDraft",
                "wbeDiscardPricingDraft",
                "POST",
                "drafts/{draftId}/discard",
                true,
                false,
                false,
                NoQuery
            ),
            Op(
                "listPricingVersions",
                "wbeListPricingVersions",
                "GET",
                "versions",
                false,
                false,
                false,
                ListQuery
            ),
            Op(
                "exportPricingVersions",
                "wbeExportPricingVersions",
                "GET",
                "versions/export",
                false,
                false,
                false,
                NoQuery
            ),
            Op(
                "importPricingVersions",
                "wbeImportPricingVersions",
                "POST",
                "versions/import",
                true,
                false,
                true,
                NoQuery
            ),
            Op(
                "activatePackageForSale",
                "wbeActivatePackageForSale",
                "POST",
                "packages/{packageId}/activate-for-sale",
                true,
                true,
                false,
                NoQuery
            ),
            Op(
                "lowerPricingCeiling",
                "wbeLowerPricingCeiling",
                "POST",
                "safety/lower-ceiling",
                true,
                false,
                false,
                NoQuery
            ),
            Op(
                "closePackageToNewCustomers",
                "wbeClosePackageToNewCustomers",
                "POST",
                "safety/close-package",
                true,
                false,
                false,
                NoQuery
            ),
            Op(
                "disablePricingGrant",
                "wbeDisablePricingGrant",
                "POST",
                "safety/disable-grant",
                true,
                false,
                false,
                NoQuery
            ),
            Op(
                "getPricingLiveMargin",
                "wbeGetPricingLiveMargin",
                "GET",
                "live-margin",
                false,
                false,
                false,
                NoQuery
            ),
            Op(
                "getPricingFundingDashboard",
                "wbeGetPricingFundingDashboard",
                "GET",
                "dashboard/funding",
                false,
                false,
                false,
                PeriodQuery
            ),
            Op(
                "getPricingMarginDashboard",
                "wbeGetPricingMarginDashboard",
                "GET",
                "dashboard/margin",
                false,
                false,
                false,
                PeriodQuery
            ),
        }.ToDictionary(operation => operation.Id, StringComparer.Ordinal);

    private static PricingAdminOperation Op(
        string id,
        string wbeOperation,
        string method,
        string route,
        bool writes,
        bool founderOnly,
        bool deployMaximum,
        string[] query
    ) =>
        new(
            id,
            wbeOperation,
            method,
            $"{PublicRoutePrefix}/{route}",
            $"{WbeRoutePrefix}/{route}",
            writes,
            founderOnly,
            deployMaximum,
            query
        );

    public long HardMaximumPaise => checked((long)(spend.HardMaximumInr * 100m));

    public async Task<PricingAdminResult> ExecuteAsync(
        PricingAdminActor actor,
        PricingAdminCommand command,
        CancellationToken ct
    )
    {
        if (!Operations.TryGetValue(command.Operation, out var operation))
            throw Problem(404, "PRICING_NOT_FOUND", "The pricing operation does not exist.");
        Authorize(actor, operation);
        var correlation = command.CorrelationId ?? Guid.NewGuid();
        if (operation.Writes)
        {
            if (command.IdempotencyKey is null || command.CorrelationId is null)
                throw Problem(
                    400,
                    "PRICING_REQUEST_INVALID",
                    "Idempotency-Key and X-Correlation-ID are required."
                );
            if (!limiter.TryAcquire(actor.Subject))
                throw Problem(
                    429,
                    "PRICING_RATE_LIMITED",
                    "Too many pricing changes; retry shortly."
                );
        }
        var path = BuildPath(operation, command.PathValues);
        var query = BuildQuery(operation, command.Query);
        var body = PrepareBody(operation, command.Body);
        var call = new Call(
            actor,
            operation,
            path,
            query,
            body,
            correlation,
            command.IdempotencyKey
        );
        return command.Operation switch
        {
            "authorizePricingDraft" => await AuthorizeAsync(
                call,
                command.PathValues["draftId"],
                ct
            ),
            "lowerPricingCeiling" => await LowerCeilingAsync(call, ct),
            _ => await ForwardAsync(call, ct),
        };
    }

    private sealed record Call(
        PricingAdminActor Actor,
        PricingAdminOperation Operation,
        string Path,
        string? Query,
        Dictionary<string, JsonElement>? Body,
        Guid Correlation,
        Guid? IdempotencyKey
    );

    public static void Authorize(PricingAdminActor actor, PricingAdminOperation operation)
    {
        if (!actor.CanOperate || (operation.FounderOnly && !actor.IsFounder))
            throw Problem(
                403,
                "PRICING_FORBIDDEN",
                "The role may not perform this pricing operation."
            );
        if (operation.FounderOnly && !actor.HasStepUp)
            throw Problem(
                403,
                "PRICING_STEP_UP_REQUIRED",
                "This operation needs a fresh step-up authentication."
            );
    }

    private static string BuildPath(
        PricingAdminOperation operation,
        IReadOnlyDictionary<string, string> values
    )
    {
        var path = operation.WbeRoute;
        foreach (var name in new[] { "draftId", "packageId" })
        {
            var token = "{" + name + "}";
            if (!path.Contains(token, StringComparison.Ordinal))
                continue;
            if (!values.TryGetValue(name, out var raw) || !Guid.TryParse(raw, out var id))
                throw Problem(400, "PRICING_REQUEST_INVALID", $"{name} must be a UUID.");
            path = path.Replace(token, id.ToString("D"), StringComparison.Ordinal);
        }
        return path;
    }

    private static string? BuildQuery(
        PricingAdminOperation operation,
        IReadOnlyList<KeyValuePair<string, string>> query
    )
    {
        if (query.Count == 0)
            return null;
        var parts = new List<string>();
        foreach (var (name, value) in query)
        {
            if (!operation.QueryNames.Contains(name) || value.Length is 0 or > 300)
                throw Problem(
                    400,
                    "PRICING_REQUEST_INVALID",
                    $"The query parameter {name} is not accepted."
                );
            parts.Add($"{Uri.EscapeDataString(name)}={Uri.EscapeDataString(value)}");
        }
        return string.Join('&', parts);
    }

    private Dictionary<string, JsonElement>? PrepareBody(
        PricingAdminOperation operation,
        JsonElement? body
    )
    {
        if (!operation.Writes)
            return null;
        if (body is not { ValueKind: JsonValueKind.Object } element)
            throw Problem(400, "PRICING_REQUEST_INVALID", "The body must be a JSON object.");
        var members = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        foreach (var property in element.EnumerateObject())
            members[property.Name] = property.Value.Clone();
        if (
            !members.TryGetValue("schemaVersion", out var version)
            || version.ValueKind != JsonValueKind.String
            || version.GetString() != SchemaVersion
        )
            throw Problem(400, "PRICING_REQUEST_INVALID", "schemaVersion must be 1.0.");
        if (members.ContainsKey("deployTimeMaximumPaise"))
            throw Problem(
                400,
                "PRICING_REQUEST_INVALID",
                "The deploy-time maximum is set by the platform, not by the caller."
            );
        if (operation.DeployMaximum)
            members["deployTimeMaximumPaise"] = JsonSerializer.SerializeToElement(HardMaximumPaise);
        return members;
    }

    private static string SubjectReference(Call call)
    {
        if (call.Body is not null)
        {
            if (
                call.Operation.Id == "lowerPricingCeiling"
                && Text(call.Body, "scope") is { } scope
                && Text(call.Body, "ref") is { } reference
            )
                return $"budget:{scope}|{reference}";
            if (Text(call.Body, "subjectKey") is { } subject)
                return subject;
            if (Text(call.Body, "packageId") is { } package)
                return package;
        }
        var identifier = call
            .Path.Split('/')
            .FirstOrDefault(segment => Guid.TryParse(segment, out _));
        return identifier ?? "pricing";
    }

    private static string? Text(IReadOnlyDictionary<string, JsonElement> body, string name) =>
        body.TryGetValue(name, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    private async Task<PricingAdminResult> ForwardAsync(Call call, CancellationToken ct)
    {
        var response = await SendAsync(call, call.Operation, call.Path, call.Query, call.Body, ct);
        return Succeeded(response);
    }

    private async Task<PricingGatewayResponse> SendAsync(
        Call call,
        PricingAdminOperation operation,
        string path,
        string? query,
        Dictionary<string, JsonElement>? body,
        CancellationToken ct
    )
    {
        var bytes = body is null
            ? Array.Empty<byte>()
            : JsonSerializer.SerializeToUtf8Bytes(
                new SortedDictionary<string, JsonElement>(body, StringComparer.Ordinal)
            );
        var subject = SubjectReference(
            call with
            {
                Operation = operation,
                Path = path,
                Body = body,
            }
        );
        try
        {
            return await gateway.SendAsync(
                new PricingGatewayRequest(
                    operation.WbeOperation,
                    operation.Method,
                    operation.WbeRoute,
                    path,
                    query,
                    bytes,
                    call.Actor.Subject,
                    call.Actor.EffectiveRole,
                    call.Actor.HasStepUp,
                    call.Actor.TenantId,
                    subject,
                    call.Correlation,
                    operation.Writes ? call.IdempotencyKey : null
                ),
                ct
            );
        }
        catch (PricingAdminOwnerUnavailableException exception)
        {
            logger.LogWarning(
                exception,
                "pricing owner unavailable operation={Operation}",
                operation.Id
            );
            throw Problem(
                503,
                "PRICING_UNAVAILABLE",
                "The pricing owner is unavailable; retry shortly."
            );
        }
    }

    private static PricingAdminResult Succeeded(PricingGatewayResponse response)
    {
        if (response.Status is >= 200 and < 300)
            return new(response.Status, response.Body, response.ETag);
        throw MapFailure(response);
    }

    private static PricingAdminProblemException MapFailure(PricingGatewayResponse response)
    {
        string? code = null;
        var extras = new Dictionary<string, JsonElement>();
        if (response.Body is { ValueKind: JsonValueKind.Object } problem)
        {
            if (
                problem.TryGetProperty("code", out var value)
                && value.ValueKind == JsonValueKind.String
            )
                code = value.GetString();
            foreach (var name in ExtraMembers)
                if (problem.TryGetProperty(name, out var extra))
                    extras[name] = extra.Clone();
        }
        if (
            code is null
            || !PublishedCodes.Contains(code)
            || !PassThroughStatuses.Contains(response.Status)
        )
            return Problem(
                503,
                "PRICING_UNAVAILABLE",
                "The pricing owner could not complete the request."
            );
        return new(response.Status, code, DetailFor(code), extras);
    }

    private static string DetailFor(string code) =>
        code switch
        {
            "PRICING_FORBIDDEN" => "The role may not perform this pricing operation.",
            "PRICING_STEP_UP_REQUIRED" => "This operation needs a fresh step-up authentication.",
            "PRICING_DRAFT_INVALID" => "The draft breaks pricing rules; see the violations.",
            "PRICING_BELOW_FLOOR" => "The price is below the cost floor.",
            "PRICING_NEEDS_SECOND_CONFIRMATION" =>
                "The change is large and needs a second confirmation.",
            "PRICING_ILLEGAL_TRANSITION" => "The version is not in a state that allows this step.",
            "PRICING_CEILING_ABOVE_MAXIMUM" => "The ceiling is above the deploy-time maximum.",
            "PRICING_CEILING_BELOW_OPEN_RESERVATIONS" =>
                "The ceiling is below what is reserved or settled.",
            "PACKAGE_COMPONENT_NOT_AVAILABLE" =>
                "A package component is not available for this agent.",
            "RECIPE_THREAD_NOT_AUTHORIZED" => "A recipe thread is not authorized in the catalogue.",
            "PRICING_REQUEST_INVALID" => "The request is not valid.",
            "PRICING_NOT_FOUND" => "The pricing version does not exist.",
            "PRICING_VERSION_CONFLICT" => "The version changed since it was read; reload it.",
            "PRICING_IDEMPOTENCY_CONFLICT" => "The idempotency key was used with another request.",
            "PRICING_RATE_LIMITED" => "Too many pricing changes; retry shortly.",
            _ => "The pricing owner could not complete the request.",
        };

    // ----------------------------------------------------------------- C5-04 ceiling administration

    private async Task<PricingAdminResult> AuthorizeAsync(
        Call call,
        string draftId,
        CancellationToken ct
    )
    {
        var read = Operations["getPricingDraft"];
        var draft = Succeeded(
            await SendAsync(
                call,
                read,
                BuildPath(read, new Dictionary<string, string> { ["draftId"] = draftId }),
                null,
                null,
                ct
            )
        );
        if (
            !IsEnvironmentCeiling(
                draft.Body,
                out var environment,
                out var maximum,
                out var state,
                out var versionId
            )
        )
            return await ForwardAsync(call, ct);
        if (
            call.Body!.TryGetValue("effectiveFrom", out var from)
            && from.ValueKind == JsonValueKind.String
            && DateTimeOffset.TryParse(from.GetString(), out var at)
            && at > clock.GetUtcNow()
        )
            throw Problem(
                400,
                "PRICING_REQUEST_INVALID",
                "An environment ceiling takes effect when it is authorized and cannot be scheduled."
            );
        if (state == "EFFECTIVE")
        {
            await ApplyCeilingAsync(
                environment,
                maximum,
                Evidence(draft.Body, versionId),
                false,
                ct
            );
            return draft;
        }
        if (state == "SUBMITTED")
            await ApplyCeilingAsync(environment, maximum, Guid.NewGuid(), true, ct);
        var authorized = await ForwardAsync(call, ct);
        if (state == "SUBMITTED" && authorized.Body is { } body && StateOf(body) == "EFFECTIVE")
            await ApplyCeilingAsync(environment, maximum, Evidence(body, versionId), false, ct);
        return authorized;
    }

    private async Task<PricingAdminResult> LowerCeilingAsync(Call call, CancellationToken ct)
    {
        var body = call.Body!;
        if (
            Text(body, "scope") == EnvironmentCeilingScope
            && Text(body, "ref") is { } environment
            && body.TryGetValue("newMaximumPaise", out var maximum)
            && maximum.ValueKind == JsonValueKind.Number
            && maximum.TryGetInt64(out var paise)
        )
        {
            var check = await ApplyCeilingAsync(environment, paise, call.Correlation, true, ct);
            if (
                check.Outcome == EnvironmentCeilingOutcomes.DryRunOk
                && check.AppliedPaise > check.PreviousPaise
            )
                throw Problem(
                    422,
                    "PRICING_CEILING_ABOVE_MAXIMUM",
                    "A safety operation can only lower the ceiling; raising needs a Founder authorization."
                );
            if (check.Outcome == EnvironmentCeilingOutcomes.DryRunOk)
                await ApplyCeilingAsync(environment, paise, call.Correlation, false, ct);
        }
        return await ForwardAsync(call, ct);
    }

    private async Task<EnvironmentCeilingOutcome> ApplyCeilingAsync(
        string environment,
        long maximumPaise,
        Guid evidenceId,
        bool dryRun,
        CancellationToken ct
    )
    {
        EnvironmentCeilingOutcome outcome;
        try
        {
            outcome = await ceilings.ApplyAsync(
                environment,
                maximumPaise,
                HardMaximumPaise,
                evidenceId,
                clock.GetUtcNow(),
                dryRun,
                ct
            );
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogError(
                exception,
                "environment spend ceiling update failed environment={Environment}",
                environment
            );
            throw Problem(
                503,
                "PRICING_UNAVAILABLE",
                "The environment spend authority is unavailable."
            );
        }
        switch (outcome.Outcome)
        {
            case EnvironmentCeilingOutcomes.BelowExposure:
                throw Problem(
                    409,
                    "PRICING_CEILING_BELOW_OPEN_RESERVATIONS",
                    "The ceiling is below what is reserved, leased or settled in the window.",
                    new Dictionary<string, JsonElement>
                    {
                        ["blockingPaise"] = JsonSerializer.SerializeToElement(
                            outcome.BlockingPaise ?? 0
                        ),
                    }
                );
            case EnvironmentCeilingOutcomes.AboveHardMaximum:
                throw Problem(
                    422,
                    "PRICING_CEILING_ABOVE_MAXIMUM",
                    "The ceiling is above the deploy-time maximum."
                );
            case EnvironmentCeilingOutcomes.AuthorityAbsent:
                logger.LogWarning(
                    "environment spend authority absent environment={Environment}; the operator provisions it",
                    environment
                );
                break;
        }
        return outcome;
    }

    private static bool IsEnvironmentCeiling(
        JsonElement? draft,
        out string environment,
        out long maximum,
        out string state,
        out Guid versionId
    )
    {
        environment = "";
        maximum = 0;
        state = "";
        versionId = Guid.Empty;
        if (
            draft is not { ValueKind: JsonValueKind.Object } root
            || !root.TryGetProperty("kind", out var kind)
            || kind.ValueKind != JsonValueKind.String
            || kind.GetString() != "BUDGET"
            || !root.TryGetProperty("body", out var body)
            || body.ValueKind != JsonValueKind.Object
            || !body.TryGetProperty("scope", out var scope)
            || scope.ValueKind != JsonValueKind.String
            || scope.GetString() != EnvironmentCeilingScope
            || !body.TryGetProperty("ref", out var reference)
            || reference.ValueKind != JsonValueKind.String
            || reference.GetString() is not { Length: > 0 } name
            || !body.TryGetProperty("maximumPaise", out var value)
            || value.ValueKind != JsonValueKind.Number
            || !value.TryGetInt64(out maximum)
            || !root.TryGetProperty("versionId", out var id)
            || id.ValueKind != JsonValueKind.String
            || !Guid.TryParse(id.GetString(), out versionId)
        )
            return false;
        environment = name;
        state = StateOf(root) ?? "";
        return true;
    }

    private static string? StateOf(JsonElement version) =>
        version.ValueKind == JsonValueKind.Object
        && version.TryGetProperty("state", out var state)
        && state.ValueKind == JsonValueKind.String
            ? state.GetString()
            : null;

    private static Guid Evidence(JsonElement? version, Guid fallback) =>
        version is { ValueKind: JsonValueKind.Object } root
        && root.TryGetProperty("evidenceId", out var evidence)
        && evidence.ValueKind == JsonValueKind.String
        && Guid.TryParse(evidence.GetString(), out var id)
        && id != Guid.Empty
            ? id
            : fallback;

    private static PricingAdminProblemException Problem(
        int status,
        string code,
        string detail,
        IReadOnlyDictionary<string, JsonElement>? extras = null
    ) => new(status, code, detail, extras);
}
