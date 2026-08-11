// Implements: ADR-046 sections 3, 4.1, 5, 6, and 7.2
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Net.Security;
using System.Formats.Asn1;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public sealed record DelegatedRequestContext(
    string ActorSubject,
    string EffectiveRole,
    string TenantId,
    string RelationshipId,
    string Purpose,
    string SubjectReference,
    string CommandId,
    string? IdempotencyKey,
    IReadOnlyDictionary<string, string> ExpectedVersions,
    string CorrelationId);

public sealed class WorkloadIdentityClient : IDisposable
{
    private sealed record TargetIdentity(string IdentityUri, string Audience);

    private readonly ECDsa _delegationKey;
    private readonly X509Certificate2 _clientCertificate;
    private readonly X509Certificate2 _rootCertificate;
    private readonly string _issuerUri;
    private readonly string _keyId;
    private readonly IReadOnlyDictionary<string, TargetIdentity> _targets;

    private WorkloadIdentityClient(
        ECDsa delegationKey,
        X509Certificate2 clientCertificate,
        X509Certificate2 rootCertificate,
        string issuerUri,
        string keyId,
        IReadOnlyDictionary<string, TargetIdentity> targets)
    {
        _delegationKey = delegationKey;
        _clientCertificate = clientCertificate;
        _rootCertificate = rootCertificate;
        _issuerUri = issuerUri;
        _keyId = keyId;
        _targets = targets;
    }

    public static WorkloadIdentityClient Load(string credentialsPath)
    {
        var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(credentialsPath, "manifest.json")));
        var bp = manifest.RootElement.GetProperty("workloads").GetProperty("business-platform");
        var workloadPath = Path.Combine(credentialsPath, "workloads", "business-platform");
        var publicCertificate = X509Certificate2.CreateFromPem(
            File.ReadAllText(Path.Combine(workloadPath, "tls-cert.pem")));
        using var tlsKey = ECDsa.Create();
        tlsKey.ImportFromPem(File.ReadAllText(Path.Combine(workloadPath, "tls-key.pem")));
        var certificate = publicCertificate.CopyWithPrivateKey(tlsKey);
        publicCertificate.Dispose();
        var delegationKey = ECDsa.Create();
        delegationKey.ImportFromPem(File.ReadAllText(Path.Combine(workloadPath, "delegation-key.pem")));
        var targets = new Dictionary<string, TargetIdentity>(StringComparer.Ordinal);
        foreach (var targetName in new[] { "billing-engine", "professional-runtime", "domain-adapter-dma" })
        {
            var target = manifest.RootElement.GetProperty("workloads").GetProperty(targetName);
            targets[targetName] = new TargetIdentity(
                target.GetProperty("identity_uri").GetString()
                    ?? throw new InvalidOperationException($"{targetName} identity is missing"),
                target.GetProperty("audience").GetString()
                    ?? throw new InvalidOperationException($"{targetName} audience is missing"));
        }
        return new WorkloadIdentityClient(
            delegationKey,
            certificate,
            X509Certificate2.CreateFromPem(
                File.ReadAllText(Path.Combine(credentialsPath, "trust", "root.pem"))),
            bp.GetProperty("identity_uri").GetString() ?? throw new InvalidOperationException("BP identity is missing"),
            bp.GetProperty("delegation_key_id").GetString() ?? throw new InvalidOperationException("BP key ID is missing"),
            targets);
    }

    public HttpClient CreateClient(Uri baseAddress, string targetName)
    {
        var target = GetTarget(targetName);
        return CreateClientForIdentity(baseAddress, target.IdentityUri);
    }

    public string GetAudience(string targetName) => GetTarget(targetName).Audience;

    internal HttpClient CreateClientForIdentity(Uri baseAddress, string targetIdentityUri)
    {
        if (baseAddress.Scheme != Uri.UriSchemeHttps) throw new InvalidOperationException("Private owner clients require HTTPS");
        var handler = new HttpClientHandler();
        handler.ClientCertificates.Add(_clientCertificate);
        handler.ServerCertificateCustomValidationCallback = (_, certificate, chain, errors) =>
            ValidateTargetCertificate(certificate, chain, errors, targetIdentityUri);
        return new HttpClient(handler) { BaseAddress = baseAddress, Timeout = TimeSpan.FromSeconds(10) };
    }

    public string Sign(
        DelegatedRequestContext context,
        string targetAudience,
        string method,
        string route,
        string operation,
        int contractMajor,
        string requestDigest,
        DateTimeOffset now)
    {
        var issuedAt = now.ToUnixTimeSeconds();
        var payload = new SortedDictionary<string, object?>
        {
            ["actor_source"] = "BP_SESSION",
            ["actor_subject"] = context.ActorSubject,
            ["command_id"] = context.CommandId,
            ["contract_major"] = contractMajor,
            ["correlation_id"] = context.CorrelationId,
            ["effective_role"] = context.EffectiveRole,
            ["envelope_id"] = Guid.NewGuid().ToString(),
            ["expected_versions"] = new SortedDictionary<string, string>(
                context.ExpectedVersions.ToDictionary(entry => entry.Key, entry => entry.Value)),
            ["expires_at"] = issuedAt + 60,
            ["idempotency_key"] = context.IdempotencyKey,
            ["issued_at"] = issuedAt,
            ["issuer_uri"] = _issuerUri,
            ["key_id"] = _keyId,
            ["method"] = method.ToUpperInvariant(),
            ["not_before"] = issuedAt,
            ["operation"] = operation,
            ["purpose"] = context.Purpose,
            ["relationship_id"] = context.RelationshipId,
            ["request_digest"] = requestDigest,
            ["route"] = route,
            ["schema_version"] = "1.0",
            ["subject_reference"] = context.SubjectReference,
            ["target_audience"] = targetAudience,
            ["tenant_id"] = context.TenantId,
        };
        var bytes = JsonSerializer.SerializeToUtf8Bytes(payload, new JsonSerializerOptions { WriteIndented = false });
        var signature = _delegationKey.SignData(bytes, HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence);
        return $"{Base64Url(bytes)}.{Base64Url(signature)}";
    }

    private bool ValidateTargetCertificate(
        X509Certificate2? certificate,
        X509Chain? suppliedChain,
        SslPolicyErrors errors,
        string targetIdentityUri)
    {
        if (certificate is null) return false;
        using var chain = new X509Chain();
        chain.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
        chain.ChainPolicy.CustomTrustStore.Add(_rootCertificate);
        chain.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
        if (suppliedChain is not null)
            foreach (var element in suppliedChain.ChainElements.Cast<X509ChainElement>().Skip(1))
                chain.ChainPolicy.ExtraStore.Add(element.Certificate);
        if (!chain.Build(certificate)) return false;
        return HasExactUriSan(certificate, targetIdentityUri);
    }

    private static bool HasExactUriSan(X509Certificate2 certificate, string targetIdentityUri)
    {
        var extension = certificate.Extensions["2.5.29.17"];
        if (extension is null) return false;
        var names = new AsnReader(extension.RawData, AsnEncodingRules.DER).ReadSequence();
        var uriTag = new Asn1Tag(TagClass.ContextSpecific, 6);
        while (names.HasData)
        {
            if (names.PeekTag().HasSameClassAndValue(uriTag))
            {
                var uri = names.ReadCharacterString(UniversalTagNumber.IA5String, uriTag);
                if (uri.Equals(targetIdentityUri, StringComparison.Ordinal)) return true;
            }
            else
            {
                names.ReadEncodedValue();
            }
        }
        return false;
    }

    private static string Base64Url(byte[] value) => Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private TargetIdentity GetTarget(string targetName) =>
        _targets.TryGetValue(targetName, out var target)
            ? target
            : throw new InvalidOperationException($"Unknown workload target: {targetName}");

    public void Dispose()
    {
        _delegationKey.Dispose();
        _clientCertificate.Dispose();
        _rootCertificate.Dispose();
    }
}