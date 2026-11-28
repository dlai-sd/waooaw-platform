// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R001
// constitutional_basis: C-023, C-026, C-059, C-063
using System.Reflection;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Routing;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>
/// A registered customer's token that reaches a route with no customer identity marker is refused with
/// IDENTITY_ACTION_DENIED (the Alerts inbox defect). Every authorized controller action must therefore be classified
/// as customer, staff, internal or role-gated, anonymous, or appear on the short written allow-list below.
/// </summary>
public sealed class CustomerRouteClassificationTests
{
    /// <summary>
    /// Documented exceptions: routes that no registered customer reaches. A customer token refused here is correct.
    /// An entry that no longer matches an unclassified controller fails the test, so the list cannot go stale.
    /// </summary>
    private static readonly Dictionary<string, string> AllowList = new()
    {
        ["AcceptanceSyntheticController"] =
            "Internal acceptance provisioner route (AcceptanceProvisionerRoute, internal/v1)",
        ["AgentAdmissionsController"] =
            "Admission lifecycle for the platform's admission operators (admission_operator role); customers get workspace admissions through the Founder's approval",
        ["AgentsController"] =
            "Legacy service-to-service hire route; the customer Hire runs through EmploymentRelationships and Acquisition",
        ["CustomerDataController"] =
            "Platform erasure by tenant id, service-to-service; the customer erasure request is a separate route (WC176-R006)",
        ["CustomersController"] =
            "Legacy service-to-service registration and contract routes; customers register through Identity",
        ["OfferabilityController"] =
            "Founder-only evaluation, checked by IsFounder in the action; not a customer route",
        ["ProvidersController"] =
            "Service-to-service provider configuration read with a validated service JWT",
        ["SkillsController"] =
            "Service-to-service skill catalogue; customers see skills through the relationship workspace",
        ["SubscriptionsController"] =
            "Service-to-service Trial start from the billing and acquisition services",
    };

    private static IEnumerable<Type> Controllers() =>
        typeof(AlertControlsController)
            .Assembly.GetTypes()
            .Where(type =>
                type is { IsClass: true, IsAbstract: false }
                && typeof(ControllerBase).IsAssignableFrom(type)
            );

    private static IEnumerable<MethodInfo> Actions(Type controller) =>
        controller
            .GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
            .Where(method => method.GetCustomAttributes<HttpMethodAttribute>(true).Any());

    private static bool Has<T>(Type controller, MethodInfo action)
        where T : Attribute =>
        action.GetCustomAttributes<T>(true).Any() || controller.GetCustomAttributes<T>(true).Any();

    private static string? Classify(Type controller, MethodInfo action)
    {
        if (Has<AllowAnonymousAttribute>(controller, action))
            return "anonymous";
        if (Has<CustomerIdentityRouteAttribute>(controller, action))
            return "customer";
        if (controller.GetCustomAttributes<StaffIdentityRouteAttribute>(true).Any())
            return "staff";
        var authorize = action
            .GetCustomAttributes<AuthorizeAttribute>(true)
            .Concat(controller.GetCustomAttributes<AuthorizeAttribute>(true))
            .ToArray();
        if (authorize.Any(item => item.Policy == "InternalService"))
            return "internal-service";
        if (authorize.Any(item => !string.IsNullOrWhiteSpace(item.Roles)))
            return "role-gated";
        return null;
    }

    [Fact]
    public void EveryControllerActionIsClassifiedOrDocumented()
    {
        var unclassified = new List<string>();
        foreach (var controller in Controllers())
        foreach (var action in Actions(controller))
        {
            if (Classify(controller, action) is not null)
                continue;
            if (!AllowList.ContainsKey(controller.Name))
                unclassified.Add($"{controller.Name}.{action.Name}");
        }

        Assert.True(
            unclassified.Count == 0,
            "Add the customer identity marker (or classify as staff, internal, anonymous) for: "
                + string.Join(", ", unclassified)
        );
    }

    [Fact]
    public void EveryAllowListEntryStillNamesAnUnclassifiedController()
    {
        var unclassifiedControllers = Controllers()
            .Where(controller =>
                Actions(controller).Any(action => Classify(controller, action) is null)
            )
            .Select(controller => controller.Name)
            .ToHashSet();

        var stale = AllowList.Keys.Where(name => !unclassifiedControllers.Contains(name)).ToArray();

        Assert.True(
            stale.Length == 0,
            "Remove stale allow-list entries: " + string.Join(", ", stale)
        );
        Assert.All(AllowList.Values, reason => Assert.False(string.IsNullOrWhiteSpace(reason)));
    }

    [Theory]
    [InlineData(typeof(AlertControlsController))]
    [InlineData(typeof(NotificationsController))]
    public void CustomerAlertRoutesCarryTheMembershipMarker(Type controller)
    {
        var marker = controller.GetCustomAttribute<CustomerIdentityRouteAttribute>();

        Assert.NotNull(marker);
        Assert.True(marker.RequiresMembership);
    }
}
