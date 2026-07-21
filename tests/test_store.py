"""Stockage SQLite : upsert idempotent et aller-retour ORM <-> dataclasses."""

from datetime import date, datetime, timezone

import pytest

from garmin_sleep.models import DailySummary, SleepNight, SleepScores
from sleep import models as orm
from sleep.converters import load_export_from_db
from sleep.services import store


def make_night(cal: str = "2026-07-18", **overrides) -> SleepNight:
    kwargs = dict(
        calendar_date=date.fromisoformat(cal),
        start_gmt=datetime(2026, 7, 17, 21, 30, tzinfo=timezone.utc),
        end_gmt=datetime(2026, 7, 18, 5, 30, tzinfo=timezone.utc),
        deep_s=4800,
        light_s=15000,
        rem_s=5400,
        awake_s=600,
        awake_count=1,
        avg_spo2=94.0,
        lowest_spo2=88,
        scores=SleepScores(overall=75, feedback="POSITIVE_DEEP_SLEEP"),
    )
    kwargs.update(overrides)
    return SleepNight(**kwargs)


def make_day(cal: str = "2026-07-18", **overrides) -> DailySummary:
    kwargs = dict(calendar_date=date.fromisoformat(cal), steps=8000, resting_hr=52)
    kwargs.update(overrides)
    return DailySummary(**kwargs)


@pytest.mark.django_db
def test_upsert_then_load_roundtrip():
    store.upsert_nights([make_night()], source="zip")
    store.upsert_days([make_day()], source="zip")

    export = load_export_from_db()
    assert export.nights == [make_night()]
    assert export.days == {date(2026, 7, 18): make_day()}


@pytest.mark.django_db
def test_upsert_is_idempotent_and_updates():
    store.upsert_nights([make_night(deep_s=100)], source="zip")
    store.upsert_nights([make_night(deep_s=200)], source="api")

    assert orm.SleepNight.objects.count() == 1
    row = orm.SleepNight.objects.get()
    assert row.deep_s == 200
    assert row.source == "api"


@pytest.mark.django_db
def test_night_without_scores_loads_as_none():
    store.upsert_nights([make_night(scores=None)], source="api")
    export = load_export_from_db()
    assert export.nights[0].scores is None
