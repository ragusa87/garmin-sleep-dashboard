"""Fonctions pures de calcul de métriques du sommeil."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from .models import DailySummary, SleepNight


@dataclass(frozen=True)
class NightMetrics:
    calendar_date: date
    total_h: float
    deep_pct: float | None
    light_pct: float | None
    rem_pct: float | None
    awake_pct: float | None
    efficiency: float | None
    bedtime_local: datetime
    wake_local: datetime
    midsleep_local: datetime


def night_metrics(n: SleepNight, tz: ZoneInfo) -> NightMetrics:
    total = n.total_sleep_s
    # dénominateur = sommeil mesuré ; REM exclu s'il n'est pas mesuré
    deep_pct = light_pct = rem_pct = None
    if total > 0:
        deep_pct = 100 * n.deep_s / total
        light_pct = 100 * n.light_s / total
        if n.rem_s is not None:
            rem_pct = 100 * n.rem_s / total
    awake_pct = 100 * n.awake_s / n.in_bed_s if n.in_bed_s > 0 else None
    bedtime = n.start_gmt.astimezone(tz)
    wake = n.end_gmt.astimezone(tz)
    return NightMetrics(
        calendar_date=n.calendar_date,
        total_h=total / 3600,
        deep_pct=deep_pct,
        light_pct=light_pct,
        rem_pct=rem_pct,
        awake_pct=awake_pct,
        efficiency=n.efficiency,
        bedtime_local=bedtime,
        wake_local=wake,
        midsleep_local=bedtime + (wake - bedtime) / 2,
    )


def bedtime_offset_min(bedtime_local: datetime) -> float:
    """Minutes écoulées depuis 18:00 — rend 23:30 et 00:30 adjacents (axe circulaire).

    Résultat dans [0, 1440) : 18:00 -> 0, minuit -> 360, 06:00 -> 720.
    """
    minutes = bedtime_local.hour * 60 + bedtime_local.minute + bedtime_local.second / 60
    return (minutes - 18 * 60) % 1440


def rolling_mean(
    series: list[tuple[date, float]], window_days: int
) -> list[tuple[date, float]]:
    """Moyenne glissante sur fenêtre calendaire (pas sur nombre de points)."""
    out = []
    values = sorted(series)
    for i, (d, _) in enumerate(values):
        lo = d - timedelta(days=window_days - 1)
        window = [v for dd, v in values[: i + 1] if dd >= lo]
        out.append((d, sum(window) / len(window)))
    return out


def bedtime_std_minutes(nights: list[SleepNight], tz: ZoneInfo) -> float | None:
    offsets = [bedtime_offset_min(n.start_gmt.astimezone(tz)) for n in nights]
    if len(offsets) < 2:
        return None
    return statistics.stdev(offsets)


@dataclass(frozen=True)
class WeekdayStats:
    weekday: int  # 0 = lundi (jour du réveil)
    n: int
    avg_total_h: float
    avg_score: float | None
    avg_bedtime_offset_min: float


def weekday_profile(nights: list[SleepNight], tz: ZoneInfo) -> list[WeekdayStats]:
    buckets: dict[int, list[SleepNight]] = {}
    for n in nights:
        buckets.setdefault(n.calendar_date.weekday(), []).append(n)
    out = []
    for wd in range(7):
        group = buckets.get(wd, [])
        if not group:
            continue
        scores = [n.scores.overall for n in group if n.scores and n.scores.overall is not None]
        out.append(
            WeekdayStats(
                weekday=wd,
                n=len(group),
                avg_total_h=statistics.mean(n.total_sleep_s / 3600 for n in group),
                avg_score=statistics.mean(scores) if scores else None,
                avg_bedtime_offset_min=statistics.mean(
                    bedtime_offset_min(n.start_gmt.astimezone(tz)) for n in group
                ),
            )
        )
    return out


def social_jetlag_min(nights: list[SleepNight], tz: ZoneInfo) -> float | None:
    """Écart |mi-sommeil week-end − mi-sommeil semaine| en minutes.

    Week-end = réveils du samedi et dimanche.
    """

    def midsleep_offset(n: SleepNight) -> float:
        m = night_metrics(n, tz)
        return bedtime_offset_min(m.midsleep_local)

    week = [midsleep_offset(n) for n in nights if n.calendar_date.weekday() < 5]
    weekend = [midsleep_offset(n) for n in nights if n.calendar_date.weekday() >= 5]
    if not week or not weekend:
        return None
    return abs(statistics.mean(weekend) - statistics.mean(week))


def pearson(pairs: list[tuple[float, float]], min_n: int = 14) -> float | None:
    if len(pairs) < min_n:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    try:
        return statistics.correlation(xs, ys)
    except statistics.StatisticsError:  # variance nulle
        return None


@dataclass(frozen=True)
class CorrRow:
    variable: str  # "steps", "intensity_min", "avg_stress", "bb_charged", "resting_hr"
    target: str  # "total_h" ou "score"
    lag: str  # "same_day" (jour précédant la nuit) — la nuit du calendarDate J suit la journée J-1
    r: float | None
    n: int


_DAY_VARS = {
    "steps": lambda d: d.steps,
    "intensity_min": lambda d: d.intensity_min,
    "avg_stress": lambda d: d.avg_stress,
    "bb_charged": lambda d: d.bb_charged,
    "resting_hr": lambda d: d.resting_hr,
}


def correlate(
    nights: list[SleepNight],
    days: dict[date, DailySummary],
    lag: Literal["prev_day"] = "prev_day",
    min_n: int = 14,
) -> list[CorrRow]:
    """Corrèle les variables de la journée J-1 avec la nuit datée J (soir de J-1)."""
    rows = []
    for var, getter in _DAY_VARS.items():
        for target in ("total_h", "score"):
            pairs = []
            for n in nights:
                day = days.get(n.calendar_date - timedelta(days=1))
                if day is None:
                    continue
                x = getter(day)
                if x is None:
                    continue
                if target == "total_h":
                    y = n.total_sleep_s / 3600
                else:
                    if not (n.scores and n.scores.overall is not None):
                        continue
                    y = float(n.scores.overall)
                pairs.append((float(x), y))
            rows.append(
                CorrRow(variable=var, target=target, lag=lag, r=pearson(pairs, min_n), n=len(pairs))
            )
    return rows


@dataclass(frozen=True)
class MonthlySpo2:
    month: str  # "2026-03"
    n: int  # nuits avec mesure SpO2
    avg_spo2: float | None
    median_lowest: float | None
    share_below_85: float | None
    share_below_80: float | None


def monthly_spo2(nights: list[SleepNight]) -> list[MonthlySpo2]:
    buckets: dict[str, list[SleepNight]] = {}
    for n in nights:
        if n.avg_spo2 is None and n.lowest_spo2 is None:
            continue
        buckets.setdefault(n.calendar_date.strftime("%Y-%m"), []).append(n)
    out = []
    for month in sorted(buckets):
        group = buckets[month]
        avgs = [n.avg_spo2 for n in group if n.avg_spo2 is not None]
        lows = [n.lowest_spo2 for n in group if n.lowest_spo2 is not None]
        out.append(
            MonthlySpo2(
                month=month,
                n=len(group),
                avg_spo2=statistics.mean(avgs) if avgs else None,
                median_lowest=float(statistics.median(lows)) if lows else None,
                share_below_85=(
                    sum(1 for v in lows if v < 85) / len(lows) if lows else None
                ),
                share_below_80=(
                    sum(1 for v in lows if v < 80) / len(lows) if lows else None
                ),
            )
        )
    return out


def low_spo2_share(
    nights: list[SleepNight], start: date, end: date, threshold: int = 85
) -> tuple[float | None, int]:
    """Part des nuits [start, end] dont la SpO2 minimale passe sous `threshold`."""
    lows = [
        n.lowest_spo2
        for n in nights
        if n.lowest_spo2 is not None and start <= n.calendar_date <= end
    ]
    if not lows:
        return None, 0
    return sum(1 for v in lows if v < threshold) / len(lows), len(lows)


def feedback_frequencies(nights: list[SleepNight]) -> dict[str, float]:
    """Fréquence (0..1) de chaque enum feedback/insight Garmin sur les nuits scorées."""
    counts: dict[str, int] = {}
    total = 0
    for n in nights:
        if not n.scores:
            continue
        total += 1
        for enum in (n.scores.feedback, n.scores.insight):
            if enum and enum != "NONE":
                counts[enum] = counts.get(enum, 0) + 1
    if total == 0:
        return {}
    return {k: v / total for k, v in counts.items()}


def sleep_hr_elevation(
    nights: list[SleepNight], days: dict[date, DailySummary]
) -> list[tuple[date, float]]:
    """FC nocturne moins la médiane de FC au repos des 30 jours précédents."""
    out = []
    for n in nights:
        if n.avg_sleep_hr is None:
            continue
        window = [
            d.resting_hr
            for dd, d in days.items()
            if d.resting_hr is not None
            and n.calendar_date - timedelta(days=30) <= dd <= n.calendar_date
        ]
        if len(window) < 7:
            continue
        out.append((n.calendar_date, n.avg_sleep_hr - statistics.median(window)))
    return out
