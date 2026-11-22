// Implements: ADR-046 sections 3, 4.2, 5.1, 5.2 and 12.2 D4; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WorkloadCredentialsUnavailableException(
    string message = "SERVICE_IDENTITY_UNAVAILABLE"
) : HttpRequestException(message);

internal sealed record WorkloadTarget(string IdentityUri, string Audience);

internal sealed record DelegationSigner(
    ECDsa Key,
    string KeyId,
    DateTimeOffset ActivateAfter,
    DateTimeOffset NotAfter
);

internal sealed class WorkloadCredentialSnapshot : IDisposable
{
    public required X509Certificate2 ClientCertificate { get; init; }
    public System.Net.Security.SslStreamCertificateContext? Context { get; init; }
    public required X509Certificate2Collection TrustAnchors { get; init; }
    public required X509Certificate2Collection Intermediates { get; init; }
    public required string IssuerUri { get; init; }
    public required DelegationSigner Pending { get; init; }
    public DelegationSigner? Fallback { get; init; }
    public required IReadOnlyDictionary<string, WorkloadTarget> Targets { get; init; }
    public DateTimeOffset? NotAfter { get; init; }
    public long BundleVersion { get; init; }
    public long TrustVersion { get; init; }
    public IReadOnlySet<string> RevokedSerials { get; init; } = new HashSet<string>();
    public IReadOnlySet<string> RevokedIdentityUris { get; init; } = new HashSet<string>();

    public bool IsLiveAt(DateTimeOffset now) => NotAfter is null || now < NotAfter;

    public DelegationSigner? SignerAt(DateTimeOffset now)
    {
        if (Pending.ActivateAfter <= now && now < Pending.NotAfter)
            return Pending;
        return Fallback is { } previous && now < previous.NotAfter ? previous : null;
    }

    public void Dispose()
    {
        ClientCertificate.Dispose();
        Pending.Key.Dispose();
    }
}

public sealed record WorkloadCredentialSettings(
    string Workload,
    string TrustDomain,
    string? Environment = null
);

internal sealed record WorkloadCredentialVerification(
    WorkloadCredentialSnapshot? Snapshot,
    string? Reason
);

internal sealed class WorkloadCredentialRejectedException(string reason) : Exception(reason)
{
    public string Reason { get; } = reason;
}

internal static class WorkloadCredentialVerifier
{
    public const string DelegationSigningOid = "1.3.6.1.4.1.55555.46.1";
    public const string ClientAuthOid = "1.3.6.1.5.5.7.3.2";
    public static readonly TimeSpan MaximumLeafLifetime = TimeSpan.FromHours(24);
    public static readonly string[] RequiredTargets = ["billing-engine", "professional-runtime"];
    public static readonly string[] OptionalTargets = ["domain-adapter", "domain-adapter-dma"];

    public static WorkloadCredentialVerification Verify(
        string bundleJson,
        string trustJson,
        WorkloadCredentialSettings settings,
        long lastTrustVersion,
        long lastBundleVersion,
        DelegationSigner? previousSigner,
        DateTimeOffset now
    )
    {
        try
        {
            return new WorkloadCredentialVerification(
                Build(
                    bundleJson,
                    trustJson,
                    settings,
                    lastTrustVersion,
                    lastBundleVersion,
                    previousSigner,
                    now
                ),
                null
            );
        }
        catch (WorkloadCredentialRejectedException rejected)
        {
            return new WorkloadCredentialVerification(null, rejected.Reason);
        }
        catch (Exception exception)
            when (exception
                    is JsonException
                        or InvalidOperationException
                        or CryptographicException
                        or FormatException
                        or ArgumentException
                        or KeyNotFoundException
                        or OverflowException
            )
        {
            return new WorkloadCredentialVerification(null, "SCHEMA");
        }
    }

    private static WorkloadCredentialSnapshot Build(
        string bundleJson,
        string trustJson,
        WorkloadCredentialSettings settings,
        long lastTrustVersion,
        long lastBundleVersion,
        DelegationSigner? previousSigner,
        DateTimeOffset now
    )
    {
        using var bundleDocument = Parse(bundleJson);
        using var trustDocument = Parse(trustJson);
        var bundle = bundleDocument.RootElement;
        var trust = trustDocument.RootElement;
        if (bundle.ValueKind != JsonValueKind.Object || trust.ValueKind != JsonValueKind.Object)
            throw Reject("SCHEMA");
        Require(Text(bundle, "schema_version") == "1.1", "SCHEMA");
        Require(Text(trust, "schema_version") == "1.1", "SCHEMA");

        var root = X509Certificate2.CreateFromPem(Text(trust, "root_pem"));
        var intermediate = X509Certificate2.CreateFromPem(Text(trust, "intermediate_pem"));
        var anchors = new X509Certificate2Collection { root };
        var intermediates = new X509Certificate2Collection { intermediate };
        if (
            trust.TryGetProperty("ca_bundle_pem", out var caBundle)
            && caBundle.ValueKind == JsonValueKind.String
        )
        {
            var extra = new X509Certificate2Collection();
            extra.ImportFromPem(caBundle.GetString()!);
            foreach (var certificate in extra)
            {
                if (
                    certificate
                        .SubjectName.RawData.AsSpan()
                        .SequenceEqual(certificate.IssuerName.RawData)
                )
                    anchors.Add(certificate);
                else
                    intermediates.Add(certificate);
            }
        }
        if (!ChainsTo(intermediate, new X509Certificate2Collection { root }, [], now))
            throw Reject("TRUST_CHAIN");
        VerifySignature(trust, intermediate);

        var trustVersion = Integer(trust, "bundle_version");
        var bundleVersion = Integer(bundle, "bundle_version");
        Require(trustVersion >= lastTrustVersion && bundleVersion >= lastBundleVersion, "ROLLBACK");
        var environment = Text(trust, "environment");
        Require(
            environment == Text(bundle, "environment")
                && (settings.Environment is null || settings.Environment == environment),
            "ENVIRONMENT"
        );
        var manifest = trust.GetProperty("manifest");
        Require(Text(manifest, "environment") == environment, "ENVIRONMENT");
        Require(
            Text(trust, "trust_domain") == settings.TrustDomain
                && Text(manifest, "trust_domain") == settings.TrustDomain,
            "TRUST_DOMAIN"
        );
        var prefix = $"spiffe://{settings.TrustDomain}/workload/";
        var workloads = manifest.GetProperty("workloads");
        var own = workloads.GetProperty(settings.Workload);
        var identityUri = Text(own, "identity_uri");
        Require(
            identityUri.StartsWith(prefix, StringComparison.Ordinal)
                && identityUri == Text(bundle, "identity_uri")
                && Text(bundle, "workload") == settings.Workload,
            "LEAF_IDENTITY"
        );

        var revokedSerials = Strings(trust, "revoked_serials");
        var revokedUris = Strings(trust, "revoked_identity_uris");
        var leafChain = new X509Certificate2Collection();
        leafChain.ImportFromPem(Text(bundle, "tls_cert_pem"));
        Require(leafChain.Count > 0, "SCHEMA");
        var leaf = leafChain[0];
        foreach (var certificate in leafChain.Skip(1))
            intermediates.Add(certificate);
        if (revokedSerials.Contains(DecimalSerial(leaf)) || revokedUris.Contains(identityUri))
            throw Reject("REVOKED");
        Require(
            now >= leaf.NotBefore
                && now < leaf.NotAfter
                && leaf.NotAfter - leaf.NotBefore <= MaximumLeafLifetime,
            "LEAF_VALIDITY"
        );
        Require(ChainsTo(leaf, anchors, intermediates, now), "LEAF_CHAIN");
        Require(
            Waooaw.WorkloadIdentity.InferenceWorkloadValidator.HasExactUriSan(leaf, identityUri),
            "LEAF_IDENTITY"
        );
        Require(HasUsage(leaf, ClientAuthOid), "LEAF_USAGE");
        using var tlsKey = ECDsa.Create();
        tlsKey.ImportFromPem(Text(bundle, "tls_key_pem"));
        Require(SamePublicKey(leaf, tlsKey), "LEAF_KEY_MISMATCH");
        var clientCertificate = leaf.CopyWithPrivateKey(tlsKey);

        var delegationCertificate = X509Certificate2.CreateFromPem(
            Text(bundle, "delegation_cert_pem")
        );
        var delegationKeyId = Text(bundle, "delegation_key_id");
        var activateAfter = Time(Text(bundle, "delegation_activate_after"));
        Require(
            now >= delegationCertificate.NotBefore && now < delegationCertificate.NotAfter,
            "DELEGATION_VALIDITY"
        );
        Require(ChainsTo(delegationCertificate, anchors, intermediates, now), "DELEGATION_CHAIN");
        Require(HasUsage(delegationCertificate, DelegationSigningOid), "DELEGATION_USAGE");
        Require(
            Waooaw.WorkloadIdentity.InferenceWorkloadValidator.HasExactUriSan(
                delegationCertificate,
                identityUri
            ),
            "DELEGATION_IDENTITY"
        );
        var delegationKey = ECDsa.Create();
        try
        {
            delegationKey.ImportFromPem(Text(bundle, "delegation_key_pem"));
            Require(SamePublicKey(delegationCertificate, delegationKey), "DELEGATION_KEY_MISMATCH");
            Require(
                IsPublished(own, delegationKeyId, delegationCertificate),
                "DELEGATION_NOT_PUBLISHED"
            );
            var targets = new Dictionary<string, WorkloadTarget>(StringComparer.Ordinal);
            foreach (var name in RequiredTargets.Concat(OptionalTargets))
            {
                if (!workloads.TryGetProperty(name, out var target))
                {
                    Require(!RequiredTargets.Contains(name), "TARGETS");
                    continue;
                }
                var targetUri = Text(target, "identity_uri");
                Require(targetUri.StartsWith(prefix, StringComparison.Ordinal), "TARGETS");
                targets[name] = new WorkloadTarget(targetUri, Text(target, "audience"));
            }
            var notAfter = new[] { leaf.NotAfter, Time(Text(bundle, "not_after")) }.Min();
            Require(now < notAfter, "LEAF_VALIDITY");
            var pending = new DelegationSigner(
                delegationKey,
                delegationKeyId,
                activateAfter,
                delegationCertificate.NotAfter
            );
            var context = System.Net.Security.SslStreamCertificateContext.Create(
                clientCertificate,
                intermediates,
                offline: true
            );
            return new WorkloadCredentialSnapshot
            {
                ClientCertificate = clientCertificate,
                Context = context,
                TrustAnchors = anchors,
                Intermediates = intermediates,
                IssuerUri = identityUri,
                Pending = pending,
                Fallback = pending.ActivateAfter > now ? previousSigner : null,
                Targets = targets,
                NotAfter = notAfter,
                BundleVersion = bundleVersion,
                TrustVersion = trustVersion,
                RevokedSerials = revokedSerials,
                RevokedIdentityUris = revokedUris,
            };
        }
        catch
        {
            delegationKey.Dispose();
            throw;
        }
    }

    public static bool ChainsTo(
        X509Certificate2 certificate,
        X509Certificate2Collection anchors,
        X509Certificate2Collection intermediates,
        DateTimeOffset now
    )
    {
        using var chain = new X509Chain();
        chain.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
        chain.ChainPolicy.CustomTrustStore.AddRange(anchors);
        chain.ChainPolicy.ExtraStore.AddRange(intermediates);
        chain.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
        chain.ChainPolicy.VerificationTime = now.UtcDateTime;
        return chain.Build(certificate);
    }

    public static string DecimalSerial(X509Certificate2 certificate) =>
        new BigInteger(
            Convert.FromHexString(certificate.SerialNumber),
            isUnsigned: true,
            isBigEndian: true
        ).ToString(CultureInfo.InvariantCulture);

    private static JsonDocument Parse(string value)
    {
        try
        {
            return JsonDocument.Parse(value);
        }
        catch (JsonException)
        {
            throw Reject("NO_CREDENTIAL");
        }
    }

    private static void VerifySignature(JsonElement trust, X509Certificate2 intermediate)
    {
        byte[] signature;
        try
        {
            signature = Convert.FromBase64String(Text(trust, "signature"));
        }
        catch (FormatException)
        {
            throw Reject("TRUST_SIGNATURE");
        }
        using var key = intermediate.GetECDsaPublicKey() ?? throw Reject("TRUST_SIGNATURE");
        var canonical = Encoding.ASCII.GetBytes(Canonical(trust, true));
        if (
            !key.VerifyData(
                canonical,
                signature,
                HashAlgorithmName.SHA256,
                DSASignatureFormat.Rfc3279DerSequence
            )
        )
            throw Reject("TRUST_SIGNATURE");
    }

    internal static string Canonical(JsonElement element, bool dropSignature = false)
    {
        var builder = new StringBuilder();
        Write(builder, element, dropSignature);
        return builder.ToString();
    }

    private static void Write(StringBuilder builder, JsonElement element, bool dropSignature)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                builder.Append('{');
                var first = true;
                foreach (
                    var property in element
                        .EnumerateObject()
                        .Where(property => !(dropSignature && property.Name == "signature"))
                        .OrderBy(property => property.Name, StringComparer.Ordinal)
                )
                {
                    if (!first)
                        builder.Append(',');
                    first = false;
                    WriteString(builder, property.Name);
                    builder.Append(':');
                    Write(builder, property.Value, false);
                }
                builder.Append('}');
                break;
            case JsonValueKind.Array:
                builder.Append('[');
                var index = 0;
                foreach (var item in element.EnumerateArray())
                {
                    if (index++ > 0)
                        builder.Append(',');
                    Write(builder, item, false);
                }
                builder.Append(']');
                break;
            case JsonValueKind.String:
                WriteString(builder, element.GetString()!);
                break;
            case JsonValueKind.Number:
                builder.Append(element.GetRawText());
                break;
            case JsonValueKind.True:
                builder.Append("true");
                break;
            case JsonValueKind.False:
                builder.Append("false");
                break;
            default:
                builder.Append("null");
                break;
        }
    }

    private static void WriteString(StringBuilder builder, string value)
    {
        builder.Append('"');
        foreach (var character in value)
        {
            switch (character)
            {
                case '"':
                    builder.Append("\\\"");
                    break;
                case '\\':
                    builder.Append("\\\\");
                    break;
                case '\n':
                    builder.Append("\\n");
                    break;
                case '\r':
                    builder.Append("\\r");
                    break;
                case '\t':
                    builder.Append("\\t");
                    break;
                case '\b':
                    builder.Append("\\b");
                    break;
                case '\f':
                    builder.Append("\\f");
                    break;
                default:
                    if (character < 0x20 || character > 0x7e)
                        builder
                            .Append("\\u")
                            .Append(((int)character).ToString("x4", CultureInfo.InvariantCulture));
                    else
                        builder.Append(character);
                    break;
            }
        }
        builder.Append('"');
    }

    private static bool IsPublished(JsonElement own, string keyId, X509Certificate2 certificate)
    {
        if (
            !own.TryGetProperty("delegation_certificates", out var published)
            || published.ValueKind != JsonValueKind.Array
        )
            return false;
        foreach (var entry in published.EnumerateArray())
        {
            if (Text(entry, "key_id") != keyId)
                continue;
            using var listed = X509Certificate2.CreateFromPem(Text(entry, "certificate_pem"));
            if (listed.RawData.AsSpan().SequenceEqual(certificate.RawData))
                return true;
        }
        return false;
    }

    private static bool HasUsage(X509Certificate2 certificate, string oid) =>
        certificate
            .Extensions.OfType<X509EnhancedKeyUsageExtension>()
            .Any(extension =>
                extension
                    .EnhancedKeyUsages.Cast<System.Security.Cryptography.Oid>()
                    .Any(usage => usage.Value == oid)
            );

    private static bool SamePublicKey(X509Certificate2 certificate, ECDsa key)
    {
        using var publicKey = certificate.GetECDsaPublicKey();
        return publicKey is not null
            && publicKey
                .ExportSubjectPublicKeyInfo()
                .AsSpan()
                .SequenceEqual(key.ExportSubjectPublicKeyInfo());
    }

    private static HashSet<string> Strings(JsonElement element, string name) =>
        element.TryGetProperty(name, out var list) && list.ValueKind == JsonValueKind.Array
            ? list.EnumerateArray()
                .Select(item => item.GetString() ?? "")
                .ToHashSet(StringComparer.Ordinal)
            : [];

    private static string Text(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value)
        && value.ValueKind == JsonValueKind.String
        && !string.IsNullOrWhiteSpace(value.GetString())
            ? value.GetString()!
            : throw Reject("SCHEMA");

    private static long Integer(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) && value.TryGetInt64(out var number)
            ? number
            : throw Reject("SCHEMA");

    private static DateTimeOffset Time(string value) =>
        DateTimeOffset.Parse(
            value,
            CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal
        );

    private static void Require(bool condition, string reason)
    {
        if (!condition)
            throw Reject(reason);
    }

    private static WorkloadCredentialRejectedException Reject(string reason) => new(reason);
}
