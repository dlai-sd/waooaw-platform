// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Authorize]
[CustomerIdentityRoute(requiresMembership: true)]
[RequestSizeLimit(65536)]
[Route("api/v1/employment/relationships/{relationshipId:guid}")]
public sealed class WorkbenchController(
    EmploymentRelationshipService relationships,
    WorkbenchProjectionService projection,
    WorkbenchCommandService commands,
    IOptions<WorkbenchOptions> options
) : ControllerBase
{
    private const string ProblemTitle = "The workbench request could not be completed";
    private const string StrongAuthDetail = "A fresh strong sign-in is required for this action.";

    private static readonly JsonSerializerOptions StrictJson = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = System.Text.Json.Serialization.JsonUnmappedMemberHandling.Disallow,
    };

    private sealed record Call(
        WorkbenchContext Context,
        ChannelCapabilities Capabilities,
        Guid IdempotencyKey
    );

    [HttpGet("workbench")]
    public Task<IActionResult> GetWorkbenchAsync(Guid relationshipId, CancellationToken ct) =>
        ReadAsync(
            relationshipId,
            (call, token) => projection.BuildAsync(call.Context, call.Capabilities, token),
            ct
        );

    [HttpGet("workbench/goals")]
    public Task<IActionResult> ListGoalsAsync(
        Guid relationshipId,
        [FromQuery] string? cursor,
        [FromQuery] int? limit,
        CancellationToken ct
    )
    {
        var page = WorkbenchPaging.Parse(cursor, limit, out var problem);
        return ReadAsync(
            relationshipId,
            (call, token) => projection.ListGoalsAsync(call.Context, page, token),
            ct,
            problem
        );
    }

    [HttpPost("workbench/goals")]
    public Task<IActionResult> CreateGoalAsync(Guid relationshipId, CancellationToken ct) =>
        CommandAsync<CreateWorkbenchGoalRequest, WorkbenchCommandReceipt>(
            relationshipId,
            false,
            (call, request, token) =>
                commands.CreateGoalAsync(call.Context, call.IdempotencyKey, request, token),
            ct
        );

    [HttpGet("workbench/goals/{goalId:guid}")]
    public Task<IActionResult> GetGoalAsync(
        Guid relationshipId,
        Guid goalId,
        CancellationToken ct
    ) =>
        ReadAsync(
            relationshipId,
            (call, token) => projection.GetGoalAsync(call.Context, goalId, token),
            ct
        );

    [HttpPost("workbench/goals/{goalId:guid}/revisions")]
    public Task<IActionResult> ReviseGoalAsync(
        Guid relationshipId,
        Guid goalId,
        CancellationToken ct
    ) =>
        CommandAsync<ReviseWorkbenchGoalRequest, WorkbenchCommandReceipt>(
            relationshipId,
            false,
            (call, request, token) =>
                commands.ReviseGoalAsync(call.Context, call.IdempotencyKey, goalId, request, token),
            ct
        );

    [HttpGet("workbench/goals/{goalId:guid}/versions")]
    public Task<IActionResult> ListGoalVersionsAsync(
        Guid relationshipId,
        Guid goalId,
        [FromQuery] string? cursor,
        [FromQuery] int? limit,
        CancellationToken ct
    )
    {
        var page = WorkbenchPaging.Parse(cursor, limit, out var problem);
        return ReadAsync(
            relationshipId,
            (call, token) => projection.ListGoalVersionsAsync(call.Context, goalId, page, token),
            ct,
            problem
        );
    }

    [HttpGet("workbench/plans/current")]
    public Task<IActionResult> GetCurrentPlanAsync(Guid relationshipId, CancellationToken ct) =>
        ReadAsync(
            relationshipId,
            (call, token) => projection.GetCurrentPlanAsync(call.Context, token),
            ct
        );

    [HttpPost("workbench/plans")]
    public Task<IActionResult> ProposePlanAsync(Guid relationshipId, CancellationToken ct) =>
        CommandAsync<ProposeWorkbenchPlanRequest, WorkbenchCommandReceipt>(
            relationshipId,
            false,
            (call, request, token) =>
                commands.ProposePlanAsync(call.Context, call.IdempotencyKey, request, token),
            ct
        );

    [HttpPost("workbench/plans/{planVersion}/accept")]
    public Task<IActionResult> AcceptPlanAsync(
        Guid relationshipId,
        string planVersion,
        CancellationToken ct
    ) =>
        CommandAsync<AcceptWorkbenchPlanRequest, WorkbenchCommandReceipt>(
            relationshipId,
            true,
            (call, request, token) =>
                commands.AcceptPlanAsync(
                    call.Context,
                    call.IdempotencyKey,
                    planVersion,
                    request,
                    token
                ),
            ct
        );

    [HttpGet("workbench/capabilities")]
    public Task<IActionResult> ListCapabilitiesAsync(Guid relationshipId, CancellationToken ct) =>
        ReadAsync(
            relationshipId,
            (call, token) => projection.ListCapabilitiesAsync(call.Context, token),
            ct
        );

    [HttpPost("workbench/capabilities/{skillId}/commands")]
    public Task<IActionResult> CommandCapabilityAsync(
        Guid relationshipId,
        string skillId,
        CancellationToken ct
    ) =>
        CommandAsync<WorkbenchCapabilityCommandRequest, WorkbenchCapabilityCommandResult>(
            relationshipId,
            true,
            (call, request, token) =>
                commands.CommandCapabilityAsync(
                    call.Context,
                    call.IdempotencyKey,
                    skillId,
                    request,
                    token
                ),
            ct
        );

    [HttpGet("workbench/work-items")]
    public Task<IActionResult> ListWorkItemsAsync(
        Guid relationshipId,
        [FromQuery] string? cursor,
        [FromQuery] int? limit,
        CancellationToken ct
    )
    {
        var page = WorkbenchPaging.Parse(cursor, limit, out var problem);
        return ReadAsync(
            relationshipId,
            (call, token) => projection.ListWorkItemsAsync(call.Context, page, token),
            ct,
            problem
        );
    }

    [HttpGet("workbench/decisions")]
    public Task<IActionResult> ListDecisionsAsync(
        Guid relationshipId,
        [FromQuery] string? cursor,
        [FromQuery] int? limit,
        CancellationToken ct
    )
    {
        var page = WorkbenchPaging.Parse(cursor, limit, out var problem);
        return ReadAsync(
            relationshipId,
            (call, token) =>
                projection.ListDecisionsAsync(call.Context, call.Capabilities, page, token),
            ct,
            problem
        );
    }

    [HttpPost("workbench/decisions/{decisionId:guid}/resolve")]
    public Task<IActionResult> ResolveDecisionAsync(
        Guid relationshipId,
        Guid decisionId,
        CancellationToken ct
    ) =>
        CommandAsync<ResolveWorkbenchDecisionRequest, WorkbenchCommandReceipt>(
            relationshipId,
            true,
            (call, request, token) =>
                commands.ResolveDecisionAsync(
                    call.Context,
                    call.IdempotencyKey,
                    decisionId,
                    request,
                    token
                ),
            ct
        );

    [HttpGet("workbench/monitor")]
    public Task<IActionResult> GetMonitorAsync(Guid relationshipId, CancellationToken ct) =>
        ReadAsync(
            relationshipId,
            (call, token) => projection.GetMonitorAsync(call.Context, call.Capabilities, token),
            ct
        );

    [HttpGet("workbench/monitor/narratives")]
    public Task<IActionResult> ListNarrativesAsync(
        Guid relationshipId,
        [FromQuery] string? cursor,
        [FromQuery] int? limit,
        CancellationToken ct
    )
    {
        var page = WorkbenchPaging.Parse(cursor, limit, out var problem);
        return ReadAsync(
            relationshipId,
            (call, token) => projection.ListNarrativesAsync(call.Context, page, token),
            ct,
            problem
        );
    }

    [HttpGet("workbench/wallet")]
    public Task<IActionResult> GetWalletAsync(Guid relationshipId, CancellationToken ct) =>
        ReadAsync(
            relationshipId,
            (call, token) => projection.GetWalletAsync(call.Context, token),
            ct
        );

    [HttpPost("workbench/topups")]
    public Task<IActionResult> CreateTopupAsync(Guid relationshipId, CancellationToken ct) =>
        CommandAsync<CreateWorkbenchTopupRequest, WorkbenchTopupReceipt>(
            relationshipId,
            true,
            (call, request, token) =>
                commands.CreateTopupAsync(call.Context, call.IdempotencyKey, request, token),
            ct
        );

    [HttpGet("workbench/evidence")]
    public Task<IActionResult> ListEvidenceAsync(
        Guid relationshipId,
        [FromQuery] string? cursor,
        [FromQuery] int? limit,
        CancellationToken ct
    )
    {
        var page = WorkbenchPaging.Parse(cursor, limit, out var problem);
        return ReadAsync(
            relationshipId,
            (call, token) => projection.ListEvidenceAsync(call.Context, page, token),
            ct,
            problem
        );
    }

    [HttpPost("workbench/evidence/exports")]
    public Task<IActionResult> ExportEvidenceAsync(Guid relationshipId, CancellationToken ct) =>
        CommandAsync<ExportWorkbenchEvidenceRequest, WorkbenchCommandReceipt>(
            relationshipId,
            false,
            (call, request, token) =>
                commands.ExportEvidenceAsync(call.Context, call.IdempotencyKey, request, token),
            ct
        );

    [HttpPost("workbench/controls/stop")]
    public Task<IActionResult> StopAsync(Guid relationshipId, CancellationToken ct) =>
        CommandAsync<WorkbenchControlRequest, WorkbenchCommandReceipt>(
            relationshipId,
            false,
            (call, request, token) =>
                commands.StopAsync(call.Context, call.IdempotencyKey, request, token),
            ct
        );

    [HttpPost("workbench/controls/pause")]
    public Task<IActionResult> PauseAsync(Guid relationshipId, CancellationToken ct) =>
        CommandAsync<WorkbenchControlRequest, WorkbenchCommandReceipt>(
            relationshipId,
            false,
            (call, request, token) =>
                commands.PauseAsync(call.Context, call.IdempotencyKey, request, token),
            ct
        );

    [HttpPost("workbench/handoffs")]
    public Task<IActionResult> CreateHandoffAsync(Guid relationshipId, CancellationToken ct) =>
        CommandAsync<CreateWorkbenchHandoffRequest, WorkbenchHandoff>(
            relationshipId,
            false,
            (call, request, token) =>
                commands.CreateHandoffAsync(call.Context, call.IdempotencyKey, request, token),
            ct,
            StatusCodes.Status201Created
        );

    [HttpPost("workbench/handoffs/consume")]
    public Task<IActionResult> ConsumeHandoffAsync(Guid relationshipId, CancellationToken ct) =>
        CommandAsync<ConsumeWorkbenchHandoffRequest, WorkbenchHandoffConsumption>(
            relationshipId,
            false,
            async (call, request, token) =>
                new WorkbenchCommandResult<WorkbenchHandoffConsumption>(
                    await commands.ConsumeHandoffAsync(call.Context, request, token),
                    false
                ),
            ct,
            StatusCodes.Status200OK,
            requireKey: false
        );

    [HttpPost("subscription/changes")]
    public Task<IActionResult> ChangeSubscriptionAsync(Guid relationshipId, CancellationToken ct) =>
        CommandAsync<SubscriptionChangeRequest, SubscriptionChangeReceipt>(
            relationshipId,
            true,
            (call, request, token) =>
                commands.ChangeSubscriptionAsync(call.Context, call.IdempotencyKey, request, token),
            ct
        );

    private async Task<IActionResult> ReadAsync<T>(
        Guid relationshipId,
        Func<Call, CancellationToken, Task<T>> read,
        CancellationToken ct,
        string? invalid = null
    )
    {
        var correlation = CorrelationOf(requireHeader: false, out var correlationInvalid);
        if (!options.Value.Enabled)
            return Problem(404, WorkbenchProblemCodes.Disabled, correlation);
        if (correlationInvalid)
            return Problem(
                400,
                WorkbenchProblemCodes.RequestInvalid,
                correlation,
                "X-Correlation-ID must be a UUID."
            );
        if (invalid is not null)
            return Problem(400, WorkbenchProblemCodes.RequestInvalid, correlation, invalid);
        try
        {
            var prepared = await PrepareAsync(
                relationshipId,
                correlation,
                requireKey: false,
                strongAuth: false,
                ct
            );
            if (prepared.Failure is not null)
                return prepared.Failure;
            var result = await read(prepared.Call!, ct);
            if (result is null)
                return Problem(
                    404,
                    WorkbenchProblemCodes.RequestInvalid,
                    correlation,
                    "The resource was not found."
                );
            var relationship = await relationships.GetAsync(
                prepared.Call!.Context.TenantId,
                relationshipId,
                ct
            );
            if (relationship is not null)
                Response.Headers.ETag = $"\"{WorkbenchProjectionService.VersionOf(relationship)}\"";
            return Ok(result);
        }
        catch (Exception exception) when (ProblemFor(exception, correlation) is { } problem)
        {
            return problem;
        }
    }

    private async Task<IActionResult> CommandAsync<TRequest, TBody>(
        Guid relationshipId,
        bool strongAuth,
        Func<Call, TRequest, CancellationToken, Task<WorkbenchCommandResult<TBody>>> execute,
        CancellationToken ct,
        int createdStatus = StatusCodes.Status202Accepted,
        bool requireKey = true
    )
        where TRequest : class
        where TBody : class
    {
        var correlation = CorrelationOf(requireHeader: true, out var correlationInvalid);
        if (!options.Value.Enabled)
            return Problem(404, WorkbenchProblemCodes.Disabled, correlation);
        if (correlationInvalid)
            return Problem(
                400,
                WorkbenchProblemCodes.RequestInvalid,
                correlation,
                "X-Correlation-ID is required and must be a UUID."
            );
        try
        {
            var prepared = await PrepareAsync(
                relationshipId,
                correlation,
                requireKey,
                strongAuth,
                ct
            );
            if (prepared.Failure is not null)
                return prepared.Failure;
            var request = await ReadBodyAsync<TRequest>(ct);
            if (request is null)
                return Problem(
                    400,
                    WorkbenchProblemCodes.RequestInvalid,
                    correlation,
                    "The request body is missing or does not match the contract."
                );
            var result = await execute(prepared.Call!, request, ct);
            return StatusCode(
                result.Replayed ? StatusCodes.Status200OK : createdStatus,
                result.Body
            );
        }
        catch (Exception exception) when (ProblemFor(exception, correlation) is { } problem)
        {
            return problem;
        }
    }

    private sealed record Prepared(Call? Call, IActionResult? Failure);

    private async Task<Prepared> PrepareAsync(
        Guid relationshipId,
        string correlation,
        bool requireKey,
        bool strongAuth,
        CancellationToken ct
    )
    {
        var capabilities = ChannelCapabilities.Parse(
            Request.Headers[ChannelCapabilities.HeaderName].FirstOrDefault()
        );
        if (capabilities is null)
            return Fail(
                400,
                WorkbenchProblemCodes.RequestInvalid,
                correlation,
                "X-Experience-Capabilities is invalid."
            );
        var key = Guid.Empty;
        if (
            requireKey
            && !Guid.TryParse(Request.Headers["Idempotency-Key"].FirstOrDefault(), out key)
        )
            return Fail(
                400,
                WorkbenchProblemCodes.RequestInvalid,
                correlation,
                "Idempotency-Key must be a UUID."
            );
        if (
            !HttpContext.Items.TryGetValue(
                TenantIsolationMiddleware.TenantIdItemKey,
                out var tenant
            )
            || tenant is not string tenantText
            || !Guid.TryParse(tenantText, out var tenantId)
        )
            return Fail(
                403,
                WorkbenchProblemCodes.RequestInvalid,
                correlation,
                "The relationship is not accessible."
            );
        var actor =
            User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        if (!Guid.TryParse(actor, out var participantId))
            return Fail(
                403,
                WorkbenchProblemCodes.RequestInvalid,
                correlation,
                "The relationship is not accessible."
            );
        var role = await relationships.GetActiveRoleAsync(
            tenantId,
            relationshipId,
            participantId,
            ct
        );
        if (role is null)
            return Fail(
                403,
                WorkbenchProblemCodes.RequestInvalid,
                correlation,
                "The relationship is not accessible."
            );
        if (strongAuth && !HasFreshAal3())
            return Fail(403, WorkbenchProblemCodes.RequestInvalid, correlation, StrongAuthDetail);
        var context = await projection.NarrowAsync(
            new WorkbenchContext(
                tenantId,
                relationshipId,
                actor!,
                participantId,
                role.Value,
                WorkbenchAudiences.FromRole(role.Value),
                correlation
            ),
            ct
        );
        return new Prepared(new Call(context, capabilities, key), null);
    }

    private Prepared Fail(int status, string code, string correlation, string detail) =>
        new(null, Problem(status, code, correlation, detail));

    private async Task<T?> ReadBodyAsync<T>(CancellationToken ct)
        where T : class
    {
        try
        {
            return await JsonSerializer.DeserializeAsync<T>(Request.Body, StrictJson, ct);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private string CorrelationOf(bool requireHeader, out bool invalid)
    {
        var header = Request.Headers["X-Correlation-ID"].FirstOrDefault();
        if (header is null)
        {
            invalid = requireHeader;
            return User.FindFirstValue("correlation_id") ?? HttpContext.TraceIdentifier;
        }
        invalid = !Guid.TryParse(header, out var parsed);
        return invalid
            ? User.FindFirstValue("correlation_id") ?? HttpContext.TraceIdentifier
            : parsed.ToString("D");
    }

    private bool HasFreshAal3()
    {
        if (
            !string.Equals(
                User.FindFirstValue("authentication_assurance"),
                "AAL3_FRESH",
                StringComparison.Ordinal
            ) || !long.TryParse(User.FindFirstValue("auth_time"), out var unixTime)
        )
            return false;
        var age = DateTimeOffset.UtcNow - DateTimeOffset.FromUnixTimeSeconds(unixTime);
        return age >= TimeSpan.FromSeconds(-60) && age <= TimeSpan.FromMinutes(5);
    }

    private ObjectResult? ProblemFor(Exception exception, string correlation) =>
        exception switch
        {
            WorkbenchException failure => Problem(
                failure.Status,
                failure.Code,
                correlation,
                failure.Detail
            ),
            KeyNotFoundException => Problem(
                404,
                WorkbenchProblemCodes.RequestInvalid,
                correlation,
                "The resource was not found."
            ),
            OperationCanceledException => null,
            _ => Problem(
                503,
                WorkbenchProblemCodes.Unavailable,
                correlation,
                "A required owner did not answer. Nothing was changed; try again."
            ),
        };

    private ObjectResult Problem(int status, string code, string correlation, string? detail = null)
    {
        if (status == StatusCodes.Status429TooManyRequests)
            Response.Headers.RetryAfter = "60";
        Response.Headers["X-Correlation-ID"] = correlation;
        var response = StatusCode(
            status,
            new WorkbenchProblem(
                $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
                ProblemTitle,
                status,
                code,
                correlation,
                detail
            )
        );
        response.ContentTypes.Add("application/problem+json");
        return response;
    }
}
