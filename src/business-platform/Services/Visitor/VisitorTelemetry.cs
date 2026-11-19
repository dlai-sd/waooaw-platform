// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R010, WC135-R013
// Constitutional basis: C-023, C-048, C-059, C-063

using System.Diagnostics.Metrics;

namespace Waooaw.BusinessPlatform.Services.Visitor;

/// <summary>
/// Metrics and structured response events for the visitor conversation. Events carry the channel, HTTP
/// status, a fixed reason code and the conversation states; never message text, phone, email or name.
/// </summary>
public sealed class VisitorTelemetry : IDisposable
{
    public const string MeterName = "Waooaw.Visitor";

    private readonly Meter _meter = new(MeterName);
    private readonly Counter<long> _turns;
    private readonly Counter<long> _outcomes;
    private readonly Counter<long> _stateExits;
    private readonly Counter<long> _choiceTaps;
    private readonly Counter<long> _policyViolations;
    private readonly Histogram<double> _turnsToFirstValue;
    private readonly Histogram<double> _responseMs;
    private readonly ILogger<VisitorTelemetry> _logger;

    public VisitorTelemetry(ILogger<VisitorTelemetry> logger)
    {
        _logger = logger;
        _turns = _meter.CreateCounter<long>("visitor_turn");
        _outcomes = _meter.CreateCounter<long>("visitor_outcome");
        _stateExits = _meter.CreateCounter<long>("visitor_state_exit");
        _choiceTaps = _meter.CreateCounter<long>("visitor_choice_tap");
        _policyViolations = _meter.CreateCounter<long>("visitor_policy_violation");
        _turnsToFirstValue = _meter.CreateHistogram<double>("visitor_turns_to_first_value");
        _responseMs = _meter.CreateHistogram<double>("visitor_response_ms", "ms");
    }

    /// <summary>One structured event per response (WC135-R010).</summary>
    public void Response(
        string channel,
        int status,
        string reason,
        string state,
        string priorState,
        string contentVersion,
        double latencyMs,
        Guid correlationId
    )
    {
        _turns.Add(1, new KeyValuePair<string, object?>("channel", channel));
        _responseMs.Record(latencyMs, new KeyValuePair<string, object?>("channel", channel));
        if (!string.Equals(state, priorState, StringComparison.Ordinal))
            _stateExits.Add(1, new KeyValuePair<string, object?>("state", priorState));
        var level = status >= 500 ? LogLevel.Warning : LogLevel.Information;
        _logger.Log(
            level,
            "visitor.response channel={Channel} status={Status} reason={Reason} state={State} priorState={PriorState} contentVersion={ContentVersion} latencyMs={LatencyMs} correlationId={CorrelationId}",
            channel,
            status,
            reason,
            state,
            priorState,
            contentVersion,
            Math.Round(latencyMs, 1),
            correlationId
        );
    }

    public void Outcome(string outcome, string channel) =>
        _outcomes.Add(
            1,
            new KeyValuePair<string, object?>("outcome", outcome),
            new KeyValuePair<string, object?>("channel", channel)
        );

    public void ChoiceTap(string choiceId) =>
        _choiceTaps.Add(1, new KeyValuePair<string, object?>("choiceId", choiceId));

    public void TurnsToFirstValue(int turns) => _turnsToFirstValue.Record(turns);

    public void PolicyViolation(string code) =>
        _policyViolations.Add(1, new KeyValuePair<string, object?>("code", code));

    public void Dispose() => _meter.Dispose();
}
