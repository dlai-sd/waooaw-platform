# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
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
)
from visitor_simulation.models import GoalSpec, build_conversation

RUBRIC = load_rubric()


def _anchor_cases():
    for criterion in CRITERIA:
        for anchor in RUBRIC.anchors(criterion):
            yield pytest.param(criterion, anchor, id=anchor["id"])


def _conv_from_anchor(anchor):
    return build_conversation(
        anchor["turns"],
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
