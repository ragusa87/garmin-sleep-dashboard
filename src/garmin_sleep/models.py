"""Structures de données immuables issues de l'export Garmin."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class SleepScores:
    overall: int | None = None
    quality: int | None = None
    duration: int | None = None
    recovery: int | None = None
    deep: int | None = None
    rem: int | None = None
    feedback: str | None = None
    insight: str | None = None


@dataclass(frozen=True)
class SleepNight:
    calendar_date: date  # date du matin (réveil)
    start_gmt: datetime  # tz-aware UTC
    end_gmt: datetime
    deep_s: int = 0
    light_s: int = 0
    rem_s: int | None = None
    awake_s: int = 0
    unmeasurable_s: int = 0
    awake_count: int | None = None
    avg_sleep_stress: float | None = None
    restless_moments: int | None = None
    avg_spo2: float | None = None
    lowest_spo2: int | None = None
    avg_sleep_hr: float | None = None
    scores: SleepScores | None = None

    @property
    def total_sleep_s(self) -> int:
        return self.deep_s + self.light_s + (self.rem_s or 0)

    @property
    def in_bed_s(self) -> int:
        return int((self.end_gmt - self.start_gmt).total_seconds())

    @property
    def efficiency(self) -> float | None:
        if self.in_bed_s <= 0:
            return None
        return self.total_sleep_s / self.in_bed_s


@dataclass(frozen=True)
class DailySummary:
    calendar_date: date
    resting_hr: int | None = None
    steps: int | None = None
    moderate_min: int | None = None
    vigorous_min: int | None = None
    avg_stress: int | None = None
    bb_charged: int | None = None
    bb_drained: int | None = None

    @property
    def intensity_min(self) -> int | None:
        if self.moderate_min is None and self.vigorous_min is None:
            return None
        return (self.moderate_min or 0) + (self.vigorous_min or 0)


@dataclass(frozen=True)
class ExportData:
    nights: list[SleepNight]  # triées par calendar_date, dédupliquées
    days: dict[date, DailySummary]
