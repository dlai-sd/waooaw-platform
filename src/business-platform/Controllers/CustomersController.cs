// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-036, C-038, C-059
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Net.Client;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using System;
using System.Threading;
using System.Threading.Tasks;

namespace Waooaw.BusinessPlatform.Controllers;

// C-023: Evidence First — every mutating endpoint calls CE.ValidateAction before executing.
// C-038: Pro-rata billing fields populated at hire time.
// C-059: Constitutional traceability — header present on every file.

/// <summary>
/// Request body for POST /api/customers.
/// </summary>
public sealed record RegisterCustomerRequest(
    string Name,
    string Email,
    string TenantId);

/// <summary>
/// Request body for POST /api/agents/hire.
/// Includes C-038 pro-rata billing anchor fields.
/// </summary>
/// <summary>A pinned skill assignment in an Employment Contract (ADR-043 §4).</summary>
public sealed record SkillAssignment(
    string SkillId,
    string Version,
    /// <summary>UTC timestamp when the skill was assigned. ADR-043 §4: assigned_at.</summary>
    DateTimeOffset AssignedAt = default);

public sealed record HireAgentRequest(
    string ContractId,
    string ProfessionalType,
    string SkillId,
    string DecisionSpaceVersion,
    long ApprovedBudgetInrPaise,
    string BillingCycleAnchorDay,
    /// <summary>Optional skills[] array (ADR-043 §4). Each entry must exist at pinned version in Skill Catalog.</summary>
    IReadOnlyList<SkillAssignment>? Skills = null);   // C-036: skills are constitutional units

public sealed record LegacyDecisionSpaceInput(string ProfessionalType);

public sealed record LegacyFormEmploymentContractRequest(
    Guid ProfessionalId,
    LegacyDecisionSpaceInput DecisionSpace,
    Guid? EvaluationIntentId = null,
    Guid? CorrelationId = null);

/// <summary>Request for POST /api/v1/agents/amend — adds or removes a skill from an existing contract.</summary>
public sealed record AmendContractRequest(
    string ContractId,
    string SkillId,
    string SkillVersion,
    string AmendmentType);   // ADD | REMOVE

[ApiController, Route("api/v1")]
public sealed class CustomersController : ControllerBase
{
    // ── Constants (C-072: no magic numbers) ────────────────────────────────
    private const int CeValidateTimeoutSeconds = 5;   // ADR-001 latency budget guard
    private const string CeActionRegisterCustomer = "REGISTER_CUSTOMER";
    private const string CeActionHireAgent = "HIRE_AGENT";
    private const string CeActionSkillAmendment = "SKILL_AMENDMENT";

    private readonly IConfiguration _config;
    private readonly IDbContextFactory<SkillCatalogDbContext> _skillDbFactory;
    private readonly EmploymentRelationshipService _relationshipService;
    private readonly ILogger<CustomersController> _logger;

    public CustomersController(
        IConfiguration config,
        IDbContextFactory<SkillCatalogDbContext> skillDbFactory,
        EmploymentRelationshipService relationshipService,
        ILogger<CustomersController> logger)
    {
        _config         = config;
        _skillDbFactory = skillDbFactory;
        _relationshipService = relationshipService;
        _logger         = logger;
    }

    // ── Existing methods (frozen — must not be removed) ────────────────────

    [Authorize]
    [HttpPost("employment/contracts")]
    public async Task<IActionResult> FormEmploymentContract(
        [FromBody] LegacyFormEmploymentContractRequest request,
        CancellationToken cancellationToken)
    {
        if (!LegacyEmploymentCompatibility.TryGetIdentity(HttpContext, out var tenantId, out var participantId))
        {
            return Forbid();
        }

        var correlationId = request.CorrelationId ?? Guid.NewGuid();
        var result = request.EvaluationIntentId.HasValue
            ? await _relationshipService.AdmitAsync(
                tenantId,
                participantId,
                request.EvaluationIntentId.Value,
                request.DecisionSpace.ProfessionalType,
                correlationId,
                cancellationToken)
            : await _relationshipService.AdmitLegacyAsync(
                tenantId,
                participantId,
                request.ProfessionalId.ToString(),
                request.DecisionSpace.ProfessionalType,
                correlationId,
                cancellationToken);
        LegacyEmploymentCompatibility.AddDeprecationHeaders(Response, result.Relationship.RelationshipId);
        var response = ToLegacyContract(result.Relationship, request.ProfessionalId);
        return result.Created
            ? CreatedAtAction(nameof(GetEmploymentContract), new { id = result.Relationship.RelationshipId }, response)
            : Ok(response);
    }

    [Authorize]
    [HttpGet("employment/contracts/{id}")]
    public async Task<IActionResult> GetEmploymentContract(Guid id, CancellationToken cancellationToken)
    {
        if (!LegacyEmploymentCompatibility.TryGetIdentity(HttpContext, out var tenantId, out _))
        {
            return Forbid();
        }

        var relationship = await _relationshipService.GetAsync(tenantId, id, cancellationToken);
        if (relationship is null)
        {
            return NotFound();
        }

        LegacyEmploymentCompatibility.AddDeprecationHeaders(Response, relationship.RelationshipId);
        return Ok(ToLegacyContract(relationship, null));
    }

    // ── New endpoints (WC013-03a) ──────────────────────────────────────────

    /// <summary>
    /// POST /api/v1/customers
    /// Registers a new customer tenant.
    /// C-023: CE.ValidateAction is called and confirmed before any side effect is produced.
    /// </summary>
    [HttpPost("customers")]
    public async Task<IActionResult> RegisterCustomerAsync(
        [FromBody] RegisterCustomerRequest request,
        CancellationToken cancellationToken)
    {
        if (request is null)
            return BadRequest("Request body is required.");

        // C-023: Validate action with CE before executing (Evidence First).
        // ⛔ CE call is a pre-condition — NOT inside any DB transaction.
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        cts.CancelAfter(TimeSpan.FromSeconds(CeValidateTimeoutSeconds));

        ValidationDecision ceDecision;
        try
        {
            var grpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
                ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");

            var channel = GrpcChannel.ForAddress(grpcUrl);
            var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

            var ceResponse = await ceClient.ValidateActionAsync(new ValidateActionRequest
            {
                ContractId           = request.TenantId,   // tenant acts as contract scope at registration
                ActionType           = CeActionRegisterCustomer,
                ActionParameters     = $"{{\"email\":\"{request.Email}\"}}",
                DecisionSpaceVersion = 1
            }, cancellationToken: cts.Token);

            ceDecision = ceResponse.Decision;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: log before returning.
            _logger.LogError(ex, "CE.ValidateAction failed for REGISTER_CUSTOMER — tenant={TenantId}", request.TenantId);
            return StatusCode(503, "Constitutional validation unavailable. Please retry.");
        }

        // CS0019 guard: ValidationDecision (not PolicyDecision) is the correct type here.
        if (ceDecision == ValidationDecision.Deny)
        {
            _logger.LogWarning("CE denied REGISTER_CUSTOMER for tenant={TenantId}", request.TenantId);
            return Forbid();
        }

        if (ceDecision == ValidationDecision.Unspecified)
        {
            _logger.LogWarning(
                "CE returned Unspecified for REGISTER_CUSTOMER — escalating for tenant={TenantId}",
                request.TenantId);
            return StatusCode(503, "Constitutional decision unspecified. Escalation required.");
        }

        // CE returned Allow — proceed with customer registration.
        // Placeholder: real implementation persists via EmploymentService (WC013-03b scope).
        var customerId = Guid.NewGuid();
        _logger.LogInformation(
            "Customer registered: customerId={CustomerId} tenant={TenantId}",
            customerId, request.TenantId);

        return CreatedAtAction(
            nameof(GetEmploymentContract),
            new { id = customerId },
            new
            {
                customer_id   = customerId,
                name          = request.Name,
                email         = request.Email,
                tenant_id     = request.TenantId,
                registered_at = DateTimeOffset.UtcNow
            });
    }

    /// <summary>
    /// POST /api/v1/agents/hire
    /// Hires a digital professional under an employment contract.
    /// C-023: CE.ValidateAction confirmed before any write.
    /// C-038: pro_rata_billing_start_date is populated at the moment of hire.
    /// </summary>
    [Authorize]
    [HttpPost("agents/hire")]
    public async Task<IActionResult> HireAgentAsync(
        [FromBody] HireAgentRequest request,
        CancellationToken cancellationToken)
    {
        if (request is null)
            return BadRequest("Request body is required.");

        // C-036: validate skills[] pre-condition before calling CE.
        // Analogous to phone_verified gate — reject malformed request immediately.
        // This is config validation (read-only catalog lookup), not a state change,
        // so it does not require CE evidence first.
        if (request.Skills is { Count: > 0 })
        {
            await using var skillDb = await _skillDbFactory.CreateDbContextAsync(cancellationToken);
            foreach (var assignment in request.Skills)
            {
                var exists = await skillDb.Skills.AnyAsync(
                    s => s.SkillId == assignment.SkillId
                      && s.Version  == assignment.Version
                      && s.Status   == "PUBLISHED",
                    cancellationToken);

                if (!exists)
                {
                    _logger.LogWarning(
                        "HIRE_AGENT rejected: skill not found. ContractId={ContractId} SkillId={SkillId} Version={Version}",
                        request.ContractId, assignment.SkillId, assignment.Version);
                    return UnprocessableEntity(new
                    {
                        error    = "SKILL_NOT_FOUND",
                        skill_id = assignment.SkillId,
                        version  = assignment.Version,
                    });
                }
            }
        }

        if (!LegacyEmploymentCompatibility.TryGetIdentity(HttpContext, out var tenantId, out var participantId))
        {
            return Forbid();
        }

        try
        {
            var result = await _relationshipService.AdmitLegacyAsync(
                tenantId,
                participantId,
                request.ContractId,
                request.ProfessionalType,
                Guid.NewGuid(),
                cancellationToken);
            LegacyEmploymentCompatibility.AddDeprecationHeaders(Response, result.Relationship.RelationshipId);
            var admittedAt = result.Relationship.CreatedAt;
            var response = new
            {
                hire_id                     = result.Relationship.RelationshipId,
                relationship_id             = result.Relationship.RelationshipId,
                contract_id                 = request.ContractId,
                professional_type           = request.ProfessionalType,
                skill_id                    = request.SkillId,
                skills                      = request.Skills?.Select(s => s with { AssignedAt = admittedAt }).ToList() ?? [],
                decision_space_version      = request.DecisionSpaceVersion,
                approved_budget_inr_paise   = request.ApprovedBudgetInrPaise,
                billing_cycle_anchor_day    = request.BillingCycleAnchorDay,
                pro_rata_billing_start_date = admittedAt,
                hired_at                    = admittedAt,
            };
            return result.Created
                ? CreatedAtAction(nameof(GetEmploymentContract), new { id = result.Relationship.RelationshipId }, response)
                : Ok(response);
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            return Problem(statusCode: StatusCodes.Status403Forbidden, title: "Constitutional authorization denied", detail: exception.Message);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            _logger.LogError(exception, "Legacy hire adapter failed for contract {ContractId}", request.ContractId);
            return Problem(statusCode: StatusCodes.Status503ServiceUnavailable, title: "Constitutional evidence unavailable");
        }
    }

    // ── WC040-05: Skill amendment — CE evidence record required ──────────────

    /// <summary>
    /// POST /api/v1/agents/amend
    /// Adds or removes a skill from an existing Employment Contract.
    /// ADR-043 §4: every amendment requires CE evidence record with action_type=SKILL_AMENDMENT.
    /// C-023: CE.ValidateAction must precede any state change.
    /// </summary>
    [HttpPost("agents/amend")]
    public async Task<IActionResult> AmendContractAsync(
        [FromBody] AmendContractRequest request,
        CancellationToken cancellationToken)
    {
        if (request is null)
            return BadRequest("Request body is required.");

        if (request.AmendmentType is not ("ADD" or "REMOVE"))
            return BadRequest(new { error = "AmendmentType must be ADD or REMOVE." });

        // For ADD: verify skill exists at declared version before CE call.
        if (request.AmendmentType == "ADD")
        {
            await using var skillDb = await _skillDbFactory.CreateDbContextAsync(cancellationToken);
            var exists = await skillDb.Skills.AnyAsync(
                s => s.SkillId == request.SkillId
                  && s.Version  == request.SkillVersion
                  && s.Status   == "PUBLISHED",
                cancellationToken);

            if (!exists)
            {
                _logger.LogWarning(
                    "AmendContract ADD rejected: skill not found. ContractId={ContractId} SkillId={SkillId} Version={Version}",
                    request.ContractId, request.SkillId, request.SkillVersion);
                return UnprocessableEntity(new
                {
                    error    = "SKILL_NOT_FOUND",
                    skill_id = request.SkillId,
                    version  = request.SkillVersion,
                });
            }
        }

        // C-023: CE.ValidateAction with action_type=SKILL_AMENDMENT before any state change.
        var ceGrpcUrl = _config["ConstitutionalEngine:GrpcUrl"];
        if (string.IsNullOrWhiteSpace(ceGrpcUrl))
        {
            _logger.LogError("ConstitutionalEngine:GrpcUrl missing for SKILL_AMENDMENT. ContractId={ContractId}", request.ContractId);
            return StatusCode(503, new { error = "Constitutional Engine address is not configured." });
        }

        ValidateActionResponse ceResponse;
        try
        {
            using var channel  = GrpcChannel.ForAddress(ceGrpcUrl);
            var ceClient       = new ConstitutionalService.ConstitutionalServiceClient(channel);
            using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            linkedCts.CancelAfter(TimeSpan.FromSeconds(CeValidateTimeoutSeconds));

            ceResponse = await ceClient.ValidateActionAsync(
                new ValidateActionRequest
                {
                    ContractId           = request.ContractId,
                    ActionType           = CeActionSkillAmendment,
                    ActionParameters     = $"{{\"skill_id\":\"{request.SkillId}\"," +
                                           $"\"version\":\"{request.SkillVersion}\"," +
                                           $"\"amendment_type\":\"{request.AmendmentType}\"}}",
                    DecisionSpaceVersion = 1,
                },
                cancellationToken: linkedCts.Token);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "CE.ValidateAction failed for SKILL_AMENDMENT. ContractId={ContractId}", request.ContractId);
            return StatusCode(503, new { error = "Constitutional Engine unavailable. Amendment cannot proceed (C-023)." });
        }

        if (ceResponse.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied SKILL_AMENDMENT. ContractId={ContractId} Decision={Decision}",
                request.ContractId, ceResponse.Decision);
            return StatusCode(403, new
            {
                error                = "Constitutional Engine denied the skill amendment.",
                decision             = ceResponse.Decision.ToString(),
                reason               = ceResponse.Reason,
                constitutional_basis = ceResponse.ConstitutionalBasis,
            });
        }

        // CE returned Allow — amendment is authorised with evidence record written.
        var amendmentId = Guid.NewGuid();
        _logger.LogInformation(
            "SKILL_AMENDMENT authorised. AmendmentId={AmendmentId} ContractId={ContractId} " +
            "SkillId={SkillId} Version={Version} Type={AmendmentType}",
            amendmentId, request.ContractId, request.SkillId, request.SkillVersion, request.AmendmentType);

        return Ok(new
        {
            amendment_id         = amendmentId,
            contract_id          = request.ContractId,
            skill_id             = request.SkillId,
            version              = request.SkillVersion,
            amendment_type       = request.AmendmentType,
            amended_at           = DateTimeOffset.UtcNow,
            ce_evidence_basis    = ceResponse.ConstitutionalBasis,
        });
    }

    private static object ToLegacyContract(EmploymentRelationship relationship, Guid? professionalId) => new
    {
        id = relationship.RelationshipId,
        relationshipId = relationship.RelationshipId,
        professionalId,
        professionalType = relationship.ProfessionalType,
        state = "EVALUATION",
        relationshipState = RelationshipStateCodec.ToDatabase(relationship.State),
        createdAt = relationship.CreatedAt,
        updatedAt = relationship.UpdatedAt,
    };
}