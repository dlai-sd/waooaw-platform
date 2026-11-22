// Implements: ADR-046 sections 3, 4.1, 5, 6, and 7.2
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Net.Security;
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
    string CorrelationId
);

public sealed record WorkloadCredentialStatus(
    string Source,
    string State,
    long? RemainingSeconds,
    long? BundleVersion
);

public sealed record WorkloadCredentialApplyResult(string Outcome, string? Reason);

/// <summary>
/// Holds the CURRENT workload credential snapshot. Directory credentials are loaded once; Key Vault credentials
/// are swapped atomically in process when a newer bundle fully verifies (ADR-046 12.2 D4).
/// </summary>
public sealed class WorkloadIdentityClient : IDisposable
{
    private static readonly string[] KnownTargets =
    [
        "billing-engine",
        "professional-runtime",
        "domain-adapter",
        "domain-adapter-dma",
    ];
    private static readonly TimeSpan ConnectionLifetime = TimeSpan.FromMinutes(5);
    private static readonly TimeSpan RetireDelay = TimeSpan.FromMinutes(2);

    private readonly object _applyLock = new();
    private readonly TimeProvider _clock;
    private readonly WorkloadCredentialSettings? _settings;
    private volatile WorkloadCredentialSnapshot? _current;
    private long _lastTrustVersion;
    private long _lastBundleVersion;

    private WorkloadIdentityClient(
        WorkloadCredentialSnapshot? snapshot,
        WorkloadCredentialSettings? settings,
        TimeProvider clock
    )
    {
        _current = snapshot;
        _settings = settings;
        _clock = clock;
    }

    public static WorkloadIdentityClient CreateReloadable(
        WorkloadCredentialSettings settings,
        TimeProvider? clock = null
    ) => new(null, settings, clock ?? TimeProvider.System);

    public bool IsAvailable =>
        LiveSnapshot() is { } snapshot && snapshot.SignerAt(_clock.GetUtcNow()) is not null;

    public WorkloadCredentialStatus GetStatus()
    {
        var source = _settings is null ? "directory" : "keyvault";
        var now = _clock.GetUtcNow();
        if (LiveSnapshot() is not { } snapshot || snapshot.SignerAt(now) is null)
            return new WorkloadCredentialStatus(source, "UNAVAILABLE", null, null);
        return new WorkloadCredentialStatus(
            source,
            "READY",
            snapshot.NotAfter is { } notAfter
                ? Math.Max(0, (long)(notAfter - now).TotalSeconds)
                : null,
            _settings is null ? null : snapshot.BundleVersion
        );
    }

    public WorkloadCredentialApplyResult Apply(string bundleJson, string trustBundleJson)
    {
        if (_settings is null)
            throw new InvalidOperationException("Directory credentials are not reloadable");
        lock (_applyLock)
        {
            var now = _clock.GetUtcNow();
            var previous = _current;
            var verification = WorkloadCredentialVerifier.Verify(
                bundleJson,
                trustBundleJson,
                _settings,
                _lastTrustVersion,
                _lastBundleVersion,
                previous is not null && previous.IsLiveAt(now) ? previous.SignerAt(now) : null,
                now
            );
            if (verification.Snapshot is not { } snapshot)
            {
                if (verification.Reason == "REVOKED")
                    _current = null;
                return new WorkloadCredentialApplyResult("rejected", verification.Reason);
            }
            _lastTrustVersion = snapshot.TrustVersion;
            _lastBundleVersion = snapshot.BundleVersion;
            if (
                previous is not null
                && previous.TrustVersion == snapshot.TrustVersion
                && previous.BundleVersion == snapshot.BundleVersion
            )
            {
                snapshot.Dispose();
                return new WorkloadCredentialApplyResult("unchanged", null);
            }
            _current = snapshot;
            return new WorkloadCredentialApplyResult(
                previous is null ? "loaded" : "refreshed",
                null
            );
        }
    }

    public static WorkloadIdentityClient Load(string credentialsPath)
    {
        var manifest = JsonDocument.Parse(
            File.ReadAllText(Path.Combine(credentialsPath, "manifest.json"))
        );
        var bp = manifest.RootElement.GetProperty("workloads").GetProperty("business-platform");
        var workloadPath = Path.Combine(credentialsPath, "workloads", "business-platform");
        var publicCertificate = X509Certificate2.CreateFromPem(
            File.ReadAllText(Path.Combine(workloadPath, "tls-cert.pem"))
        );
        using var tlsKey = ECDsa.Create();
        tlsKey.ImportFromPem(File.ReadAllText(Path.Combine(workloadPath, "tls-key.pem")));
        var certificate = publicCertificate.CopyWithPrivateKey(tlsKey);
        publicCertificate.Dispose();
        var delegationKey = ECDsa.Create();
        delegationKey.ImportFromPem(
            File.ReadAllText(Path.Combine(workloadPath, "delegation-key.pem"))
        );
        var targets = new Dictionary<string, WorkloadTarget>(StringComparer.Ordinal);
        foreach (var targetName in KnownTargets)
        {
            var target = manifest.RootElement.GetProperty("workloads").GetProperty(targetName);
            targets[targetName] = new WorkloadTarget(
                target.GetProperty("identity_uri").GetString()
                    ?? throw new InvalidOperationException($"{targetName} identity is missing"),
                target.GetProperty("audience").GetString()
                    ?? throw new InvalidOperationException($"{targetName} audience is missing")
            );
        }
        return new WorkloadIdentityClient(
            new WorkloadCredentialSnapshot
            {
                ClientCertificate = certificate,
                TrustAnchors =
                [
                    X509Certificate2.CreateFromPem(
                        File.ReadAllText(Path.Combine(credentialsPath, "trust", "root.pem"))
                    ),
                ],
                Intermediates = [],
                IssuerUri =
                    bp.GetProperty("identity_uri").GetString()
                    ?? throw new InvalidOperationException("BP identity is missing"),
                Pending = new DelegationSigner(
                    delegationKey,
                    bp.GetProperty("delegation_key_id").GetString()
                        ?? throw new InvalidOperationException("BP key ID is missing"),
                    DateTimeOffset.MinValue,
                    DateTimeOffset.MaxValue
                ),
                Targets = targets,
            },
            null,
            TimeProvider.System
        );
    }

    public HttpClient CreateClient(Uri baseAddress, string targetName)
    {
        RequireTargetName(targetName);
        return CreateClientCore(baseAddress, () => CreateHandler(targetName));
    }

    public string GetAudience(string targetName) => GetTarget(targetName).Audience;

    public string GetIdentityUri(string targetName) => GetTarget(targetName).IdentityUri;

    internal HttpClient CreateClientForIdentity(Uri baseAddress, string targetIdentityUri) =>
        CreateClientCore(baseAddress, () => CreateHandlerForIdentity(targetIdentityUri));

    private static HttpClient CreateClientCore(Uri baseAddress, Func<HttpMessageHandler> handler)
    {
        if (baseAddress.Scheme != Uri.UriSchemeHttps)
            throw new InvalidOperationException("Private owner clients require HTTPS");
        return new HttpClient(handler())
        {
            BaseAddress = baseAddress,
            Timeout = TimeSpan.FromSeconds(10),
        };
    }

    public HttpMessageHandler CreateHandler(string targetName)
    {
        RequireTargetName(targetName);
        return _settings is null
            ? CreateHandlerForIdentity(GetTarget(targetName).IdentityUri)
            : new ReloadingHandler(this, targetName);
    }

    private HttpClientHandler CreateHandlerForIdentity(string targetIdentityUri)
    {
        var snapshot = _current ?? throw new WorkloadCredentialsUnavailableException();
        var handler = new HttpClientHandler { AllowAutoRedirect = false };
        handler.ClientCertificates.Add(snapshot.ClientCertificate);
        handler.ServerCertificateCustomValidationCallback = (_, certificate, chain, errors) =>
            ValidateTargetCertificate(certificate, chain, errors, targetIdentityUri);
        return handler;
    }

    private SocketsHttpHandler CreateReloadedHandler(
        WorkloadCredentialSnapshot snapshot,
        string targetIdentityUri
    ) =>
        new()
        {
            AllowAutoRedirect = false,
            PooledConnectionLifetime = ConnectionLifetime,
            PooledConnectionIdleTimeout = TimeSpan.FromMinutes(1),
            SslOptions = new SslClientAuthenticationOptions
            {
                ClientCertificateContext = snapshot.Context,
                ClientCertificates = snapshot.Context is null ? [snapshot.ClientCertificate] : null,
                RemoteCertificateValidationCallback = (_, certificate, chain, errors) =>
                    certificate is not null
                    && ValidateTargetCertificate(certificate, chain, errors, targetIdentityUri),
            },
        };

    private sealed class ReloadingHandler(WorkloadIdentityClient owner, string targetName)
        : HttpMessageHandler
    {
        private readonly object _gate = new();
        private WorkloadCredentialSnapshot? _generation;
        private HttpMessageInvoker? _invoker;

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Invoker().SendAsync(request, cancellationToken);

        protected override HttpResponseMessage Send(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Invoker().Send(request, cancellationToken);

        private HttpMessageInvoker Invoker()
        {
            var snapshot =
                owner.LiveSnapshot() ?? throw new WorkloadCredentialsUnavailableException();
            if (!snapshot.Targets.TryGetValue(targetName, out var target))
                throw new WorkloadCredentialsUnavailableException();
            lock (_gate)
            {
                if (!ReferenceEquals(_generation, snapshot) || _invoker is null)
                {
                    var retired = _invoker;
                    _invoker = new HttpMessageInvoker(
                        owner.CreateReloadedHandler(snapshot, target.IdentityUri),
                        disposeHandler: true
                    );
                    _generation = snapshot;
                    if (retired is not null)
                        _ = Task.Delay(RetireDelay).ContinueWith(_ => retired.Dispose());
                }
                return _invoker;
            }
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
                lock (_gate)
                    _invoker?.Dispose();
            base.Dispose(disposing);
        }
    }

    private WorkloadCredentialSnapshot? LiveSnapshot()
    {
        var snapshot = _current;
        return snapshot is not null && snapshot.IsLiveAt(_clock.GetUtcNow()) ? snapshot : null;
    }

    public string Sign(
        DelegatedRequestContext context,
        string targetAudience,
        string method,
        string route,
        string operation,
        int contractMajor,
        string requestDigest,
        DateTimeOffset now
    )
    {
        var snapshot = LiveSnapshot() ?? throw new WorkloadCredentialsUnavailableException();
        var signer =
            snapshot.SignerAt(_clock.GetUtcNow())
            ?? throw new WorkloadCredentialsUnavailableException();
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
                context.ExpectedVersions.ToDictionary(entry => entry.Key, entry => entry.Value)
            ),
            ["expires_at"] = issuedAt + 60,
            ["idempotency_key"] = context.IdempotencyKey,
            ["issued_at"] = issuedAt,
            ["issuer_uri"] = snapshot.IssuerUri,
            ["key_id"] = signer.KeyId,
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
        var bytes = JsonSerializer.SerializeToUtf8Bytes(
            payload,
            new JsonSerializerOptions { WriteIndented = false }
        );
        var signature = signer.Key.SignData(
            bytes,
            HashAlgorithmName.SHA256,
            DSASignatureFormat.Rfc3279DerSequence
        );
        return $"{Base64Url(bytes)}.{Base64Url(signature)}";
    }

    private bool ValidateTargetCertificate(
        X509Certificate certificate,
        X509Chain? suppliedChain,
        SslPolicyErrors errors,
        string targetIdentityUri
    )
    {
        if (certificate is X509Certificate2 typed)
            return ValidateTargetCertificate(typed, suppliedChain, errors, targetIdentityUri);
        using var converted = new X509Certificate2(certificate);
        return ValidateTargetCertificate(converted, suppliedChain, errors, targetIdentityUri);
    }

    private bool ValidateTargetCertificate(
        X509Certificate2? certificate,
        X509Chain? suppliedChain,
        SslPolicyErrors errors,
        string targetIdentityUri
    )
    {
        if (certificate is null || LiveSnapshot() is not { } snapshot)
            return false;
        using var chain = new X509Chain();
        chain.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
        chain.ChainPolicy.CustomTrustStore.AddRange(snapshot.TrustAnchors);
        chain.ChainPolicy.ExtraStore.AddRange(snapshot.Intermediates);
        chain.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
        if (suppliedChain is not null)
            foreach (var element in suppliedChain.ChainElements.Cast<X509ChainElement>().Skip(1))
                chain.ChainPolicy.ExtraStore.Add(element.Certificate);
        if (!chain.Build(certificate))
            return false;
        return HasExactUriSan(certificate, targetIdentityUri)
            && !snapshot.RevokedIdentityUris.Contains(targetIdentityUri)
            && !snapshot.RevokedSerials.Contains(
                WorkloadCredentialVerifier.DecimalSerial(certificate)
            );
    }

    internal static bool HasExactUriSan(X509Certificate2 certificate, string targetIdentityUri) =>
        Waooaw.WorkloadIdentity.InferenceWorkloadValidator.HasExactUriSan(
            certificate,
            targetIdentityUri
        );

    private static string Base64Url(byte[] value) =>
        Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private WorkloadTarget GetTarget(string targetName)
    {
        var snapshot = LiveSnapshot() ?? throw new WorkloadCredentialsUnavailableException();
        return snapshot.Targets.TryGetValue(targetName, out var target)
            ? target
            : throw new InvalidOperationException($"Unknown workload target: {targetName}");
    }

    private static void RequireTargetName(string targetName)
    {
        if (!KnownTargets.Contains(targetName))
            throw new InvalidOperationException($"Unknown workload target: {targetName}");
    }

    public void Dispose() => _current?.Dispose();
}
