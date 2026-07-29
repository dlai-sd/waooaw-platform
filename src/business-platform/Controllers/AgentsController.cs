// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-038, C-059
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Net.Client;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// Manages agent hire operations under the employment lifecycle (C-034).
/// Every hire call is pre-authorised by CE.ValidateAction (C-023 — Evidence First).
/// Pro-rata billing start date is populated on contract creation (C-038).
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
    /// C-023: CE.ValidateAction is called as a pre-condition — never inside a DB transaction.
    /// C-038: ProRataBillingStartDate is set at the moment of contract creation.
    /// C-034: Contract begins in EVALUATION state.
    /// </summary>
    [HttpPost("agents/hire")]
    public async Task<IActionResult> HireAgent(
        [FromBody] HireAgentRequest request,
        CancellationToken cancellationToken)
    {
        var contractId = Guid.NewGuid();
        var tenantClaim = HttpContext.User.FindFirst("tenant_id")?.Value ?? string.Empty;

        // ── C-023: CE.ValidateAction pre-condition ───────────────────────────────
        // MUST complete before any business state is written.
        // MUST NOT be inside a database transaction.
        ValidateActionResponse ceResponse;
        try
        {
            var grpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
                ?? throw new InvalidOperationException(
                    "ConstitutionalEngine:GrpcUrl is not configured");

            using var channel = GrpcChannel.ForAddress(grpcUrl);
            var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

            var validateRequest = new ValidateActionRequest
            {
                ContractId         = contractId.ToString(),
                ActionType         = "HIRE_AGENT",
                ActionParameters   =
                    $"{{\"professional_type\":\"{request.ProfessionalType}\"," +
                    $"\"contract_display_name\":\"{request.ContractDisplayName}\"," +
                    $"\"approved_budget_inr_paise\":{request.ApprovedBudgetInrPaise}}}",
                DecisionSpaceVersion = 1,
            };

            ceResponse = await ceClient.ValidateActionAsync(
                validateRequest,
                cancellationToken: cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(
                ex,
                "CE.ValidateAction failed for HireAgent: {ContractId} tenant={TenantId}",
                contractId, tenantClaim);

            return StatusCode(503, new
            {
                error      = "Constitutional Engine validation unavailable",
                contractId = contractId,
            });
        }

        // C-023: only proceed when CE explicitly permits — deny on anything else
        if (ceResponse.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied HIRE_AGENT for contract {ContractId} tenant={TenantId}: {Reason}",
                contractId, tenantClaim, ceResponse.Reason);

            return StatusCode(403, new
            {
                error      = "Action denied by Constitutional Engine",
                reason     = ceResponse.Reason,
                contractId = contractId,
            });
        }

        // ── Parse tenant from JWT claim ───────────────────────────────────────────
        if (!Guid.TryParse(tenantClaim, out var tenantId))
        {
            _logger.LogWarning(
                "HireAgent: missing or invalid tenant_id claim for contract {ContractId}",
                contractId);
            return Unauthorized(new { error = "tenant_id claim absent or malformed" });
        }

        // ── C-038: Pro-rata billing start date = instant of contract creation ─────
        var now = DateTimeOffset.UtcNow;

        var dto = new EmploymentContractDto(
            contractId,
            tenantId,
            request.ProfessionalType,
            request.ContractDisplayName,
            "EVALUATION",                   // C-034: lifecycle begins in EVALUATION state
            request.ApprovedBudgetInrPaise, // C-038: budget locked at hire
            now,                            // ProRataBillingStartDate — C-038
            request.BillingPreference,      // "SEPARATE" | "COMBINED"
            now                             // CreatedAt
        );

        _logger.LogInformation(
            "HireAgent: contract {ContractId} created (state=EVALUATION, tenant={TenantId}, " +
            "professionalType={ProfessionalType}, billingStart={BillingStart:O}) — C-034 C-038",
            contractId, tenantId, request.ProfessionalType, now);

        return Created($"/api/v1/employment/contracts/{contractId}", dto);
    }
}