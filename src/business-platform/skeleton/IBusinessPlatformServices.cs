// Implements: architecture/reference/components/manifest/bp.yaml §surface.endpoints
// Constitutional basis: C-038 (Pro-rata billing), C-043 (Budget ceiling), C-059
// EA-PRODUCED SKELETON — DO NOT change signatures. Raise SPEC_GAP if change needed.

#nullable enable
namespace Waooaw.BusinessPlatform.Skeleton;

/// <summary>
/// Employment contract management. All actions require prior CE.ValidateAction.
/// </summary>
public interface IEmploymentService
{
    Task<EmploymentContractDto> CreateContractAsync(
        CreateContractRequest request,
        CancellationToken ct = default);

    Task<EmploymentContractDto> GetContractAsync(
        Guid contractId,
        string tenantId,
        CancellationToken ct = default);

    Task PauseContractAsync(Guid contractId, string tenantId, CancellationToken ct = default);
    Task ResumeContractAsync(Guid contractId, string tenantId, CancellationToken ct = default);
}

/// <summary>
/// Customer (organisation) registration and management.
/// </summary>
public interface ICustomerService
{
    Task<OrganisationDto> RegisterAsync(RegisterCustomerRequest request, CancellationToken ct = default);
    Task<OrganisationDto> GetAsync(Guid organisationId, string tenantId, CancellationToken ct = default);
}

/// <summary>Thrown when CE.ValidateAction returns DENY for a business operation.</summary>
public sealed class ConstitutionalDenyException(string reason, string claimId)
    : Exception($"CE DENY [{claimId}]: {reason}");

public sealed record CreateContractRequest(
    Guid OrganisationId,
    string AgentType,
    string BundleTier,
    string[] AuthorisedSkills);

public sealed record EmploymentContractDto(
    Guid Id,
    Guid OrganisationId,
    string AgentType,
    string Status,
    DateTimeOffset CreatedAt);

public sealed record RegisterCustomerRequest(
    string DisplayName,
    string Email,
    string? Phone,
    string? Gstin);

public sealed record OrganisationDto(Guid Id, string DisplayName, string Status);
