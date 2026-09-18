from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OFFICE_CARD = ROOT / ".github/agent-context/office-platform-it-expert.md"


def test_platform_it_story_commentary_declares_ordered_boundaries() -> None:
    source = OFFICE_CARD.read_text(encoding="utf-8")

    section = source.index("## Story Commentary Boundaries")
    start = source.index("`START <story-id>: <intended outcome>`", section)
    end = source.index("`END <story-id>: <evidence summary>; blockers: <none or blocker>`", start)
    before_end = source[section:end].lower()
    after_end = source[end:].lower()

    assert "before story execution begins" in before_end
    assert "after completing or stopping the story" in before_end
    assert "before starting another story" in after_end
    assert start < end
