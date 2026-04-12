"""
Tests for app.orchestrator.scene — SessionController.render() and NSFW gating.

Covers all five cases from the Phase 5 verification matrix and additional
edge cases for mood rendering and escalation pace.
"""
from app.models.relationship import ClosenessLevel
from app.orchestrator.scene import EscalationPace, SessionController


def _make_scene(
    level: int,
    adult: bool,
    mood: str = "neutral",
    nsfw_eligible: bool = None,
    pace: EscalationPace = EscalationPace.HOLD,
) -> SessionController:
    if nsfw_eligible is None:
        nsfw_eligible = level >= int(ClosenessLevel.INTIMATE)
    return SessionController(
        closeness=ClosenessLevel(level),
        adult_enabled=adult,
        nsfw_eligible=nsfw_eligible,
        current_mood=mood,
        escalation_pace=pace,
        current_topic=None,
    )


# ---------------------------------------------------------------------------
# NSFW gate — three conditions must all pass
# ---------------------------------------------------------------------------

class TestNSFWGate:
    """Verify the strict three-gate NSFW check."""

    def test_new_adult_false_gate_fails(self):
        # Case 1: NEW + adult false
        r = _make_scene(1, False).render()
        assert "not permitted" in r
        assert "Adult content: enabled" not in r

    def test_familiar_adult_false_gate_fails(self):
        # Case 2: FAMILIAR + adult false
        r = _make_scene(2, False).render()
        assert "not permitted" in r

    def test_close_adult_false_gate_fails(self):
        r = _make_scene(3, False).render()
        assert "not permitted" in r

    def test_intimate_adult_false_gate_fails(self):
        # Case 4: INTIMATE but adult disabled — must still be prohibited
        r = _make_scene(4, False).render()
        assert "not permitted" in r
        assert "Adult content: enabled" not in r

    def test_intimate_adult_true_nsfw_eligible_gate_passes(self):
        # Case 5: all three gates pass
        r = _make_scene(4, True, nsfw_eligible=True).render()
        assert "Adult content: enabled" in r
        assert "not permitted" not in r

    def test_intimate_adult_true_nsfw_not_eligible_gate_fails(self):
        # nsfw_eligible explicitly False despite adult+INTIMATE — gate must fail
        r = _make_scene(4, True, nsfw_eligible=False).render()
        assert "not permitted" in r
        assert "Adult content: enabled" not in r

    def test_no_unprompted_instruction_when_gate_passes(self):
        # Even when enabled, must not instruct model to open with explicit content
        r = _make_scene(4, True).render()
        assert "unprompted" in r


# ---------------------------------------------------------------------------
# Closeness-level behavioral instructions
# ---------------------------------------------------------------------------

class TestClosenessInstructions:
    def test_new_includes_no_flirt(self):
        r = _make_scene(1, False).render()
        assert "Do not flirt" in r

    def test_new_includes_distance_language(self):
        r = _make_scene(1, False).render()
        assert "distance" in r.lower() or "beginning" in r.lower()

    def test_familiar_mentions_playfulness(self):
        r = _make_scene(2, False).render()
        lower = r.lower()
        assert "playful" in lower or "teasing" in lower

    def test_close_mentions_warmth(self):
        r = _make_scene(3, False).render()
        lower = r.lower()
        assert "warm" in lower or "close" in lower

    def test_intimate_mentions_romantic_connection(self):
        r = _make_scene(4, False).render()
        lower = r.lower()
        assert "romantic" in lower or "deeply" in lower or "intimate" in lower.replace("not permitted", "")


# ---------------------------------------------------------------------------
# Mood rendering
# ---------------------------------------------------------------------------

class TestMoodRendering:
    def test_heavy_mood_renders(self):
        # Case 3: CLOSE + heavy mood
        r = _make_scene(3, False, mood="heavy").render()
        assert "heavy" in r.lower()
        assert "grounding" in r.lower()

    def test_playful_mood_renders(self):
        r = _make_scene(2, False, mood="playful").render()
        assert "playful" in r.lower()

    def test_warm_mood_renders(self):
        r = _make_scene(2, False, mood="warm").render()
        assert "warm" in r.lower()

    def test_neutral_mood_produces_no_mood_line(self):
        r = _make_scene(2, False, mood="neutral").render()
        assert "Mood right now" not in r

    def test_unknown_mood_produces_no_mood_line(self):
        r = _make_scene(2, False, mood="confused").render()
        assert "Mood right now" not in r


# ---------------------------------------------------------------------------
# Escalation pace rendering
# ---------------------------------------------------------------------------

class TestEscalationPace:
    def test_increase_pace_renders_instruction(self):
        r = _make_scene(4, True, pace=EscalationPace.INCREASE).render()
        assert "gradual intimacy" in r.lower()

    def test_decrease_pace_renders_instruction(self):
        r = _make_scene(3, False, pace=EscalationPace.DECREASE).render()
        assert "pull back" in r.lower()

    def test_hold_pace_renders_no_pace_instruction(self):
        r = _make_scene(2, False, pace=EscalationPace.HOLD).render()
        assert "gradual intimacy" not in r.lower()
        assert "pull back" not in r.lower()
