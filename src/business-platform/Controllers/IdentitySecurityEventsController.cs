// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S12
// Constitutional basis: C-002, C-005, C-007, C-027, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed class IdentitySecurityEventIngestOptions
{
    public const string SectionName = "IdentitySecurityEvents:Ingest";
    public const int MinimumKeyLength = 32;
    public string SigningKey { get; set; } = string.Empty;
}

public sealed record WebIdentitySecurityEventRequest(
    Guid CorrelationId,
    string SourceEventId,
    string EventType,
    string ProviderClass,
    string Outcome,
    string ReasonCode,
    string AssuranceClass,
    DateTimeOffset OccurredAt
);

[ApiController]
[AllowAnonymous]
[Route("internal/identity/security-events")]
public sealed class IdentitySecurityEventsController(
    IdentitySecurityEventService events,
    IOptions<IdentitySecurityEventIngestOptions> options
) : ControllerBase
{
    private static readonly IReadOnlySet<string> WebEventTypes = new HashSet<string>(
        [
            "AUTHENTICATION_START",
            "PROVIDER_HANDOFF",
            "CALLBACK_SUCCESS",
            "CALLBACK_FAILURE",
            "REFRESH_SUCCESS",
            "REFRESH_FAILURE",
            "LOGOUT_REQUEST",
            "LOGOUT_COMPLETION",
            "LOGOUT_FAILURE",
            "ACCOUNT_SWITCH",
            "SESSION_EXPIRY",
        ],
        StringComparer.Ordinal
    );
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };
    private readonly byte[] _signingKey = RequireKey(options.Value.SigningKey);

    [HttpPost]
    public async Task<IActionResult> ReceiveAsync(CancellationToken cancellationToken)
    {
        using var reader = new StreamReader(Request.Body, Encoding.UTF8);
        var rawBody = await reader.ReadToEndAsync(cancellationToken);
        if (!IsValidSignature(rawBody, Request.Headers["X-WAOOAW-Identity-Event-Signature"].ToString()))
            return Problem(statusCode: 403, title: "IDENTITY_EVENT_SIGNATURE_INVALID");

        WebIdentitySecurityEventRequest? request;
        try
        {
            request = JsonSerializer.Deserialize<WebIdentitySecurityEventRequest>(rawBody, JsonOptions);
        }
        catch (JsonException)
        {
            return Problem(statusCode: 400, title: "IDENTITY_EVENT_INVALID");
        }

        if (request is null || !WebEventTypes.Contains(request.EventType))
            return Problem(statusCode: 400, title: "IDENTITY_EVENT_INVALID");

        try
        {
            var inserted = await events.RecordAsync(
                new IdentitySecurityEventInput(
                    request.CorrelationId,
                    request.SourceEventId,
                    request.EventType,
                    request.ProviderClass,
                    request.Outcome,
                    request.ReasonCode,
                    request.AssuranceClass,
                    "WEB_APPLICATION",
                    OccurredAt: request.OccurredAt
                ),
                cancellationToken
            );
            return inserted ? StatusCode(StatusCodes.Status201Created) : Ok();
        }
        catch (ArgumentException)
        {
            return Problem(statusCode: 400, title: "IDENTITY_EVENT_INVALID");
        }
    }

    private bool IsValidSignature(string rawBody, string suppliedSignature)
    {
        if (!suppliedSignature.StartsWith("sha256=", StringComparison.OrdinalIgnoreCase))
            return false;
        try
        {
            var supplied = Convert.FromHexString(suppliedSignature[7..]);
            var expected = HMACSHA256.HashData(_signingKey, Encoding.UTF8.GetBytes(rawBody));
            return supplied.Length == expected.Length
                && CryptographicOperations.FixedTimeEquals(supplied, expected);
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static byte[] RequireKey(string value) =>
        value.Length >= IdentitySecurityEventIngestOptions.MinimumKeyLength
            ? Encoding.UTF8.GetBytes(value)
            : throw new InvalidOperationException(
                $"{IdentitySecurityEventIngestOptions.SectionName}:SigningKey must contain at least {IdentitySecurityEventIngestOptions.MinimumKeyLength} characters."
            );
}