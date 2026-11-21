using System.Text.RegularExpressions;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

// Enforces rules V2/V3 of standards/CI-VALIDATION-SPEED-POLICY.md: a Postgres test uses the pooled helper
// unless it needs real container start-up (init scripts), and those few files are named here.
public sealed class PooledPostgresPolicyTests
{
    private static readonly string[] RealContainerFiles =
    [
        "PooledPostgres.cs",
        "PooledPostgresAliases.cs",
        "Identity/CustomerPhoneChangePostgresTests.cs",
        "Identity/CustomerWorkspaceFullSchemaPostgresTests.cs",
        "Conversation/ConversationPendingStartPostgresTests.cs",
    ];

    private static readonly Regex RealContainerUse = new(
        @"Testcontainers\.PostgreSql\.PostgreSql(Builder|Container)|using\s+\w+\s*=\s*Testcontainers\.PostgreSql|new\s+ContainerBuilder\s*\(",
        RegexOptions.Compiled);

    [Fact]
    public void OnlyNamedFilesStartARealPostgresContainer()
    {
        var testRoot = Path.Combine(RepositoryPaths.Root(), "tests", "business-platform.Tests");
        var offenders = Directory
            .EnumerateFiles(testRoot, "*.cs", SearchOption.AllDirectories)
            .Where(path => !path.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}"))
            .Where(path => !path.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}"))
            .Select(path => Path.GetRelativePath(testRoot, path).Replace('\\', '/'))
            .Where(relative => !RealContainerFiles.Contains(relative))
            .Where(relative => RealContainerUse.IsMatch(File.ReadAllText(Path.Combine(testRoot, relative))))
            .OrderBy(relative => relative, StringComparer.Ordinal)
            .ToArray();

        Assert.True(
            offenders.Length == 0,
            "These tests start a real Postgres container. Use new PostgreSqlBuilder(image)...Build() so the pooled helper is used "
            + "(standards/CI-VALIDATION-SPEED-POLICY.md V2), or add the file to RealContainerFiles with a reason (V3): "
            + string.Join(", ", offenders));
    }

    [Fact]
    public void NamedRealContainerFilesStillExist()
    {
        var testRoot = Path.Combine(RepositoryPaths.Root(), "tests", "business-platform.Tests");
        var missing = RealContainerFiles.Where(relative => !File.Exists(Path.Combine(testRoot, relative))).ToArray();

        Assert.True(missing.Length == 0, "Remove stale entries from RealContainerFiles: " + string.Join(", ", missing));
    }
}
