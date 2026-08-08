// Implements: architecture/reference/product/ae01-solution-contract.md § Failure Contract
// constitutional_basis: C-023, C-059, C-070

using System.Text.Json;
using Grpc.Core;
using Grpc.Net.Client;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.BusinessPlatform.Services;

public interface IRelationshipConstitutionalGateway
{
    Task<Guid> AuthorizeAndRecordAsync(
        Guid tenantId,
        Guid relationshipId,
        string professionalType,
        string actionType,
        Guid correlationId,
        object actionParameters,
        CancellationToken cancellationToken);
}

public sealed class ConstitutionalActionDeniedException(string reason) : Exception(reason);

public sealed class RelationshipConstitutionalGateway : IRelationshipConstitutionalGateway
{
    private static readonly TimeSpan ConstitutionalTimeout = TimeSpan.FromSeconds(5);

    private readonly IConfiguration _configuration;
    private readonly ILogger<RelationshipConstitutionalGateway> _logger;

    public RelationshipConstitutionalGateway(
        IConfiguration configuration,
        ILogger<RelationshipConstitutionalGateway> logger)
    {
        _configuration = configuration;
        _logger = logger;
    }

    public async Task<Guid> AuthorizeAndRecordAsync(
        Guid tenantId,
        Guid relationshipId,
        string professionalType,
        string actionType,
        Guid correlationId,
        object actionParameters,
        CancellationToken cancellationToken)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(ConstitutionalTimeout);

        var endpoint = _configuration["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");
        using var channel = GrpcChannel.ForAddress(endpoint);
        var client = new ConstitutionalService.ConstitutionalServiceClient(channel);
        var headers = new Metadata { { "x-tenant-id", tenantId.ToString("D") } };
        var parametersJson = JsonSerializer.Serialize(actionParameters);

        try
        {
            var validation = await client.ValidateActionAsync(
                new ValidateActionRequest
                {
                    ContractId = relationshipId.ToString("D"),
                    ActionType = actionType,
                    ActionParameters = parametersJson,
                    DecisionSpaceVersion = 1,
                    ApprovalType = ApprovalType.CustomerExplicit,
                    DcmCategory = DcmCategory.DeterministicRequired,
                },
                headers,
                cancellationToken: timeout.Token);

            if (validation.Decision != ValidationDecision.Allow)
            {
                throw new ConstitutionalActionDeniedException(
                    string.IsNullOrWhiteSpace(validation.Reason)
                        ? $"Constitutional Engine returned {validation.Decision}."
                        : validation.Reason);
            }

            var evidence = await client.RecordEvidenceAsync(
                new RecordEvidenceRequest
                {
                    ActionInstanceId = correlationId.ToString("D"),
                    ContractId = relationshipId.ToString("D"),
                    ProfessionalId = professionalType,
                    ActionType = actionType,
                    State = EvidenceState.Approved,
                    ProposedContent = parametersJson,
                    DecisionSpaceVersion = 1,
                    ConstitutionalBasis = string.IsNullOrWhiteSpace(validation.ConstitutionalBasis)
                        ? "C-023; C-059; GOAL-005-D03"
                        : validation.ConstitutionalBasis,
                },
                headers,
                cancellationToken: timeout.Token);

            if (!Guid.TryParse(evidence.EvidenceRecordId, out var evidenceId))
            {
                throw new InvalidOperationException("Constitutional Engine returned an invalid evidence identifier.");
            }

            return evidenceId;
        }
        catch (ConstitutionalActionDeniedException)
        {
            throw;
        }
        catch (Exception exception)
        {
            _logger.LogError(
                exception,
                "Constitutional authorization failed for relationship {RelationshipId}, action {ActionType}, correlation {CorrelationId}",
                relationshipId,
                actionType,
                correlationId);
            throw;
        }
    }
}