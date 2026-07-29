// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-038, C-059
using Microsoft.AspNetCore.Mvc;
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
public sealed record HireAgentRequest(
    string ContractId,
    string ProfessionalType,
    string SkillId,
    string DecisionSpaceVersion,
    long ApprovedBudgetInrPaise,
    string BillingCycleAnchorDay);   // C-038: day-of-month anchor for pro-rata calculation

[ApiController, Route("api/v1")]
public sealed class CustomersController : ControllerBase
{
    // ── Constants (C-072: no magic numbers) ────────────────────────────────
    private const int CeValidateTimeoutSeconds = 5;   // ADR-001 latency budget guard
    private const string CeActionRegisterCustomer = "REGISTER_CUSTOMER";
    private const string CeActionHireAgent = "HIRE_AGENT";

    private readonly IConfiguration _config;
    private readonly ILogger<CustomersController> _logger;

    public CustomersController(IConfiguration config, ILogger<CustomersController> logger)
    {
        _config = config;
        _logger = logger;
    }

    // ── Existing methods (frozen — must not be removed) ────────────────────

    [HttpPost("employment/contracts")]
    public IActionResult FormEmploymentContract() => Ok();

    [HttpGet("employment/contracts/{id}")]
    public IActionResult GetEmploymentContract(Guid id) => Ok();

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
    [HttpPost("agents/hire")]
    public async Task<IActionResult> HireAgentAsync(
        [FromBody] HireAgentRequest request,
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

            // C-038: include budget fields in action parameters so CE can enforce ceiling.
            var actionParams =
                $"{{\"contract_id\":\"{request.ContractId}\"," +
                $"\"professional_type\":\"{request.ProfessionalType}\"," +
                $"\"skill_id\":\"{request.SkillId}\"," +
                $"\"approved_budget_inr_paise\":{request.ApprovedBudgetInrPaise}," +
                $"\"billing_cycle_anchor_day\":\"{request.BillingCycleAnchorDay}\"}}";

            var ceResponse = await ceClient.ValidateActionAsync(new ValidateActionRequest
            {
                ContractId           = request.ContractId,
                ActionType           = CeActionHireAgent,
                ActionParameters     = actionParams,
                DecisionSpaceVersion = int.TryParse(request.DecisionSpaceVersion, out var dsv) ? dsv : 1
            }, cancellationToken: cts.Token);

            ceDecision = ceResponse.Decision;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: log before returning.
            _logger.LogError(
                ex,
                "CE.ValidateAction failed for HIRE_AGENT — contractId={ContractId} skill={SkillId}",
                request.ContractId, request.SkillId);
            return StatusCode(503, "Constitutional validation unavailable. Please retry.");
        }

        // CS0019 guard: ValidationDecision (not PolicyDecision) is the correct type here.
        if (ceDecision == ValidationDecision.Deny)
        {
            _logger.LogWarning(
                "CE denied HIRE_AGENT — contractId={ContractId} skill={SkillId}",
                request.ContractId, request.SkillId);
            return Forbid();
        }

        if (ceDecision == ValidationDecision.Unspecified)
        {
            _logger.LogWarning(
                "CE returned Unspecified for HIRE_AGENT — escalating contractId={ContractId}",
                request.ContractId);
            return StatusCode(503, "Constitutional decision unspecified. Escalation required.");
        }

        // CE returned Allow — proceed with agent hire.
        // C-038: pro_rata_billing_start_date is the exact moment of hire confirmation.
        var agentHireId = Guid.NewGuid();
        var proRataBillingStartDate = DateTimeOffset.UtcNow;   // C-038: billing clock starts NOW

        _logger.LogInformation(
            "Agent hired: hireId={HireId} contractId={ContractId} skill={SkillId} " +
            "proRataBillingStart={ProRataBillingStart} budgetPaise={BudgetPaise}",
            agentHireId, request.ContractId, request.SkillId,
            proRataBillingStartDate, request.ApprovedBudgetInrPaise);

        return CreatedAtAction(
            nameof(GetEmploymentContract),
            new { id = agentHireId },
            new
            {
                hire_id                     = agentHireId,
                contract_id                 = request.ContractId,
                professional_type           = request.ProfessionalType,
                skill_id                    = request.SkillId,
                decision_space_version      = request.DecisionSpaceVersion,
                approved_budget_inr_paise   = request.ApprovedBudgetInrPaise,
                billing_cycle_anchor_day    = request.BillingCycleAnchorDay,
                pro_rata_billing_start_date = proRataBillingStartDate,   // C-038
                hired_at                    = proRataBillingStartDate
            });
    }
}