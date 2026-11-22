// Implements: ADR-046 sections 5.1 and 12.2 D4, D9
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using System.Reflection;
using System.Runtime.ExceptionServices;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>
/// Routes each owner-gateway call to the real gateway while a verified workload credential exists and to the
/// Unconfigured gateway otherwise, so a missing or expired credential gives the same outcome as no configuration.
/// </summary>
public class OwnerGatewayGuard<T> : DispatchProxy
    where T : class
{
    private T _real = null!;
    private T _unavailable = null!;
    private WorkloadIdentityClient _identity = null!;

    public static T Create(T real, T unavailable, WorkloadIdentityClient identity)
    {
        var proxy = Create<T, OwnerGatewayGuard<T>>();
        var guard = (OwnerGatewayGuard<T>)(object)proxy;
        guard._real = real;
        guard._unavailable = unavailable;
        guard._identity = identity;
        return proxy;
    }

    protected override object? Invoke(MethodInfo? targetMethod, object?[]? args)
    {
        var method = targetMethod ?? throw new InvalidOperationException("Missing gateway method");
        if (!_identity.IsAvailable)
            return Call(method, _unavailable, args);
        object? result;
        try
        {
            result = Call(method, _real, args);
        }
        catch (WorkloadCredentialsUnavailableException)
        {
            return Call(method, _unavailable, args);
        }
        if (result is not Task task)
            return result;
        var returned = method.ReturnType;
        if (returned == typeof(Task))
            return FallbackAsync(task, () => (Task)Call(method, _unavailable, args)!);
        if (returned.IsGenericType && returned.GetGenericTypeDefinition() == typeof(Task<>))
            return typeof(OwnerGatewayGuard<T>)
                .GetMethod(nameof(FallbackAsyncOf), BindingFlags.NonPublic | BindingFlags.Static)!
                .MakeGenericMethod(returned.GetGenericArguments()[0])
                .Invoke(null, [task, (Func<object?>)(() => Call(method, _unavailable, args))]);
        return result;
    }

    private static async Task FallbackAsync(Task task, Func<Task> fallback)
    {
        try
        {
            await task.ConfigureAwait(false);
        }
        catch (WorkloadCredentialsUnavailableException)
        {
            await fallback().ConfigureAwait(false);
        }
    }

    private static async Task<TResult> FallbackAsyncOf<TResult>(
        Task<TResult> task,
        Func<object?> fallback
    )
    {
        try
        {
            return await task.ConfigureAwait(false);
        }
        catch (WorkloadCredentialsUnavailableException)
        {
            return await ((Task<TResult>)fallback()!).ConfigureAwait(false);
        }
    }

    private static object? Call(MethodInfo method, T target, object?[]? args)
    {
        try
        {
            return method.Invoke(target, args);
        }
        catch (TargetInvocationException exception) when (exception.InnerException is not null)
        {
            ExceptionDispatchInfo.Capture(exception.InnerException).Throw();
            throw;
        }
    }
}
