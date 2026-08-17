namespace Waooaw.BusinessPlatform.Tests;

internal static class RepositoryPaths
{
    public static string Resolve(string relativePath)
    {
        var roots = new[]
        {
            Environment.GetEnvironmentVariable("GITHUB_WORKSPACE"),
            Directory.GetCurrentDirectory(),
            AppContext.BaseDirectory,
        };

        var searched = new List<string>();
        foreach (var root in roots.Where(value => !string.IsNullOrWhiteSpace(value)).Distinct())
        {
            for (var directory = new DirectoryInfo(root!); directory is not null; directory = directory.Parent)
            {
                var candidate = Path.Combine(directory.FullName, relativePath);
                searched.Add(candidate);
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }
        }

        throw new FileNotFoundException(
            $"Repository file '{relativePath}' was not found. Searched: {string.Join(", ", searched)}");
    }
}
