// Implements: architecture/reference/components/conversation-core.md §4 Internal PR Execution Contract
// constitutional_basis: C-005, C-023, C-026, C-059, C-063, C-079

using System.IdentityModel.Tokens.Jwt;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text;
using Microsoft.IdentityModel.Tokens;

namespace Waooaw.BusinessPlatform.Services;

public sealed class HttpConversationExecutionGateway(
    IHttpClientFactory httpClientFactory,
    IConfiguration configuration
) : IConversationExecutionGateway
{
    private sealed record ExecutionText(
        string SchemaVersion,
        string ContentType,
        string Text,
        string Language
    );

    private sealed record StartRequest(
        string SchemaVersion,
        Guid MessageId,
        int DecisionSpaceVersion,
        string Locale,
        OperationalMandateV1 OperationalMandate,
        ExecutionText Content
    );

    public async Task StartAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        Guid relationshipId,
        string locale,
        IReadOnlyList<ConversationTextBlockV1> content,
        OperationalMandateV1 operationalMandate,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    )
    {
        var secret = configuration["Conversation:ProfessionalRuntimeJwtSecret"];
        if (string.IsNullOrWhiteSpace(secret) || content.Count != 1)
            throw new ConversationExecutionUnavailableException();
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"api/v1/internal/conversations/{conversationId:D}/executions"
        );
        request.Headers.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            CreateAssertion(secret, operationalMandate)
        );
        request.Headers.Add("Idempotency-Key", idempotencyKey.ToString("D"));
        request.Headers.Add("X-Correlation-Id", executionId.ToString("D"));
        request.Content = JsonContent.Create(
            new StartRequest(
                "1.0",
                messageId,
                operationalMandate.DecisionSpaceRevision,
                locale,
                operationalMandate,
                new ExecutionText("1.0", "TEXT", content[0].Text, content[0].Language ?? locale)
            )
        );
        try
        {
            using var response = await httpClientFactory
                .CreateClient("ConversationProfessionalRuntime")
                .SendAsync(request, cancellationToken);
            if (!response.IsSuccessStatusCode)
                throw new ConversationExecutionUnavailableException();
        }
        catch (Exception exception)
            when (exception is HttpRequestException or TaskCanceledException)
        {
            throw new ConversationExecutionUnavailableException();
        }
    }

    public Task CancelAsync(
        Guid conversationId,
        Guid executionId,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    ) => throw new ConversationExecutionUnavailableException();

    private static string CreateAssertion(string secret, OperationalMandateV1 mandate)
    {
        var now = DateTimeOffset.UtcNow;
        var claims = new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, "business-platform"),
            new Claim("scope", "conversation:execute"),
            new Claim("contract_id", mandate.ConstitutionalDecisionRef),
            new Claim("tenant_id", mandate.TenantId.ToString("D")),
            new Claim("relationship_id", mandate.RelationshipId.ToString("D")),
            new Claim("delegated_actor_id", mandate.ActorId.ToString("D")),
            new Claim("participant_role", mandate.ActorRole),
        };
        var credentials = new SigningCredentials(
            new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret)),
            SecurityAlgorithms.HmacSha256
        );
        return new JwtSecurityTokenHandler().WriteToken(
            new JwtSecurityToken(
                issuer: "business-platform",
                audience: "professional-runtime",
                claims: claims,
                notBefore: now.UtcDateTime,
                expires: now.AddSeconds(30).UtcDateTime,
                signingCredentials: credentials
            )
        );
    }
}
