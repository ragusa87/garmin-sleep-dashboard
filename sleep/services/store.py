"""Écriture en base : upsert idempotent par calendar_date.

Point d'entrée unique pour les deux sources (zip GDPR et API Garmin Connect) :
les deux produisent des dataclasses garmin_sleep.models, stockées ici.
"""

from __future__ import annotations

from django.db import transaction

from garmin_sleep.models import DailySummary, SleepNight

from .. import models as orm
from ..converters import day_to_fields, night_to_fields


@transaction.atomic
def upsert_nights(nights: list[SleepNight], source: str) -> int:
    """Insère ou met à jour chaque nuit ; retourne le nombre de lignes touchées."""
    count = 0
    for night in nights:
        orm.SleepNight.objects.update_or_create(
            calendar_date=night.calendar_date,
            defaults={**night_to_fields(night), "source": source},
        )
        count += 1
    return count


@transaction.atomic
def upsert_days(days: list[DailySummary], source: str) -> int:
    count = 0
    for day in days:
        orm.DailySummary.objects.update_or_create(
            calendar_date=day.calendar_date,
            defaults={**day_to_fields(day), "source": source},
        )
        count += 1
    return count
