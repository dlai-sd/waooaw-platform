// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-038, C-059
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Net.Client;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// Manages the agent hire endpoint (POST /api/agents/hire).
/// C-023: Every hire action calls CE.ValidateAction before execution (Evidence First).
/// C-038: Pro-rata billing start date is stamped at hire time.
/// </summary>
[ApiController, Route("api")]
public sealed class AgentsController : ControllerBase
{
    private readonly IConfiguration _config;
    private readonly ILogger<AgentsController> _logger;

    public AgentsController(IConfiguration config, ILogger<AgentsController> logger)
    {
        _config = config;
        _logger = logger;
    }

    /// <summary>
    /// POST /api/agents/hire
    /// C-023: CE.ValidateAction is called and confirmed before any state change.
    /// C-038: pro_rata_billing_start_date is populated from the moment of hire.
    /// </summary>
    [HttpPost("agents/hire")]
    public async Task<IActionResult> HireAgentAsync(
        [FromBody] HireAgentRequest request,
        CancellationToken cancellationToken)
    {
        // ── C-023: Constitutional pre-condition — CE.ValidateAction BEFORE execution ──
        // ⛔ CE call is NOT inside a DB transaction (stack rule).
        var ceGrpcUrl = _config["ConstitutionalEngine:GrpcUrl"];
        if (string.IsNullOrWhiteSpace(ceGrpcUrl))
        {
            _logger.LogError(
                "ConstitutionalEngine:GrpcUrl is missing from configuration. Contract={ContractId}",
                request.ContractId);
            return StatusCode(503, new { error = "Constitutional Engine address is not configured." });
        }

        ValidateActionResponse ceResponse;
        try
        {
            using var channel = GrpcChannel.ForAddress(ceGrpcUrl);
            var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

            var validateRequest = new ValidateActionRequest
            {
                ContractId = request.ContractId,
                ActionType = "AGENT_HIRE",
                ActionParameters =
                    $"{{\"professional_type\":\"{request.ProfessionalType}\"," +
                    $"\"skill_id\":\"{request.SkillId}\"," +
                    $"\"approved_budget_inr_paise\":\"{request.ApprovedBudgetInrPaise}\"}}",
                DecisionSpaceVersion = int.TryParse(request.DecisionSpaceVersion, out var dsvA) ? dsvA : 1,
            };

            // ERROR HANDLING RULE 4: bounded timeout — never block indefinitely
            using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            linkedCts.CancelAfter(TimeSpan.FromSeconds(5));

            ceResponse = await ceClient.ValidateActionAsync(
                validateRequest,
                cancellationToken: linkedCts.Token);
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: never swallow — always log with context
            _logger.LogError(
                ex,
                "Operation failed: CE.ValidateAction for AGENT_HIRE. Contract={ContractId}",
                request.ContractId);
            return StatusCode(503, new
            {
                error = "Constitutional Engine unavailable. Hire cannot proceed (C-023).",
            });
        }

        // ⛔ CS0019 guard: ValidateActionResponse.Decision is ValidationDecision, NOT PolicyDecision.
        // CORRECT comparison: ceResponse.Decision != ValidationDecision.Allow
        if (ceResponse.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied AGENT_HIRE. Contract={ContractId} Decision={Decision} Reason={Reason}",
                request.ContractId,
                ceResponse.Decision,
                ceResponse.Reason);

            return StatusCode(403, new
            {
                error = "Constitutional Engine denied the hire action.",
                decision = ceResponse.Decision.ToString(),
                reason = ceResponse.Reason,
                constitutional_basis = ceResponse.ConstitutionalBasis,
            });
        }

        // ── C-038: Pro-rata billing — stamp start date at the moment of hire ──────
        var proRataBillingStartDate = DateTimeOffset.UtcNow;

        // TODO(WC013-04): persist EmploymentContract via EmploymentService once
        // that service is wired. For now return the contract skeleton so the endpoint
        // is contractually complete and testable.
        var contractResponse = new
        {
            contract_id = request.ContractId,
            professional_type = request.ProfessionalType,
            skill_id = request.SkillId,
            decision_space_version = request.DecisionSpaceVersion,
            approved_budget_inr_paise = request.ApprovedBudgetInrPaise,
            billing_cycle_anchor_day = request.BillingCycleAnchorDay,
            pro_rata_billing_start_date = proRataBillingStartDate,
            state = "EVALUATION",
            ce_evidence_basis = ceResponse.ConstitutionalBasis,
        };

        _logger.LogInformation(
            "AGENT_HIRE authorised by CE. Contract={ContractId} BillingStart={BillingStart}",
            request.ContractId,
            proRataBillingStartDate);

        return Ok(contractResponse);
    }
}