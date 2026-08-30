// Implements: WC-079 AA-02, AA-04, AA-09, AA-10
// constitutional_basis: C-003, C-023, C-036, C-037, C-059, C-063, C-070, C-094

using System.Text.Json;
using FluentAssertions;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AgentAdmissionValidatorTests
{
    [Fact]
    public void Canonicalizer_SortsObjectKeys_AndPreservesUnicode()
    {
        using var document = JsonDocument.Parse("{\"z\":0,\"é\":\"é\",\"a\":[3,2,1]}");

        AgentAdmissionCanonicalizer.Canonicalize(document.RootElement)
            .Should().Be("{\"a\":[3,2,1],\"z\":0,\"é\":\"é\"}");
    }

    [Fact]
    public void Canonicalizer_UsesRfc8785NumberSerialization()
    {
      using var document = JsonDocument.Parse("[333333333.33333329,1E30,4.50,2e-3,0.000000000000000000000000001,1e-6,1e-7,-0]");

      AgentAdmissionCanonicalizer.Canonicalize(document.RootElement)
        .Should().Be("[333333333.3333333,1e+30,4.5,0.002,1e-27,0.000001,1e-7,0]");
    }

    [Theory]
    [InlineData("DIGITAL_MARKETING_LOCAL_SERVICE", "3.1.0")]
    [InlineData("TRADING_FO_CRYPTO", "1.8.0")]
    public void SharedValidator_AcceptsMateriallyDifferentProfessionals(string professionalType, string version)
    {
        using var document = ValidContract(professionalType, version);
        var digest = AgentAdmissionCanonicalizer.Digest(document.RootElement);

        var findings = new AgentAdmissionValidator().Validate(document.RootElement, professionalType, version, digest);

        findings.Should().BeEmpty();
    }

    [Fact]
    public void Validator_ReturnsMultipleSafeStableFindings()
    {
        using var document = JsonDocument.Parse("{\"contractSchemaVersion\":\"2.0.0\",\"professionalIdentity\":{},\"complianceDeclaration\":{},\"skillManifest\":[]}");

        var findings = new AgentAdmissionValidator().Validate(
            document.RootElement,
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            "3.1.0",
            "sha256:0000000000000000000000000000000000000000000000000000000000000000");

        findings.Select(value => value.RuleId).Should().Contain(["AAV-001", "AAV-002", "AAV-003", "AAV-004", "AAV-005", "AAV-006", "AAV-009", "AAV-010"]);
        findings.Should().OnlyContain(value => value.Blocking && value.Severity == "ERROR");
        JsonSerializer.Serialize(findings).Should().NotContain("credential").And.NotContain("prompt");
    }

      [Fact]
      public void Validator_RejectsUnknownAndNonObjectContractShapes()
      {
        using var valid = ValidContract("DIGITAL_MARKETING_LOCAL_SERVICE", "3.1.0");
        var content = valid.RootElement.GetRawText().Replace(
          "\"canonicalizationProfile\": \"RFC8785\"",
          "\"canonicalizationProfile\": \"RFC8785\", \"submitterReadiness\": \"PASS\"",
          StringComparison.Ordinal);
        using var unknown = JsonDocument.Parse(content);
        using var array = JsonDocument.Parse("[]");

        new AgentAdmissionValidator().Validate(
            unknown.RootElement, "DIGITAL_MARKETING_LOCAL_SERVICE", "3.1.0", AgentAdmissionCanonicalizer.Digest(unknown.RootElement))
          .Should().Contain(value => value.RuleId == "AAV-001" && value.ObservedCategory == "UNKNOWN_FIELD");
        new AgentAdmissionValidator().Validate(
            array.RootElement, "DIGITAL_MARKETING_LOCAL_SERVICE", "3.1.0", AgentAdmissionCanonicalizer.Digest(array.RootElement))
          .Should().ContainSingle(value => value.RuleId == "AAV-001" && value.ObservedCategory == "INVALID_CONTRACT_SHAPE");
      }

    [Fact]
    public void Validator_FailsClosed_WhenPlatformReadinessWasRequestedFromDraftContent()
    {
        using var document = ValidContract("DIGITAL_MARKETING_LOCAL_SERVICE", "3.1.0");

        var findings = new AgentAdmissionValidator().Validate(
            document.RootElement,
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            "3.1.0",
            AgentAdmissionCanonicalizer.Digest(document.RootElement),
            includeReadiness: true);

        findings.Should().ContainSingle(value => value.RuleId == "AAV-012" && value.ObservedCategory == "READINESS_REQUIRED");
    }

    internal static JsonDocument ValidContract(string professionalType, string version) => JsonDocument.Parse($$"""
        {
          "contractSchemaVersion": "1.0.0",
          "canonicalizationProfile": "RFC8785",
          "professionalIdentity": {
            "professionalTypeId": "{{professionalType}}",
            "professionalVersion": "{{version}}",
            "ownerSubjectId": "11111111-1111-1111-1111-111111111111",
            "supportedLanguages": ["en"],
            "supportedChannels": ["WEB", "WHATSAPP"],
            "agentSpecification": { "path": "architecture/reference/agents/spec.md", "version": "1", "digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111" },
            "agentVerificationDocument": { "path": "avd/spec.md", "version": "1", "digest": "sha256:2222222222222222222222222222222222222222222222222222222222222222" }
          },
          "complianceDeclaration": {
            "constitutionalDna": { "path": "dna.md", "version": "1", "digest": "sha256:3333333333333333333333333333333333333333333333333333333333333333" },
            "agentBaseSpec": { "path": "base.md", "version": "1", "digest": "sha256:4444444444444444444444444444444444444444444444444444444444444444" },
            "platformAgentContract": { "schemaVersion": "1.0.0", "schemaDigest": "sha256:5555555555555555555555555555555555555555555555555555555555555555" },
            "decisionSpaceSchema": { "schemaVersion": "1.0.0", "schemaDigest": "sha256:6666666666666666666666666666666666666666666666666666666666666666" },
            "decisionConsequenceMap": { "path": "dcm.md", "version": "1", "digest": "sha256:7777777777777777777777777777777777777777777777777777777777777777" },
            "evidenceFirstOperations": ["EXECUTE"],
            "emergencyStop": { "supported": true, "signal": "STOP", "maximumResponseSeconds": 1 },
            "constitutionalConformanceTests": ["CCT-EF-04"],
            "dataClasses": ["BUSINESS_DATA"],
            "retentionPolicy": { "schemaVersion": "1.0.0", "schemaDigest": "sha256:8888888888888888888888888888888888888888888888888888888888888888" },
            "securityPosture": { "schemaVersion": "1.0.0", "schemaDigest": "sha256:9999999999999999999999999999999999999999999999999999999999999999" },
            "limitationBehavior": "fail closed",
            "degradationBehavior": "pause"
          },
          "skillManifest": [{
            "skillId": "PRIMARY_SKILL",
            "skillVersion": "1.0.0",
            "capability": "Deliver a bounded business outcome",
            "businessKpi": "verified outcome rate",
            "inputs": ["brief"],
            "outputs": ["result"],
            "decisionSpaceSubset": ["propose"],
            "tools": [{ "toolId": "tool", "providerId": "provider", "defaultDenied": true, "governedAction": "USE_TOOL" }],
            "constitutionalActions": ["USE_TOOL"],
            "configurationSchema": { "schemaVersion": "1.0.0", "schemaDigest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" },
            "goalSchema": { "schemaVersion": "1.0.0", "schemaDigest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" },
            "schedulePolicy": { "mode": "EVENT_DRIVEN", "customerAdjustable": false, "governedEvents": ["CUSTOMER_REQUEST"] },
            "reviewPolicy": { "performanceReviewDays": 30, "customerContractReviewDays": 30 },
            "costUnits": { "execution": 1 },
            "trialBehavior": "bounded",
            "degradationBehavior": "pause",
            "compatibility": { "schemaVersion": "1.0.0", "schemaDigest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc" }
          }]
        }
        """);
}