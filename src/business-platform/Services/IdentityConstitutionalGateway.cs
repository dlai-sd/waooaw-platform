// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S10
// Constitutional basis: C-005, C-023, C-026, C-059

using System.Text.Json;
using Grpc.Core;
using Grpc.Net.Client;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.BusinessPlatform.Services;

public interface IIdentityConstitutionalGateway
{
    Task<Guid> AuthorizeAndRecordAsync(
        Guid tenantId,
        Guid actionInstanceId,
        string actionType,
        object actionParameters,
        CancellationToken cancellationToken
    );
}

public sealed class IdentityConstitutionalUnavailableException(string reason, Exception? inner = null)
    : Exception(reason, inner);

public sealed class GrpcIdentityConstitutionalGateway(
    IConfiguration configuration,
    ILogger<GrpcIdentityConstitutionalGateway> logger
) : IIdentityConstitutionalGateway
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(5);

    public async Task<Guid> AuthorizeAndRecordAsync(
        Guid tenantId,
        Guid actionInstanceId,
        string actionType,
        object actionParameters,
        CancellationToken cancellationToken
    )
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(Timeout);
        var endpoint = configuration["ConstitutionalEngine:GrpcUrl"]
            ?? configuration["ConstitutionalEngine:Address"]
            ?? throw new InvalidOperationException("Constitutional Engine endpoint is not configured.");
        using var channel = GrpcChannel.ForAddress(endpoint);
        var client = new ConstitutionalService.ConstitutionalServiceClient(channel);
        var headers = new Metadata { { "x-tenant-id", tenantId.ToString("D") } };
        var parameters = JsonSerializer.Serialize(actionParameters);

        try
        {
            var validation = await client.ValidateActionAsync(
                new ValidateActionRequest
                {
                    ContractId = tenantId.ToString("D"),
                    ActionType = actionType,
                    ActionParameters = parameters,
                    DecisionSpaceVersion = 1,
                    ApprovalType = ApprovalType.CustomerExplicit,
                    DcmCategory = DcmCategory.DeterministicRequired,
                },
                headers,
                cancellationToken: timeout.Token
            );
            if (validation.Decision != ValidationDecision.Allow)
                throw new ConstitutionalActionDeniedException(
                    string.IsNullOrWhiteSpace(validation.Reason)
                        ? $"Constitutional Engine returned {validation.Decision}."
                        : validation.Reason
                );

            var evidence = await client.RecordEvidenceAsync(
                new RecordEvidenceRequest
                {
                    ActionInstanceId = actionInstanceId.ToString("D"),
                    ContractId = tenantId.ToString("D"),
                    ProfessionalId = "customer-identity-boundary",
                    ActionType = actionType,
                    State = EvidenceState.Approved,
                    ProposedContent = parameters,
                    DecisionSpaceVersion = 1,
                    ConstitutionalBasis = string.IsNullOrWhiteSpace(validation.ConstitutionalBasis)
                        ? "C-023; C-026; WC-103"
                        : validation.ConstitutionalBasis,
                },
                headers,
                cancellationToken: timeout.Token
            );
            return Guid.TryParse(evidence.EvidenceRecordId, out var evidenceId)
                ? evidenceId
                : throw new InvalidOperationException("Constitutional Engine returned an invalid evidence identifier.");
        }
        catch (ConstitutionalActionDeniedException)
        {
            throw;
        }
        catch (Exception exception)
        {
            logger.LogError(
                exception,
                "Constitutional evidence failed for identity action {ActionType}, correlation {CorrelationId}",
                actionType,
                actionInstanceId
            );
            throw new IdentityConstitutionalUnavailableException(
                "Constitutional evidence is unavailable for the identity action.",
                exception
            );
        }
    }
}