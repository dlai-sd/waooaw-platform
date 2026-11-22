// Implements: ADR-046 sections 4.2, 5.1 and 12.2 D4; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json.Nodes;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class TestClock(DateTimeOffset now) : TimeProvider
{
    private DateTimeOffset _now = now;

    public override DateTimeOffset GetUtcNow() => _now;

    public void Advance(TimeSpan by) => _now += by;
}

public sealed class CredentialOptions
{
    public long Version { get; set; } = 1_000;
    public string Environment { get; set; } = TestPki.Environment;
    public string TrustDomain { get; set; } = TestPki.TrustDomain;
    public TimeSpan LeafNotBeforeOffset { get; set; } = TimeSpan.FromSeconds(-60);
    public TimeSpan LeafLifetime { get; set; } = TimeSpan.FromHours(24);
    public string[] LeafUsages { get; set; } = [TestPki.ClientAuth, TestPki.ServerAuth];
    public string? LeafSanUri { get; set; }
    public TestPki? LeafIssuer { get; set; }
    public bool MismatchedTlsKey { get; set; }
    public TimeSpan DelegationActivateIn { get; set; } = TimeSpan.FromMinutes(-1);
    public TimeSpan DelegationNotBeforeOffset { get; set; } = TimeSpan.FromSeconds(-60);
    public TimeSpan DelegationLifetime { get; set; } = TimeSpan.FromHours(24);
    public string[] DelegationUsages { get; set; } = [TestPki.DelegationSigning];
    public string? DelegationSanUri { get; set; }
    public TestPki? DelegationIssuer { get; set; }
    public bool MismatchedDelegationKey { get; set; }
    public bool PublishDelegation { get; set; } = true;
    public bool RevokeLeafSerial { get; set; }
    public bool RevokeIdentity { get; set; }
    public string[] Targets { get; set; } =
    ["billing-engine", "professional-runtime", "domain-adapter"];
    public TimeSpan? BundleNotAfterOffset { get; set; }
    public Action<JsonObject>? Trust { get; set; }
    public Action<JsonObject>? Bundle { get; set; }
    public Action<JsonObject>? TrustAfterSigning { get; set; }
    public ECDsa? TrustSigningKey { get; set; }
}

public sealed record IssuedCredentials(
    string Bundle,
    string Trust,
    X509Certificate2 Leaf,
    X509Certificate2 Delegation,
    string DelegationKeyId,
    ECDsa DelegationKey,
    string TlsKeyPem
);

/// <summary>An in-test root and intermediate that publish the documents in the schema of scripts/workload_identity_issuance.py.</summary>
public sealed class TestPki : IDisposable
{
    public const string Environment = "demo";
    public const string TrustDomain = "waooaw.test";
    public const string ClientAuth = "1.3.6.1.5.5.7.3.2";
    public const string ServerAuth = "1.3.6.1.5.5.7.3.1";
    public const string DelegationSigning = "1.3.6.1.4.1.55555.46.1";

    public DateTimeOffset Now { get; }
    public ECDsa RootKey { get; } = ECDsa.Create(ECCurve.NamedCurves.nistP256);
    public ECDsa IntermediateKey { get; } = ECDsa.Create(ECCurve.NamedCurves.nistP256);
    public X509Certificate2 Root { get; }
    public X509Certificate2 Intermediate { get; }

    public TestPki(DateTimeOffset? now = null, TimeSpan? intermediateLifetime = null)
    {
        Now = now ?? DateTimeOffset.FromUnixTimeSeconds(DateTimeOffset.UtcNow.ToUnixTimeSeconds());
        var suffix = Guid.NewGuid().ToString("N")[..8];
        var rootRequest = new CertificateRequest(
            $"CN=WAOOAW test root {suffix}",
            RootKey,
            HashAlgorithmName.SHA256
        );
        rootRequest.CertificateExtensions.Add(
            new X509BasicConstraintsExtension(true, true, 1, true)
        );
        rootRequest.CertificateExtensions.Add(
            new X509KeyUsageExtension(
                X509KeyUsageFlags.KeyCertSign | X509KeyUsageFlags.CrlSign,
                true
            )
        );
        Root = rootRequest.CreateSelfSigned(Now.AddDays(-1), Now.AddDays(365));
        var intermediateRequest = new CertificateRequest(
            $"CN=WAOOAW test intermediate {suffix}",
            IntermediateKey,
            HashAlgorithmName.SHA256
        );
        intermediateRequest.CertificateExtensions.Add(
            new X509BasicConstraintsExtension(true, true, 0, true)
        );
        intermediateRequest.CertificateExtensions.Add(
            new X509KeyUsageExtension(
                X509KeyUsageFlags.KeyCertSign | X509KeyUsageFlags.CrlSign,
                true
            )
        );
        Intermediate = intermediateRequest.Create(
            Root.SubjectName,
            X509SignatureGenerator.CreateForECDsa(RootKey),
            Now.AddDays(-1),
            Now.Add(intermediateLifetime ?? TimeSpan.FromDays(90)),
            RandomSerial()
        );
    }

    public X509Certificate2 Issue(
        ECDsa subjectKey,
        string identityUri,
        DateTimeOffset notBefore,
        TimeSpan lifetime,
        params string[] usages
    )
    {
        var request = new CertificateRequest(
            $"CN={identityUri[(identityUri.LastIndexOf('/') + 1)..]}",
            subjectKey,
            HashAlgorithmName.SHA256
        );
        request.CertificateExtensions.Add(new X509BasicConstraintsExtension(false, false, 0, true));
        request.CertificateExtensions.Add(
            new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature, true)
        );
        var san = new SubjectAlternativeNameBuilder();
        san.AddUri(new Uri(identityUri));
        request.CertificateExtensions.Add(san.Build());
        var oids = new OidCollection();
        foreach (var usage in usages)
            oids.Add(new Oid(usage));
        request.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(oids, false));
        return request.Create(
            Intermediate.SubjectName,
            X509SignatureGenerator.CreateForECDsa(IntermediateKey),
            notBefore,
            notBefore + lifetime,
            RandomSerial()
        );
    }

    public static string Identity(string workload) => $"spiffe://{TrustDomain}/workload/{workload}";

    public IssuedCredentials Create(CredentialOptions? options = null)
    {
        options ??= new CredentialOptions();
        var identity = Identity("business-platform");
        using var tlsKey = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var leafIssuer = options.LeafIssuer ?? this;
        var leaf = leafIssuer.Issue(
            tlsKey,
            options.LeafSanUri ?? identity,
            Now + options.LeafNotBeforeOffset,
            options.LeafLifetime,
            options.LeafUsages
        );
        var delegationKey = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var delegation = (options.DelegationIssuer ?? this).Issue(
            delegationKey,
            options.DelegationSanUri ?? identity,
            Now + options.DelegationNotBeforeOffset,
            options.DelegationLifetime,
            options.DelegationUsages
        );
        var delegationKeyId = KeyId(delegationKey);
        var activateAfter = Now + options.DelegationActivateIn;
        var serial = DecimalSerial(leaf);

        var workloads = new JsonObject
        {
            ["business-platform"] = new JsonObject
            {
                ["identity_uri"] = identity,
                ["audience"] = "urn:waooaw:service:business-platform",
                ["tls_certificate_sha256"] = Convert
                    .ToHexString(SHA256.HashData(leaf.RawData))
                    .ToLowerInvariant(),
                ["tls_serial"] = serial,
                ["not_before"] = Iso(leaf.NotBefore),
                ["not_after"] = Iso(leaf.NotAfter),
                ["delegation_certificates"] = options.PublishDelegation
                    ? new JsonArray
                    {
                        new JsonObject
                        {
                            ["key_id"] = delegationKeyId,
                            ["certificate_pem"] = delegation.ExportCertificatePem(),
                            ["not_before"] = Iso(delegation.NotBefore),
                            ["not_after"] = Iso(delegation.NotAfter),
                            ["activate_after"] = Iso(activateAfter),
                        },
                    }
                    : new JsonArray(),
                ["delegation_key_id"] = delegationKeyId,
            },
        };
        foreach (var target in options.Targets)
            workloads[target] = new JsonObject
            {
                ["identity_uri"] = Identity(target),
                ["audience"] = $"urn:waooaw:service:{target}",
                ["delegation_certificates"] = new JsonArray(),
                ["delegation_key_id"] = null,
            };

        var intermediatePem = Intermediate.ExportCertificatePem();
        var trust = new JsonObject
        {
            ["schema_version"] = "1.1",
            ["bundle_version"] = options.Version,
            ["environment"] = options.Environment,
            ["trust_domain"] = options.TrustDomain,
            ["generated_at"] = Iso(Now),
            ["root_pem"] = Root.ExportCertificatePem(),
            ["intermediate_pem"] = intermediatePem,
            ["ca_bundle_pem"] = Root.ExportCertificatePem() + "\n" + intermediatePem + "\n",
            ["revoked_serials"] = new JsonArray(),
            ["revoked_identity_uris"] = new JsonArray(),
            ["manifest"] = new JsonObject
            {
                ["schema_version"] = "1.0",
                ["policy_version"] = "1.1",
                ["environment"] = options.Environment,
                ["trust_domain"] = options.TrustDomain,
                ["workloads"] = workloads,
                ["route_grants"] = new JsonArray(),
            },
        };
        if (options.RevokeLeafSerial)
            trust["revoked_serials"] = new JsonArray(serial);
        if (options.RevokeIdentity)
            trust["revoked_identity_uris"] = new JsonArray(identity);
        options.Trust?.Invoke(trust);
        trust["signature"] = Convert.ToBase64String(
            (options.TrustSigningKey ?? IntermediateKey).SignData(
                Encoding.ASCII.GetBytes(Canonical(trust)),
                HashAlgorithmName.SHA256,
                DSASignatureFormat.Rfc3279DerSequence
            )
        );
        options.TrustAfterSigning?.Invoke(trust);

        var tlsKeyPem = (
            options.MismatchedTlsKey ? ECDsa.Create(ECCurve.NamedCurves.nistP256) : tlsKey
        ).ExportPkcs8PrivateKeyPem();
        var delegationKeyPem = (
            options.MismatchedDelegationKey
                ? ECDsa.Create(ECCurve.NamedCurves.nistP256)
                : delegationKey
        ).ExportPkcs8PrivateKeyPem();
        var bundle = new JsonObject
        {
            ["schema_version"] = "1.1",
            ["bundle_version"] = options.Version,
            ["environment"] = options.Environment,
            ["workload"] = "business-platform",
            ["identity_uri"] = identity,
            ["generated_at"] = Iso(Now),
            ["not_after"] = Iso(
                options.BundleNotAfterOffset is { } offset ? Now + offset : leaf.NotAfter
            ),
            ["tls_key_pem"] = tlsKeyPem,
            ["tls_cert_pem"] = leaf.ExportCertificatePem() + "\n" + intermediatePem + "\n",
            ["delegation_key_pem"] = delegationKeyPem,
            ["delegation_cert_pem"] = delegation.ExportCertificatePem(),
            ["delegation_key_id"] = delegationKeyId,
            ["delegation_activate_after"] = Iso(activateAfter),
        };
        options.Bundle?.Invoke(bundle);
        return new IssuedCredentials(
            bundle.ToJsonString(),
            trust.ToJsonString(),
            leaf,
            delegation,
            delegationKeyId,
            delegationKey,
            tlsKeyPem
        );
    }

    public static string KeyId(ECDsa key) =>
        Convert.ToHexString(SHA256.HashData(key.ExportSubjectPublicKeyInfo())).ToLowerInvariant()[
            ..32
        ];

    public static string DecimalSerial(X509Certificate2 certificate) =>
        new BigInteger(
            Convert.FromHexString(certificate.SerialNumber),
            isUnsigned: true,
            isBigEndian: true
        ).ToString(CultureInfo.InvariantCulture);

    public static string Iso(DateTimeOffset value) =>
        value
            .ToUniversalTime()
            .ToString("yyyy-MM-dd'T'HH:mm:ss'+00:00'", CultureInfo.InvariantCulture);

    /// <summary>Canonical JSON as Python's sort_keys, no whitespace, ensure_ascii; the signature member is excluded.</summary>
    public static string Canonical(JsonNode? node) =>
        node switch
        {
            null => "null",
            JsonObject document => "{"
                + string.Join(
                    ",",
                    document
                        .Where(property => property.Key != "signature")
                        .OrderBy(property => property.Key, StringComparer.Ordinal)
                        .Select(property => Quote(property.Key) + ":" + Canonical(property.Value))
                )
                + "}",
            JsonArray array => "[" + string.Join(",", array.Select(Canonical)) + "]",
            JsonValue value when value.TryGetValue<string>(out var text) => Quote(text),
            JsonValue value when value.TryGetValue<bool>(out var flag) => flag ? "true" : "false",
            _ => node.ToJsonString(),
        };

    private static string Quote(string value)
    {
        var builder = new StringBuilder("\"");
        foreach (var character in value)
            builder.Append(
                character switch
                {
                    '"' => "\\\"",
                    '\\' => "\\\\",
                    '\n' => "\\n",
                    '\r' => "\\r",
                    '\t' => "\\t",
                    '\b' => "\\b",
                    '\f' => "\\f",
                    < ' ' or > '~' => $"\\u{(int)character:x4}",
                    _ => character.ToString(),
                }
            );
        return builder.Append('"').ToString();
    }

    private static byte[] RandomSerial()
    {
        var serial = RandomNumberGenerator.GetBytes(16);
        serial[0] &= 0x7f;
        serial[0] |= 0x40;
        return serial;
    }

    public void Dispose()
    {
        RootKey.Dispose();
        IntermediateKey.Dispose();
        Root.Dispose();
        Intermediate.Dispose();
    }
}
