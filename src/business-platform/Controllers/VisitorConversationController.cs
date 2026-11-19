// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R003, WC135-R010, WC135-R011
// Implements: architecture/reference/api-specs/visitor-conversation-business-platform.openapi.yaml
// Constitutional basis: C-009, C-023, C-026, C-048, C-049, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Visitor;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>Demo-only simulated-customer request signature (see the OpenAPI VisitorSimulatorAuth scheme).</summary>
public static class VisitorSimulatorSignature
{
    public const string TimestampHeader = "X-Visitor-Timestamp";
    public const string SignatureHeader = "X-Visitor-Signature";
    public static readonly TimeSpan Tolerance = TimeSpan.FromMinutes(5);

    public static string Compute(
        string secret,
        long timestamp,
        string method,
        string path,
        byte[] body
    ) =>
        Convert.ToHexStringLower(
            HMACSHA256.HashData(
                Encoding.UTF8.GetBytes(secret),
                Encoding.UTF8.GetBytes(
                    $"{timestamp}.{method.ToUpperInvariant()}.{path}.{Convert.ToHexStringLower(SHA256.HashData(body))}"
                )
            )
        );

    public static bool Verify(
        string secret,
        string? timestampHeader,
        string? signatureHeader,
        string method,
        string path,
        byte[] body,
        DateTimeOffset now
    )
    {
        if (
            string.IsNullOrEmpty(secret)
            || string.IsNullOrWhiteSpace(signatureHeader)
            || !long.TryParse(timestampHeader, out var timestamp)
        )
            return false;
        var skew = now - DateTimeOffset.FromUnixTimeSeconds(timestamp);
        if (skew.Duration() > Tolerance)
            return false;
        var expected = Encoding.ASCII.GetBytes(Compute(secret, timestamp, method, path, body));
        var supplied = Encoding.ASCII.GetBytes(signatureHeader.Trim().ToLowerInvariant());
        return expected.Length == supplied.Length
            && CryptographicOperations.FixedTimeEquals(expected, supplied);
    }
}

/// <summary>Signed short-lived visitor session token (WEB and MOBILE). Never a tenant or role authority.</summary>
public static class VisitorSessionTokens
{
    public static string Issue(string key, Guid sessionId, Guid tenantId, DateTimeOffset expiresAt)
    {
        var payload = $"v1.{sessionId:N}.{expiresAt.ToUnixTimeSeconds()}";
        return $"{payload}.{Sign(key, payload, tenantId)}";
    }

    public static bool TryValidate(
        string key,
        string token,
        Guid tenantId,
        DateTimeOffset now,
        out Guid sessionId
    )
    {
        sessionId = Guid.Empty;
        var parts = token.Split('.');
        if (
            string.IsNullOrEmpty(key)
            || parts.Length != 4
            || parts[0] != "v1"
            || !Guid.TryParseExact(parts[1], "N", out sessionId)
            || !long.TryParse(parts[2], out var expires)
            || DateTimeOffset.FromUnixTimeSeconds(expires) <= now
        )
            return false;
        var expected = Encoding.ASCII.GetBytes(Sign(key, $"v1.{parts[1]}.{parts[2]}", tenantId));
        var supplied = Encoding.ASCII.GetBytes(parts[3]);
        return expected.Length == supplied.Length
            && CryptographicOperations.FixedTimeEquals(expected, supplied);
    }

    private static string Sign(string key, string payload, Guid tenantId) =>
        Convert.ToHexStringLower(
            HMACSHA256.HashData(
                Encoding.UTF8.GetBytes(key),
                Encoding.UTF8.GetBytes($"{payload}.{tenantId:N}")
            )
        );
}

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record OpenVisitorSessionBody(
    [property: JsonPropertyName("schemaVersion")] string SchemaVersion,
    [property: JsonPropertyName("channel")] string Channel,
    [property: JsonPropertyName("subjectKey")] string? SubjectKey,
    [property: JsonPropertyName("resumeToken")] string? ResumeToken
);

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record VisitorMessageContentBody(
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("text")] string? Text,
    [property: JsonPropertyName("choiceId")] string? ChoiceId
);

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record SendVisitorMessageBody(
    [property: JsonPropertyName("schemaVersion")] string SchemaVersion,
    [property: JsonPropertyName("content")] VisitorMessageContentBody Content,
    [property: JsonPropertyName("expectedCursor")] string? ExpectedCursor
);

[ApiController]
[AllowAnonymous]
[Route("api/v1/visitor")]
public sealed class VisitorConversationController(
    VisitorConversationService service,
    IOptionsMonitor<VisitorConversationOptions> options,
    TimeProvider clock,
    ILogger<VisitorConversationController> logger,
    WhatsAppTenantExecutionScope? tenantExecution = null
) : ControllerBase
{
    private const int MaxBodyBytes = 8 * 1024;
    private static readonly JsonSerializerOptions Json = VisitorJson.Options;

    [HttpPost("sessions")]
    public async Task<IActionResult> OpenAsync(CancellationToken ct)
    {
        var raw = await ReadBodyAsync(ct);
        if (raw is null)
            return Fail("VISITOR_REQUEST_INVALID", 400);
        using var tenant = BeginTenant(out var tenantId, out var failure);
        if (failure is not null)
            return failure;
        var opts = options.CurrentValue;
        if (!opts.IsV2)
            return Fail("VISITOR_DISABLED", 503);
        OpenVisitorSessionBody? body;
        try
        {
            body = JsonSerializer.Deserialize<OpenVisitorSessionBody>(raw, Json);
        }
        catch (JsonException)
        {
            return Fail("VISITOR_REQUEST_INVALID", 400);
        }
        if (
            body is null
            || body.SchemaVersion != "1.0"
            || !VisitorChannels.IsEndpointChannel(body.Channel)
            || body.SubjectKey is { Length: > 64 or < 8 }
            || body.ResumeToken is { Length: > 512 }
        )
            return Fail("VISITOR_REQUEST_INVALID", 400);

        var simulator = IsSimulatorRequest(raw, opts);
        if (body.Channel == VisitorChannels.Simulation)
        {
            if (!simulator || body.SubjectKey is null)
                return Fail("VISITOR_SESSION_REQUIRED", 401);
        }
        else if (!opts.PublicEntryEnabled)
        {
            return Fail("VISITOR_SESSION_REQUIRED", 401);
        }

        try
        {
            var view = await service.OpenSessionAsync(tenantId, body.Channel, body.SubjectKey, ct);
            string? token = null;
            DateTimeOffset? expires = null;
            if (body.Channel != VisitorChannels.Simulation)
            {
                expires = clock.GetUtcNow().AddMinutes(opts.SessionTokenMinutes);
                token = VisitorSessionTokens.Issue(
                    opts.SessionTokenKey,
                    view.SessionId,
                    tenantId,
                    expires.Value
                );
            }
            return StatusCode(
                view.Created ? StatusCodes.Status201Created : StatusCodes.Status200OK,
                ToSession(view, token, expires)
            );
        }
        catch (VisitorConversationException exception)
        {
            return Fail(exception);
        }
    }

    [HttpGet("sessions/{sessionId:guid}")]
    public async Task<IActionResult> GetAsync(Guid sessionId, CancellationToken ct)
    {
        using var tenant = BeginTenant(out var tenantId, out var failure);
        if (failure is not null)
            return failure;
        var opts = options.CurrentValue;
        if (!opts.IsV2)
            return Fail("VISITOR_DISABLED", 503);
        var auth = Authenticate(Array.Empty<byte>(), sessionId, tenantId, opts);
        if (auth is null)
            return Fail("VISITOR_SESSION_REQUIRED", 401);
        try
        {
            var view = await service.GetSessionAsync(tenantId, sessionId, ct);
            if (!ChannelAllowed(auth, view.Channel))
                return Fail("VISITOR_SESSION_NOT_FOUND", 404);
            return Ok(ToSession(view, null, null));
        }
        catch (VisitorConversationException exception)
        {
            return Fail(exception);
        }
    }

    [HttpGet("sessions/{sessionId:guid}/messages")]
    public async Task<IActionResult> ListAsync(
        Guid sessionId,
        [FromQuery] string? cursor,
        [FromQuery] int limit = 40,
        CancellationToken ct = default
    )
    {
        using var tenant = BeginTenant(out var tenantId, out var failure);
        if (failure is not null)
            return failure;
        var opts = options.CurrentValue;
        if (!opts.IsV2)
            return Fail("VISITOR_DISABLED", 503);
        if (Request.Query.Keys.Any(key => key is not "cursor" and not "limit"))
            return Fail("VISITOR_REQUEST_INVALID", 400);
        var auth = Authenticate(Array.Empty<byte>(), sessionId, tenantId, opts);
        if (auth is null)
            return Fail("VISITOR_SESSION_REQUIRED", 401);
        try
        {
            var view = await service.GetSessionAsync(tenantId, sessionId, ct);
            if (!ChannelAllowed(auth, view.Channel))
                return Fail("VISITOR_SESSION_NOT_FOUND", 404);
            var page = await service.ListAsync(tenantId, sessionId, cursor, limit, ct);
            return Ok(
                new
                {
                    schemaVersion = "1.0",
                    items = page.Items.Select(ToTranscriptItem),
                    nextCursor = page.NextCursor,
                }
            );
        }
        catch (VisitorConversationException exception)
        {
            return Fail(exception);
        }
    }

    [HttpPost("sessions/{sessionId:guid}/messages")]
    public async Task<IActionResult> SendAsync(Guid sessionId, CancellationToken ct)
    {
        var raw = await ReadBodyAsync(ct);
        if (raw is null)
            return Fail("VISITOR_REQUEST_INVALID", 400);
        using var tenant = BeginTenant(out var tenantId, out var failure);
        if (failure is not null)
            return failure;
        var opts = options.CurrentValue;
        if (!opts.IsV2)
            return Fail("VISITOR_DISABLED", 503);
        var auth = Authenticate(raw, sessionId, tenantId, opts);
        if (auth is null)
            return Fail("VISITOR_SESSION_REQUIRED", 401);
        if (!Guid.TryParse(Request.Headers["Idempotency-Key"].FirstOrDefault(), out var key))
            return Fail("VISITOR_REQUEST_INVALID", 400);
        SendVisitorMessageBody? body;
        try
        {
            body = JsonSerializer.Deserialize<SendVisitorMessageBody>(raw, Json);
        }
        catch (JsonException)
        {
            return Fail("VISITOR_REQUEST_INVALID", 400);
        }
        var input = ToInput(body);
        if (input is null)
            return Fail("VISITOR_REQUEST_INVALID", 400);
        try
        {
            var view = await service.GetSessionAsync(tenantId, sessionId, ct);
            if (!ChannelAllowed(auth, view.Channel))
                return Fail("VISITOR_SESSION_NOT_FOUND", 404);
            var turn = await service.SendAsync(tenantId, sessionId, key, input, ct);
            return Ok(
                new
                {
                    schemaVersion = "1.0",
                    sessionId = turn.SessionId,
                    messageId = turn.MessageId,
                    cursor = turn.Cursor,
                    state = turn.State,
                    outcome = turn.Outcome,
                    captured = ToCaptured(turn.Captured),
                    reply = turn.Reply,
                }
            );
        }
        catch (VisitorConversationException exception)
        {
            return Fail(exception);
        }
    }

    /// <summary>The shared link: records the tap, then sends the visitor on to the portal.</summary>
    [HttpGet("handoffs/{reference}/open")]
    public async Task<IActionResult> OpenAsync(string reference, CancellationToken ct)
    {
        using var tenant = BeginTenant(out var tenantId, out var failure);
        if (failure is not null)
            return failure;
        var opts = options.CurrentValue;
        if (!opts.IsV2)
            return Fail("VISITOR_DISABLED", 503);
        try
        {
            await service.TapHandoffAsync(tenantId, reference, ct);
        }
        catch (VisitorConversationException exception)
        {
            return Fail(exception);
        }
        var separator = opts.HandoffBaseUrl.Contains('?') ? '&' : '?';
        return Redirect($"{opts.HandoffBaseUrl}{separator}lead={Uri.EscapeDataString(reference)}");
    }

    [HttpPost("handoffs/{reference}/tap")]
    public async Task<IActionResult> TapAsync(string reference, CancellationToken ct)
    {
        using var tenant = BeginTenant(out var tenantId, out var failure);
        if (failure is not null)
            return failure;
        if (!options.CurrentValue.IsV2)
            return Fail("VISITOR_DISABLED", 503);
        try
        {
            var recorded = await service.TapHandoffAsync(tenantId, reference, ct);
            return Ok(new { schemaVersion = "1.0", recorded });
        }
        catch (VisitorConversationException exception)
        {
            return Fail(exception);
        }
    }

    // ── Helpers ─────────────────────────────────────────────────────────────────────────────────

    private sealed record Principal(bool Simulator, Guid? SessionId);

    private Principal? Authenticate(
        byte[] body,
        Guid sessionId,
        Guid tenantId,
        VisitorConversationOptions opts
    )
    {
        if (opts.SimulatorEnabled && IsSimulatorRequest(body, opts))
            return new Principal(true, null);
        var header = Request.Headers.Authorization.ToString();
        if (
            opts.PublicEntryEnabled
            && header.StartsWith("Bearer ", StringComparison.Ordinal)
            && VisitorSessionTokens.TryValidate(
                opts.SessionTokenKey,
                header["Bearer ".Length..].Trim(),
                tenantId,
                clock.GetUtcNow(),
                out var tokenSession
            )
            && tokenSession == sessionId
        )
            return new Principal(false, tokenSession);
        return null;
    }

    private static bool ChannelAllowed(Principal principal, string channel) =>
        principal.Simulator
            ? channel == VisitorChannels.Simulation
            : channel != VisitorChannels.Simulation;

    private bool IsSimulatorRequest(byte[] body, VisitorConversationOptions opts) =>
        opts.SimulatorEnabled
        && VisitorSimulatorSignature.Verify(
            opts.SimulatorSecret,
            Request.Headers[VisitorSimulatorSignature.TimestampHeader].FirstOrDefault(),
            Request.Headers[VisitorSimulatorSignature.SignatureHeader].FirstOrDefault(),
            Request.Method,
            Request.Path.Value ?? string.Empty,
            body,
            clock.GetUtcNow()
        );

    private async Task<byte[]?> ReadBodyAsync(CancellationToken ct)
    {
        if (Request.ContentLength > MaxBodyBytes)
            return null;
        using var stream = new MemoryStream();
        var buffer = new byte[2048];
        while (true)
        {
            var read = await Request.Body.ReadAsync(buffer, ct);
            if (read == 0)
                break;
            if (stream.Length + read > MaxBodyBytes)
                return null;
            await stream.WriteAsync(buffer.AsMemory(0, read), ct);
        }
        return stream.ToArray();
    }

    /// <summary>
    /// Resolves the tenant on the server and sets it for row-level security; never from the request.
    /// The WhatsApp activation tenant is used when active, otherwise the configured default tenant.
    /// </summary>
    private IDisposable? BeginTenant(out Guid tenantId, out IActionResult? failure)
    {
        failure = null;
        tenantId = Guid.Empty;
        IDisposable? scope = null;
        try
        {
            scope = tenantExecution?.Begin();
            if (tenantExecution?.ServiceTenantId is { } active)
                tenantId = active;
        }
        catch (WhatsAppCapabilityUnavailableException)
        {
            scope = null;
        }
        if (tenantId == Guid.Empty && options.CurrentValue.DefaultTenantId is { } fallback)
            tenantId = fallback;
        if (tenantId == Guid.Empty)
        {
            failure = Fail("VISITOR_UNAVAILABLE", 503);
            return scope;
        }
        HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString("D");
        return scope;
    }

    private static VisitorInput? ToInput(SendVisitorMessageBody? body)
    {
        if (body is null || body.SchemaVersion != "1.0" || body.Content is null)
            return null;
        if (body.ExpectedCursor is { Length: > 256 })
            return null;
        var content = body.Content;
        return content.Type switch
        {
            "TEXT"
                when !string.IsNullOrWhiteSpace(content.Text)
                    && content.Text.Length <= 1000
                    && content.ChoiceId is null => VisitorInput.FromText(content.Text),
            "CHOICE"
                when !string.IsNullOrWhiteSpace(content.ChoiceId)
                    && content.ChoiceId.Length <= 64
                    && content.Text is null => VisitorInput.FromChoice(content.ChoiceId),
            _ => null,
        };
    }

    private static object ToCaptured(VisitorCaptured captured) =>
        new
        {
            businessDomain = captured.BusinessDomain,
            city = captured.City,
            goalCode = captured.GoalCode,
            hasName = captured.HasName,
            hasEmail = captured.HasEmail,
        };

    private static object ToSession(
        VisitorSessionView view,
        string? token,
        DateTimeOffset? expires
    ) =>
        new
        {
            schemaVersion = "1.0",
            sessionId = view.SessionId,
            channel = view.Channel,
            state = view.State,
            outcome = view.Outcome,
            captured = ToCaptured(view.Captured),
            sessionToken = token,
            expiresAt = expires,
            reply = view.Reply,
        };

    private static object ToTranscriptItem(VisitorTranscriptEntry entry) =>
        new
        {
            sequence = entry.Sequence,
            role = entry.Role,
            content = entry.Content is null
                ? null
                : new
                {
                    type = entry.Content.Kind,
                    text = entry.Content.Text,
                    choiceId = entry.Content.ChoiceId,
                },
            reply = entry.Reply,
            at = entry.At,
        };

    private IActionResult Fail(VisitorConversationException exception)
    {
        if (exception.RetryAfterSeconds is { } retry)
            Response.Headers.RetryAfter = retry.ToString();
        return Fail(exception.Code, exception.Status, exception.RetryAfterSeconds);
    }

    private IActionResult Fail(string code, int status, int? retryAfter = null)
    {
        var correlationId = Guid.NewGuid();
        logger.LogInformation(
            "visitor.response.problem status={Status} code={Code} correlationId={CorrelationId}",
            status,
            code,
            correlationId
        );
        var problem = new Dictionary<string, object?>
        {
            ["type"] = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
            ["title"] = code,
            ["status"] = status,
            ["code"] = code,
            ["correlationId"] = correlationId,
        };
        if (retryAfter is { } seconds)
            problem["retryAfterSeconds"] = seconds;
        return new ObjectResult(problem)
        {
            StatusCode = status,
            ContentTypes = { "application/problem+json" },
        };
    }
}
