// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C7-02
// Constitutional basis: C-023, C-059, C-063

using System.Security.Claims;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.Spend;

/// <summary>
/// Test-only switch for the simulator spend header. Absent in every environment unless an operator
/// turns it on, and even then only a server-verified simulator principal ever sees the header.
/// </summary>
public sealed class SimulatorHeaderOptions
{
    public const string SectionName = "SimulatorHeaders";

    public bool Enabled { get; set; }
}

public static class SimulatorSpendHeader
{
    public const string HeaderName = "X-Spend-Account-Class";
    public const string SimulatorRole = "visitor-simulator";

    // Same role-claim reading as the other BP role gates; the role is never taken from a request field.
    public static bool HasSimulatorRole(ClaimsPrincipal? user) =>
        user is { Identity.IsAuthenticated: true }
        && (
            user.IsInRole(SimulatorRole)
            || user.Claims.Where(claim =>
                    claim.Type is ClaimTypes.Role or "role" or "participant_role"
                )
                .Any(claim =>
                    string.Equals(claim.Value, SimulatorRole, StringComparison.OrdinalIgnoreCase)
                )
        );
}

/// <summary>What the resolver decided for one request, shared with the header middleware.</summary>
public sealed class SpendAccountObservation(bool isSimulator)
{
    private SpendAccountClass? _accountClass;

    public bool IsSimulator { get; } = isSimulator;

    public SpendAccountClass? AccountClass => _accountClass;

    public void Record(SpendAccountClass accountClass) => _accountClass = accountClass;
}

/// <summary>Per-request ambient observation; the resolver is a singleton so it cannot take the request.</summary>
public static class SpendAccountObservationScope
{
    private static readonly AsyncLocal<SpendAccountObservation?> Holder = new();

    public static SpendAccountObservation? Current => Holder.Value;

    public static SpendAccountObservation Begin(bool isSimulator)
    {
        var observation = new SpendAccountObservation(isSimulator);
        Holder.Value = observation;
        return observation;
    }

    public static void End() => Holder.Value = null;
}

/// <summary>
/// Wraps the account resolver. Traffic from the simulator role is always simulated, so its spend lands
/// on the SIMULATION account whatever the header flag says; the decided class is recorded for the header.
/// </summary>
public sealed class ObservingSpendAccountResolver(ISpendAccountResolver inner)
    : ISpendAccountResolver
{
    public SpendPurpose ResolvePurpose(string? contextKey, string? phase) =>
        inner.ResolvePurpose(contextKey, phase);

    public SpendAccountDecision Resolve(RelationshipSpendInput input)
    {
        var observation = SpendAccountObservationScope.Current;
        var routed = observation is { IsSimulator: true }
            ? input with
            {
                IsSimulation = true,
            }
            : input;
        var decision = inner.Resolve(routed);
        observation?.Record(decision.AccountClass);
        return decision;
    }
}

/// <summary>
/// Emits X-Spend-Account-Class only when SimulatorHeaders:Enabled is true and the authenticated principal
/// has the visitor-simulator role. Every other caller never receives the header, including when a client
/// sends one.
/// </summary>
public sealed class SimulatorSpendHeaderMiddleware(
    RequestDelegate next,
    IOptions<SimulatorHeaderOptions> options
)
{
    public async Task InvokeAsync(HttpContext context)
    {
        var simulator = SimulatorSpendHeader.HasSimulatorRole(context.User);
        var observation = SpendAccountObservationScope.Begin(simulator);
        var emit = simulator && options.Value.Enabled;
        context.Response.OnStarting(
            static state =>
            {
                var (http, seen, allowed) = ((HttpContext, SpendAccountObservation, bool))state;
                http.Response.Headers.Remove(SimulatorSpendHeader.HeaderName);
                if (allowed && seen.AccountClass is { } accountClass)
                    http.Response.Headers[SimulatorSpendHeader.HeaderName] =
                        accountClass.ToStorage();
                return Task.CompletedTask;
            },
            (context, observation, emit)
        );
        try
        {
            await next(context);
        }
        finally
        {
            SpendAccountObservationScope.End();
        }
    }
}

public static class SimulatorSpendHeaderExtensions
{
    public static IServiceCollection AddSimulatorSpendHeader(
        this IServiceCollection services,
        IConfiguration configuration
    )
    {
        services
            .AddOptions<SimulatorHeaderOptions>()
            .Bind(
                configuration.GetSection(SimulatorHeaderOptions.SectionName),
                options => options.ErrorOnUnknownConfiguration = true
            )
            .ValidateOnStart();
        return services;
    }

    public static IApplicationBuilder UseSimulatorSpendHeader(this IApplicationBuilder app) =>
        app.UseMiddleware<SimulatorSpendHeaderMiddleware>();
}
