import pytest
from streaming.metrics import (
    match_second, match_minute_label,
    is_shot, is_goal, is_attacking, safe_xg, win_probability,
)

def test_match_second_kickoff(): assert match_second(0, 0) == 0
def test_match_second_mid(): assert match_second(1, 30) == 90
def test_match_second_extra_time(): assert match_second(105, 10) == 6310
def test_match_second_p2_overtakes_p1():
    assert match_second(60, 0) > match_second(52, 0)
def test_label_normal(): assert match_minute_label(32, 2) == "32"
def test_label_stoppage_p1(): assert match_minute_label(47, 1) == "45+2"
def test_label_stoppage_p2(): assert match_minute_label(93, 2) == "90+3"
def test_label_extra_time(): assert match_minute_label(96, 3) == "90+6"
def test_is_shot_true(): assert is_shot("Shot") is True
def test_is_shot_false(): assert is_shot("Pass") is False
def test_is_goal_true(): assert is_goal("Shot", "Goal") is True
def test_is_goal_saved(): assert is_goal("Shot", "Saved") is False
def test_is_goal_non_shot(): assert is_goal("Pass", None) is False
def test_is_attacking_shot(): assert is_attacking("Shot") is True
def test_is_attacking_carry(): assert is_attacking("Carry") is True
def test_is_attacking_foul(): assert is_attacking("Foul Committed") is False
def test_safe_xg_normal(): assert safe_xg(0.24) == pytest.approx(0.24)
def test_safe_xg_none(): assert safe_xg(None) == 0.0
def test_safe_xg_negative(): assert safe_xg(-0.01) == 0.0
def test_win_prob_level(): assert win_probability(0, 0.0, 45) == pytest.approx(0.5, abs=0.001)
def test_win_prob_leading(): assert win_probability(1, 0.5, 45) > 0.5
def test_win_prob_trailing_late(): assert win_probability(-1, -0.5, 5) < 0.3
def test_win_prob_bounded():
    for d in [-3, -1, 0, 1, 3]:
        assert 0.0 <= win_probability(d, float(d) * 0.3, 45) <= 1.0
