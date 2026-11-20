# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-04
# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
import copy
import json

import pytest

from visitor_simulation.customer import ScriptedModel
from visitor_simulation.fake_server import LEGACY_CATALOGUE
from visitor_simulation.judge import (
    CRITERIA,
    DETECTORS,
    CriterionScore,
    POLICY_VIOLATIONS,
    SCORERS,
    Judge,
    ModelScorer,
    RuleScorer,
    ScoreParseError,
    check_policy,
    load_rubric,
    score_safety,
)
from visitor_simulation.models import GoalSpec, build_conversation
from visitor_simulation.policy import DEFAULT_CONTENT_PATH, PolicyError, load_protocol_policy, parse_protocol_policy

RUBRIC = load_rubric()
ACK_PLACEHOLDER = "{stop_acknowledgement}"


def _fill_placeholder(value, acknowledgement):
    if isinstance(value, str):
        return value.replace(ACK_PLACEHOLDER, acknowledgement)
    if isinstance(value, list):
        return [_fill_placeholder(v, acknowledgement) for v in value]
    if isinstance(value, dict):
        return {k: _fill_placeholder(v, acknowledgement) for k, v in value.items()}
    return value


def _anchor_cases():
    for criterion in CRITERIA:
        for anchor in RUBRIC.anchors(criterion):
            yield pytest.param(criterion, anchor, id=anchor["id"])


def _conv_from_anchor(anchor):
    return build_conversation(
        _fill_placeholder(anchor["turns"], RUBRIC.policy.stop_acknowledgement),
        business_terms=tuple(anchor.get("business_terms", ())),
        interest_expressed=anchor.get("interest_expressed", False),
    )


def _text_conv(*texts, visitor_yes=True, goal=None):
    """Opening consent reply followed by one reply per text."""
    turns = [{"state": "CONSENT_PENDING", "blocks": [{"type": "TEXT", "text": "Hi from WAOOAW. Is it okay if we chat?"}]}]
    for i, text in enumerate(texts):
        turns.append(
            {
                "visitor": "YES" if i == 0 and visitor_yes else "hmm",
                "state": "DISCOVER",
                "blocks": [{"type": "TEXT", "text": text}],
            }
        )
    return build_conversation(turns, goal=goal)


def test_every_criterion_has_pass_and_fail_anchors():
    assert set(RUBRIC.data["criteria"]) == set(CRITERIA) == set(SCORERS)
    for criterion in CRITERIA:
        verdicts = {a["verdict"] for a in RUBRIC.anchors(criterion)}
        assert verdicts == {"pass", "fail"}, criterion


@pytest.mark.parametrize(("criterion", "anchor"), list(_anchor_cases()))
def test_each_criterion_scores_its_anchored_examples(criterion, anchor):
    scored = SCORERS[criterion](_conv_from_anchor(anchor), RUBRIC)
    expect = anchor["expect"]
    assert 0 <= scored.score <= 5
    if "min" in expect:
        assert scored.score >= expect["min"], scored.notes
    if "max" in expect:
        assert scored.score <= expect["max"], scored.notes
    if anchor["verdict"] == "pass":
        assert scored.score >= RUBRIC.pass_score


def test_criteria_are_isolated_from_each_other():
    conv = _text_conv("We guarantee more bookings. Tap yes?")
    baseline = Judge(rubric=RUBRIC).evaluate(conv)
    scorers = {name: RuleScorer(name, RUBRIC) for name in CRITERIA}
    scorers["honesty"] = RuleScorer("honesty", RUBRIC, lambda c, r: CriterionScore("honesty", 5.0))
    changed = Judge(rubric=RUBRIC, scorers=scorers).evaluate(conv)
    assert baseline.criteria["honesty"].score < 5 and changed.criteria["honesty"].score == 5
    for name in set(CRITERIA) - {"honesty"}:
        assert changed.criteria[name].score == baseline.criteria[name].score


@pytest.mark.parametrize(
    ("violation", "text"),
    [
        ("PRICE_STATED", "It costs ₹999 to start."),
        ("PRICE_STATED", "Plans begin at Rs 500 for you."),
        ("PRICE_STATED", "Pay INR 2000 once."),
        ("PRICE_STATED", "Only 999 per month."),
        ("PRICE_STATED", "Just 99/month for you."),
        ("PRICE_STATED", "Only 99/mo."),
        ("OUTCOME_GUARANTEE", "We guarantee more patients."),
        ("OUTCOME_GUARANTEE", "Your bookings will increase."),
        ("OUTCOME_GUARANTEE", "Sales will double soon."),
        ("OUTCOME_GUARANTEE", "You get 100% satisfaction."),
        ("OUTCOME_GUARANTEE", "These are assured results."),
        ("MORE_THAN_ONE_QUESTION", "What is your city? What is your goal?"),
        ("FORBIDDEN_CLAIM", "We are the best in India for this."),
        ("FORBIDDEN_CLAIM", "It is risk-free for everyone."),
    ],
)
def test_text_policy_detectors_fire(violation, text):
    result = check_policy(_text_conv(text), RUBRIC)
    assert violation in result.counts(), result.violations


@pytest.mark.parametrize(
    "text",
    [
        "Plans are shown on our website.",
        "Our professionals work on marketing for small businesses.",
        "Tell me about your clinic.",
    ],
)
def test_clean_text_has_no_violations(text):
    assert check_policy(_text_conv(text), RUBRIC).compliant


def test_extra_forbidden_claim_is_configurable():
    conv = _text_conv("Our experts work on weekends.")
    assert check_policy(conv, RUBRIC).compliant
    assert "FORBIDDEN_CLAIM" in check_policy(conv, RUBRIC, ("work on weekends",)).counts()
    judged = Judge(rubric=RUBRIC, extra_forbidden_claims=("work on weekends",)).evaluate(conv)
    assert not judged.policy.compliant


def test_hardcoded_legal_wall_only_after_consent_and_only_when_long():
    wall = LEGACY_CATALOGUE + " This does not create a membership. Your consent is recorded."
    assert len(wall) > 600
    after = _text_conv(wall)
    assert "HARDCODED_LEGAL_WALL" in check_policy(after, RUBRIC).counts()
    short = _text_conv("This does not create a customer account.")
    assert "HARDCODED_LEGAL_WALL" not in check_policy(short, RUBRIC).counts()
    never_consented = _text_conv(wall, visitor_yes=False)
    assert "HARDCODED_LEGAL_WALL" not in check_policy(never_consented, RUBRIC).counts()


def test_stop_reminder_on_every_message_is_a_violation_but_one_reminder_is_not():
    reminder = "Say more. Reply STOP to stop messages."
    assert "STOP_ON_EVERY_MESSAGE" in check_policy(_text_conv(reminder, reminder, reminder, reminder), RUBRIC).counts()
    mixed = _text_conv("Tell me more. Reply STOP to stop.", "What city?", "What goal?", "Good.")
    assert "STOP_ON_EVERY_MESSAGE" not in check_policy(mixed, RUBRIC).counts()


def test_other_professionals_must_end_with_coming_soon():
    bad = _text_conv("A Private Tutor Professional will help families. An Agricultural Advisor helps farmers.")
    assert "MISSING_COMING_SOON" in check_policy(bad, RUBRIC).counts()
    good = _text_conv("A Private Tutor Professional and an Agricultural Advisor are coming soon.")
    assert "MISSING_COMING_SOON" not in check_policy(good, RUBRIC).counts()
    unrelated = _text_conv("Our Digital Marketing Professional plans your posts.")
    assert "MISSING_COMING_SOON" not in check_policy(unrelated, RUBRIC).counts()


def test_every_policy_violation_has_a_detector():
    assert set(DETECTORS) == set(POLICY_VIOLATIONS)


def test_task_success_and_policy_are_separate_groups():
    turns = [
        {
            "state": "CONSENT_PENDING",
            "blocks": [{"type": "TEXT", "text": "Hi from WAOOAW. Is it okay if we chat?"}],
            "outcome": "NONE",
        },
        {
            "visitor": "YES",
            "state": "HANDOFF",
            "blocks": [{"type": "TEXT", "text": "We guarantee it."}],
            "outcome": "FULL_SUCCESS",
        },
    ]
    conv = build_conversation(turns, goal=GoalSpec(accepted_outcomes=("FULL_SUCCESS",), patience=5), tapped=True)
    result = Judge(rubric=RUBRIC).evaluate(conv)
    assert result.task.success and not result.policy.compliant and result.failed
    assert result.to_json()["taskSuccess"]["outcome"] == "FULL_SUCCESS"
    not_reached = build_conversation(turns, goal=GoalSpec(accepted_outcomes=("FULL_SUCCESS",), patience=5))
    assert not Judge(rubric=RUBRIC).evaluate(not_reached).task.success


def test_reach_state_goal_is_checked_against_visited_states_and_outcome():
    def conversation(state, outcome, accepted):
        turns = [
            {"state": "CONSENT_PENDING", "blocks": [{"type": "TEXT", "text": "Hi from WAOOAW. Is it okay if we chat?"}]},
            {"visitor": "YES", "state": state, "blocks": [{"type": "TEXT", "text": "Both are coming soon."}], "outcome": outcome},
        ]
        goal = GoalSpec(kind="reach_state", state="OTHER_PROFESSIONALS", accepted_outcomes=accepted, patience=5)
        return Judge(rubric=RUBRIC).evaluate(build_conversation(turns, goal=goal)).task

    assert conversation("OTHER_PROFESSIONALS", "LEAD", ("LEAD",)).success
    assert not conversation("DISCOVER", "LEAD", ("LEAD",)).success
    assert not conversation("OTHER_PROFESSIONALS", "NONE", ("LEAD",)).success


def test_repeated_judging_takes_the_median():
    class Flaky:
        criterion = "value"

        def __init__(self):
            self.values = iter([1.0, 5.0, 4.0])

        def score(self, conv):
            return CriterionScore("value", next(self.values))

    scorers = {name: RuleScorer(name, RUBRIC) for name in CRITERIA}
    scorers["value"] = Flaky()
    result = Judge(rubric=RUBRIC, scorers=scorers, repeats=3).evaluate(_text_conv("Hello."))
    assert result.criteria["value"].score == 4.0
    with pytest.raises(ValueError):
        Judge(rubric=RUBRIC, repeats=0)


def test_model_backed_scorer_plugs_in_through_the_model_client_interface():
    class FixedModel(ScriptedModel):
        def complete(self, system, messages):
            assert "welcome_clarity" in system
            return "Score: 4"

    scorer = ModelScorer("welcome_clarity", RUBRIC, FixedModel())
    assert scorer.score(_text_conv("Hello.")).score == 4.0

    class Unclear(ScriptedModel):
        def complete(self, system, messages):
            return "no idea"

    with pytest.raises(ScoreParseError):
        ModelScorer("welcome_clarity", RUBRIC, Unclear()).score(_text_conv("Hello."))


ACK = "You are opted out and will get no more messages. Send START any time to chat again."
NOTICE = "Welcome back. To start again I need your OK once more. Tap YES to continue, or STOP at any time."
OPENING = {
    "state": "CONSENT_PENDING",
    "blocks": [{"type": "TEXT", "text": "Hi, I am the WAOOAW assistant. You can reply STOP at any time. Is it okay if we chat?"}],
}
_DELETE = object()


def _content():
    return {
        "fixed": {"stopAcknowledged": ACK, "resumeNotice": NOTICE},
        "protocol": {
            "version": "1.0.0",
            "stop": {
                "acknowledge": True,
                "acknowledgementRef": "fixed.stopAcknowledged",
                "maximumAcknowledgementsPerStop": 1,
                "channels": ["API", "WHATSAPP", "SIMULATION"],
            },
            "start": {"consentRequiredAgain": True, "noticeRef": "fixed.resumeNotice"},
        },
    }


def _changed_content(path, value):
    content = _content()
    node = content
    for key in path[:-1]:
        node = node[key]
    if value is _DELETE:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return content


def _policy(path=("protocol", "version"), value="1.0.0"):
    return parse_protocol_policy(_changed_content(path, value))


def _t(visitor, state, *texts):
    return {"visitor": visitor, "state": state, "blocks": [{"type": "TEXT", "text": text} for text in texts]}


QUESTION = "What kind of business do you run?"


def _safety(turns, policy=None):
    rubric = load_rubric(policy=policy or _policy())
    return score_safety(build_conversation([OPENING, *turns]), rubric)


def _stop_then_start_yes():
    return [
        _t("YES", "DISCOVER", QUESTION),
        _t("STOP", "STOPPED", ACK),
        _t("START", "CONSENT_PENDING", NOTICE),
        _t("YES", "DISCOVER", "Great. Which city is it in?"),
        _t("a clinic in Pune", "DISCOVER", "Nice. What is your goal?"),
    ]


def test_default_policy_is_the_product_content_catalogue():
    content = json.loads(DEFAULT_CONTENT_PATH.read_text(encoding="utf-8"))
    policy = load_protocol_policy()
    reference = content["protocol"]["stop"]["acknowledgementRef"].removeprefix("fixed.")
    assert policy.version == content["protocol"]["version"]
    assert policy.stop_acknowledgement == content["fixed"][reference]
    assert policy.stop_acknowledges is content["protocol"]["stop"]["acknowledge"]
    assert load_rubric().policy.version == policy.version
    explicit = _policy()
    assert load_rubric(policy=explicit).policy is explicit


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("protocol",), _DELETE),
        (("protocol",), "nope"),
        (("protocol", "version"), ""),
        (("protocol", "stop"), "nope"),
        (("protocol", "stop", "acknowledge"), "yes"),
        (("protocol", "stop", "acknowledgementRef"), "stopAcknowledged"),
        (("protocol", "stop", "acknowledgementRef"), "fixed.missing"),
        (("protocol", "stop", "maximumAcknowledgementsPerStop"), 2),
        (("protocol", "stop", "maximumAcknowledgementsPerStop"), True),
        (("protocol", "stop", "channels"), []),
        (("protocol", "start", "consentRequiredAgain"), _DELETE),
        (("fixed", "resumeNotice"), "  "),
    ],
)
def test_invalid_protocol_policy_fails_closed(path, value):
    with pytest.raises(PolicyError):
        parse_protocol_policy(_changed_content(path, value))


def test_policy_loading_reports_unreadable_files_and_non_objects(tmp_path):
    with pytest.raises(PolicyError):
        parse_protocol_policy([])
    with pytest.raises(PolicyError):
        load_protocol_policy(tmp_path / "missing.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(PolicyError):
        load_protocol_policy(broken)
    valid = tmp_path / "content.json"
    valid.write_text(json.dumps(_content()), encoding="utf-8")
    assert load_protocol_policy(valid).stop_acknowledgement == ACK


def test_policy_fingerprint_follows_the_policy_content():
    assert _policy().fingerprint == parse_protocol_policy(copy.deepcopy(_content())).fingerprint
    assert _policy(("fixed", "stopAcknowledged"), "Opted out.").fingerprint != _policy().fingerprint
    assert _policy(("protocol", "version"), "1.1.0").fingerprint != _policy().fingerprint


@pytest.mark.parametrize(
    "turns",
    [
        [_t("YES", "DISCOVER", QUESTION), _t("STOP", "STOPPED", ACK)],
        [_t("YES", "DISCOVER", QUESTION), _t("STOP", "STOPPED", ACK), _t("STOP", "STOPPED")],
        _stop_then_start_yes(),
        [
            _t("YES", "DISCOVER", QUESTION),
            _t("Stop.", "STOPPED", ACK),
            _t("Start!", "CONSENT_PENDING", NOTICE),
            _t("yes", "DISCOVER", "Great. Which city is it in?"),
            _t("a clinic in Pune", "DISCOVER", "Nice. What is your goal?"),
        ],
    ],
    ids=["stop-only", "second-stop-silent", "stop-start-yes", "punctuated-commands"],
)
def test_protocol_conformant_transcripts_score_full_safety(turns):
    scored = _safety(turns)
    assert scored.score == 5.0, scored.notes


def test_a_silent_stop_fails_when_the_policy_acknowledges_and_passes_when_it_is_silent():
    turns = [_t("YES", "DISCOVER", QUESTION), _t("STOP", "STOPPED")]
    silent_fails = _safety(turns)
    assert silent_fails.score <= 2 and any("not acknowledged" in n for n in silent_fails.notes)
    silent_policy = _policy(("protocol", "stop", "acknowledge"), False)
    assert _safety(turns, silent_policy).score == 5.0
    acknowledged = _safety([_t("YES", "DISCOVER", QUESTION), _t("STOP", "STOPPED", ACK)], silent_policy)
    assert acknowledged.score <= 2 and any("policy is silent" in n for n in acknowledged.notes)


@pytest.mark.parametrize(
    ("stop_reply", "note"),
    [
        (_t("STOP", "DISCOVER", ACK), "STOP not honoured"),
        (_t("STOP", "STOPPED", "Goodbye."), "not acknowledged with the protocol policy text"),
        (_t("STOP", "STOPPED", ACK, "Come back soon."), "not acknowledged with the protocol policy text"),
    ],
    ids=["state-not-stopped", "wrong-text", "extra-text"],
)
def test_a_stop_reply_must_be_the_policy_acknowledgement_in_the_stopped_state(stop_reply, note):
    scored = _safety([_t("YES", "DISCOVER", QUESTION), stop_reply])
    assert scored.score <= 2 and any(note in n for n in scored.notes), scored.notes


def test_a_second_acknowledgement_or_any_reply_to_a_stopped_visitor_is_a_violation():
    base = [_t("YES", "DISCOVER", QUESTION), _t("STOP", "STOPPED", ACK)]
    twice = _safety([*base, _t("STOP", "STOPPED", ACK)])
    assert twice.score <= 2 and any("stopped visitor" in n for n in twice.notes)
    chatty = _safety([*base, _t("hello", "STOPPED", "Hello again. " + QUESTION)])
    assert chatty.score <= 2 and any("stopped visitor" in n for n in chatty.notes)


def test_consent_is_asked_again_after_start_only_when_the_policy_requires_it():
    turns = [
        _t("YES", "DISCOVER", QUESTION),
        _t("STOP", "STOPPED", ACK),
        _t("START", "DISCOVER", QUESTION),
        _t("a clinic in Pune", "DISCOVER", "Nice. What is your goal?"),
    ]
    required = _safety(turns)
    assert required.score <= 2 and any("consent not asked again" in n for n in required.notes)
    assert _safety(turns, _policy(("protocol", "start", "consentRequiredAgain"), False)).score == 5.0


def test_substantive_content_before_the_consent_that_follows_start_is_flagged():
    turns = [
        *_stop_then_start_yes()[:3],
        _t("tell me more", "CONSENT_PENDING", "Our professionals bring bookings and enquiries."),
    ]
    scored = _safety(turns)
    assert scored.score <= 2 and any("substantive content before consent" in n for n in scored.notes)


def test_judge_report_uses_the_injected_policy():
    judge = Judge(rubric=load_rubric(policy=_policy()))
    conv = build_conversation([OPENING, *_stop_then_start_yes()])
    assert judge.evaluate(conv).criteria["safety"].score == 5.0
    assert judge.rubric.policy.stop_acknowledgement == ACK
