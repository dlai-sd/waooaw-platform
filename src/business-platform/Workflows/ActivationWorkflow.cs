// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-05
// constitutional_basis: C-002, C-023, C-059, C-088

using Temporalio.Activities;
using Temporalio.Exceptions;
using Temporalio.Workflows;
using System.Security.Cryptography;
using System.Text;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Workflows;

[Workflow]
public sealed class ActivationWorkflow
{
    private static readonly ActivityOptions ActivityOptions = new()
    {
        StartToCloseTimeout = TimeSpan.FromMinutes(5),
        RetryPolicy = new() { MaximumAttempts = 5 },
    };

    [WorkflowRun]
    public Task<ActivationOutcome> RunAsync(ActivationRequest request) =>
        Workflow.ExecuteActivityAsync(
            (ActivationActivities activities) => activities.ActivateAsync(request),
            ActivityOptions);

    public static string WorkflowIdFor(ActivationRequest request)
    {
        var paymentDigest = Convert.ToHexStringLower(SHA256.HashData(
            Encoding.UTF8.GetBytes(request.PaymentReference)))[..16];
        return $"activation-{request.TenantId:D}-{request.RelationshipId:D}-{request.AcceptedContractId:D}-{paymentDigest}";
    }
}

public sealed class ActivationActivities(ActivationOrchestrationService orchestration)
{
    [Activity]
    public async Task<ActivationOutcome> ActivateAsync(ActivationRequest request)
    {
        try
        {
            return await orchestration.ActivateAsync(request, ActivityExecutionContext.Current.CancellationToken);
        }
        catch (ActivationConflictException exception)
        {
            throw new ApplicationFailureException(exception.Message, nonRetryable: true);
        }
        catch (ActivationEligibilityException exception)
        {
            throw new ApplicationFailureException(exception.Message, nonRetryable: true);
        }
    }
}