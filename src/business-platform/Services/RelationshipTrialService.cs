// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-04
// constitutional_basis: C-023, C-026, C-049, C-059, C-088

using System.Net.Http.Json;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record WbeTrialEntitlement(Guid TrialId, DateTimeOffset StartsAt, DateTimeOffset ExpiresAt);
public sealed record PrTrialWorkflow(Guid TrialId, string WorkflowState, DateTimeOffset ExpiresAt);
public sealed record RelationshipTrialResult(Guid TrialId, DateTimeOffset StartsAt, DateTimeOffset ExpiresAt, string Status);

public interface IRelationshipTrialOwnerGateway
{
    Task<WbeTrialEntitlement?> StartWbeTrialAsync(
        Guid customerId, string professionalType, Guid relationshipId, Guid correlationId,
        CancellationToken cancellationToken);
    Task<PrTrialWorkflow?> StartPrTrialAsync(
        Guid tenantId, Guid relationshipId, Guid trialId, DateTimeOffset startsAt,
        DateTimeOffset expiresAt, Guid correlationId, CancellationToken cancellationToken);
}

public sealed class UnconfiguredRelationshipTrialOwnerGateway : IRelationshipTrialOwnerGateway
{
    public Task<WbeTrialEntitlement?> StartWbeTrialAsync(
        Guid customerId, string professionalType, Guid relationshipId, Guid correlationId,
        CancellationToken cancellationToken) => Task.FromResult<WbeTrialEntitlement?>(null);

    public Task<PrTrialWorkflow?> StartPrTrialAsync(
        Guid tenantId, Guid relationshipId, Guid trialId, DateTimeOffset startsAt,
        DateTimeOffset expiresAt, Guid correlationId, CancellationToken cancellationToken) =>
        Task.FromResult<PrTrialWorkflow?>(null);
}

public sealed class HttpRelationshipTrialOwnerGateway : IRelationshipTrialOwnerGateway, IDisposable
{
    private const string PrRoute = "/api/v1/internal/relationships/{relationshipId}/evaluation-trial";
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _professionalRuntime;

    public HttpRelationshipTrialOwnerGateway(
        IHttpClientFactory httpClientFactory,
        WorkloadIdentityClient identity,
        Uri professionalRuntimeBaseAddress)
    {
        _httpClientFactory = httpClientFactory;
        _identity = identity;
        _professionalRuntime = identity.CreateClient(professionalRuntimeBaseAddress, "professional-runtime");
    }

    public async Task<WbeTrialEntitlement?> StartWbeTrialAsync(
        Guid customerId, string professionalType, Guid relationshipId, Guid correlationId,
        CancellationToken cancellationToken)
    {
        try
        {
            var client = _httpClientFactory.CreateClient("WBE");
            using var response = await client.PostAsJsonAsync(
                "/trial/start",
                new { customer_id = customerId, agent_type = professionalType, phone_verified = true },
                cancellationToken);
            if (response.StatusCode == HttpStatusCode.Conflict)
            {
                using var statusResponse = await client.GetAsync($"/trial/status/{customerId}", cancellationToken);
                if (!statusResponse.IsSuccessStatusCode) return null;
                using var statusDocument = await JsonDocument.ParseAsync(
                    await statusResponse.Content.ReadAsStreamAsync(cancellationToken), cancellationToken: cancellationToken);
                var status = statusDocument.RootElement;
                if (status.GetProperty("agent_type").GetString() != professionalType
                    || status.GetProperty("status").GetString() != "ACTIVE") return null;
                return ParseWbeEntitlement(status);
            }
            if (!response.IsSuccessStatusCode) return null;
            using var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(cancellationToken), cancellationToken: cancellationToken);
            return ParseWbeEntitlement(document.RootElement);
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException
            or JsonException or InvalidOperationException or FormatException)
        {
            return null;
        }
    }

    private static WbeTrialEntitlement ParseWbeEntitlement(JsonElement root) => new(
        root.GetProperty("trial_id").GetGuid(),
        root.GetProperty("started_at").GetDateTimeOffset(),
        root.GetProperty("expires_at").GetDateTimeOffset());

    public async Task<PrTrialWorkflow?> StartPrTrialAsync(
        Guid tenantId, Guid relationshipId, Guid trialId, DateTimeOffset startsAt,
        DateTimeOffset expiresAt, Guid correlationId, CancellationToken cancellationToken)
    {
        var route = PrRoute.Replace("{relationshipId}", relationshipId.ToString());
        var body = new SortedDictionary<string, object?>
        {
            ["credentialUseAllowed"] = false,
            ["expiresAt"] = expiresAt,
            ["externalActionsAllowed"] = false,
            ["inferenceTier"] = "LOCAL",
            ["paidProviderFallback"] = false,
            ["schemaVersion"] = "1.0",
            ["startsAt"] = startsAt,
            ["trialId"] = trialId,
        };
        var bodyJson = JsonSerializer.Serialize(body);
        var digest = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(bodyJson)));
        var context = new DelegatedRequestContext(
            ActorSubject: relationshipId.ToString(),
            EffectiveRole: "EVALUATOR",
            TenantId: tenantId.ToString(),
            RelationshipId: relationshipId.ToString(),
            Purpose: "startRelationshipTrial",
            SubjectReference: relationshipId.ToString(),
            CommandId: correlationId.ToString(),
            IdempotencyKey: null,
            ExpectedVersions: new Dictionary<string, string>(),
            CorrelationId: correlationId.ToString());
        var envelope = _identity.Sign(
            context, _identity.GetAudience("professional-runtime"), HttpMethod.Post.Method,
            PrRoute, "startRelationshipTrial", 1, digest, DateTimeOffset.UtcNow);
        using var request = new HttpRequestMessage(HttpMethod.Post, route)
        {
            Content = new StringContent(bodyJson, Encoding.UTF8, "application/json"),
        };
        request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", correlationId.ToString());
        try
        {
            using var response = await _professionalRuntime.SendAsync(request, cancellationToken);
            if (!response.IsSuccessStatusCode) return null;
            using var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(cancellationToken), cancellationToken: cancellationToken);
            var root = document.RootElement;
            return new(
                root.GetProperty("trialId").GetGuid(),
                root.GetProperty("workflowState").GetString()!,
                root.GetProperty("expiresAt").GetDateTimeOffset());
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException
            or JsonException or InvalidOperationException or FormatException)
        {
            return null;
        }
    }

    public void Dispose() => _professionalRuntime.Dispose();
}

public sealed class RelationshipTrialService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    EmploymentRelationshipService relationships,
    IRelationshipTrialOwnerGateway owners)
{
    public async Task<RelationshipTrialResult> StartAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorParticipantId,
        Guid correlationId,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Relationship not found.");
        var binding = await db.RelationshipTrialBindings.SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken);
        if (binding?.Status == "ACTIVE" && binding.TrialId.HasValue
            && binding.StartsAt.HasValue && binding.ExpiresAt.HasValue)
        {
            return new(binding.TrialId.Value, binding.StartsAt.Value, binding.ExpiresAt.Value, binding.Status);
        }
        if (relationship.State is not EmploymentRelationshipState.Interviewing)
        {
            throw new IllegalRelationshipTransitionException(relationship.State, EmploymentRelationshipState.TrialActive);
        }
        binding ??= new RelationshipTrialBinding
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            CustomerId = relationship.InitiatingParticipantId,
            CorrelationId = correlationId,
        };
        if (db.Entry(binding).State == EntityState.Detached) db.RelationshipTrialBindings.Add(binding);
        await db.SaveChangesAsync(cancellationToken);

        var wbe = binding.TrialId.HasValue && binding.StartsAt.HasValue && binding.ExpiresAt.HasValue
            ? new WbeTrialEntitlement(binding.TrialId.Value, binding.StartsAt.Value, binding.ExpiresAt.Value)
            : await owners.StartWbeTrialAsync(
                binding.CustomerId, relationship.ProfessionalType, relationshipId,
                binding.CorrelationId, cancellationToken);
        if (wbe is null || wbe.ExpiresAt - wbe.StartsAt != TimeSpan.FromDays(14))
        {
            binding.Status = "UNRESOLVED";
            binding.UnresolvedOwner = "WBE";
            binding.UpdatedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync(cancellationToken);
            throw new InvalidOperationException("WBE trial entitlement is unresolved or invalid.");
        }
        binding.TrialId = wbe.TrialId;
        binding.StartsAt = wbe.StartsAt;
        binding.ExpiresAt = wbe.ExpiresAt;
        await db.SaveChangesAsync(cancellationToken);

        var pr = await owners.StartPrTrialAsync(
            tenantId, relationshipId, wbe.TrialId, wbe.StartsAt, wbe.ExpiresAt,
            binding.CorrelationId, cancellationToken);
        if (pr is null || pr.TrialId != wbe.TrialId || pr.ExpiresAt != wbe.ExpiresAt
            || pr.WorkflowState != "TRIAL_DEMONSTRATING")
        {
            binding.Status = "UNRESOLVED";
            binding.UnresolvedOwner = "PR";
            binding.UpdatedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync(cancellationToken);
            throw new InvalidOperationException("PR trial workflow is unresolved or inconsistent.");
        }

        await relationships.TransitionAsync(
            tenantId, relationshipId, actorParticipantId, RelationshipParticipantRole.Evaluator,
            EmploymentRelationshipState.TrialActive, binding.CorrelationId, false, cancellationToken);
        binding.Status = "ACTIVE";
        binding.UnresolvedOwner = null;
        binding.UpdatedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(cancellationToken);
        return new(wbe.TrialId, wbe.StartsAt, wbe.ExpiresAt, binding.Status);
    }
}