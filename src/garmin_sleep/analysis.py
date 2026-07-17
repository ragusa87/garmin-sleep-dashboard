"""Orchestration : ExportData -> objet Analysis unique pour conseils et rapport."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from . import metrics
from .metrics import CorrRow, MonthlySpo2, NightMetrics, WeekdayStats
from .models import ExportData, SleepNight


@dataclass(frozen=True)
class Analysis:
    tz_name: str
    nights: list[SleepNight]
    night_rows: list[NightMetrics]
    trend_total_h_7d: list[tuple[date, float]]
    trend_total_h_30d: list[tuple[date, float]]
    trend_score_7d: list[tuple[date, float]]
    trend_score_30d: list[tuple[date, float]]
    weekday: list[WeekdayStats]
    correlations: list[CorrRow]
    feedback_freq: dict[str, float]
    hr_elevation: list[tuple[date, float]]
    bedtime_std_min: float | None
    social_jetlag_min: float | None
    median_bedtime_offset_min: float | None
    avg_total_h_30d: float | None  # moyenne des 30 derniers jours
    avg_score: float | None
    avg_deep_pct: float | None
    avg_rem_pct: float | None
    avg_awake_pct: float | None
    avg_awake_count: float | None
    avg_sleep_stress: float | None
    avg_spo2: float | None
    low_spo2_night_share: float | None  # part de nuits avec SpO2 min < 85
    elevated_hr_share: float | None  # part de nuits avec FC nocturne >= baseline+8
    monthly_spo2: list[MonthlySpo2] = field(default_factory=list)
    spo2_low_share_recent: float | None = None  # nuits < 85 %, 30 derniers jours
    spo2_low_share_prev: float | None = None  # nuits < 85 %, 30 jours précédents
    spo2_n_recent: int = 0
    spo2_n_prev: int = 0


def _mean_or_none(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def analyze(export: ExportData, tz: ZoneInfo, days_limit: int | None = None) -> Analysis:
    nights = export.nights
    if days_limit and nights:
        cutoff = nights[-1].calendar_date - timedelta(days=days_limit - 1)
        nights = [n for n in nights if n.calendar_date >= cutoff]

    rows = [metrics.night_metrics(n, tz) for n in nights]

    total_series = [(r.calendar_date, r.total_h) for r in rows]
    score_series = [
        (n.calendar_date, float(n.scores.overall))
        for n in nights
        if n.scores and n.scores.overall is not None
    ]

    last_date = nights[-1].calendar_date if nights else None
    recent = (
        [r.total_h for r in rows if r.calendar_date >= last_date - timedelta(days=29)]
        if last_date
        else []
    )

    bedtimes = [metrics.bedtime_offset_min(r.bedtime_local) for r in rows]
    hr_elev = metrics.sleep_hr_elevation(nights, export.days)

    spo2_nights = [n for n in nights if n.lowest_spo2 is not None]

    spo2_recent = spo2_prev = None
    n_recent = n_prev = 0
    if last_date:
        spo2_recent, n_recent = metrics.low_spo2_share(
            nights, last_date - timedelta(days=29), last_date
        )
        spo2_prev, n_prev = metrics.low_spo2_share(
            nights, last_date - timedelta(days=59), last_date - timedelta(days=30)
        )

    return Analysis(
        tz_name=str(tz),
        nights=nights,
        night_rows=rows,
        trend_total_h_7d=metrics.rolling_mean(total_series, 7),
        trend_total_h_30d=metrics.rolling_mean(total_series, 30),
        trend_score_7d=metrics.rolling_mean(score_series, 7),
        trend_score_30d=metrics.rolling_mean(score_series, 30),
        weekday=metrics.weekday_profile(nights, tz),
        correlations=metrics.correlate(nights, export.days),
        feedback_freq=metrics.feedback_frequencies(nights),
        hr_elevation=hr_elev,
        bedtime_std_min=metrics.bedtime_std_minutes(nights, tz),
        social_jetlag_min=metrics.social_jetlag_min(nights, tz),
        median_bedtime_offset_min=statistics.median(bedtimes) if bedtimes else None,
        avg_total_h_30d=_mean_or_none(recent),
        avg_score=_mean_or_none([s for _, s in score_series]),
        avg_deep_pct=_mean_or_none([r.deep_pct for r in rows if r.deep_pct is not None]),
        avg_rem_pct=_mean_or_none([r.rem_pct for r in rows if r.rem_pct is not None]),
        avg_awake_pct=_mean_or_none([r.awake_pct for r in rows if r.awake_pct is not None]),
        avg_awake_count=_mean_or_none(
            [float(n.awake_count) for n in nights if n.awake_count is not None]
        ),
        avg_sleep_stress=_mean_or_none(
            [n.avg_sleep_stress for n in nights if n.avg_sleep_stress is not None]
        ),
        avg_spo2=_mean_or_none([n.avg_spo2 for n in nights if n.avg_spo2 is not None]),
        low_spo2_night_share=(
            sum(1 for n in spo2_nights if n.lowest_spo2 < 85) / len(spo2_nights)
            if spo2_nights
            else None
        ),
        elevated_hr_share=(
            sum(1 for _, e in hr_elev if e >= 8) / len(hr_elev) if hr_elev else None
        ),
        monthly_spo2=metrics.monthly_spo2(nights),
        spo2_low_share_recent=spo2_recent,
        spo2_low_share_prev=spo2_prev,
        spo2_n_recent=n_recent,
        spo2_n_prev=n_prev,
    )
