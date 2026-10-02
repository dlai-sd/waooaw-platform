using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Mvc;

namespace Waooaw.BusinessPlatform.Infrastructure;

public sealed record IdentityProblemResponse(
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("title")] string Title,
    [property: JsonPropertyName("status")] int Status,
    [property: JsonPropertyName("detail")] string Detail,
    [property: JsonPropertyName("code")] string Code,
    [property: JsonPropertyName("correlationId")] Guid CorrelationId,
    [property: JsonPropertyName("stepUpIntentId")] Guid? StepUpIntentId
);

public static class IdentityProblemResponses
{
    public static ObjectResult Create(
        int status,
        string code,
        string detail,
        Guid? stepUpIntentId = null,
        Guid? correlationId = null
    ) =>
        new(
            new IdentityProblemResponse(
                $"https://waooaw.com/errors/identity/{code.ToLowerInvariant().Replace('_', '-')}",
                code,
                status,
                detail,
                code,
                correlationId ?? Guid.NewGuid(),
                stepUpIntentId
            )
        )
        {
            StatusCode = status,
            ContentTypes = { "application/problem+json" },
        };
}
