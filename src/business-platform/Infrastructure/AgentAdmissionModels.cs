// Implements: WC-079 AA-03, AA-06, AA-08
// constitutional_basis: C-003, C-005, C-007, C-023, C-026, C-059, C-063

namespace Waooaw.BusinessPlatform.Infrastructure;

public enum AgentAdmissionState
{
    Draft,
    Validating,
    RemediationRequired,
    Validated,
    ReadyForReview,
    Approved,
    Active,
    Suspended,
    Superseded,
    Retired,
    Rejected,
}

public sealed class AgentAdmission
{
    public Guid AdmissionId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public string ProfessionalTypeId { get; init; } = string.Empty;
    public string ProfessionalVersion { get; init; } = string.Empty;
    public Guid OwnerSubjectId { get; init; }
    public Guid? SubmitterSubjectId { get; set; }
    public AgentAdmissionState State { get; set; } = AgentAdmissionState.Draft;
    public int StateVersion { get; set; }
    public int CurrentRevision { get; set; }
    public string? AdmissionContentDigest { get; set; }
    public string? EvidenceSetDigest { get; set; }
    public string? ArtifactDigest { get; set; }
    public string? PolicyVersion { get; set; }
    public string? SuccessorVersion { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class AgentAdmissionRevision
{
    public Guid RevisionId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid AdmissionId { get; init; }
    public int Revision { get; init; }
    public string ContractSchemaVersion { get; init; } = string.Empty;
    public string AdmissionContentDigest { get; init; } = string.Empty;
    public string AdmissionContentJson { get; init; } = "{}";
    public Guid ActorSubjectId { get; init; }
    public Guid? PredecessorRevisionId { get; init; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class AgentAdmissionValidation
{
    public Guid ValidationId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid AdmissionId { get; init; }
    public int Revision { get; init; }
    public string ValidatorProfile { get; init; } = string.Empty;
    public Guid IdempotencyKey { get; init; }
    public string RequestHash { get; init; } = string.Empty;
    public string Result { get; init; } = string.Empty;
    public int FindingCount { get; init; }
    public DateTimeOffset ValidatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class AgentAdmissionFinding
{
    public Guid FindingId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid ValidationId { get; init; }
    public string RuleId { get; init; } = string.Empty;
    public string Severity { get; init; } = "ERROR";
    public string ContractPath { get; init; } = string.Empty;
    public string ConstitutionalBasis { get; init; } = string.Empty;
    public string Expected { get; init; } = string.Empty;
    public string ObservedCategory { get; init; } = string.Empty;
    public string Remediation { get; init; } = string.Empty;
    public bool Blocking { get; init; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class AgentAdmissionAssertion
{
    public Guid AssertionId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid AdmissionId { get; init; }
    public string AssertionType { get; init; } = string.Empty;
    public string SubjectDigest { get; init; } = string.Empty;
    public string Environment { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty;
    public string SourceAuthority { get; init; } = string.Empty;
    public DateTimeOffset ObservedAt { get; init; }
    public DateTimeOffset ValidUntil { get; init; }
    public string PolicyVersion { get; init; } = string.Empty;
    public string EvidenceRef { get; init; } = string.Empty;
}

public sealed class AgentAdmissionTransition
{
    public Guid TransitionId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid AdmissionId { get; init; }
    public string FromState { get; init; } = string.Empty;
    public string ToState { get; init; } = string.Empty;
    public Guid ActorSubjectId { get; init; }
    public string ActorAuthority { get; init; } = string.Empty;
    public Guid CorrelationId { get; init; }
    public string AdmissionContentDigest { get; init; } = string.Empty;
    public string EvidenceSetDigest { get; init; } = string.Empty;
    public string? ArtifactDigest { get; init; }
    public string PolicyVersion { get; init; } = string.Empty;
    public Guid CeEvidenceRef { get; init; }
    public string? ReasonCategory { get; init; }
    public DateTimeOffset OccurredAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class AgentAdmissionIdempotency
{
    public Guid IdempotencyId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid AdmissionId { get; init; }
    public string Operation { get; init; } = string.Empty;
    public Guid IdempotencyKey { get; init; }
    public Guid ActorSubjectId { get; init; }
    public string? SubjectDigest { get; init; }
    public string MaterialRequestHash { get; init; } = string.Empty;
    public Guid? OutcomeReference { get; set; }
    public string? ResponseJson { get; set; }
    public string Status { get; set; } = "RECEIVED";
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? CompletedAt { get; set; }
}

public sealed class AgentAdmissionOutbox
{
    public Guid OutboxId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid AdmissionId { get; init; }
    public Guid TransitionId { get; init; }
    public string EventType { get; init; } = string.Empty;
    public string ScopeHash { get; init; } = string.Empty;
    public string PayloadJson { get; init; } = "{}";
    public DateTimeOffset OccurredAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? PublishedAt { get; set; }
    public int PublishAttempts { get; set; }
}

public static class AgentAdmissionStateCodec
{
    public static string ToDatabase(AgentAdmissionState state) => state switch
    {
        AgentAdmissionState.Draft => "DRAFT",
        AgentAdmissionState.Validating => "VALIDATING",
        AgentAdmissionState.RemediationRequired => "REMEDIATION_REQUIRED",
        AgentAdmissionState.Validated => "VALIDATED",
        AgentAdmissionState.ReadyForReview => "READY_FOR_REVIEW",
        AgentAdmissionState.Approved => "APPROVED",
        AgentAdmissionState.Active => "ACTIVE",
        AgentAdmissionState.Suspended => "SUSPENDED",
        AgentAdmissionState.Superseded => "SUPERSEDED",
        AgentAdmissionState.Retired => "RETIRED",
        AgentAdmissionState.Rejected => "REJECTED",
        _ => throw new ArgumentOutOfRangeException(nameof(state)),
    };

    public static AgentAdmissionState FromDatabase(string state) => state switch
    {
        "DRAFT" => AgentAdmissionState.Draft,
        "VALIDATING" => AgentAdmissionState.Validating,
        "REMEDIATION_REQUIRED" => AgentAdmissionState.RemediationRequired,
        "VALIDATED" => AgentAdmissionState.Validated,
        "READY_FOR_REVIEW" => AgentAdmissionState.ReadyForReview,
        "APPROVED" => AgentAdmissionState.Approved,
        "ACTIVE" => AgentAdmissionState.Active,
        "SUSPENDED" => AgentAdmissionState.Suspended,
        "SUPERSEDED" => AgentAdmissionState.Superseded,
        "RETIRED" => AgentAdmissionState.Retired,
        "REJECTED" => AgentAdmissionState.Rejected,
        _ => throw new ArgumentOutOfRangeException(nameof(state), state, "Unknown admission state."),
    };
}