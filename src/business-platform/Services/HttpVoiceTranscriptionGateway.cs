// Implements: architecture/reference/api-specs/professional-runtime.openapi.yaml VoiceOrchestrationV1
// constitutional_basis: C-005, C-026, C-042, C-049, C-059, C-063

using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text;
using System.Text.Json.Serialization;
using Microsoft.IdentityModel.Tokens;

namespace Waooaw.BusinessPlatform.Services;

public sealed class HttpVoiceTranscriptionGateway(
    IHttpClientFactory httpClientFactory,
    IConfiguration configuration) : IVoiceTranscriptionGateway
{
    private sealed record StartRequest(
        string ContractVersion,
        Guid VoiceSessionId,
        Guid PayloadReference,
        string Locale,
        string MediaType,
        string ContentSha256,
        int DurationSeconds,
        long SizeBytes);

    private sealed record OrchestrationResponse(
        string ContractVersion,
        Guid OrchestrationId,
        Guid VoiceSessionId,
        string State,
        string Locale,
        string? Transcript,
        string? ConfidenceBand,
        string? FailureCode,
        DateTimeOffset UpdatedAt);

    public async Task<VoiceTranscriptionResult> TranscribeAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid sessionId,
        VoiceMediaInspection inspection,
        string locale,
        CancellationToken cancellationToken)
    {
        if (!Guid.TryParse(inspection.PayloadReference, out var payloadReference))
            throw new VoiceUnavailableException();

        var secret = configuration["Voice:ProfessionalRuntimeJwtSecret"];
        if (string.IsNullOrWhiteSpace(secret)) throw new VoiceUnavailableException();
        var idempotencyKey = Guid.NewGuid();
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"api/v1/internal/relationships/{relationshipId}/voice-orchestrations");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", CreateAssertion(secret, tenantId, relationshipId));
        request.Headers.Add("Idempotency-Key", idempotencyKey.ToString());
        request.Headers.Add("X-Correlation-Id", Guid.NewGuid().ToString());
        request.Content = JsonContent.Create(new StartRequest(
            "1.0.0",
            sessionId,
            payloadReference,
            locale,
            inspection.DetectedMediaType,
            inspection.ContentSha256,
            Math.Max(1, (int)Math.Ceiling(inspection.DurationMilliseconds / 1000m)),
            inspection.SizeBytes));

        using var response = await httpClientFactory.CreateClient("VoiceProfessionalRuntime")
            .SendAsync(request, cancellationToken);
        if (response.StatusCode is HttpStatusCode.Locked or HttpStatusCode.ServiceUnavailable)
            throw new VoiceUnavailableException();
        if (!response.IsSuccessStatusCode) throw new VoiceUnavailableException();
        var result = await response.Content.ReadFromJsonAsync<OrchestrationResponse>(cancellationToken)
            ?? throw new VoiceUnavailableException();
        if (result.ContractVersion != "1.0.0" || result.State is not ("COMPLETED" or "REVIEW_REQUIRED")
            || string.IsNullOrWhiteSpace(result.Transcript))
            throw new VoiceUnavailableException();
        return new VoiceTranscriptionResult(
            result.Transcript,
            result.Locale,
            result.ConfidenceBand switch { "HIGH" => 0.95m, "REVIEW" => 0.80m, "LOW" => 0.50m, _ => 0m },
            result.ContractVersion);
    }

    private static string CreateAssertion(string secret, Guid tenantId, Guid relationshipId)
    {
        var now = DateTimeOffset.UtcNow;
        var claims = new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, "business-platform"),
            new Claim("scope", "voice:orchestrate"),
            new Claim("contract_id", "voice-contribution-v1"),
            new Claim("tenant_id", tenantId.ToString()),
            new Claim("relationship_id", relationshipId.ToString()),
            new Claim("delegated_actor_id", "business-platform"),
            new Claim("participant_role", "SERVICE"),
        };
        var credentials = new SigningCredentials(
            new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret)),
            SecurityAlgorithms.HmacSha256);
        return new JwtSecurityTokenHandler().WriteToken(new JwtSecurityToken(
            issuer: "business-platform",
            audience: "professional-runtime",
            claims: claims,
            notBefore: now.UtcDateTime,
            expires: now.AddSeconds(30).UtcDateTime,
            signingCredentials: credentials));
    }
}