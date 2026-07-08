using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Constitutional.V1;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Route("api/v1/employment/contracts")]
[Authorize]
public class EmploymentController : ControllerBase
{
    private readonly BusinessDbContext _db;
    private readonly ConstitutionalService.ConstitutionalServiceClient _ce;
    private readonly ILogger<EmploymentController> _logger;

    public EmploymentController(
        BusinessDbContext db,
        ConstitutionalService.ConstitutionalServiceClient ce,
        ILogger<EmploymentController> logger)
    {
        _db = db;
        _ce = ce;
        _logger = logger;
    }

    /// <summary>
    /// Form an Employment Contract.
    /// Evidence First (C-023): CE.RecordEvidence is called and confirmed
    /// BEFORE this method returns 200 to the customer.
    /// If CE fails, this method returns 500 — the contract is not formed.
    /// </summary>
    [HttpPost]
    public async Task<IActionResult> FormEmploymentContract(
        [FromBody] FormEmploymentContractRequest request,
        CancellationToken ct)
    {
        var tenantId = HttpContext.Items["tenant_id"]?.ToString();
        if (string.IsNullOrEmpty(tenantId))
            return Unauthorized("tenant_id claim required");

        var contract = new EmploymentContract
        {
            Id = Guid.NewGuid(),
            TenantId = Guid.Parse(tenantId),
            ProfessionalId = Guid.Parse(request.ProfessionalId),
            State = "EVALUATION",
            Goals = request.Goals ?? "[]",
            ReviewCadence = """{"frequencyDays": 30}""",
            IsTrial = request.IsTrial,
            TrialEndsAt = request.IsTrial ? DateTime.UtcNow.AddDays(7) : null,
            CreatedAt = DateTime.UtcNow
        };

        await _db.EmploymentContracts.AddAsync(contract, ct);

        // Evidence First (C-023, AD-002):
        // Call CE BEFORE saving to DB and BEFORE returning 200.
        // If CE fails, we return 500 — the contract must not be formed.
        var actionInstanceId = Guid.NewGuid().ToString();
        try
        {
            var headers = new Grpc.Core.Metadata
            {
                { "x-tenant-id", tenantId }
            };

            var evidenceResponse = await _ce.RecordEvidenceAsync(
                new RecordEvidenceRequest
                {
                    ActionInstanceId = actionInstanceId,
                    ContractId = contract.Id.ToString(),
                    ProfessionalId = contract.ProfessionalId.ToString(),
                    ActionType = "EMPLOYMENT_CONTRACT_FORMED",
                    State = EvidenceState.Proposed,
                    DecisionSpaceVersion = 1,
                    ConstitutionalBasis = "C-034; C-003; AD-002"
                },
                headers,
                cancellationToken: ct);

            _logger.LogInformation(
                "Evidence First: contract formation recorded as {EvidenceId}",
                evidenceResponse.EvidenceRecordId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "CE.RecordEvidence failed — contract not formed (Evidence First, C-023)");
            // Evidence First: CE failure means this operation failed
            return StatusCode(500, new ProblemDetails
            {
                Type = "https://waooaw.com/errors/evidence-first-failure",
                Title = "Evidence write failed",
                Status = 500,
                Detail = "Constitutional Engine could not record evidence. Contract not formed. (C-023)"
            });
        }

        // Only save to DB AFTER CE confirmed the evidence record
        await _db.SaveChangesAsync(ct);

        return Created($"/api/v1/employment/contracts/{contract.Id}", new
        {
            id = contract.Id,
            tenantId = contract.TenantId,
            professionalId = contract.ProfessionalId,
            state = contract.State,
            isTrial = contract.IsTrial,
            trialEndsAt = contract.TrialEndsAt,
            createdAt = contract.CreatedAt
        });
    }

    [HttpGet("{contractId}")]
    public async Task<IActionResult> GetContract(Guid contractId, CancellationToken ct)
    {
        var tenantId = HttpContext.Items["tenant_id"]?.ToString();
        if (string.IsNullOrEmpty(tenantId)) return Unauthorized();

        var contract = await _db.EmploymentContracts
            .Where(c => c.Id == contractId && c.TenantId == Guid.Parse(tenantId))
            .FirstOrDefaultAsync(ct);

        return contract == null ? NotFound() : Ok(contract);
    }
}

public record FormEmploymentContractRequest(
    string ProfessionalId,
    string? Goals,
    bool IsTrial = false);
