// Implements: ADR-046 sections 3.1, 4.1 and Amendment 1 (cloud credential delivery); WC-149 R003
// constitutional_basis: C-001, C-026, C-059, C-063, C-083, C-084, C-085

using System.Net.Security;
using System.Security.Authentication;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.AspNetCore.Server.Kestrel.Https;
using Waooaw.WorkloadIdentity;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>
/// Supplies the inbound workload validator with the CURRENT verified Key Vault bundle: the signed manifest,
/// the published delegation certificates and the trust anchors. Nothing is read from a credentials directory.
/// </summary>
internal sealed class WorkloadInboundCredentialSource(
    WorkloadIdentityClient client,
    TimeProvider clock
) : IInboundCredentialSource
{
    private const string DelegationSigningOid = WorkloadCredentialVerifier.DelegationSigningOid;
    private const string ClientAuthOid = WorkloadCredentialVerifier.ClientAuthOid;

    public InboundCredentialMaterial? Current()
    {
        var snapshot = client.InboundSnapshot();
        if (snapshot is null || snapshot.ManifestJson.Length == 0)
            return null;
        return new InboundCredentialMaterial(
            snapshot.ManifestJson,
            (certificate, expectedUri) =>
                InferenceWorkloadValidator.HasExactUriSan(certificate, expectedUri)
                && IsTrustedPeer(snapshot, certificate, clock.GetUtcNow()),
            (caller, keyId) => PublishedDelegation(snapshot, caller, keyId, clock.GetUtcNow())
        );
    }

    internal static bool IsTrustedPeer(
        WorkloadCredentialSnapshot snapshot,
        X509Certificate certificate,
        DateTimeOffset now
    )
    {
        using var typed = new X509Certificate2(certificate);
        if (
            snapshot.RevokedSerials.Contains(WorkloadCredentialVerifier.DecimalSerial(typed))
            || !WorkloadCredentialVerifier.ChainsTo(
                typed,
                snapshot.TrustAnchors,
                snapshot.Intermediates,
                now
            )
        )
            return false;
        return HasUsage(typed, ClientAuthOid)
            && SameTrustDomain(snapshot.IssuerUri, typed, snapshot.RevokedIdentityUris);
    }

    private static bool SameTrustDomain(
        string ownIdentityUri,
        X509Certificate2 certificate,
        IReadOnlySet<string> revokedUris
    )
    {
        const string marker = "/workload/";
        var split = ownIdentityUri.IndexOf(marker, StringComparison.Ordinal);
        if (split < 0)
            return false;
        var prefix = ownIdentityUri[..(split + marker.Length)];
        return UriSans(certificate)
            .Any(uri =>
                uri.StartsWith(prefix, StringComparison.Ordinal) && !revokedUris.Contains(uri)
            );
    }

    private static X509Certificate2? PublishedDelegation(
        WorkloadCredentialSnapshot snapshot,
        string caller,
        string keyId,
        DateTimeOffset now
    )
    {
        using var manifest = JsonDocument.Parse(snapshot.ManifestJson);
        if (
            !manifest.RootElement.GetProperty("workloads").TryGetProperty(caller, out var record)
            || !record.TryGetProperty("delegation_certificates", out var published)
            || published.ValueKind != JsonValueKind.Array
        )
            return null;
        var identityUri = record.GetProperty("identity_uri").GetString();
        foreach (var entry in published.EnumerateArray())
        {
            if (entry.GetProperty("key_id").GetString() != keyId)
                continue;
            var certificate = X509Certificate2.CreateFromPem(
                entry.GetProperty("certificate_pem").GetString()
            );
            if (
                identityUri is not null
                && now >= certificate.NotBefore
                && now < certificate.NotAfter
                && HasUsage(certificate, DelegationSigningOid)
                && InferenceWorkloadValidator.HasExactUriSan(certificate, identityUri)
                && !snapshot.RevokedSerials.Contains(
                    WorkloadCredentialVerifier.DecimalSerial(certificate)
                )
                && WorkloadCredentialVerifier.ChainsTo(
                    certificate,
                    snapshot.TrustAnchors,
                    snapshot.Intermediates,
                    now
                )
            )
                return certificate;
            certificate.Dispose();
            return null;
        }
        return null;
    }

    private static bool HasUsage(X509Certificate2 certificate, string oid) =>
        certificate
            .Extensions.OfType<X509EnhancedKeyUsageExtension>()
            .Any(extension =>
                extension
                    .EnhancedKeyUsages.Cast<System.Security.Cryptography.Oid>()
                    .Any(usage => usage.Value == oid)
            );

    private static IEnumerable<string> UriSans(X509Certificate2 certificate)
    {
        var extension = certificate.Extensions["2.5.29.17"];
        if (extension is null)
            yield break;
        var names = new System.Formats.Asn1.AsnReader(
            extension.RawData,
            System.Formats.Asn1.AsnEncodingRules.DER
        ).ReadSequence();
        var uriTag = new System.Formats.Asn1.Asn1Tag(
            System.Formats.Asn1.TagClass.ContextSpecific,
            6
        );
        while (names.HasData)
        {
            if (names.PeekTag().HasSameClassAndValue(uriTag))
                yield return names.ReadCharacterString(
                    System.Formats.Asn1.UniversalTagNumber.IA5String,
                    uriTag
                );
            else
                names.ReadEncodedValue();
        }
    }
}

/// <summary>
/// The Key Vault mode inbound ADR-046 listener: a dedicated private HTTPS port that presents the live workload
/// certificate, requires a client certificate chained to the CURRENT trust bundle, and serves only /internal/v1.
/// </summary>
internal static class WorkloadInboundListener
{
    public const int DefaultPort = 5445;
    public const string RoutePrefix = "/internal/v1";

    public static int? Configure(
        WebApplicationBuilder builder,
        WorkloadCredentialOptions options,
        WorkloadIdentityClient? client
    )
    {
        if (!options.IsKeyVault || client is null)
            return null;
        var port =
            int.TryParse(builder.Configuration["WorkloadInbound:Port"], out var configured)
            && configured is > 0 and < 65536
                ? configured
                : DefaultPort;
        builder.WebHost.ConfigureKestrel(server =>
            server.ListenAnyIP(
                port,
                listen =>
                {
                    listen.Protocols = HttpProtocols.Http1;
                    listen.UseHttps(
                        new TlsHandshakeCallbackOptions
                        {
                            OnConnection = _ =>
                            {
                                var snapshot =
                                    client.InboundSnapshot()
                                    ?? throw new AuthenticationException(
                                        "Workload credentials are unavailable."
                                    );
                                return ValueTask.FromResult(
                                    new SslServerAuthenticationOptions
                                    {
                                        ServerCertificateContext = snapshot.Context,
                                        ServerCertificate = snapshot.Context is null
                                            ? snapshot.ClientCertificate
                                            : null,
                                        ClientCertificateRequired = true,
                                        EnabledSslProtocols =
                                            SslProtocols.Tls12 | SslProtocols.Tls13,
                                        ApplicationProtocols = [SslApplicationProtocol.Http11],
                                        RemoteCertificateValidationCallback = (_, peer, _, _) =>
                                            peer is not null
                                            && WorkloadInboundCredentialSource.IsTrustedPeer(
                                                snapshot,
                                                peer,
                                                DateTimeOffset.UtcNow
                                            ),
                                    }
                                );
                            },
                        }
                    );
                }
            )
        );
        return port;
    }
}
