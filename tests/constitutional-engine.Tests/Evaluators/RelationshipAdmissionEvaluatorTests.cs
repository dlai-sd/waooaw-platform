using System.Text.Json;
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class RelationshipAdmissionEvaluatorTests
{
    [Fact]
    public async Task GovernedCustomerAcquisitionIsAllowed()
    {
        var result = await new RelationshipAdmissionEvaluator().EvaluateAsync(Context());

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Theory]
    [InlineData(ApprovalType.Unspecified, DcmCategory.DeterministicRequired)]
    [InlineData(ApprovalType.CustomerExplicit, DcmCategory.Unspecified)]
    public async Task MissingApprovalOrDeterministicRoutingIsDenied(
        ApprovalType approval,
        DcmCategory category
    )
    {
        var result = await new RelationshipAdmissionEvaluator().EvaluateAsync(
            Context(approval, category)
        );

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task IncompleteAcquisitionBindingIsDenied()
    {
        var context = Context() with
        {
            ActionParameters = JsonSerializer.Serialize(
                new
                {
                    evaluation_intent_id = Guid.NewGuid(),
                    initiating_participant_id = Guid.NewGuid(),
                    agent_instance_id = Guid.NewGuid(),
                    professional_type = "DIGITAL_MARKETING",
                    target_state = "DISCOVERED",
                    acquisition_intent = "HIRE",
                }
            ),
        };

        var result = await new RelationshipAdmissionEvaluator().EvaluateAsync(context);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    private static EvaluationContext Context(
        ApprovalType approval = ApprovalType.CustomerExplicit,
        DcmCategory category = DcmCategory.DeterministicRequired
    ) =>
        new(
            Guid.NewGuid().ToString(),
            "ADMIT_EMPLOYMENT_RELATIONSHIP",
            JsonSerializer.Serialize(
                new
                {
                    evaluation_intent_id = Guid.NewGuid(),
                    initiating_participant_id = Guid.NewGuid(),
                    agent_instance_id = Guid.NewGuid(),
                    professional_admission_id = Guid.NewGuid(),
                    professional_type = "DIGITAL_MARKETING",
                    professional_version = "1.0.0",
                    target_state = "DISCOVERED",
                    acquisition_intent = "HIRE",
                    disclosure_revision = "2026-09-24",
                    terms_version = "2026-09-24",
                }
            ),
            1,
            Guid.NewGuid().ToString(),
            ApprovalType: approval,
            DcmCategory: category
        );
}