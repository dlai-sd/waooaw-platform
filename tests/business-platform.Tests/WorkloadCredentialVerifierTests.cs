// Implements: ADR-046 sections 3, 4.2, 5.1 and 12.2 D4; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using FluentAssertions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WorkloadCredentialVerifierTests
{
    private static readonly WorkloadCredentialSettings Settings = new(
        "business-platform",
        TestPki.TrustDomain
    );

    public static TheoryData<string, string, Action<CredentialOptions, TestPki>> Rejections =>
        new()
        {
            { "trust schema", "SCHEMA", (o, _) => o.Trust = t => t["schema_version"] = "1.0" },
            { "bundle schema", "SCHEMA", (o, _) => o.Bundle = b => b["schema_version"] = "1.0" },
            { "missing tls key", "SCHEMA", (o, _) => o.Bundle = b => b.Remove("tls_key_pem") },
            { "string version", "SCHEMA", (o, _) => o.Bundle = b => b["bundle_version"] = "7" },
            {
                "trust string version",
                "SCHEMA",
                (o, _) => o.Trust = t => t["bundle_version"] = "x"
            },
            { "garbage leaf pem", "SCHEMA", (o, _) => o.Bundle = b => b["tls_cert_pem"] = "nope" },
            {
                "garbage tls key",
                "SCHEMA",
                (o, _) =>
                    o.Bundle = b =>
                        b["tls_key_pem"] =
                            "-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----\n"
            },
            {
                "no delegation",
                "SCHEMA",
                (o, _) => o.Bundle = b => b["delegation_cert_pem"] = null
            },
            {
                "own workload missing",
                "SCHEMA",
                (o, _) =>
                    o.Trust = t =>
                        t["manifest"]!["workloads"]!.AsObject().Remove("business-platform")
            },
            {
                "unrelated root",
                "TRUST_CHAIN",
                (o, foreign) => o.Trust = t => t["root_pem"] = foreign.Root.ExportCertificatePem()
            },
            {
                "signed by wrong key",
                "TRUST_SIGNATURE",
                (o, foreign) => o.TrustSigningKey = foreign.IntermediateKey
            },
            {
                "revocation list stripped after signing",
                "TRUST_SIGNATURE",
                (o, _) => o.TrustAfterSigning = t => t["revoked_serials"] = new JsonArray("1")
            },
            {
                "signature not base64",
                "TRUST_SIGNATURE",
                (o, _) => o.TrustAfterSigning = t => t["signature"] = "***"
            },
            {
                "bundle environment",
                "ENVIRONMENT",
                (o, _) => o.Bundle = b => b["environment"] = "prod"
            },
            {
                "manifest environment",
                "ENVIRONMENT",
                (o, _) => o.Trust = t => t["manifest"]!["environment"] = "prod"
            },
            { "trust domain", "TRUST_DOMAIN", (o, _) => o.TrustDomain = "other.test" },
            {
                "manifest trust domain",
                "TRUST_DOMAIN",
                (o, _) => o.Trust = t => t["manifest"]!["trust_domain"] = "other.test"
            },
            {
                "bundle identity",
                "LEAF_IDENTITY",
                (o, _) => o.Bundle = b => b["identity_uri"] = TestPki.Identity("billing-engine")
            },
            {
                "bundle workload",
                "LEAF_IDENTITY",
                (o, _) => o.Bundle = b => b["workload"] = "billing-engine"
            },
            {
                "identity outside trust domain",
                "LEAF_IDENTITY",
                (o, _) =>
                    o.Trust = t =>
                        t["manifest"]!["workloads"]!["business-platform"]!["identity_uri"] =
                            "spiffe://evil.test/workload/business-platform"
            },
            {
                "leaf san of another workload",
                "LEAF_IDENTITY",
                (o, _) => o.LeafSanUri = TestPki.Identity("billing-engine")
            },
            { "revoked serial", "REVOKED", (o, _) => o.RevokeLeafSerial = true },
            { "revoked identity", "REVOKED", (o, _) => o.RevokeIdentity = true },
            {
                "expired leaf",
                "LEAF_VALIDITY",
                (o, _) =>
                {
                    o.LeafNotBeforeOffset = TimeSpan.FromHours(-2);
                    o.LeafLifetime = TimeSpan.FromHours(1);
                }
            },
            {
                "future leaf",
                "LEAF_VALIDITY",
                (o, _) =>
                {
                    o.LeafNotBeforeOffset = TimeSpan.FromHours(1);
                    o.LeafLifetime = TimeSpan.FromHours(2);
                }
            },
            {
                "leaf over 24 hours",
                "LEAF_VALIDITY",
                (o, _) => o.LeafLifetime = TimeSpan.FromHours(25)
            },
            {
                "bundle not after elapsed",
                "LEAF_VALIDITY",
                (o, _) => o.BundleNotAfterOffset = TimeSpan.FromMinutes(-1)
            },
            { "leaf from another ca", "LEAF_CHAIN", (o, foreign) => o.LeafIssuer = foreign },
            { "server only leaf", "LEAF_USAGE", (o, _) => o.LeafUsages = [TestPki.ServerAuth] },
            { "tls key mismatch", "LEAF_KEY_MISMATCH", (o, _) => o.MismatchedTlsKey = true },
            {
                "expired delegation",
                "DELEGATION_VALIDITY",
                (o, _) =>
                {
                    o.DelegationNotBeforeOffset = TimeSpan.FromHours(-2);
                    o.DelegationLifetime = TimeSpan.FromHours(1);
                }
            },
            {
                "delegation from another ca",
                "DELEGATION_CHAIN",
                (o, foreign) => o.DelegationIssuer = foreign
            },
            {
                "delegation without signing usage",
                "DELEGATION_USAGE",
                (o, _) => o.DelegationUsages = [TestPki.ClientAuth]
            },
            {
                "delegation for another workload",
                "DELEGATION_IDENTITY",
                (o, _) => o.DelegationSanUri = TestPki.Identity("billing-engine")
            },
            {
                "delegation key mismatch",
                "DELEGATION_KEY_MISMATCH",
                (o, _) => o.MismatchedDelegationKey = true
            },
            {
                "delegation unpublished",
                "DELEGATION_NOT_PUBLISHED",
                (o, _) => o.PublishDelegation = false
            },
            {
                "delegation published under another key id",
                "DELEGATION_NOT_PUBLISHED",
                (o, _) =>
                    o.Trust = t =>
                        t["manifest"]!["workloads"]!["business-platform"]![
                            "delegation_certificates"
                        ]![0]!["key_id"] = "0000"
            },
            { "billing target missing", "TARGETS", (o, _) => o.Targets = ["professional-runtime"] },
            {
                "target outside trust domain",
                "TARGETS",
                (o, _) =>
                    o.Trust = t =>
                        t["manifest"]!["workloads"]!["billing-engine"]!["identity_uri"] =
                            "spiffe://evil.test/workload/billing-engine"
            },
        };

    [Fact]
    public void ValidBundleIsAcceptedWithExactIdentityTargetsAndKeys()
    {
        using var pki = new TestPki();
        var issued = pki.Create(new CredentialOptions { Version = 42 });

        var result = Verify(issued, pki.Now);

        result.Reason.Should().BeNull();
        using var snapshot = result.Snapshot!;
        snapshot.IssuerUri.Should().Be(TestPki.Identity("business-platform"));
        snapshot.BundleVersion.Should().Be(42);
        snapshot.TrustVersion.Should().Be(42);
        snapshot.NotAfter.Should().Be(new DateTimeOffset(issued.Leaf.NotAfter));
        snapshot.ClientCertificate.Thumbprint.Should().Be(issued.Leaf.Thumbprint);
        snapshot.ClientCertificate.HasPrivateKey.Should().BeTrue();
        snapshot
            .Targets.Keys.Should()
            .BeEquivalentTo("billing-engine", "professional-runtime", "domain-adapter");
        snapshot
            .Targets["billing-engine"]
            .IdentityUri.Should()
            .Be(TestPki.Identity("billing-engine"));
        snapshot
            .Targets["billing-engine"]
            .Audience.Should()
            .Be("urn:waooaw:service:billing-engine");
        snapshot
            .TrustAnchors.Select(anchor => anchor.Thumbprint)
            .Distinct()
            .Should()
            .ContainSingle();
        snapshot.SignerAt(pki.Now)!.KeyId.Should().Be(issued.DelegationKeyId);
    }

    [Fact]
    public void BundleWithOnlyRequiredTargetsAndMatchingEnvironmentIsAccepted()
    {
        using var pki = new TestPki();
        var issued = pki.Create(
            new CredentialOptions { Targets = ["billing-engine", "professional-runtime"] }
        );

        var result = WorkloadCredentialVerifier.Verify(
            issued.Bundle,
            issued.Trust,
            Settings with
            {
                Environment = TestPki.Environment,
            },
            0,
            0,
            null,
            pki.Now
        );

        result.Reason.Should().BeNull();
        result
            .Snapshot!.Targets.Keys.Should()
            .BeEquivalentTo("billing-engine", "professional-runtime");
        result.Snapshot.Dispose();
    }

    [Fact]
    public void DualTrustBundleKeepsThePreviousRootAsAnAdditionalAnchor()
    {
        using var pki = new TestPki();
        using var previous = new TestPki();
        var issued = pki.Create(
            new CredentialOptions
            {
                Trust = t =>
                    t["ca_bundle_pem"] =
                        pki.Root.ExportCertificatePem()
                        + "\n"
                        + pki.Intermediate.ExportCertificatePem()
                        + "\n"
                        + previous.Root.ExportCertificatePem()
                        + "\n",
            }
        );

        var result = Verify(issued, pki.Now);

        result.Reason.Should().BeNull();
        result
            .Snapshot!.TrustAnchors.Select(anchor => anchor.Thumbprint)
            .Distinct()
            .Should()
            .BeEquivalentTo(pki.Root.Thumbprint, previous.Root.Thumbprint);
        result.Snapshot.Dispose();
    }

    [Fact]
    public void RevokedPeerIdentityDoesNotRejectOwnBundleButIsCarriedForPeerValidation()
    {
        using var pki = new TestPki();
        var peer = TestPki.Identity("billing-engine");
        var issued = pki.Create(
            new CredentialOptions { Trust = t => t["revoked_identity_uris"] = new JsonArray(peer) }
        );

        var result = Verify(issued, pki.Now);

        result.Reason.Should().BeNull();
        result.Snapshot!.RevokedIdentityUris.Should().Contain(peer);
        result.Snapshot.Dispose();
    }

    [Fact]
    public void DelegationIsPublishedBeforeItActivatesAndTheSignerWaitsForTheActivationTime()
    {
        using var pki = new TestPki();
        var issued = pki.Create(
            new CredentialOptions { DelegationActivateIn = TimeSpan.FromMinutes(10) }
        );

        var result = Verify(issued, pki.Now);

        result.Reason.Should().BeNull();
        using var snapshot = result.Snapshot!;
        snapshot.SignerAt(pki.Now).Should().BeNull();
        snapshot.SignerAt(pki.Now.AddMinutes(9)).Should().BeNull();
        snapshot.SignerAt(pki.Now.AddMinutes(10))!.KeyId.Should().Be(issued.DelegationKeyId);
    }

    [Fact]
    public void PendingDelegationFallsBackToThePreviousSignerOnlyWhileItIsStillValid()
    {
        using var pki = new TestPki();
        var first = Verify(pki.Create(new CredentialOptions { Version = 1 }), pki.Now);
        var next = pki.Create(
            new CredentialOptions { Version = 2, DelegationActivateIn = TimeSpan.FromMinutes(10) }
        );

        var result = WorkloadCredentialVerifier.Verify(
            next.Bundle,
            next.Trust,
            Settings,
            1,
            1,
            first.Snapshot!.SignerAt(pki.Now),
            pki.Now
        );

        using var snapshot = result.Snapshot!;
        snapshot.SignerAt(pki.Now)!.KeyId.Should().Be(first.Snapshot.Pending.KeyId);
        snapshot.SignerAt(pki.Now.AddMinutes(10))!.KeyId.Should().Be(next.DelegationKeyId);
        snapshot.SignerAt(pki.Now.AddHours(25)).Should().BeNull();
    }

    [Theory]
    [MemberData(nameof(Rejections))]
    public void InvalidBundleIsRejectedWithItsReason(
        string scenario,
        string reason,
        Action<CredentialOptions, TestPki> configure
    )
    {
        using var pki = new TestPki();
        using var foreign = new TestPki();
        var options = new CredentialOptions();
        configure(options, foreign);
        var issued = pki.Create(options);

        var result = Verify(issued, pki.Now);

        result.Snapshot.Should().BeNull(scenario);
        result.Reason.Should().Be(reason, scenario);
    }

    [Theory]
    [InlineData("UNISSUED", "bundle")]
    [InlineData("UNISSUED", "trust")]
    [InlineData("", "bundle")]
    [InlineData("{not json", "trust")]
    public void UnissuedOrMalformedDocumentsMeanNoCredentialAndNeverThrow(
        string value,
        string which
    )
    {
        using var pki = new TestPki();
        var issued = pki.Create();
        var bundle = which == "bundle" ? value : issued.Bundle;
        var trust = which == "trust" ? value : issued.Trust;

        var result = WorkloadCredentialVerifier.Verify(
            bundle,
            trust,
            Settings,
            0,
            0,
            null,
            pki.Now
        );

        result.Snapshot.Should().BeNull();
        result.Reason.Should().Be("NO_CREDENTIAL");
    }

    [Theory]
    [InlineData("[]")]
    [InlineData("\"text\"")]
    [InlineData("null")]
    [InlineData("{}")]
    public void WellFormedJsonOfTheWrongShapeIsASchemaRejection(string value)
    {
        using var pki = new TestPki();
        var issued = pki.Create();

        var result = WorkloadCredentialVerifier.Verify(
            value,
            issued.Trust,
            Settings,
            0,
            0,
            null,
            pki.Now
        );

        result.Snapshot.Should().BeNull();
        result.Reason.Should().Be("SCHEMA");
    }

    [Fact]
    public void LowerTrustOrBundleVersionThanLastAcceptedIsARollback()
    {
        using var pki = new TestPki();
        var issued = pki.Create(new CredentialOptions { Version = 10 });

        WorkloadCredentialVerifier
            .Verify(issued.Bundle, issued.Trust, Settings, 11, 0, null, pki.Now)
            .Reason.Should()
            .Be("ROLLBACK");
        WorkloadCredentialVerifier
            .Verify(issued.Bundle, issued.Trust, Settings, 0, 11, null, pki.Now)
            .Reason.Should()
            .Be("ROLLBACK");
        var equal = WorkloadCredentialVerifier.Verify(
            issued.Bundle,
            issued.Trust,
            Settings,
            10,
            10,
            null,
            pki.Now
        );
        equal.Reason.Should().BeNull();
        equal.Snapshot!.Dispose();
    }

    [Fact]
    public void ExpectedEnvironmentOrTrustDomainOrWorkloadMismatchIsRejected()
    {
        using var pki = new TestPki();
        var issued = pki.Create();

        WorkloadCredentialVerifier
            .Verify(
                issued.Bundle,
                issued.Trust,
                Settings with
                {
                    Environment = "prod",
                },
                0,
                0,
                null,
                pki.Now
            )
            .Reason.Should()
            .Be("ENVIRONMENT");
        WorkloadCredentialVerifier
            .Verify(
                issued.Bundle,
                issued.Trust,
                Settings with
                {
                    TrustDomain = "other.test",
                },
                0,
                0,
                null,
                pki.Now
            )
            .Reason.Should()
            .Be("TRUST_DOMAIN");
        WorkloadCredentialVerifier
            .Verify(
                issued.Bundle,
                issued.Trust,
                Settings with
                {
                    Workload = "billing-engine",
                },
                0,
                0,
                null,
                pki.Now
            )
            .Reason.Should()
            .Be("LEAF_IDENTITY");
    }

    [Fact]
    public void ExpiredIntermediateBreaksTheTrustChain()
    {
        using var pki = new TestPki(intermediateLifetime: TimeSpan.FromDays(1));
        var issued = pki.Create();

        var result = Verify(issued, pki.Now.AddDays(2));

        result.Reason.Should().Be("TRUST_CHAIN");
    }

    [Fact]
    public void LeafPastItsNotAfterIsRejectedWhenVerifiedLater()
    {
        using var pki = new TestPki();
        var issued = pki.Create();

        Verify(issued, pki.Now.AddHours(24)).Reason.Should().Be("LEAF_VALIDITY");
    }

    [Fact]
    public void CanonicalJsonMatchesPythonSortKeysCompactEnsureAsciiAndDropsTheSignature()
    {
        using var document = JsonDocument.Parse(
            "{\"b\":[1,true,null,\"x\"],\"a\":{\"z\":\"caf\\u00e9 \\u007f \\\"q\\\" \\\\ \\n\\t\\r\\b\\f \\u0001 \\ud83d\\ude00 +/=\",\"k\":-5},\"signature\":\"drop\"}"
        );

        var canonical = WorkloadCredentialVerifier.Canonical(
            document.RootElement,
            dropSignature: true
        );

        canonical
            .Should()
            .Be(
                "{\"a\":{\"k\":-5,\"z\":\"caf\\u00e9 \\u007f \\\"q\\\" \\\\ \\n\\t\\r\\b\\f \\u0001 \\ud83d\\ude00 +/=\"},\"b\":[1,true,null,\"x\"]}"
            );
    }

    [Fact]
    public void DecimalSerialMatchesTheUnsignedBigEndianInteger()
    {
        using var pki = new TestPki();
        var issued = pki.Create();

        WorkloadCredentialVerifier
            .DecimalSerial(issued.Leaf)
            .Should()
            .Be(TestPki.DecimalSerial(issued.Leaf));
        TestPki.DecimalSerial(issued.Leaf).Should().MatchRegex("^[1-9][0-9]+$");
    }

    [Fact]
    public async Task BundlesPublishedByThePythonIssuerLibraryAreAcceptedAndRenewalsAreMonotonic()
    {
        var now = DateTimeOffset.FromUnixTimeSeconds(1_800_000_000);
        var fixture = await PythonIssuerFixture.CreateAsync(now);
        var settings = new WorkloadCredentialSettings("business-platform", fixture.TrustDomain);

        var pending = WorkloadCredentialVerifier.Verify(
            fixture.Bundle,
            fixture.Trust,
            settings,
            0,
            0,
            null,
            now.AddMinutes(1)
        );
        var active = WorkloadCredentialVerifier.Verify(
            fixture.Bundle,
            fixture.Trust,
            settings,
            0,
            0,
            null,
            now.AddMinutes(11)
        );
        var renewed = WorkloadCredentialVerifier.Verify(
            fixture.RenewedBundle,
            fixture.RenewedTrust,
            settings,
            active.Snapshot!.TrustVersion,
            active.Snapshot.BundleVersion,
            active.Snapshot.SignerAt(now.AddHours(9)),
            now.AddHours(9).AddMinutes(1)
        );
        var stale = WorkloadCredentialVerifier.Verify(
            fixture.Bundle,
            fixture.Trust,
            settings,
            renewed.Snapshot!.TrustVersion,
            renewed.Snapshot.BundleVersion,
            null,
            now.AddHours(9).AddMinutes(1)
        );

        pending.Reason.Should().BeNull();
        pending.Snapshot!.SignerAt(now.AddMinutes(1)).Should().BeNull();
        active.Reason.Should().BeNull();
        active.Snapshot!.SignerAt(now.AddMinutes(11)).Should().NotBeNull();
        active
            .Snapshot.IssuerUri.Should()
            .Be($"spiffe://{fixture.TrustDomain}/workload/business-platform");
        active.Snapshot.Targets.Keys.Should().Contain(["billing-engine", "professional-runtime"]);
        renewed.Reason.Should().BeNull();
        renewed.Snapshot!.BundleVersion.Should().BeGreaterThan(active.Snapshot.BundleVersion);
        renewed.Snapshot.TrustVersion.Should().BeGreaterThan(active.Snapshot.TrustVersion);
        renewed
            .Snapshot.SignerAt(now.AddHours(9).AddMinutes(1))!
            .KeyId.Should()
            .Be(active.Snapshot.Pending.KeyId);
        stale.Reason.Should().Be("ROLLBACK");
    }

    private static WorkloadCredentialVerification Verify(
        IssuedCredentials issued,
        DateTimeOffset now
    ) => WorkloadCredentialVerifier.Verify(issued.Bundle, issued.Trust, Settings, 0, 0, null, now);
}

internal sealed record PythonIssuerFixture(
    string Trust,
    string Bundle,
    string RenewedTrust,
    string RenewedBundle,
    string TrustDomain
)
{
    private const string Script = """
        import json, sys
        sys.path.insert(0, "scripts")
        from datetime import datetime, timezone, timedelta
        from pathlib import Path
        import workload_identity_issuance as issuance
        now = datetime.fromtimestamp(int(sys.argv[1]), timezone.utc)
        first = issuance.build_cloud_fixture(Path("infrastructure/workload-identity/registry.yaml"), "demo", None, now)
        out = {"trust": first["wid-trust-bundle"], "bundle": first["wid-bundle-business-platform"]}
        later = issuance.renew_cloud_fixture(first, now + timedelta(hours=9))
        out["renewed_trust"] = later["wid-trust-bundle"]
        out["renewed_bundle"] = later["wid-bundle-business-platform"]
        print(json.dumps(out))
        """;

    public static async Task<PythonIssuerFixture> CreateAsync(DateTimeOffset now)
    {
        var info = new ProcessStartInfo
        {
            FileName = "python3",
            WorkingDirectory = RepositoryPaths.Root(),
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        info.ArgumentList.Add("-c");
        info.ArgumentList.Add(Script);
        info.ArgumentList.Add(now.ToUnixTimeSeconds().ToString());
        using var process =
            Process.Start(info) ?? throw new InvalidOperationException("Could not start python3");
        var output = process.StandardOutput.ReadToEndAsync();
        var error = process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        if (process.ExitCode != 0)
            throw new InvalidOperationException(await error);
        using var document = JsonDocument.Parse(await output);
        var root = document.RootElement;
        var trust = root.GetProperty("trust").GetString()!;
        using var trustDocument = JsonDocument.Parse(trust);
        return new PythonIssuerFixture(
            trust,
            root.GetProperty("bundle").GetString()!,
            root.GetProperty("renewed_trust").GetString()!,
            root.GetProperty("renewed_bundle").GetString()!,
            trustDocument.RootElement.GetProperty("trust_domain").GetString()!
        );
    }
}
