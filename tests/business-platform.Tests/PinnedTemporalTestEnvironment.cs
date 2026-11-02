// Implements: work-contracts/WC-121-demo-whatsapp-provider-enablement-work-component.md §10.6
// Constitutional basis: C-059, C-065, C-080

using System.Security.Cryptography;
using Temporalio.Testing;

namespace Waooaw.BusinessPlatform.Tests;

internal static class PinnedTemporalTestEnvironment
{
    internal const string ServerPath = "/opt/temporal-test-server";
    internal const string ServerSha256 =
        "19defb9f7318c7cf249518b3642a735efb79876c2b6918afe312336476b796a5";

    internal static Task<WorkflowEnvironment> StartTimeSkippingAsync()
    {
        RequirePinnedServer(ServerPath);
        return WorkflowEnvironment.StartTimeSkippingAsync(
            new() { TestServer = new() { ExistingPath = ServerPath } }
        );
    }

    internal static void RequirePinnedServer(string path)
    {
        using var executable = File.OpenRead(path);
        if (Convert.ToHexStringLower(SHA256.HashData(executable)) != ServerSha256)
            throw new InvalidOperationException(
                "Temporal test server differs from the pinned validation-runner dependency."
            );
    }
}
