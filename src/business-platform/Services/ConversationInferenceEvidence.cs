using System.Security.Cryptography;
using System.Text.Json;
using Google.Protobuf;
using Grpc.Core;
using Grpc.Net.Client;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.BusinessPlatform.Services;

public sealed class ConversationInferenceEvidence(IConfiguration configuration, TimeProvider clock)
{
    public async Task<Guid> RecordAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        string action,
        Guid correlation,
        object parameters,
        CancellationToken ct
    )
    {
        var credentials =
            configuration["WAOOAW_WORKLOAD_CREDENTIALS"]
            ?? throw new ConversationExecutionUnavailableException();
        var endpoint =
            configuration["ConstitutionalEngine:GrpcUrl"]
            ?? throw new ConversationExecutionUnavailableException();
        using var manifest = JsonDocument.Parse(
            await File.ReadAllTextAsync(Path.Combine(credentials, "manifest.json"), ct)
        );
        var target = manifest
            .RootElement.GetProperty("workloads")
            .GetProperty("constitutional-engine");
        using var identity = WorkloadIdentityClient.Load(credentials);
        using var transport = identity.CreateClientForIdentity(
            new Uri(endpoint),
            target.GetProperty("identity_uri").GetString()!
        );
        using var channel = GrpcChannel.ForAddress(
            endpoint,
            new GrpcChannelOptions { HttpClient = transport }
        );
        var client = new ConstitutionalService.ConstitutionalServiceClient(channel);
        var mandate = request.OperationalMandate;
        var json = JsonSerializer.Serialize(parameters);
        var validate = new ValidateActionRequest
        {
            ContractId = caller.RelationshipId.ToString("D"),
            ActionType = action,
            ActionParameters = json,
            DecisionSpaceVersion = mandate.DecisionSpaceRevision,
            ApprovalType = ApprovalType.CustomerExplicit,
            DcmCategory = DcmCategory.DeterministicRequired,
        };
        var decision = await client.ValidateActionAsync(
            validate,
            Headers(validate.ToByteArray(), "ValidateAction", identity),
            deadline: clock.GetUtcNow().AddSeconds(5).UtcDateTime,
            cancellationToken: ct
        );
        if (decision.Decision != ValidationDecision.Allow)
            throw new ConstitutionalActionDeniedException("Inference authorization was denied.");
        var record = new RecordEvidenceRequest
        {
            ActionInstanceId = correlation.ToString("D"),
            ContractId = caller.RelationshipId.ToString("D"),
            ProfessionalId = mandate.ProfessionalType,
            ActionType = action,
            State = EvidenceState.Approved,
            ProposedContent = json,
            DecisionSpaceVersion = mandate.DecisionSpaceRevision,
            ConstitutionalBasis = decision.ConstitutionalBasis,
        };
        var evidence = await client.RecordEvidenceAsync(
            record,
            Headers(record.ToByteArray(), "RecordEvidence", identity),
            deadline: clock.GetUtcNow().AddSeconds(5).UtcDateTime,
            cancellationToken: ct
        );
        if (!Guid.TryParse(evidence.EvidenceRecordId, out var id) || id == Guid.Empty)
            throw new IdentityConstitutionalUnavailableException(
                "Inference evidence identifier is invalid."
            );
        return id;

        Metadata Headers(byte[] body, string operation, WorkloadIdentityClient signer)
        {
            var context = new DelegatedRequestContext(
                caller.ActorId.ToString("D"),
                caller.Role,
                caller.TenantId.ToString("D"),
                caller.RelationshipId.ToString("D"),
                "CONVERSATION_INFERENCE_EVIDENCE",
                caller.ContributionId.ToString("D"),
                caller.ExecutionId.ToString("D"),
                caller.IdempotencyKey.ToString("D"),
                new Dictionary<string, string>
                {
                    ["mandateDigest"] = mandate.MandateDigest,
                    ["decisionSpaceRevision"] = mandate.DecisionSpaceRevision.ToString(
                        System.Globalization.CultureInfo.InvariantCulture
                    ),
                    ["professionalType"] = mandate.ProfessionalType,
                },
                correlation.ToString("D")
            );
            var token = signer.Sign(
                context,
                target.GetProperty("audience").GetString()!,
                "POST",
                $"/constitutional.v1.ConstitutionalService/{operation}",
                operation,
                1,
                Convert.ToHexStringLower(SHA256.HashData(body)),
                clock.GetUtcNow()
            );
            return new Metadata
            {
                { "authorization", $"Bearer {token}" },
                { "x-tenant-id", caller.TenantId.ToString("D") },
            };
        }
    }
}
