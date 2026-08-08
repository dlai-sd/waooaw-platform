// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-038, C-059
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// Manages the agent hire endpoint (POST /api/agents/hire).
/// C-023: Every hire action calls CE.ValidateAction before execution (Evidence First).
/// C-038: Pro-rata billing start date is stamped at hire time.
/// </summary>
[ApiController, Route("api")]
public sealed class AgentsController : ControllerBase
{
    private readonly EmploymentRelationshipService _relationshipService;
    private readonly ILogger<AgentsController> _logger;

    public AgentsController(
        EmploymentRelationshipService relationshipService,
        ILogger<AgentsController> logger)
    {
        _relationshipService = relationshipService;
        _logger = logger;
    }

    /// <summary>
    /// POST /api/agents/hire
    /// C-023: CE.ValidateAction is called and confirmed before any state change.
    /// C-038: pro_rata_billing_start_date is populated from the moment of hire.
    /// </summary>
    [Authorize]
    [HttpPost("agents/hire")]
    public async Task<IActionResult> HireAgentAsync(
        [FromBody] HireAgentRequest request,
        CancellationToken cancellationToken)
    {
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
            return Ok(new
            {
                contract_id = request.ContractId,
                relationship_id = result.Relationship.RelationshipId,
                professional_type = request.ProfessionalType,
                skill_id = request.SkillId,
                decision_space_version = request.DecisionSpaceVersion,
                approved_budget_inr_paise = request.ApprovedBudgetInrPaise,
                billing_cycle_anchor_day = request.BillingCycleAnchorDay,
                pro_rata_billing_start_date = admittedAt,
                state = "EVALUATION",
            });
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
}