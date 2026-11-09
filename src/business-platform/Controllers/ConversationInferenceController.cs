using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Grpc.Core;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[AllowAnonymous]
[Route("internal/v1/conversation-inference")]
public sealed class ConversationInferenceController(
    InferenceWorkloadAuthority authority,
    IConversationInferenceOwner owner,
    ILogger<ConversationInferenceController> logger
) : ControllerBase
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = false,
        UnmappedMemberHandling = System.Text.Json.Serialization.JsonUnmappedMemberHandling.Disallow,
    };

    [HttpPost("resolve")]
    [RequestSizeLimit(131072)]
    public Task<IActionResult> Resolve([FromBody] JsonElement body, CancellationToken ct) =>
        Execute(
            body,
            "resolve",
            "resolveConversationInference",
            (caller, value) => owner.ResolveAsync(caller, value, ct),
            ct
        );

    [HttpPost("reserve")]
    [RequestSizeLimit(131072)]
    public Task<IActionResult> Reserve([FromBody] JsonElement body, CancellationToken ct) =>
        Execute(
            body,
            "reserve",
            "reserveConversationInference",
            (caller, value) => owner.ReserveAsync(caller, value, ct),
            ct
        );

    [HttpPost("reconcile")]
    [RequestSizeLimit(131072)]
    public Task<IActionResult> Reconcile([FromBody] JsonElement body, CancellationToken ct) =>
        Execute(
            body,
            "reconcile",
            "reconcileConversationInference",
            (caller, value) => owner.ReconcileAsync(caller, value, ct),
            ct
        );

    [HttpPost("read-content")]
    [RequestSizeLimit(131072)]
    public Task<IActionResult> ReadContent([FromBody] JsonElement body, CancellationToken ct) =>
        ExecuteRequest<ConversationInferenceContentReadRequest, ConversationInferenceContentReadV1>(
            body,
            "read-content",
            "readConversationInferenceContent",
            (caller, value) => owner.ReadContentAsync(caller, value, ct),
            ct,
            "CONVERSATION_CONTENT_RECOVERY"
        );

    [HttpPost("settle")]
    [RequestSizeLimit(131072)]
    public Task<IActionResult> Settle([FromBody] JsonElement body, CancellationToken ct) =>
        Execute(
            body,
            "settle",
            "settleConversationInference",
            async (caller, value) =>
            {
                await owner.SettleAsync(caller, value, false, ct);
                return new ConversationInferenceSettlementV1("SETTLED");
            },
            ct
        );

    [HttpPost("release")]
    [RequestSizeLimit(131072)]
    public Task<IActionResult> Release([FromBody] JsonElement body, CancellationToken ct) =>
        Execute(
            body,
            "release",
            "releaseConversationInference",
            async (caller, value) =>
            {
                await owner.SettleAsync(caller, value, true, ct);
                return new ConversationInferenceSettlementV1("RELEASED");
            },
            ct
        );

    private async Task<IActionResult> Execute<T>(
        JsonElement body,
        string suffix,
        string operation,
        Func<InferenceCaller, ConversationInferenceRequest, Task<T>> action,
        CancellationToken ct
    ) => await ExecuteRequest(body, suffix, operation, action, ct);

    private async Task<IActionResult> ExecuteRequest<TRequest, TResponse>(
        JsonElement body,
        string suffix,
        string operation,
        Func<InferenceCaller, TRequest, Task<TResponse>> action,
        CancellationToken ct,
        string purpose = "CONVERSATION_INFERENCE_OWNER"
    )
    {
        try
        {
            RuntimeEventStreamReader.ValidateUniqueProperties(body);
            var canonical = AgentAdmissionCanonicalizer.Canonicalize(body);
            var digest = Convert.ToHexStringLower(
                SHA256.HashData(Encoding.UTF8.GetBytes(canonical))
            );
            var caller = await authority.RequireAsync(
                HttpContext,
                $"/internal/v1/conversation-inference/{suffix}",
                operation,
                digest,
                ct,
                purpose
            );
            var value =
                body.Deserialize<TRequest>(Json)
                ?? throw new JsonException("Inference request is required.");
            var original = value switch
            {
                ConversationInferenceRequest direct => direct,
                ConversationInferenceContentReadRequest read when read.Permission is not null =>
                    read.Original,
                _ => null,
            };
            if (
                original is null
                || original.OperationalMandate is null
                || original.RequestDigest is null
                || original.InputDigest is null
                || original.InputLanguage is null
            )
                throw new JsonException("Inference authority is required.");
            return Ok(await action(caller, value));
        }
        catch (Exception error)
            when (error is ConversationNotAccessibleException or ConstitutionalActionDeniedException
            )
        {
            logger.LogWarning(
                "Inference owner denied operation {Operation}: {Error}",
                operation,
                error.GetType().Name
            );
            return StatusCode(403, new { code = "INFERENCE_AUTHORITY_DENIED" });
        }
        catch (Exception error)
            when (error
                    is JsonException
                        or ConversationStateConflictException
                        or OperationalMandateUnavailableException
            )
        {
            logger.LogWarning(
                "Inference binding rejected for {Operation}: {Error}",
                operation,
                error.GetType().Name
            );
            return Conflict(new { code = "INFERENCE_BINDING_CONFLICT" });
        }
        catch (ConversationStoppedException)
        {
            return StatusCode(423, new { code = "INFERENCE_STOPPED" });
        }
        catch (WhatsAppCapabilityUnavailableException error)
            when (error.ReasonCode == "MODEL_CONCURRENCY_DENIED")
        {
            logger.LogWarning("Inference admission is waiting for the shared dispatch owner.");
            Response.Headers.RetryAfter = "5";
            Response.Headers["X-Inference-State"] = "QUEUED";
            return StatusCode(503, new { code = "INFERENCE_BUSY" });
        }
        catch (Exception error)
            when (error
                    is ConversationExecutionUnavailableException
                        or IdentityConstitutionalUnavailableException
                        or WhatsAppCapabilityUnavailableException
                        or RpcException
            )
        {
            logger.LogWarning(
                "Inference dependency unavailable for {Operation}: {Error}",
                operation,
                error.GetType().Name
            );
            return StatusCode(503, new { code = "INFERENCE_DEPENDENCY_UNAVAILABLE" });
        }
    }
}
