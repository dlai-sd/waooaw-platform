// Implements: architecture/reference/components/conversational-employment-solution-contract.md §5.5.1
// Constitutional basis: C-001, C-023, C-026, C-059, C-063, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Text.Json;
using Newtonsoft.Json;
using Waooaw.Generated.DomainEmployment.Api;
using Waooaw.Generated.DomainEmployment.Model;
using Waooaw.Generated.WbeEmployment.Api;
using DomainApiException = Waooaw.Generated.DomainEmployment.Client.ApiException;
using DomainConfiguration = Waooaw.Generated.DomainEmployment.Client.Configuration;
using WbeApiException = Waooaw.Generated.WbeEmployment.Client.ApiException;
using WbeConfiguration = Waooaw.Generated.WbeEmployment.Client.Configuration;

namespace Waooaw.BusinessPlatform.Services;

public sealed record EmploymentOwnerValidation(
    string State,
    string? OwnerCommandRef,
    string? SourceVersion,
    string EvidenceRef
);

public sealed record EmploymentCommandCoordinationContext(
    Guid TenantId,
    Guid RelationshipId,
    Guid ActorId,
    Guid CommandId,
    string CommandKind,
    JsonElement Command,
    EmploymentWorkspaceSnapshot Workspace
);

public interface IEmploymentCommandOwnerGateway
{
    Task<EmploymentOwnerValidation> ValidateAsync(
        string owner,
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    );
}

public sealed class UnconfiguredEmploymentCommandOwnerGateway : IEmploymentCommandOwnerGateway
{
    public Task<EmploymentOwnerValidation> ValidateAsync(
        string owner,
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    ) =>
        Task.FromResult(
            new EmploymentOwnerValidation(
                "UNKNOWN",
                null,
                null,
                $"owner-unavailable:{owner}:{context.CommandId}"
            )
        );
}

public sealed class GeneratedEmploymentCommandOwnerGateway(
    WorkloadIdentityClient identity,
    HttpClient domainClient,
    HttpClient wbeClient,
    IRelationshipConstitutionalGateway constitutional,
    IConversationalEmploymentPersistence persistence
) : IEmploymentCommandOwnerGateway, IDisposable
{
    public async Task<EmploymentOwnerValidation> ValidateAsync(
        string owner,
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    )
    {
        try
        {
            return owner switch
            {
                "DOMAIN_ADAPTER" => await ValidateDomainAsync(context, cancellationToken),
                "WBE" => await ValidateWbeAsync(context, cancellationToken),
                "CE" => await ValidateConstitutionallyAsync(context, cancellationToken),
                _ => InvalidOwner(owner, context.CommandId),
            };
        }
        catch (Exception error)
            when (error
                    is HttpRequestException
                        or TaskCanceledException
                        or DomainApiException
                        or WbeApiException
                        or ConstitutionalActionDeniedException
                        or InvalidOperationException
            )
        {
            return new EmploymentOwnerValidation(
                error is ConstitutionalActionDeniedException ? "BLOCKED" : "UNKNOWN",
                null,
                null,
                $"owner-failure:{owner}:{context.CommandId}"
            );
        }
    }

    private async Task<EmploymentOwnerValidation> ValidateDomainAsync(
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    )
    {
        if (
            context.CommandKind
            is "SUBMIT_PLAN_FOR_REVIEW"
                or "ACCEPT_PLAN_VERSION"
                or "RESCHEDULE_WITHIN_TOLERANCE"
        )
            return await ValidatePlanAsync(context, cancellationToken);
        if (context.CommandKind is "REQUEST_REASSESSMENT" or "ACKNOWLEDGE_CORRECTIVE_PROPOSAL")
            return await ValidatePerformanceAsync(context, cancellationToken);
        if (context.CommandKind is "APPLY_CANDIDATE_PATCH" or "ACKNOWLEDGE_MATERIAL_CHANGE")
            return await ValidateStoredDomainContextAsync(context, cancellationToken);
        const string route =
            "/internal/v1/relationships/{relationshipId}/employment/induction-requirements";
        var correlationId = Guid.NewGuid();
        var configuration = new DomainConfiguration
        {
            BasePath = domainClient.BaseAddress?.ToString() ?? string.Empty,
        };
        AddDelegatedHeaders(
            configuration.DefaultHeaders,
            "domain-adapter",
            HttpMethod.Get,
            route,
            "getInductionRequirementSet",
            context,
            correlationId
        );
        var api = new EmploymentDomainSemanticsApi(domainClient, configuration);
        var result = await api.GetInductionRequirementSetAsync(
            context.RelationshipId,
            context.Workspace.ManifestVersion,
            correlationId,
            cancellationToken
        );
        if (result.ManifestVersion != context.Workspace.ManifestVersion)
            throw new InvalidOperationException("Domain manifest identity mismatch.");
        return new EmploymentOwnerValidation(
            "COMPLETED",
            $"induction-requirements:{result.RequirementSetVersion}",
            result.RequirementSetVersion,
            $"domain-assessment:{context.CommandId}"
        );
    }

    private async Task<EmploymentOwnerValidation> ValidatePlanAsync(
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    )
    {
        var command = context.Command;
        var subjectRef = command.GetProperty("subjectRef").GetString()!;
        var stored = persistence.LoadOwnerContext(
            context.TenantId,
            context.RelationshipId,
            subjectRef,
            "PLAN_VALIDATION"
        );
        if (stored is null)
            return MissingContext(context, "PLAN_VALIDATION");
        var request =
            JsonConvert.DeserializeObject<PlanValidationRequestV1>(stored.Context.GetRawText())
            ?? throw new InvalidOperationException("Stored plan validation context is invalid.");
        var expectedPlanVersion = command.GetProperty("expectedPlanVersion").GetString();
        if (
            request.ManifestVersion != context.Workspace.ManifestVersion
            || request.PlanVersion != expectedPlanVersion
        )
            throw new InvalidOperationException("Stored plan validation identity mismatch.");
        return await ValidatePlanRequestAsync(context, request, cancellationToken);
    }

    private async Task<EmploymentOwnerValidation> ValidatePlanRequestAsync(
        EmploymentCommandCoordinationContext context,
        PlanValidationRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        const string route =
            "/internal/v1/relationships/{relationshipId}/employment/plan-validation";
        var correlationId = Guid.NewGuid();
        var configuration = DomainConfigurationFor(
            route,
            "validatePlanCandidate",
            context,
            correlationId,
            HttpMethod.Post
        );
        var result = await new EmploymentDomainSemanticsApi(
            domainClient,
            configuration
        ).ValidatePlanCandidateAsync(
            context.RelationshipId,
            OwnerIdempotencyKey(context.CommandId, "validatePlanCandidate"),
            correlationId,
            request,
            cancellationToken
        );
        return DomainAssessment(
            result.State.ToString(),
            result.AssessmentVersion,
            context.CommandId
        );
    }

    private async Task<EmploymentOwnerValidation> ValidatePerformanceAsync(
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    )
    {
        var reviewPeriodRef = context.Command.GetProperty("subjectRef").GetString()!;
        const string route =
            "/internal/v1/relationships/{relationshipId}/employment/performance-assessments/{reviewPeriodRef}";
        var correlationId = Guid.NewGuid();
        var configuration = DomainConfigurationFor(
            route,
            "getPerformanceAssessment",
            context,
            correlationId,
            HttpMethod.Get
        );
        var result = await new EmploymentDomainSemanticsApi(
            domainClient,
            configuration
        ).GetPerformanceAssessmentAsync(
            context.RelationshipId,
            reviewPeriodRef,
            correlationId,
            cancellationToken
        );
        if (result.ReviewPeriodRef != reviewPeriodRef)
            throw new InvalidOperationException("Performance assessment identity mismatch.");
        var state = result.OutcomeState
            is PerformanceAssessmentV1.OutcomeStateEnum.UNKNOWN
                or PerformanceAssessmentV1.OutcomeStateEnum.UNAVAILABLE
                or PerformanceAssessmentV1.OutcomeStateEnum.DISPUTED
            ? "UNKNOWN"
            : "COMPLETED";
        return new EmploymentOwnerValidation(
            state,
            $"performance-assessment:{result.AssessmentVersion}",
            result.AssessmentVersion,
            $"domain-assessment:{context.CommandId}"
        );
    }

    private async Task<EmploymentOwnerValidation> ValidateStoredDomainContextAsync(
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    )
    {
        var subjectRef = context.Command.GetProperty("subjectRef").GetString()!;
        var stored = persistence.LoadOwnerContext(
            context.TenantId,
            context.RelationshipId,
            subjectRef,
            "CANDIDATE_PATCH_DOMAIN_REQUEST"
        );
        if (stored is null)
            return MissingContext(context, "CANDIDATE_PATCH_DOMAIN_REQUEST");
        var envelope = stored.Context;
        var operation = envelope.GetProperty("operation").GetString();
        var request = envelope.GetProperty("request");
        if (operation == "validatePlanCandidate")
        {
            var planRequest =
                JsonConvert.DeserializeObject<PlanValidationRequestV1>(request.GetRawText())
                ?? throw new InvalidOperationException(
                    "Stored plan validation context is invalid."
                );
            if (planRequest.ManifestVersion != context.Workspace.ManifestVersion)
                throw new InvalidOperationException("Stored plan validation manifest mismatch.");
            return await ValidatePlanRequestAsync(context, planRequest, cancellationToken);
        }
        if (operation == "classifyMaterialChange")
        {
            var materialRequest =
                JsonConvert.DeserializeObject<MaterialChangeRequestV1>(request.GetRawText())
                ?? throw new InvalidOperationException(
                    "Stored material-change context is invalid."
                );
            if (materialRequest.ManifestVersion != context.Workspace.ManifestVersion)
                throw new InvalidOperationException("Stored material-change manifest mismatch.");
            const string route =
                "/internal/v1/relationships/{relationshipId}/employment/material-change-classification";
            var correlationId = Guid.NewGuid();
            var configuration = DomainConfigurationFor(
                route,
                operation,
                context,
                correlationId,
                HttpMethod.Post
            );
            var result = await new EmploymentDomainSemanticsApi(
                domainClient,
                configuration
            ).ClassifyMaterialChangeAsync(
                context.RelationshipId,
                OwnerIdempotencyKey(context.CommandId, operation),
                correlationId,
                materialRequest,
                cancellationToken
            );
            return new EmploymentOwnerValidation(
                result.Classification.ToString() == "UNKNOWN" ? "UNKNOWN" : "COMPLETED",
                $"material-change:{stored.ContextVersion}",
                stored.ContextVersion,
                $"domain-assessment:{context.CommandId}"
            );
        }
        if (operation == "evaluateDependencyIsolation")
        {
            var isolationRequest =
                JsonConvert.DeserializeObject<DependencyIsolationRequestV1>(request.GetRawText())
                ?? throw new InvalidOperationException(
                    "Stored dependency-isolation context is invalid."
                );
            if (isolationRequest.ManifestVersion != context.Workspace.ManifestVersion)
                throw new InvalidOperationException(
                    "Stored dependency-isolation manifest mismatch."
                );
            const string route =
                "/internal/v1/relationships/{relationshipId}/employment/dependency-isolation";
            var correlationId = Guid.NewGuid();
            var configuration = DomainConfigurationFor(
                route,
                operation,
                context,
                correlationId,
                HttpMethod.Post
            );
            var result = await new EmploymentDomainSemanticsApi(
                domainClient,
                configuration
            ).EvaluateDependencyIsolationAsync(
                context.RelationshipId,
                OwnerIdempotencyKey(context.CommandId, operation),
                correlationId,
                isolationRequest,
                cancellationToken
            );
            return new EmploymentOwnerValidation(
                result.Isolation.ToString() == "UNKNOWN" ? "UNKNOWN" : "COMPLETED",
                $"dependency-isolation:{stored.ContextVersion}",
                stored.ContextVersion,
                $"domain-assessment:{context.CommandId}"
            );
        }
        return MissingContext(context, "SUPPORTED_CANDIDATE_PATCH_OPERATION");
    }

    private DomainConfiguration DomainConfigurationFor(
        string route,
        string purpose,
        EmploymentCommandCoordinationContext context,
        Guid correlationId,
        HttpMethod method
    )
    {
        var configuration = new DomainConfiguration
        {
            BasePath = domainClient.BaseAddress?.ToString() ?? string.Empty,
        };
        AddDelegatedHeaders(
            configuration.DefaultHeaders,
            "domain-adapter",
            method,
            route,
            purpose,
            context,
            correlationId
        );
        return configuration;
    }

    private static EmploymentOwnerValidation MissingContext(
        EmploymentCommandCoordinationContext context,
        string contextKind
    ) => new("UNKNOWN", null, null, $"domain-context-missing:{contextKind}:{context.CommandId}");

    private static EmploymentOwnerValidation DomainAssessment(
        string state,
        string assessmentVersion,
        Guid commandId
    ) =>
        new(
            state == "VALID" ? "COMPLETED"
                : state == "INVALID" ? "REJECTED"
                : "UNKNOWN",
            $"domain-assessment:{assessmentVersion}",
            assessmentVersion,
            $"domain-assessment:{commandId}"
        );

    private static Guid OwnerIdempotencyKey(Guid commandId, string operation)
    {
        var namespaceBytes = commandId.ToByteArray(bigEndian: true);
        var operationBytes = System.Text.Encoding.UTF8.GetBytes(operation);
        var input = new byte[namespaceBytes.Length + operationBytes.Length];
        namespaceBytes.CopyTo(input, 0);
        operationBytes.CopyTo(input, namespaceBytes.Length);
        var digest = System.Security.Cryptography.SHA1.HashData(input);
        digest[6] = (byte)((digest[6] & 0x0f) | 0x50);
        digest[8] = (byte)((digest[8] & 0x3f) | 0x80);
        return new Guid(digest.AsSpan(0, 16), bigEndian: true);
    }

    private async Task<EmploymentOwnerValidation> ValidateWbeAsync(
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    )
    {
        var command = context.Command;
        var planVersion = command.GetProperty("expectedPlanVersion").GetString()!;
        var correlationId = Guid.NewGuid();
        const string route = "/internal/v1/relationships/{relationshipId}/employment-eligibility";
        var configuration = new WbeConfiguration
        {
            BasePath = wbeClient.BaseAddress?.ToString() ?? string.Empty,
        };
        AddDelegatedHeaders(
            configuration.DefaultHeaders,
            "billing-engine",
            HttpMethod.Get,
            route,
            "getEmploymentCommercialEligibility",
            context,
            correlationId
        );
        var api = new EmploymentCommercialEligibilityApi(wbeClient, configuration);
        var result = await api.GetEmploymentCommercialEligibilityAsync(
            context.RelationshipId,
            planVersion,
            context.Workspace.ManifestVersion,
            correlationId,
            cancellationToken
        );
        var expectedSource = command.GetProperty("expectedWbeSourceVersion").GetString();
        if (
            result.RelationshipId != context.RelationshipId
            || result.ManifestVersion != context.Workspace.ManifestVersion
            || result.PlanVersion != planVersion
            || result.SourceProjectionVersion != expectedSource
        )
            throw new InvalidOperationException("WBE eligibility identity mismatch.");
        return new EmploymentOwnerValidation(
            "COMPLETED",
            $"wbe-eligibility:{result.SourceProjectionVersion}",
            result.SourceProjectionVersion,
            $"wbe-projection:{context.CommandId}"
        );
    }

    private async Task<EmploymentOwnerValidation> ValidateConstitutionallyAsync(
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    )
    {
        var evidenceId = await constitutional.AuthorizeAndRecordAsync(
            context.TenantId,
            context.RelationshipId,
            context.Workspace.Workspace.GetProperty("agentType").GetString()!,
            $"EMPLOYMENT_{context.CommandKind}",
            context.CommandId,
            new
            {
                relationshipId = context.RelationshipId,
                commandId = context.CommandId,
                commandKind = context.CommandKind,
                subjectRef = context.Command.GetProperty("subjectRef").GetString(),
                workspaceVersion = context.Workspace.WorkspaceVersion,
                manifestVersion = context.Workspace.ManifestVersion,
                decisionSpaceVersion = context.Workspace.DecisionSpaceVersion,
                wbeSourceVersion = context.Workspace.WbeSourceVersion,
                requestDigest = ConversationalEmploymentService.CommandDigest(context.Command),
            },
            checked((int)context.Workspace.DecisionSpaceVersion),
            cancellationToken
        );
        return new EmploymentOwnerValidation(
            "COMPLETED",
            evidenceId.ToString("D"),
            context.Workspace.DecisionSpaceVersion.ToString(),
            $"ce-evidence:{evidenceId:D}"
        );
    }

    private void AddDelegatedHeaders(
        IDictionary<string, string> headers,
        string target,
        HttpMethod method,
        string route,
        string operation,
        EmploymentCommandCoordinationContext context,
        Guid correlationId
    )
    {
        var delegated = new DelegatedRequestContext(
            context.ActorId.ToString("D"),
            "EMPLOYMENT_PARTICIPANT",
            context.TenantId.ToString("D"),
            context.RelationshipId.ToString("D"),
            operation,
            context.Command.GetProperty("subjectRef").GetString()!,
            context.CommandId.ToString("D"),
            context.CommandId.ToString("D"),
            new Dictionary<string, string>
            {
                ["workspace"] = context.Workspace.WorkspaceVersion,
                ["manifest"] = context.Workspace.ManifestVersion,
                ["decision_space"] = context.Workspace.DecisionSpaceVersion.ToString(),
                ["wbe"] = context.Workspace.WbeSourceVersion,
            },
            correlationId.ToString("D")
        );
        var token = identity.Sign(
            delegated,
            identity.GetAudience(target),
            method.Method,
            route,
            operation,
            1,
            method == HttpMethod.Get
                ? "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                : ConversationalEmploymentService.CommandDigest(context.Command),
            DateTimeOffset.UtcNow
        );
        headers["Authorization"] = $"Bearer {token}";
    }

    private static EmploymentOwnerValidation InvalidOwner(string owner, Guid commandId) =>
        new("BLOCKED", null, null, $"invalid-owner:{owner}:{commandId}");

    public void Dispose()
    {
        domainClient.Dispose();
        wbeClient.Dispose();
    }
}

public interface IEmploymentCommandCoordinator
{
    Task CoordinateAsync(
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    );
}

public sealed class EmploymentCommandCoordinator(
    ConversationalEmploymentService employment,
    IEmploymentCommandOwnerGateway owners
) : IEmploymentCommandCoordinator
{
    public async Task CoordinateAsync(
        EmploymentCommandCoordinationContext context,
        CancellationToken cancellationToken
    )
    {
        var outcome =
            employment.GetCommand(context.TenantId, context.RelationshipId, context.CommandId)
            ?? throw new EmploymentProtocolException("EMPLOYMENT_NOT_ACCESSIBLE");
        foreach (var step in outcome.OwnerSteps.Where(step => step.State == "PENDING"))
        {
            cancellationToken.ThrowIfCancellationRequested();
            var validation = await owners.ValidateAsync(step.Owner, context, cancellationToken);
            outcome = employment.UpdateOwnerStep(
                context.TenantId,
                context.RelationshipId,
                context.CommandId,
                step.Owner,
                validation.State,
                validation.OwnerCommandRef,
                validation.SourceVersion,
                validation.EvidenceRef
            );
            if (validation.State is not ("COMPLETED" or "COMMITTED"))
                return;
        }
    }
}
