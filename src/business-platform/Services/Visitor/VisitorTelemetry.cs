// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R010, WC135-R013
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-11
// Constitutional basis: C-023, C-048, C-059, C-063

using System.Diagnostics.Metrics;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services.Visitor;

/// <summary>
/// Metrics and structured response events for the visitor conversation. Events carry the channel, HTTP
/// status, a fixed reason code and the conversation states; never message text, phone, email or name.
/// </summary>
public sealed partial class VisitorTelemetry : IDisposable
{
    public const string MeterName = "Waooaw.Visitor";
    public const string SpendReserved = "spend_reserved";
    public const string SpendSettled = "spend_settled";
    public const string SpendReleased = "spend_released";
    public const string SpendDenied = "spend_denied";
    public const string SpendPaiseMetric = "waooaw_spend_paise_total";
    public const string SpendDeniedMetric = "waooaw_spend_denied_total";

    private readonly Meter _meter = new(MeterName);
    private readonly Counter<long> _turns;
    private readonly Counter<long> _outcomes;
    private readonly Counter<long> _stateExits;
    private readonly Counter<long> _choiceTaps;
    private readonly Counter<long> _policyViolations;
    private readonly Counter<long> _spendPaise;
    private readonly Counter<long> _spendDenied;
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
        _spendPaise = _meter.CreateCounter<long>(SpendPaiseMetric, "paise");
        _spendDenied = _meter.CreateCounter<long>(SpendDeniedMetric);
        _turnsToFirstValue = _meter.CreateHistogram<double>("visitor_turns_to_first_value");
        _responseMs = _meter.CreateHistogram<double>("visitor_response_ms", "ms");
    }

    [GeneratedRegex("^[A-Za-z0-9_.:-]{1,64}$")]
    private static partial Regex OpaqueToken();

    [GeneratedRegex(@"^\+?[0-9][0-9 ()-]{6,}$")]
    private static partial Regex PhoneLike();

    [GeneratedRegex("^[A-Z][A-Z0-9_]{1,63}$")]
    private static partial Regex ReasonShape();

    private static string? Opaque(string? value) =>
        value is not null && OpaqueToken().IsMatch(value) && !PhoneLike().IsMatch(value)
            ? value
            : null;

    /// <summary>
    /// One structured event per spend operation (WC-136 C4-11). Only identifiers, the account class, an
    /// amount and a fixed reason code are logged; a reference that could carry personal data is dropped.
    /// A settled event adds its paise to the class total; a denied event counts once by class and reason.
    /// </summary>
    public void Spend(
        string eventName,
        string accountClass,
        Guid tenantId,
        long paise,
        string reasonCode,
        Guid? relationshipId = null,
        string? skillId = null,
        string? componentId = null,
        string? campaignRef = null,
        string? leadRef = null
    )
    {
        if (eventName is not (SpendReserved or SpendSettled or SpendReleased or SpendDenied))
            return;
        var spendClass = Opaque(accountClass) ?? "UNKNOWN";
        var reason = ReasonShape().IsMatch(reasonCode) ? reasonCode : "UNSPECIFIED";
        var amount = Math.Max(0, paise);
        if (eventName == SpendSettled)
            _spendPaise.Add(amount, new KeyValuePair<string, object?>("class", spendClass));
        else if (eventName == SpendDenied)
            _spendDenied.Add(
                1,
                new KeyValuePair<string, object?>("class", spendClass),
                new KeyValuePair<string, object?>("reason", reason)
            );
        _logger.LogInformation(
            "{Event} accountClass={AccountClass} tenantId={TenantId} relationshipId={RelationshipId} skillId={SkillId} componentId={ComponentId} campaignRef={CampaignRef} leadRef={LeadRef} paise={Paise} reasonCode={ReasonCode}",
            eventName,
            spendClass,
            tenantId,
            relationshipId,
            Opaque(skillId),
            Opaque(componentId),
            Opaque(campaignRef),
            Opaque(leadRef),
            amount,
            reason
        );
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
