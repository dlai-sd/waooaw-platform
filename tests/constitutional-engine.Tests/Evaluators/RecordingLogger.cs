// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-059, C-076
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

internal sealed class RecordingLogger<T> : ILogger<T>
{
    private sealed class Scope : IDisposable
    {
        public static readonly Scope Instance = new();

        public void Dispose() { }
    }

    public List<(LogLevel Level, string Message)> Entries { get; } = [];

    public IDisposable BeginScope<TState>(TState state)
        where TState : notnull => Scope.Instance;

    public bool IsEnabled(LogLevel logLevel) => true;

    public void Log<TState>(
        LogLevel logLevel,
        EventId eventId,
        TState state,
        Exception? exception,
        Func<TState, Exception?, string> formatter
    )
    {
        Entries.Add((logLevel, formatter(state, exception)));
    }
}
