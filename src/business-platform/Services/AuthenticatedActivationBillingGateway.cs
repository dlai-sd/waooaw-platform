// Implements: ADR-046 sections 3.2, 3.3, 5.1, 6, and 10.1; WC-059 §WC059-06
// constitutional_basis: C-002, C-003, C-005, C-006, C-008, C-023, C-026, C-032

using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Waooaw.BusinessPlatform.Services;

public sealed class AuthenticatedActivationBillingGateway : IActivationBillingGateway, IDisposable
{
    private const string Route = "/internal/v1/relationships/{relationshipId}/paid-activation";
    private const string Operation = "activatePaidRelationship";
    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _billingEngine;

    public AuthenticatedActivationBillingGateway(WorkloadIdentityClient identity, Uri billingEngineBaseAddress)
    {
        _identity = identity;
        _billingEngine = identity.CreateClient(billingEngineBaseAddress, "billing-engine");
    }

    public async Task<ActivationBillingOutcome> ActivatePaidSubscriptionAsync(
        ActivationBillingRequest request, CancellationToken cancellationToken)
    {
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["accepted_contract_id"] = request.AcceptedContractId,
            ["activation_intent_id"] = request.ActivationIntentId,
            ["contract_acceptance_id"] = request.ContractAcceptanceId,
            ["contract_version"] = request.ContractVersion,
            ["correlation_id"] = request.CorrelationId,
            ["payment_evidence_id"] = request.PaymentEvidenceId,
            ["payment_reference"] = request.PaymentReference,
        };
        var bodyBytes = JsonSerializer.SerializeToUtf8Bytes(body);
        var digest = Convert.ToHexStringLower(SHA256.HashData(bodyBytes));
        var context = new DelegatedRequestContext(
            request.ActorParticipantId.ToString("D"),
            "EMPLOYER",
            request.TenantId.ToString("D"),
            request.RelationshipId.ToString("D"),
            Operation,
            request.AcceptedContractId.ToString("D"),
            request.ActivationIntentId.ToString("D"),
            request.CorrelationId.ToString("D"),
            new Dictionary<string, string>
            {
                ["activation_intent"] = request.ActivationIntentId.ToString("D"),
                ["contract"] = request.ContractVersion.ToString(),
            },
            request.CorrelationId.ToString("D"));
        var envelope = _identity.Sign(
            context, _identity.GetAudience("billing-engine"), HttpMethod.Post.Method,
            Route, Operation, 1, digest, DateTimeOffset.UtcNow);
        using var message = new HttpRequestMessage(
            HttpMethod.Post, Route.Replace("{relationshipId}", request.RelationshipId.ToString("D")))
        {
            Content = new ByteArrayContent(bodyBytes),
        };
        message.Content.Headers.ContentType = new("application/json");
        message.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        message.Headers.Add("X-Correlation-ID", request.CorrelationId.ToString("D"));
        message.Headers.Add("Idempotency-Key", request.CorrelationId.ToString("D"));

        try
        {
            using var response = await _billingEngine.SendAsync(message, cancellationToken);
            if (!response.IsSuccessStatusCode)
                throw new ActivationOwnerUnavailableException($"Authenticated WBE paid activation returned {(int)response.StatusCode}.");
            var outcome = await response.Content.ReadFromJsonAsync<WbePaidActivationOutcome>(cancellationToken)
                ?? throw new ActivationOwnerUnavailableException("Authenticated WBE paid activation returned no outcome.");
            return new ActivationBillingOutcome(outcome.SubscriptionId, outcome.Status);
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException)
        {
            throw new ActivationOwnerUnavailableException("Authenticated WBE paid activation is unresolved.", exception);
        }
    }

    public void Dispose() => _billingEngine.Dispose();

    private sealed record WbePaidActivationOutcome(
        [property: JsonPropertyName("subscription_id")] Guid SubscriptionId,
        [property: JsonPropertyName("status")] string Status);
}