// Implements: WC-079 AA-05, AA-09
// constitutional_basis: C-003, C-023, C-059, C-063, C-065

using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class AgentAdmissionTransitionEvaluatorTests
{
    [Theory]
    [InlineData("AGENT_ADMISSION_SUBMIT", "OWNER_DELEGATE")]
    [InlineData("AGENT_ADMISSION_APPROVE", "ADMISSION_APPROVER")]
    [InlineData("AGENT_ADMISSION_REJECT", "FOUNDER")]
    [InlineData("AGENT_ADMISSION_ACTIVATE", "PLATFORM_ACTIVATION_AUTHORITY")]
    [InlineData("AGENT_ADMISSION_SUSPEND", "CONSTITUTIONAL_AUTHORITY")]
    [InlineData("AGENT_ADMISSION_SUPERSEDE", "LIFECYCLE_AUTHORITY")]
    [InlineData("AGENT_ADMISSION_RETIRE", "LIFECYCLE_AUTHORITY")]
    public async Task ExactLicensedAuthorityAllows(string action, string authority)
    {
        var result = await new AgentAdmissionTransitionEvaluator().EvaluateAsync(Context(action, authority));

        Assert.Equal(EvaluationVerdict.Allow, result.Verdict);
    }

    [Fact]
    public async Task SubmitterCannotApproveSameProfessionalVersion()
    {
        var result = await new AgentAdmissionTransitionEvaluator().EvaluateAsync(
            Context("AGENT_ADMISSION_APPROVE", "ADMISSION_APPROVER", actor: "same", submitter: "same"));

        Assert.Equal(EvaluationVerdict.Deny, result.Verdict);
    }

    [Theory]
    [InlineData("AGENT_ADMISSION_PUBLISH", "FOUNDER")]
    [InlineData("AGENT_ADMISSION_APPROVE", "OWNER_DELEGATE")]
    public async Task UnknownOrUnlicensedTransitionDenies(string action, string authority)
    {
        var result = await new AgentAdmissionTransitionEvaluator().EvaluateAsync(Context(action, authority));

        Assert.Equal(EvaluationVerdict.Deny, result.Verdict);
    }

    private static EvaluationContext Context(
        string action,
        string authority,
        string actor = "actor",
        string submitter = "submitter") => new(
            Guid.NewGuid().ToString("D"),
            action,
            JsonSerializer.Serialize(new
            {
                actor_subject_id = actor,
                actor_authority = authority,
                submitter_subject_id = submitter,
                AdmissionContentDigest = "sha256:" + new string('a', 64),
                EvidenceSetDigest = "sha256:" + new string('e', 64),
                PolicyVersion = "WC-079-1.0",
            }),
            1,
            Guid.NewGuid().ToString("D"));
}