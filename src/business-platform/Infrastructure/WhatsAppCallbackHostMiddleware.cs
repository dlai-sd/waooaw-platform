// Implements: work-contracts/WC-121-demo-whatsapp-provider-enablement-work-component.md S08-S09
// Constitutional basis: C-023, C-026, C-059, C-063

using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Infrastructure;

public sealed class WhatsAppCallbackHostMiddleware(RequestDelegate next)
{
    public async Task InvokeAsync(HttpContext context, IOptions<WhatsAppJourneyOptions> options)
    {
        var host = options.Value.CallbackHost;
        if (
            !string.IsNullOrWhiteSpace(host)
            && string.Equals(context.Request.Host.Host, host, StringComparison.OrdinalIgnoreCase)
            && (
                context.Request.Path != "/api/v1/channels/whatsapp/webhook"
                || !HttpMethods.IsGet(context.Request.Method)
                    && !HttpMethods.IsPost(context.Request.Method)
            )
        )
        {
            context.Response.StatusCode = StatusCodes.Status404NotFound;
            return;
        }
        await next(context);
    }
}
