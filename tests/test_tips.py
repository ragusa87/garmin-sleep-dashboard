from dataclasses import replace

from garmin_sleep.analysis import Analysis
from garmin_sleep.metrics import CorrRow
from garmin_sleep.tips import (
    generate_tips,
    rule_activity_helps,
    rule_alcohol_like,
    rule_evening_stress,
    rule_frequent_awakenings,
    rule_garmin_feedback,
    rule_irregular_bedtime,
    rule_late_bedtime,
    rule_low_deep,
    rule_low_rem,
    rule_low_spo2,
    rule_short_sleep,
    rule_social_jetlag,
)


def make_analysis(**overrides) -> Analysis:
    """Analysis « saine » : aucune règle ne doit se déclencher."""
    defaults = dict(
        tz_name="Europe/Zurich",
        nights=[],
        night_rows=[],
        trend_total_h_7d=[],
        trend_total_h_30d=[],
        trend_score_7d=[],
        trend_score_30d=[],
        weekday=[],
        correlations=[],
        feedback_freq={},
        hr_elevation=[],
        bedtime_std_min=30.0,
        social_jetlag_min=20.0,
        median_bedtime_offset_min=300.0,  # 23:00
        avg_total_h_30d=7.5,
        avg_score=80.0,
        avg_deep_pct=18.0,
        avg_rem_pct=22.0,
        avg_awake_pct=5.0,
        avg_awake_count=1.0,
        avg_sleep_stress=15.0,
        avg_spo2=95.0,
        low_spo2_night_share=0.02,
        elevated_hr_share=0.05,
    )
    defaults.update(overrides)
    return Analysis(**defaults)


def test_healthy_analysis_triggers_nothing():
    assert generate_tips(make_analysis()) == []


def test_rule_short_sleep():
    assert rule_short_sleep(make_analysis()) is None
    tip = rule_short_sleep(make_analysis(avg_total_h_30d=6.4))
    assert tip is not None and tip.priority == 1
    assert "6 h 24" in tip.evidence["Durée moyenne (30 j)"]


def test_rule_late_bedtime():
    assert rule_late_bedtime(make_analysis()) is None
    tip = rule_late_bedtime(make_analysis(median_bedtime_offset_min=390.0))  # 00:30
    assert tip is not None
    assert tip.evidence["Coucher médian"] == "00:30"


def test_rule_irregular_bedtime():
    assert rule_irregular_bedtime(make_analysis()) is None
    assert rule_irregular_bedtime(make_analysis(bedtime_std_min=70.0)) is not None


def test_rule_stage_percentages():
    assert rule_low_deep(make_analysis()) is None
    assert rule_low_deep(make_analysis(avg_deep_pct=10.0)) is not None
    assert rule_low_rem(make_analysis()) is None
    assert rule_low_rem(make_analysis(avg_rem_pct=12.0)) is not None
    assert rule_low_rem(make_analysis(avg_rem_pct=None)) is None  # pas de données REM


def test_rule_frequent_awakenings():
    assert rule_frequent_awakenings(make_analysis()) is None
    assert rule_frequent_awakenings(make_analysis(avg_awake_count=3.0)) is not None
    assert rule_frequent_awakenings(make_analysis(avg_awake_pct=15.0)) is not None


def test_rule_low_spo2():
    assert rule_low_spo2(make_analysis()) is None
    assert rule_low_spo2(make_analysis(avg_spo2=90.0)) is not None
    assert rule_low_spo2(make_analysis(low_spo2_night_share=0.2)) is not None


def test_rule_alcohol_like():
    assert rule_alcohol_like(make_analysis()) is None
    assert rule_alcohol_like(make_analysis(elevated_hr_share=0.3)) is not None


def test_rule_social_jetlag():
    assert rule_social_jetlag(make_analysis()) is None
    assert rule_social_jetlag(make_analysis(social_jetlag_min=90.0)) is not None


def test_rule_evening_stress():
    assert rule_evening_stress(make_analysis()) is None
    assert rule_evening_stress(make_analysis(avg_sleep_stress=30.0)) is not None
    corr = [CorrRow(variable="avg_stress", target="score", lag="prev_day", r=-0.4, n=30)]
    tip = rule_evening_stress(make_analysis(correlations=corr))
    assert tip is not None
    assert "r = -0.40" in tip.evidence["Corrélation stress journée → score"]


def test_rule_activity_helps():
    assert rule_activity_helps(make_analysis()) is None
    corr = [CorrRow(variable="steps", target="score", lag="prev_day", r=0.35, n=40)]
    assert rule_activity_helps(make_analysis(correlations=corr)) is not None


def test_rule_garmin_feedback():
    assert rule_garmin_feedback(make_analysis()) is None
    tip = rule_garmin_feedback(
        make_analysis(feedback_freq={"NEGATIVE_NOT_ENOUGH_REM": 0.4, "POSITIVE_DEEP": 0.5})
    )
    assert tip is not None
    assert any("40 %" in v for v in tip.evidence.values())


def test_tips_sorted_by_priority():
    tips = generate_tips(
        make_analysis(avg_total_h_30d=6.0, social_jetlag_min=90.0, bedtime_std_min=70.0)
    )
    priorities = [t.priority for t in tips]
    assert priorities == sorted(priorities)
    assert tips[0].id == "short_sleep"


def test_rule_spo2_worsening():
    from garmin_sleep.tips import rule_spo2_worsening

    assert rule_spo2_worsening(make_analysis()) is None  # pas de données
    healthy = make_analysis(
        spo2_low_share_recent=0.3, spo2_low_share_prev=0.25, spo2_n_recent=20, spo2_n_prev=20
    )
    assert rule_spo2_worsening(healthy) is None  # +5 pts : pas significatif
    small_n = make_analysis(
        spo2_low_share_recent=0.6, spo2_low_share_prev=0.2, spo2_n_recent=5, spo2_n_prev=20
    )
    assert rule_spo2_worsening(small_n) is None  # trop peu de nuits mesurées
    tip = rule_spo2_worsening(
        make_analysis(
            spo2_low_share_recent=0.5, spo2_low_share_prev=0.2, spo2_n_recent=20, spo2_n_prev=15
        )
    )
    assert tip is not None and tip.priority == 1
    assert "50 % (n = 20)" in tip.evidence["Nuits < 85 % (30 derniers j)"]
