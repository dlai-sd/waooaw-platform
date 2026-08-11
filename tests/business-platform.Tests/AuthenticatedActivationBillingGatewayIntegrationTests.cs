// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-08
// constitutional_basis: C-002, C-023, C-026, C-065, C-076, C-083, C-084, C-085
using System.Diagnostics;
using System.Net.Sockets;
using System.Text.Json;
using FluentAssertions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AuthenticatedActivationBillingGatewayIntegrationTests : IDisposable
{
    private readonly string _temporary = Path.Combine(Path.GetTempPath(), $"wc059-mtls-{Guid.NewGuid():N}");
    private Process? _server;

    [Fact]
    public async Task RealPrivateListenerAcceptsGatewayReplayAndRejectsMissingWorkloadCertificate()
    {
        var root = FindRepositoryRoot();
        var credentials = Path.Combine(_temporary, "credentials");
        Bootstrap(root, credentials);
        var port = ReservePort();
        var ids = Enumerable.Range(0, 9).Select(_ => Guid.NewGuid()).ToArray();
        var request = new ActivationBillingRequest(
            ids[0], ids[1], ids[2], ids[3], ids[4], 3, ids[5],
            $"pay_{Guid.NewGuid():N}", ids[6], ids[7]);
        var server = StartServer(root, credentials, port, request, ids[8]);
        _server = server;
        await WaitForListenerAsync(port, server);

        using var identity = WorkloadIdentityClient.Load(credentials);
        using var gateway = new AuthenticatedActivationBillingGateway(
            identity, new Uri($"https://127.0.0.1:{port}"));
        var first = await gateway.ActivatePaidSubscriptionAsync(request, CancellationToken.None);
        var replay = await gateway.ActivatePaidSubscriptionAsync(request, CancellationToken.None);

        first.Status.Should().Be("ACTIVE");
        replay.Should().Be(first);
        using var unauthenticated = new HttpClient(new HttpClientHandler
        {
            ServerCertificateCustomValidationCallback = (_, _, _, _) => true,
        });
        var action = () => unauthenticated.GetAsync($"https://127.0.0.1:{port}/internal/v1/relationships/{ids[1]:D}/commercial-projection");
        await action.Should().ThrowAsync<HttpRequestException>();
    }

    private Process StartServer(
        string root, string credentials, int port, ActivationBillingRequest request, Guid trialId)
    {
        Directory.CreateDirectory(_temporary);
        var database = Path.Combine(_temporary, "wbe.db");
        var seed = new Dictionary<string, string>
        {
            ["tenant_id"] = request.TenantId.ToString("D"),
            ["relationship_id"] = request.RelationshipId.ToString("D"),
            ["accepted_contract_id"] = request.AcceptedContractId.ToString("D"),
            ["contract_acceptance_id"] = request.ContractAcceptanceId.ToString("D"),
            ["payment_reference"] = request.PaymentReference,
            ["payment_evidence_id"] = request.PaymentEvidenceId.ToString("D"),
            ["customer_id"] = Guid.NewGuid().ToString("D"),
            ["consent_id"] = Guid.NewGuid().ToString("D"),
            ["trial_id"] = trialId.ToString("D"),
            ["contract_hash"] = new string('a', 64),
        };
        var start = new ProcessStartInfo
        {
            FileName = "python3",
            WorkingDirectory = root,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        start.ArgumentList.Add(Path.Combine(root, "tests/billing-engine/wc059_private_activation_server.py"));
        start.Environment["WAOOAW_WORKLOAD_CREDENTIALS"] = credentials;
        start.Environment["WBE_PRIVATE_PORT"] = port.ToString();
        start.Environment["DATABASE_URL"] = $"sqlite+aiosqlite:///{database}";
        start.Environment["WC059_ACTIVATION_SEED"] = JsonSerializer.Serialize(seed);
        return Process.Start(start) ?? throw new InvalidOperationException("Could not start WBE private listener");
    }

    private static async Task WaitForListenerAsync(int port, Process server)
    {
        for (var attempt = 0; attempt < 600; attempt++)
        {
            if (server.HasExited)
                throw new InvalidOperationException(await server.StandardError.ReadToEndAsync());
            try
            {
                using var client = new TcpClient();
                await client.ConnectAsync("127.0.0.1", port);
                return;
            }
            catch (SocketException)
            {
                await Task.Delay(50);
            }
        }
        server.Kill(entireProcessTree: true);
        throw new TimeoutException($"WBE private listener did not start: {await server.StandardError.ReadToEndAsync()}");
    }

    private static void Bootstrap(string root, string credentials)
    {
        var start = new ProcessStartInfo { FileName = "python3", RedirectStandardError = true, UseShellExecute = false };
        start.ArgumentList.Add(Path.Combine(root, "scripts/bootstrap_workload_identity.py"));
        start.ArgumentList.Add("--registry");
        start.ArgumentList.Add(Path.Combine(root, "infrastructure/workload-identity/registry.yaml"));
        start.ArgumentList.Add("--environment");
        start.ArgumentList.Add("ci");
        start.ArgumentList.Add("--output");
        start.ArgumentList.Add(credentials);
        using var process = Process.Start(start) ?? throw new InvalidOperationException("Could not bootstrap identity");
        process.WaitForExit();
        process.ExitCode.Should().Be(0, process.StandardError.ReadToEnd());
    }

    private static int ReservePort()
    {
        var listener = new TcpListener(System.Net.IPAddress.Loopback, 0);
        listener.Start();
        var port = ((System.Net.IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        return port;
    }

    private static string FindRepositoryRoot()
    {
        var path = new DirectoryInfo(AppContext.BaseDirectory);
        while (path is not null && !Directory.Exists(Path.Combine(path.FullName, "constitution"))) path = path.Parent;
        return path?.FullName ?? throw new InvalidOperationException("Repository root not found");
    }

    public void Dispose()
    {
        if (_server is { HasExited: false }) _server.Kill(entireProcessTree: true);
        if (Directory.Exists(_temporary)) Directory.Delete(_temporary, recursive: true);
    }
}