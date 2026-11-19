# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
import re
import pytest
import yaml

from visitor_simulation.client import VisitorClient
from visitor_simulation.customer import (
    CostCapExceeded,
    CustomerSimulator,
    HttpModelClient,
    ModelNotConfigured,
    RunBudget,
    ScriptedModel,
    TurnCapExceeded,
    best_option,
    extract_reference,
)
from visitor_simulation.fake_server import FakeVisitorServer
from visitor_simulation.models import Block, Choice, Reply
from visitor_simulation.personas import PERSONAS_PATH, PersonaError, load_personas, select_personas
from visitor_simulation.runner import run_conversation

PERSONAS = load_personas()
EXPECTED_IDS = {"dr_mehta", "rupali", "kiran", "yashus", "farmer", "tutor_seeker", "trader"}


def _reply(state, *blocks):
    return Reply(state=state, blocks=tuple(blocks))


def _text(value):
    return Block(type="TEXT", text=value)


def _choices(*pairs):
    return Block(type="CHOICES", choices=tuple(Choice(i, label) for i, label in pairs))


def test_seven_fabricated_personas_with_the_required_fields():
    assert set(PERSONAS) == EXPECTED_IDS
    assert PERSONAS["dr_mehta"].city == "Pune" and PERSONAS["kiran"].city == "Bangalore" and PERSONAS["yashus"].city == "Mumbai"
    for persona in PERSONAS.values():
        assert persona.knowledge_of_waooaw == "nothing" and persona.mood and persona.intent
        assert persona.patience >= 3 and persona.subject_prefix.startswith("sim-")
        assert set(persona.modes) <= {"normal", "skeptic", "overwhelmed"}
    assert sum(1 for p in PERSONAS.values() if p.unknown_language_message != PERSONAS["kiran"].unknown_language_message) == 1


def test_persona_file_holds_no_real_looking_contact_data():
    text = PERSONAS_PATH.read_text(encoding="utf-8")
    assert "@" not in text and not re.search(r"\+?\d[\d\s-]{8,}\d", text)


def test_persona_validation_rejects_bad_entries(tmp_path):
    data = yaml.safe_load(PERSONAS_PATH.read_text(encoding="utf-8"))
    data["personas"][0]["patience"] = 1
    bad = tmp_path / "personas.yaml"
    bad.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(PersonaError):
        load_personas(bad)
    with pytest.raises(PersonaError):
        select_personas(["nobody"])
    assert [p.id for p in select_personas(["kiran", "rupali"])] == ["kiran", "rupali"]


def test_best_option_matches_goal_keyword_then_falls_back_to_something_else():
    options = (
        Choice("BOOKINGS", "More bookings"),
        Choice("ENQUIRIES", "More enquiries"),
        Choice("SIGNUPS", "More sign-ups"),
        Choice("NEW_CLIENTS", "More new clients"),
        Choice("OTHER", "Something else"),
    )
    assert best_option(options, "bookings").id == "BOOKINGS"
    assert best_option(options, "sign-ups").id == "SIGNUPS"
    assert best_option(options, "clients").id == "NEW_CLIENTS"
    assert best_option(options, "farming").id == "OTHER"
    assert best_option((), "bookings") is None


def test_extract_reference_reads_the_opaque_reference_only():
    assert extract_reference("https://portal.fake.invalid/trial?ref=abc.123") == "abc.123"
    assert extract_reference("https://portal.fake.invalid/h/abc123") == "abc123"
    assert extract_reference("https://api.fake.invalid/api/v1/visitor/handoffs/abc123/open") == "abc123"


def test_simulator_consent_skeptic_and_tap_behaviour():
    consent = _reply(
        "CONSENT_PENDING", _text("Hi. Is it okay if we chat?"), _choices(("YES", "Yes, let's talk"), ("STOP", "Stop"))
    )
    taps = CustomerSimulator(PERSONAS["dr_mehta"])
    action = taps.next_action(consent)
    assert (action.kind, action.choice_id) == ("CHOICE", "YES")

    types = CustomerSimulator(PERSONAS["kiran"])
    assert (types.next_action(consent).kind, types.turns) == ("TEXT", 1)

    skeptic = CustomerSimulator(PERSONAS["yashus"], mode="skeptic")
    first = skeptic.next_action(consent)
    assert first.text == "Is this just ChatGPT?"
    assert skeptic.next_action(consent).choice_id == "" and skeptic.consented

    link = Block(type="LINK", label="Start your trial", url="https://portal.fake.invalid/trial?ref=r1")
    handoff = _reply("HANDOFF", _text("Tap the button."), link)
    tap = CustomerSimulator(PERSONAS["dr_mehta"]).next_action(handoff)
    assert (tap.kind, tap.reference) == ("TAP", "r1")


def test_overwhelmed_persona_withholds_until_asked_twice_and_then_gives_up_with_stop():
    sim = CustomerSimulator(PERSONAS["rupali"], mode="overwhelmed")
    sim.consented = True
    ask = _reply("DISCOVER", _text("What kind of business do you run, and in which city?"))
    assert "small business" in sim.next_action(ask).text
    assert "solo beauty artist" in sim.next_action(ask).text
    assert sim.patience == 10
    sim.turns = sim.patience
    assert sim.next_action(ask).text == "STOP"
    assert sim.next_action(_reply("STOPPED")).kind == "END"


def test_patient_persona_leaves_quietly_when_patience_is_exhausted():
    sim = CustomerSimulator(PERSONAS["kiran"])
    sim.consented = True
    sim.turns = sim.patience
    action = sim.next_action(_reply("DISCOVER", _text("Hello.")))
    assert (action.kind, action.reason) == ("END", "patience_exhausted")


def test_turn_cap_is_enforced():
    budget = RunBudget(max_turns_per_conversation=2)
    sim = CustomerSimulator(PERSONAS["kiran"], budget=budget)
    nothing = _reply("DISCOVER", _text("Welcome."))
    sim.next_action(nothing)
    sim.next_action(nothing)
    with pytest.raises(TurnCapExceeded):
        sim.next_action(nothing)
    assert issubclass(TurnCapExceeded, CostCapExceeded)
    total = RunBudget(max_total_turns=1)
    total.charge_turn()
    with pytest.raises(TurnCapExceeded):
        total.charge_turn()


def test_model_call_cap_is_enforced_through_the_budget():
    budget = RunBudget(max_model_calls=2)
    sim = CustomerSimulator(PERSONAS["kiran"], model=ScriptedModel(1), budget=budget)
    nothing = _reply("DISCOVER", _text("Welcome."))
    sim.next_action(nothing)
    sim.next_action(nothing)
    with pytest.raises(CostCapExceeded):
        sim.next_action(nothing)
    assert budget.model_calls == 2


def test_scripted_model_is_deterministic_and_http_model_needs_configuration(monkeypatch):
    first = [ScriptedModel(7).complete("s", [{"role": "user", "content": "SAY: Hello there."}]) for _ in range(2)]
    assert first[0] == first[1] and first[0].endswith("Hello there.")
    monkeypatch.delenv(HttpModelClient.ENDPOINT_ENV, raising=False)
    monkeypatch.delenv(HttpModelClient.KEY_ENV, raising=False)
    with pytest.raises(ModelNotConfigured):
        HttpModelClient()
    monkeypatch.setenv(HttpModelClient.ENDPOINT_ENV, "http://plain.invalid/model")
    monkeypatch.setenv(HttpModelClient.KEY_ENV, "fabricated-key")
    with pytest.raises(ModelNotConfigured):
        HttpModelClient()


@pytest.mark.parametrize("persona_id", sorted(EXPECTED_IDS))
def test_same_seed_gives_an_identical_transcript(secret, persona_id):
    persona = PERSONAS[persona_id]

    def play():
        with FakeVisitorServer("good", secret) as server:
            client = VisitorClient(server.base_url, secret, sleep=lambda _: None)
            return run_conversation(
                client, persona, mode=persona.modes[-1], seed=42, subject_key="sim-determinism-001", model=ScriptedModel(42)
            )

    first, second = play(), play()
    assert first.transcript_signature() == second.transcript_signature()
    assert first.visitor_turns >= 3


def test_different_seeds_vary_the_wording(good_server, secret):
    client = VisitorClient(good_server.base_url, secret, sleep=lambda _: None)
    persona = PERSONAS["dr_mehta"]
    texts = {
        tuple(
            t.visitor_text
            for t in run_conversation(
                client, persona, mode="normal", seed=s, subject_key=f"sim-variety-{s:03d}", model=ScriptedModel(s)
            ).turns
        )
        for s in range(1, 9)
    }
    assert len(texts) > 1


def test_run_conversation_enforces_turn_cap_against_a_server(legacy_server, secret):
    client = VisitorClient(legacy_server.base_url, secret, sleep=lambda _: None)
    with pytest.raises(TurnCapExceeded):
        run_conversation(
            client,
            PERSONAS["yashus"],
            mode="normal",
            seed=1,
            subject_key="sim-cap-001",
            budget=RunBudget(max_turns_per_conversation=3),
        )
