// Implements: WC-107 R017-R018 privacy-safe journey telemetry
// Constitutional basis: C-059, C-063
using System.Diagnostics;
using Microsoft.AspNetCore.Mvc.Controllers;

namespace Waooaw.BusinessPlatform.Middleware;

public sealed class JourneyTelemetryMiddleware(RequestDelegate next)
{
    private static readonly IReadOnlyDictionary<string, string> Operations = new Dictionary<
        string,
        string
    >(StringComparer.Ordinal)
    {
        ["api/v1/identity/session"] = "identity.session",
        ["api/v1/identity/registrations"] = "identity.registration.start",
        ["api/v1/identity/registrations/{registrationId:guid}/complete"] =
            "identity.registration.complete",
        ["api/v1/identity/sessions"] = "identity.sessions",
        ["api/v1/acquisition/continuations"] = "acquisition.continue",
        ["api/v1/employment/relationships"] = "relationships.list",
        ["api/v1/employment/relationships/{relationshipId:guid}/selection-flash"] =
            "my_agents.selection.create",
        ["api/v1/employment/relationships/selection-flash/consume"] = "my_agents.selection.consume",
    };

    public async Task InvokeAsync(HttpContext context)
    {
        var descriptor = context.GetEndpoint()?.Metadata.GetMetadata<ControllerActionDescriptor>();
        var template = descriptor?.AttributeRouteInfo?.Template;
        if (template is null || !Operations.TryGetValue(template, out var operation))
        {
            await next(context);
            return;
        }

        var activity = Activity.Current;
        activity?.SetTag("waooaw.journey.operation", operation);
        if (activity is not null)
            activity.SetTag("waooaw.correlation_id", activity.TraceId.ToHexString());

        await next(context);

        var status = context.Response.StatusCode;
        activity?.SetTag("waooaw.journey.status_class", StatusClass(status));
        activity?.SetTag("waooaw.journey.outcome", TypedOutcome(operation, status));
    }

    internal static string StatusClass(int status) =>
        status is >= 100 and <= 599 ? $"{status / 100}xx" : "unknown";

    internal static string TypedOutcome(string operation, int status)
    {
        if (status is >= 200 and < 300)
            return operation switch
            {
                "identity.session" => "SESSION_RESOLVED",
                "identity.registration.start" => "REGISTRATION_STARTED",
                "identity.registration.complete" => "REGISTRATION_COMPLETED",
                "identity.sessions" => "SESSION_COMMAND_COMPLETED",
                "acquisition.continue" => "ACQUISITION_CONTINUED",
                "relationships.list" => "AUTHORIZED_PROJECTION_RETURNED",
                "my_agents.selection.create" => "SELECTION_CREATED",
                "my_agents.selection.consume" => status == 204
                    ? "NO_AUTHORIZED_SELECTION"
                    : "SELECTION_CONSUMED",
                _ => "SUCCEEDED",
            };
        if (status == 409)
            return "CONFLICT";
        if (status is 502 or 503 or 504)
            return "DEPENDENCY_UNAVAILABLE";
        return "REJECTED";
    }
}

public static class JourneyHttpTelemetry
{
    public static void ScrubRequestUrl(Activity activity, HttpRequestMessage request)
    {
        activity.DisplayName = $"{request.Method.Method} internal-service";
        activity.SetTag("url.full", null);
        activity.SetTag("http.url", null);
    }
}
