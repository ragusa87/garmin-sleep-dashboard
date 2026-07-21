"""Conversions ORM <-> dataclasses pures de garmin_sleep.models."""

from __future__ import annotations

from garmin_sleep.models import DailySummary, ExportData, SleepNight, SleepScores

from . import models as orm

_SCORE_FIELDS = {
    "overall": "score_overall",
    "quality": "score_quality",
    "duration": "score_duration",
    "recovery": "score_recovery",
    "deep": "score_deep",
    "rem": "score_rem",
    "feedback": "score_feedback",
    "insight": "score_insight",
}


def night_to_dataclass(obj: orm.SleepNight) -> SleepNight:
    score_values = {dc: getattr(obj, db) for dc, db in _SCORE_FIELDS.items()}
    scores = (
        SleepScores(**score_values) if any(v is not None for v in score_values.values()) else None
    )
    return SleepNight(
        calendar_date=obj.calendar_date,
        start_gmt=obj.start_gmt,
        end_gmt=obj.end_gmt,
        deep_s=obj.deep_s,
        light_s=obj.light_s,
        rem_s=obj.rem_s,
        awake_s=obj.awake_s,
        unmeasurable_s=obj.unmeasurable_s,
        awake_count=obj.awake_count,
        avg_sleep_stress=obj.avg_sleep_stress,
        restless_moments=obj.restless_moments,
        avg_spo2=obj.avg_spo2,
        lowest_spo2=obj.lowest_spo2,
        avg_sleep_hr=obj.avg_sleep_hr,
        scores=scores,
    )


def night_to_fields(night: SleepNight) -> dict:
    """Champs ORM (hors calendar_date) pour update_or_create."""
    scores = night.scores or SleepScores()
    fields = {
        "start_gmt": night.start_gmt,
        "end_gmt": night.end_gmt,
        "deep_s": night.deep_s,
        "light_s": night.light_s,
        "rem_s": night.rem_s,
        "awake_s": night.awake_s,
        "unmeasurable_s": night.unmeasurable_s,
        "awake_count": night.awake_count,
        "avg_sleep_stress": night.avg_sleep_stress,
        "restless_moments": night.restless_moments,
        "avg_spo2": night.avg_spo2,
        "lowest_spo2": night.lowest_spo2,
        "avg_sleep_hr": night.avg_sleep_hr,
    }
    fields.update({db: getattr(scores, dc) for dc, db in _SCORE_FIELDS.items()})
    return fields


def day_to_dataclass(obj: orm.DailySummary) -> DailySummary:
    return DailySummary(
        calendar_date=obj.calendar_date,
        resting_hr=obj.resting_hr,
        steps=obj.steps,
        moderate_min=obj.moderate_min,
        vigorous_min=obj.vigorous_min,
        avg_stress=obj.avg_stress,
        bb_charged=obj.bb_charged,
        bb_drained=obj.bb_drained,
    )


def day_to_fields(day: DailySummary) -> dict:
    return {
        "resting_hr": day.resting_hr,
        "steps": day.steps,
        "moderate_min": day.moderate_min,
        "vigorous_min": day.vigorous_min,
        "avg_stress": day.avg_stress,
        "bb_charged": day.bb_charged,
        "bb_drained": day.bb_drained,
    }


def load_export_from_db() -> ExportData:
    """Reconstruit un ExportData (entrée de analyze()) depuis la base."""
    nights = [night_to_dataclass(o) for o in orm.SleepNight.objects.all()]
    days = {o.calendar_date: day_to_dataclass(o) for o in orm.DailySummary.objects.all()}
    return ExportData(nights=nights, days=days)
