// Implements: work-contracts/WC-121-demo-whatsapp-provider-enablement-work-component.md §10.6
// Constitutional basis: C-059, C-065, C-080

using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class PinnedTemporalTestEnvironmentTests
{
    [Fact]
    public void RunnerSuppliesTheExactTemporalTestServer() =>
        PinnedTemporalTestEnvironment.RequirePinnedServer(PinnedTemporalTestEnvironment.ServerPath);

    [Fact]
    public void MissingServerIsDeniedWithoutDownloading() =>
        Assert.Throws<FileNotFoundException>(() =>
            PinnedTemporalTestEnvironment.RequirePinnedServer(
                Path.Combine(Path.GetTempPath(), $"absent-temporal-{Guid.NewGuid():N}")
            )
        );

    [Fact]
    public void ModifiedServerIsDeniedWithoutExecution()
    {
        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(path, "not the admitted Temporal test server");
            Assert.Throws<InvalidOperationException>(() =>
                PinnedTemporalTestEnvironment.RequirePinnedServer(path)
            );
        }
        finally
        {
            File.Delete(path);
        }
    }
}
