"""Modèles ORM — miroir persistant des dataclasses de garmin_sleep.models.

La logique d'analyse reste dans garmin_sleep (fonctions pures) ; ces modèles ne
font que stocker. Les conversions ORM <-> dataclasses vivent dans converters.py.
"""

from django.db import models


class Source(models.TextChoices):
    ZIP = "zip", "Export GDPR (zip)"
    API = "api", "API Garmin Connect"


class SleepNight(models.Model):
    calendar_date = models.DateField(unique=True)  # date du matin (réveil)
    start_gmt = models.DateTimeField()
    end_gmt = models.DateTimeField()
    deep_s = models.IntegerField(default=0)
    light_s = models.IntegerField(default=0)
    rem_s = models.IntegerField(null=True, blank=True)
    awake_s = models.IntegerField(default=0)
    unmeasurable_s = models.IntegerField(default=0)
    awake_count = models.IntegerField(null=True, blank=True)
    avg_sleep_stress = models.FloatField(null=True, blank=True)
    restless_moments = models.IntegerField(null=True, blank=True)
    avg_spo2 = models.FloatField(null=True, blank=True)
    lowest_spo2 = models.IntegerField(null=True, blank=True)
    avg_sleep_hr = models.FloatField(null=True, blank=True)

    score_overall = models.IntegerField(null=True, blank=True)
    score_quality = models.IntegerField(null=True, blank=True)
    score_duration = models.IntegerField(null=True, blank=True)
    score_recovery = models.IntegerField(null=True, blank=True)
    score_deep = models.IntegerField(null=True, blank=True)
    score_rem = models.IntegerField(null=True, blank=True)
    score_feedback = models.TextField(null=True, blank=True)
    score_insight = models.TextField(null=True, blank=True)

    source = models.CharField(max_length=8, choices=Source.choices)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["calendar_date"]
        verbose_name = "nuit"
        verbose_name_plural = "nuits"

    def __str__(self) -> str:
        return f"Nuit du {self.calendar_date}"


class DailySummary(models.Model):
    calendar_date = models.DateField(unique=True)
    resting_hr = models.IntegerField(null=True, blank=True)
    steps = models.IntegerField(null=True, blank=True)
    moderate_min = models.IntegerField(null=True, blank=True)
    vigorous_min = models.IntegerField(null=True, blank=True)
    avg_stress = models.IntegerField(null=True, blank=True)
    bb_charged = models.IntegerField(null=True, blank=True)
    bb_drained = models.IntegerField(null=True, blank=True)

    source = models.CharField(max_length=8, choices=Source.choices)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["calendar_date"]
        verbose_name = "journée"
        verbose_name_plural = "journées"

    def __str__(self) -> str:
        return f"Journée du {self.calendar_date}"
