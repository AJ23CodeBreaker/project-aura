"""
Tests for app.dialogue.signals — TurnSignal classifier.

Covers all cases from the Phase 5 verification matrix:
  - conflict phrases → conflict=True, positive=False
  - warmth phrases → positive=True, conflict=False
  - neutral phrases → both False
  - conflict takes priority when both patterns match
"""
from app.dialogue.signals import TurnSignal, classify_turn


class TestConflictSignals:
    def test_leave_me_alone(self):
        s = classify_turn("leave me alone")
        assert s.conflict is True
        assert s.positive is False

    def test_stop_it(self):
        s = classify_turn("stop it")
        assert s.conflict is True
        assert s.positive is False

    def test_please_stop(self):
        s = classify_turn("please stop")
        assert s.conflict is True

    def test_go_away(self):
        s = classify_turn("go away")
        assert s.conflict is True

    def test_dont_do_that(self):
        s = classify_turn("don't do that")
        assert s.conflict is True

    def test_thats_not_okay(self):
        s = classify_turn("that's not okay")
        assert s.conflict is True

    def test_case_insensitive(self):
        s = classify_turn("LEAVE ME ALONE")
        assert s.conflict is True


class TestPositiveSignals:
    def test_thank_you(self):
        s = classify_turn("thank you so much")
        assert s.positive is True
        assert s.conflict is False

    def test_thanks(self):
        s = classify_turn("Thanks, I appreciate that.")
        assert s.positive is True

    def test_enjoy_talking(self):
        s = classify_turn("I enjoy talking with you")
        assert s.positive is True

    def test_love_chatting(self):
        s = classify_turn("I love chatting with you")
        assert s.positive is True

    def test_means_a_lot(self):
        s = classify_turn("this really means a lot to me")
        assert s.positive is True

    def test_youre_wonderful(self):
        s = classify_turn("you're wonderful")
        assert s.positive is True


class TestNeutralSignals:
    def test_generic_question(self):
        s = classify_turn("how was your day")
        assert s.positive is False
        assert s.conflict is False

    def test_neutral_statement(self):
        s = classify_turn("I went to the store today")
        assert s.positive is False
        assert s.conflict is False

    def test_empty_string(self):
        s = classify_turn("")
        assert s.positive is False
        assert s.conflict is False


class TestConflictPriority:
    def test_conflict_beats_positive_in_same_message(self):
        # Boundary + warmth in the same message — conflict must win
        s = classify_turn("I love you but please stop doing that")
        assert s.conflict is True
        assert s.positive is False
