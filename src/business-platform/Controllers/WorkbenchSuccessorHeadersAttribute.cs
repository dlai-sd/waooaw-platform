// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-07
// Constitutional basis: C-001, C-059, C-063, ADR-051

using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// Marks a legacy relationship projection as superseded by the workbench. It only adds the `Deprecation` and `Link`
/// response headers while `Workbench:Enabled` is true; the response body and status are never touched.
/// </summary>
[AttributeUsage(AttributeTargets.Class)]
public sealed class WorkbenchSuccessorHeadersAttribute : ResultFilterAttribute
{
    public const string DeprecationHeader = "Deprecation";
    public const string LinkHeader = "Link";

    public override void OnResultExecuting(ResultExecutingContext context)
    {
        var enabled = context
            .HttpContext.RequestServices.GetService<IOptions<WorkbenchOptions>>()
            ?.Value.Enabled;
        if (
            enabled == true
            && context.RouteData.Values.TryGetValue("relationshipId", out var value)
            && Guid.TryParse(
                Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture),
                out var relationshipId
            )
        )
        {
            context.HttpContext.Response.Headers[DeprecationHeader] = "true";
            context.HttpContext.Response.Headers[LinkHeader] =
                $"</api/v1/employment/relationships/{relationshipId:D}/workbench>; rel=\"successor-version\"";
        }
        base.OnResultExecuting(context);
    }
}
