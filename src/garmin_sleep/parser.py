"""Lecture tolérante de l'export Garmin (zip GDPR) en mémoire."""

from __future__ import annotations

import fnmatch
import json
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from .models import DailySummary, ExportData, SleepNight, SleepScores

SLEEP_GLOB = "DI_CONNECT/DI-Connect-Wellness/*_sleepData.json"
UDS_GLOB = "DI_CONNECT/DI-Connect-Aggregator/UDSFile_*.json"


def _parse_gmt(ts: str) -> datetime:
    # Format Garmin : "2026-07-17T00:32:15.0"
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def parse_sleep_records(raw: list[dict]) -> list[SleepNight]:
    nights = []
    for rec in raw:
        start = rec.get("sleepStartTimestampGMT")
        end = rec.get("sleepEndTimestampGMT")
        cal = rec.get("calendarDate")
        if not (start and end and cal):
            continue  # enregistrements vides du type {"retro": false}

        spo2 = rec.get("spo2SleepSummary") or {}
        raw_scores = rec.get("sleepScores")
        scores = None
        if raw_scores:
            scores = SleepScores(
                overall=raw_scores.get("overallScore"),
                quality=raw_scores.get("qualityScore"),
                duration=raw_scores.get("durationScore"),
                recovery=raw_scores.get("recoveryScore"),
                deep=raw_scores.get("deepScore"),
                rem=raw_scores.get("remScore"),
                feedback=raw_scores.get("feedback"),
                insight=raw_scores.get("insight"),
            )
        nights.append(
            SleepNight(
                calendar_date=_parse_date(cal),
                start_gmt=_parse_gmt(start),
                end_gmt=_parse_gmt(end),
                deep_s=rec.get("deepSleepSeconds") or 0,
                light_s=rec.get("lightSleepSeconds") or 0,
                rem_s=rec.get("remSleepSeconds"),
                awake_s=rec.get("awakeSleepSeconds") or 0,
                unmeasurable_s=rec.get("unmeasurableSeconds") or 0,
                awake_count=rec.get("awakeCount"),
                avg_sleep_stress=rec.get("avgSleepStress"),
                restless_moments=rec.get("restlessMomentCount"),
                avg_spo2=spo2.get("averageSPO2"),
                lowest_spo2=spo2.get("lowestSPO2"),
                avg_sleep_hr=spo2.get("averageHR"),
                scores=scores,
            )
        )
    return nights


def parse_uds_records(raw: list[dict]) -> list[DailySummary]:
    days = []
    for rec in raw:
        cal = rec.get("calendarDate")
        if not cal:
            continue
        stress = None
        for agg in (rec.get("allDayStress") or {}).get("aggregatorList", []):
            if agg.get("type") == "TOTAL":
                stress = agg.get("averageStressLevel")
                break
        bb = rec.get("bodyBattery") or {}
        resting_hr = rec.get("restingHeartRate")
        if not resting_hr:  # 0 = montre non portée
            resting_hr = None
        days.append(
            DailySummary(
                calendar_date=_parse_date(cal),
                resting_hr=resting_hr,
                steps=rec.get("totalSteps"),
                moderate_min=rec.get("moderateIntensityMinutes"),
                vigorous_min=rec.get("vigorousIntensityMinutes"),
                avg_stress=stress,
                bb_charged=bb.get("chargedValue"),
                bb_drained=bb.get("drainedValue"),
            )
        )
    return days


def load_export(zip_path: Path) -> ExportData:
    nights_by_date: dict[date, SleepNight] = {}
    days_by_date: dict[date, DailySummary] = {}
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        # ordre trié : en cas de chevauchement de périodes, le fichier le plus
        # récent (nom trié en dernier) écrase les enregistrements précédents
        for name in sorted(fnmatch.filter(names, SLEEP_GLOB)):
            for night in parse_sleep_records(json.loads(zf.read(name))):
                nights_by_date[night.calendar_date] = night
        for name in sorted(fnmatch.filter(names, UDS_GLOB)):
            for day in parse_uds_records(json.loads(zf.read(name))):
                days_by_date[day.calendar_date] = day
    nights = sorted(nights_by_date.values(), key=lambda n: n.calendar_date)
    return ExportData(nights=nights, days=days_by_date)
