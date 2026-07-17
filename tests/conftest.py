import json
import zipfile
from pathlib import Path

import pytest


def sleep_record(cal_date: str, start: str, end: str, **overrides) -> dict:
    rec = {
        "calendarDate": cal_date,
        "sleepStartTimestampGMT": start,
        "sleepEndTimestampGMT": end,
        "deepSleepSeconds": 4800,
        "lightSleepSeconds": 15000,
        "remSleepSeconds": 5400,
        "awakeSleepSeconds": 600,
        "unmeasurableSeconds": 0,
        "awakeCount": 1,
        "avgSleepStress": 20.0,
        "restlessMomentCount": 30,
        "spo2SleepSummary": {"averageSPO2": 94.0, "lowestSPO2": 88, "averageHR": 55.0},
        "sleepScores": {
            "overallScore": 75,
            "qualityScore": 80,
            "durationScore": 70,
            "recoveryScore": 72,
            "deepScore": 90,
            "remScore": 60,
            "feedback": "POSITIVE_DEEP_SLEEP",
            "insight": "NONE",
        },
        "retro": False,
    }
    rec.update(overrides)
    return rec


def uds_record(cal_date: str, **overrides) -> dict:
    rec = {
        "calendarDate": cal_date,
        "restingHeartRate": 52,
        "totalSteps": 8000,
        "moderateIntensityMinutes": 20,
        "vigorousIntensityMinutes": 10,
        "allDayStress": {
            "aggregatorList": [
                {"type": "TOTAL", "averageStressLevel": 30},
                {"type": "AWAKE", "averageStressLevel": 40},
            ]
        },
        "bodyBattery": {"chargedValue": 60, "drainedValue": 55},
    }
    rec.update(overrides)
    return rec


@pytest.fixture
def make_export_zip(tmp_path):
    """Construit un zip d'export Garmin synthétique avec les chemins internes réels."""

    def _make(
        sleep_files: dict[str, list[dict]] | list[dict] | None = None,
        uds_files: dict[str, list[dict]] | list[dict] | None = None,
    ) -> Path:
        if isinstance(sleep_files, list):
            sleep_files = {"2026-01-01_2026-04-01_123456_sleepData.json": sleep_files}
        if isinstance(uds_files, list):
            uds_files = {"UDSFile_2026-01-01_2026-04-01.json": uds_files}
        zip_path = tmp_path / "export.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for fname, records in (sleep_files or {}).items():
                zf.writestr(
                    f"DI_CONNECT/DI-Connect-Wellness/{fname}", json.dumps(records)
                )
            for fname, records in (uds_files or {}).items():
                zf.writestr(
                    f"DI_CONNECT/DI-Connect-Aggregator/{fname}", json.dumps(records)
                )
        return zip_path

    return _make
