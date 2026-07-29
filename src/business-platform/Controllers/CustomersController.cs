// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-038, C-059
using Microsoft.AspNetCore.Mvc;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Net.Client;

namespace Waooaw.BusinessPlatform.Controllers;

// C-023: Every mutating action calls CE.ValidateAction BEFORE executing.
// C-038: Hire endpoint populates pro-rata billing start date on contract creation.
// C-059: All constitutional obligations are traced in headers and enforced in body.

/// <summary>
/// Request body for customer registration (POST /api/customers).
/// </summary>
public sealed record RegisterCustomerRequest(
    string DisplayName,
    string Email,
    string OrganisationName
);

/// <summary>
/// Request body for agent hire (POST /api/agents/hire).
/// C-038: pro_rata_billing_start_date is mandatory — set to UtcNow at hire time.
/// </summary>
public sealed record HireAgentRequest(
    Guid ContractId,
    string ProfessionalType,
    string SkillId,
    long ApprovedBudgetInrPaise
);

/// <summary>
/// Response for customer registration.
/// </summary>
public sealed record RegisterCustomerResponse(
    Guid CustomerId,
    string DisplayName,
    string Email,
    string OrganisationName,
    DateTimeOffset RegisteredAt
);

/// <summary>
/// Response for agent hire.
/// C-038: pro_rata_billing_start_date populated at hire time (never null after hire).
/// </summary>
public sealed record HireAgentResponse(
    Guid ContractId,
    string ProfessionalType,
    string SkillId,
    long ApprovedBudgetInrPaise,
    DateTimeOffset ProRataBillingStartDate,
    string State,
    string EvidenceRecordId
);

[ApiController]
public sealed class CustomersController : ControllerBase
{
    private readonly IConfiguration _config;
    private readonly ILogger<CustomersController> _logger;

    public CustomersController(
        IConfiguration config,
        ILogger<CustomersController> logger)
    {
        _config = config;
        _logger = logger;
    }

    // ─── Existing Employment Endpoints (preserved — WC013-02a) ─────────────

    [HttpPost("api/v1/employment/contracts")]
    public IActionResult FormEmploymentContract() => Ok();

    [HttpGet("api/v1/employment/contracts/{id}")]
    public IActionResult GetEmploymentContract(Guid id) => Ok();

    // ─── POST /api/customers ────────────────────────────────────────────────

    /// <summary>
    /// Register a new customer organisation.
    /// C-023: CE.ValidateAction(CUSTOMER_REGISTRATION) is called and confirmed BEFORE
    ///        the registration record is created.
    /// </summary>
    [HttpPost("api/customers")]
    [ProducesResponseType(typeof(RegisterCustomerResponse), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> RegisterCustomer(
        [FromBody] RegisterCustomerRequest request,
        CancellationToken cancellationToken)
    {
        if (request is null)
            return BadRequest(new { error = "Request body is required." });

        if (string.IsNullOrWhiteSpace(request.Email))
            return BadRequest(new { error = "Email is required." });

        if (string.IsNullOrWhiteSpace(request.OrganisationName))
            return BadRequest(new { error = "OrganisationName is required." });

        // C-023: Call CE.ValidateAction BEFORE any side-effect.
        // ⛔ CE call is NOT inside a DB transaction — it is a pre-condition.
        ValidateActionResponse ceDecision;
        try
        {
            var grpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
                ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");

            using var channel = GrpcChannel.ForAddress(grpcUrl);
            var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

            var validateRequest = new ValidateActionRequest
            {
                ContractId           = Guid.Empty.ToString(), // no contract yet at registration
                ActionType           = "CUSTOMER_REGISTRATION",
                ActionParameters     = $"{{\"email\":\"{request.Email}\",\"organisation\":\"{request.OrganisationName}\"}}",
                DecisionSpaceVersion = 0
            };

            using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            cts.CancelAfter(TimeSpan.FromSeconds(5)); // ERROR HANDLING RULE 4

            ceDecision = await ceClient.ValidateActionAsync(
                validateRequest,
                cancellationToken: cts.Token);
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: log before returning
            _logger.LogError(ex,
                "CE.ValidateAction failed for CUSTOMER_REGISTRATION: {Context}",
                request.Email);
            return StatusCode(StatusCodes.Status503ServiceUnavailable,
                new { error = "Constitutional Engine unavailable. Registration cannot proceed." });
        }

        // C-023: PolicyDecision.Permit is the only value that allows continuation.
        // ceDecision.Decision is of type PolicyDecision (proto ValidateActionResponse).
        if (ceDecision.Decision != PolicyDecision.Permit)
        {
            _logger.LogWarning(
                "CE denied CUSTOMER_REGISTRATION for {Email}. Decision: {Decision} Reason: {Reason}",
                request.Email, ceDecision.Decision, ceDecision.Reason);
            return StatusCode(StatusCodes.Status403Forbidden,
                new { error = "Registration denied by constitutional policy.", reason = ceDecision.Reason });
        }

        // CE confirmed — now persist the customer record.
        var customerId   = Guid.NewGuid();
        var registeredAt = DateTimeOffset.UtcNow;

        // TODO(WC013-04): persist to business.customers via EmploymentService

        var response = new RegisterCustomerResponse(
            customerId,
            request.DisplayName,
            request.Email,
            request.OrganisationName,
            registeredAt
        );

        _logger.LogInformation(
            "Customer registered: {CustomerId} {Email} {Organisation}",
            customerId, request.Email, request.OrganisationName);

        return CreatedAtAction(
            nameof(GetEmploymentContract),
            new { id = customerId },
            response);
    }

    // ─── POST /api/agents/hire ──────────────────────────────────────────────

    /// <summary>
    /// Hire a professional agent on behalf of the authenticated customer.
    /// C-023: CE.ValidateAction(AGENT_HIRE) is called and confirmed BEFORE any side-effect.
    /// C-038: ProRataBillingStartDate is set to UtcNow at hire time — never null after hire.
    /// </summary>
    [HttpPost("api/agents/hire")]
    [ProducesResponseType(typeof(HireAgentResponse), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status503ServiceUnavailable)]
    public async Task<IActionResult> HireAgent(
        [FromBody] HireAgentRequest request,
        CancellationToken cancellationToken)
    {
        if (request is null)
            return BadRequest(new { error = "Request body is required." });

        if (string.IsNullOrWhiteSpace(request.ProfessionalType))
            return BadRequest(new { error = "ProfessionalType is required." });

        if (string.IsNullOrWhiteSpace(request.SkillId))
            return BadRequest(new { error = "SkillId is required." });

        if (request.ApprovedBudgetInrPaise <= 0)
            return BadRequest(new { error = "ApprovedBudgetInrPaise must be positive." });

        // C-023: Call CE.ValidateAction BEFORE any side-effect.
        // ⛔ CE call is NOT inside a DB transaction — it is a pre-condition.
        ValidateActionResponse ceDecision;
        RecordEvidenceResponse ceEvidence;
        try
        {
            var grpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
                ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");

            using var channel = GrpcChannel.ForAddress(grpcUrl);
            var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

            // Step 1 — validate the hire action (C-023).
            var validateRequest = new ValidateActionRequest
            {
                ContractId           = request.ContractId.ToString(),
                ActionType           = "AGENT_HIRE",
                ActionParameters     = $"{{\"professional_type\":\"{request.ProfessionalType}\","
                                       + $"\"skill_id\":\"{request.SkillId}\","
                                       + $"\"approved_budget_inr_paise\":{request.ApprovedBudgetInrPaise}}}",
                DecisionSpaceVersion = 1
            };

            using var validateCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            validateCts.CancelAfter(TimeSpan.FromSeconds(5)); // ERROR HANDLING RULE 4

            ceDecision = await ceClient.ValidateActionAsync(
                validateRequest,
                cancellationToken: validateCts.Token);

            if (ceDecision.Decision != PolicyDecision.Permit)
            {
                _logger.LogWarning(
                    "CE denied AGENT_HIRE for ContractId={ContractId} SkillId={SkillId}. "
                    + "Decision: {Decision} Reason: {Reason}",
                    request.ContractId, request.SkillId, ceDecision.Decision, ceDecision.Reason);
                return StatusCode(StatusCodes.Status403Forbidden,
                    new { error = "Agent hire denied by constitutional policy.", reason = ceDecision.Reason });
            }

            // Step 2 — record evidence BEFORE returning (Evidence First — AD-002, C-023).
            var proRataBillingStartDate = DateTimeOffset.UtcNow; // C-038: captured at hire time

            var evidenceRequest = new RecordEvidenceRequest
            {
                ContractId           = request.ContractId.ToString(),
                ActionType           = "AGENT_HIRE",
                State                = "EXECUTED",
                DecisionSpaceVersion = 1,
                ConstitutionalBasis  = "C-023,C-038",
                ExecutedContent      = $"{{\"professional_type\":\"{request.ProfessionalType}\","
                                       + $"\"skill_id\":\"{request.SkillId}\","
                                       + $"\"approved_budget_inr_paise\":{request.ApprovedBudgetInrPaise},"
                                       + $"\"pro_rata_billing_start_date\":\"{proRataBillingStartDate:O}\"}}"
            };

            using var evidenceCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            evidenceCts.CancelAfter(TimeSpan.FromSeconds(5)); // ERROR HANDLING RULE 4

            ceEvidence = await ceClient.RecordEvidenceAsync(
                evidenceRequest,
                cancellationToken: evidenceCts.Token);

            // CE evidence confirmed — now build the response.
            var hireResponse = new HireAgentResponse(
                request.ContractId,
                request.ProfessionalType,
                request.SkillId,
                request.ApprovedBudgetInrPaise,
                proRataBillingStartDate,   // C-038: never null after hire
                "EVALUATION",
                ceEvidence.EvidenceRecordId
            );

            _logger.LogInformation(
                "Agent hired: ContractId={ContractId} ProfessionalType={ProfessionalType} "
                + "SkillId={SkillId} EvidenceRecordId={EvidenceRecordId} "
                + "ProRataBillingStartDate={ProRataBillingStartDate}",
                request.ContractId,
                request.ProfessionalType,
                request.SkillId,
                ceEvidence.EvidenceRecordId,
                proRataBillingStartDate);

            // TODO(WC013-04): persist EmploymentContract to business schema via EmploymentService

            return CreatedAtAction(
                nameof(GetEmploymentContract),
                new { id = request.ContractId },
                hireResponse);
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: log before returning
            _logger.LogError(ex,
                "AGENT_HIRE failed for ContractId={Context}",
                request.ContractId);
            return StatusCode(StatusCodes.Status503ServiceUnavailable,
                new { error = "Constitutional Engine unavailable. Agent hire cannot proceed." });
        }
    }
}