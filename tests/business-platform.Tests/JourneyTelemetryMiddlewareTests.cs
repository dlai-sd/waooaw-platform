using System.Diagnostics;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc.ApplicationModels;
using Microsoft.AspNetCore.Mvc.Controllers;
using Microsoft.AspNetCore.Mvc.Routing;
using Waooaw.BusinessPlatform.Middleware;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class JourneyTelemetryMiddlewareTests
{
    [Fact]
    public async Task SelectionConsume_RecordsOnlyBoundedPrivacySafeValues()
    {
        using var listener = new ActivityListener
        {
            ShouldListenTo = _ => true,
            Sample = (ref ActivityCreationOptions<ActivityContext> _) =>
                ActivitySamplingResult.AllData,
        };
        ActivitySource.AddActivityListener(listener);
        using var source = new ActivitySource("wc107-test");
        using var activity = source.StartActivity("request");
        var context = new DefaultHttpContext();
        context.SetEndpoint(
            new Endpoint(
                _ => Task.CompletedTask,
                new EndpointMetadataCollection(
                    new ControllerActionDescriptor
                    {
                        AttributeRouteInfo = new AttributeRouteInfo
                        {
                            Template = "api/v1/employment/relationships/selection-flash/consume",
                        },
                    }
                ),
                "selection-consume"
            )
        );
        var middleware = new JourneyTelemetryMiddleware(next: async current =>
        {
            current.Response.StatusCode = StatusCodes.Status204NoContent;
            await Task.CompletedTask;
        });

        await middleware.InvokeAsync(context);

        var tags = activity!.TagObjects.ToDictionary(
            pair => pair.Key,
            pair => pair.Value?.ToString()
        );
        Assert.Equal(
            new[]
            {
                "waooaw.correlation_id",
                "waooaw.journey.operation",
                "waooaw.journey.outcome",
                "waooaw.journey.status_class",
            },
            tags.Keys.Order()
        );
        Assert.Equal("my_agents.selection.consume", tags["waooaw.journey.operation"]);
        Assert.Equal("NO_AUTHORIZED_SELECTION", tags["waooaw.journey.outcome"]);
        Assert.Equal("2xx", tags["waooaw.journey.status_class"]);
        Assert.DoesNotContain(
            "relationship",
            string.Join('|', tags.Values),
            StringComparison.OrdinalIgnoreCase
        );
        Assert.DoesNotContain(
            "customer",
            string.Join('|', tags.Values),
            StringComparison.OrdinalIgnoreCase
        );
        Assert.DoesNotContain(
            "payment",
            string.Join('|', tags.Values),
            StringComparison.OrdinalIgnoreCase
        );
    }

    [Fact]
    public void HttpDependency_RemovesIdentifierBearingUrl()
    {
        using var activity = new Activity("dependency").Start();
        activity.SetTag("url.full", "http://billing/relationships/relationship-secret/trial");
        activity.SetTag("http.url", "http://billing/relationships/relationship-secret/trial");
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            "http://billing/relationships/relationship-secret/trial"
        );

        JourneyHttpTelemetry.ScrubRequestUrl(activity, request);

        Assert.Equal("POST internal-service", activity.DisplayName);
        Assert.DoesNotContain(activity.TagObjects, tag => tag.Key is "url.full" or "http.url");
        Assert.DoesNotContain("relationship-secret", string.Join('|', activity.TagObjects));
    }

    [Theory]
    [InlineData("api/v1/identity/session", 200, "SESSION_RESOLVED")]
    [InlineData("api/v1/identity/registrations", 201, "REGISTRATION_STARTED")]
    [InlineData(
        "api/v1/identity/registrations/{registrationId:guid}/complete",
        200,
        "REGISTRATION_COMPLETED"
    )]
    [InlineData("api/v1/identity/sessions", 200, "SESSION_COMMAND_COMPLETED")]
    [InlineData("api/v1/acquisition/continuations", 200, "ACQUISITION_CONTINUED")]
    [InlineData("api/v1/employment/relationships", 200, "AUTHORIZED_PROJECTION_RETURNED")]
    [InlineData(
        "api/v1/employment/relationships/{relationshipId:guid}/selection-flash",
        201,
        "SELECTION_CREATED"
    )]
    [InlineData(
        "api/v1/employment/relationships/selection-flash/consume",
        200,
        "SELECTION_CONSUMED"
    )]
    [InlineData("api/v1/identity/session", 409, "CONFLICT")]
    [InlineData("api/v1/identity/session", 502, "DEPENDENCY_UNAVAILABLE")]
    [InlineData("api/v1/identity/session", 503, "DEPENDENCY_UNAVAILABLE")]
    [InlineData("api/v1/identity/session", 504, "DEPENDENCY_UNAVAILABLE")]
    [InlineData("api/v1/identity/session", 400, "REJECTED")]
    public async Task JourneyRoute_RecordsTypedOutcome(string template, int status, string expected)
    {
        using var listener = new ActivityListener
        {
            ShouldListenTo = _ => true,
            Sample = (ref ActivityCreationOptions<ActivityContext> _) =>
                ActivitySamplingResult.AllData,
        };
        ActivitySource.AddActivityListener(listener);
        using var source = new ActivitySource("wc107-outcome-test");
        using var activity = source.StartActivity("request");
        var context = new DefaultHttpContext();
        context.SetEndpoint(
            new Endpoint(
                _ => Task.CompletedTask,
                new EndpointMetadataCollection(
                    new ControllerActionDescriptor
                    {
                        AttributeRouteInfo = new AttributeRouteInfo { Template = template },
                    }
                ),
                "journey"
            )
        );
        var middleware = new JourneyTelemetryMiddleware(current =>
        {
            current.Response.StatusCode = status;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(context);

        Assert.Equal(expected, activity!.GetTagItem("waooaw.journey.outcome"));
        Assert.Equal($"{status / 100}xx", activity.GetTagItem("waooaw.journey.status_class"));
    }
}
