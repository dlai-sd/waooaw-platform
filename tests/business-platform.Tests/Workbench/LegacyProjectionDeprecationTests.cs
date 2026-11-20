// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-07
// Constitutional basis: C-001, C-059, C-063, ADR-051

using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Abstractions;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class LegacyProjectionDeprecationTests
{
    private static readonly Guid RelationshipId = Guid.Parse(
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    );

    public static TheoryData<Type> LegacyControllers =>
        new()
        {
            typeof(RelationshipWorkspaceController),
            typeof(ConversationalEmploymentController),
            typeof(CustomerEngagementWorkspaceController),
        };

    private static (ResultExecutingContext Context, ObjectResult Result) Execute(
        bool? enabled,
        bool withRoute = true
    )
    {
        var services = new ServiceCollection();
        if (enabled is not null)
            services.AddSingleton<IOptions<WorkbenchOptions>>(
                Options.Create(new WorkbenchOptions { Enabled = enabled.Value })
            );
        var http = new DefaultHttpContext { RequestServices = services.BuildServiceProvider() };
        var route = new RouteData();
        if (withRoute)
            route.Values["relationshipId"] = RelationshipId.ToString("D");
        var result = new ObjectResult(new { relationshipId = RelationshipId, state = "ACTIVE" })
        {
            StatusCode = 200,
        };
        var context = new ResultExecutingContext(
            new ActionContext(http, route, new ActionDescriptor()),
            new List<IFilterMetadata>(),
            result,
            new object()
        );
        new WorkbenchSuccessorHeadersAttribute().OnResultExecuting(context);
        return (context, result);
    }

    [Theory]
    [MemberData(nameof(LegacyControllers))]
    public void EveryLegacyProjectionController_CarriesTheSuccessorHeaderFilter(Type controller) =>
        Assert.NotEmpty(
            controller.GetCustomAttributes(
                typeof(WorkbenchSuccessorHeadersAttribute),
                inherit: false
            )
        );

    [Fact]
    public void FlagOn_AddsDeprecationAndSuccessorLinkWithoutChangingTheBody()
    {
        var before = JsonSerializer.Serialize(
            new { relationshipId = RelationshipId, state = "ACTIVE" }
        );

        var (context, result) = Execute(true);

        Assert.Equal("true", context.HttpContext.Response.Headers["Deprecation"].ToString());
        Assert.Equal(
            $"</api/v1/employment/relationships/{RelationshipId:D}/workbench>; rel=\"successor-version\"",
            context.HttpContext.Response.Headers["Link"].ToString()
        );
        Assert.Equal(before, JsonSerializer.Serialize(result.Value));
        Assert.Equal(200, result.StatusCode);
        Assert.Same(result, context.Result);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(null)]
    public void FlagOffOrUnconfigured_AddsNoHeadersAndKeepsTheBodyByteIdentical(bool? enabled)
    {
        var before = JsonSerializer.Serialize(
            new { relationshipId = RelationshipId, state = "ACTIVE" }
        );

        var (context, result) = Execute(enabled);

        Assert.False(context.HttpContext.Response.Headers.ContainsKey("Deprecation"));
        Assert.False(context.HttpContext.Response.Headers.ContainsKey("Link"));
        Assert.Equal(before, JsonSerializer.Serialize(result.Value));
    }

    [Fact]
    public void FlagOn_WithoutARelationshipRouteValue_AddsNothing()
    {
        var (context, _) = Execute(true, withRoute: false);

        Assert.False(context.HttpContext.Response.Headers.ContainsKey("Deprecation"));
        Assert.False(context.HttpContext.Response.Headers.ContainsKey("Link"));
    }
}
