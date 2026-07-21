"""Mappers purs JSON API Garmin Connect -> dataclasses (sans réseau)."""

from datetime import date, datetime, timezone

from sleep.services.garmin_api import api_sleep_to_night, api_stats_to_day


def api_sleep_payload(**dto_overrides) -> dict:
    dto = {
        "calendarDate": "2026-07-18",
        # l'API renvoie des epoch en millisecondes
        "sleepStartTimestampGMT": 1784323800000,  # 2026-07-17T21:30:00Z
        "sleepEndTimestampGMT": 1784352600000,  # 2026-07-18T05:30:00Z
        "deepSleepSeconds": 4800,
        "lightSleepSeconds": 15000,
        "remSleepSeconds": 5400,
        "awakeSleepSeconds": 600,
        "unmeasurableSleepSeconds": 0,
        "awakeCount": 2,
        "avgSleepStress": 18.5,
        "restlessMomentsCount": 25,
        "averageSpO2Value": 94.0,
        "lowestSpO2Value": 88,
        "averageSpO2HRSleep": 55.0,
        "sleepScores": {
            "overall": {"value": 78, "qualifierKey": "FAIR"},
            "totalDuration": {"value": 70},
            "remPercentage": {"value": 60},
            "deepPercentage": {"value": 90},
        },
    }
    dto.update(dto_overrides)
    return {"dailySleepDTO": dto}


def test_api_sleep_to_night_maps_fields():
    night = api_sleep_to_night(api_sleep_payload())
    assert night is not None
    assert night.calendar_date == date(2026, 7, 18)
    assert night.start_gmt == datetime(2026, 7, 17, 21, 30, tzinfo=timezone.utc)
    assert night.end_gmt == datetime(2026, 7, 18, 5, 30, tzinfo=timezone.utc)
    assert night.deep_s == 4800
    assert night.rem_s == 5400
    assert night.lowest_spo2 == 88
    assert night.avg_sleep_hr == 55.0
    assert night.scores.overall == 78
    assert night.scores.duration == 70
    assert night.scores.deep == 90


def test_api_sleep_night_without_timestamps_is_skipped():
    payload = api_sleep_payload(sleepStartTimestampGMT=None)
    assert api_sleep_to_night(payload) is None
    assert api_sleep_to_night({}) is None
    assert api_sleep_to_night(None) is None


def test_api_sleep_accepts_string_timestamps_and_flat_scores():
    payload = api_sleep_payload(
        sleepStartTimestampGMT="2026-07-17T21:30:00.0",
        sleepEndTimestampGMT="2026-07-18T05:30:00.0",
        sleepScores={"overallScore": 80},
    )
    night = api_sleep_to_night(payload)
    assert night.start_gmt == datetime(2026, 7, 17, 21, 30, tzinfo=timezone.utc)
    assert night.scores.overall == 80


def test_api_stats_to_day_maps_fields():
    day = api_stats_to_day(
        {
            "calendarDate": "2026-07-18",
            "totalSteps": 9000,
            "restingHeartRate": 50,
            "moderateIntensityMinutes": 15,
            "vigorousIntensityMinutes": 5,
            "averageStressLevel": 28,
            "bodyBatteryChargedValue": 70,
            "bodyBatteryDrainedValue": 60,
        }
    )
    assert day.calendar_date == date(2026, 7, 18)
    assert day.steps == 9000
    assert day.resting_hr == 50
    assert day.avg_stress == 28


def test_api_stats_resting_hr_zero_means_none():
    day = api_stats_to_day({"calendarDate": "2026-07-18", "restingHeartRate": 0})
    assert day.resting_hr is None


def test_api_stats_without_date_is_skipped():
    assert api_stats_to_day({}) is None
    assert api_stats_to_day(None) is None


def test_secure_tokenstore_and_has_tokens(tmp_path):
    from sleep.services.garmin_api import has_tokens, secure_tokenstore

    store_dir = tmp_path / "tokens"
    assert has_tokens(store_dir) is False
    store_dir.mkdir()
    assert has_tokens(store_dir) is False  # dossier vide

    token = store_dir / "oauth2_token.json"
    token.write_text("{}")
    secure_tokenstore(store_dir)

    assert has_tokens(store_dir) is True
    assert (store_dir.stat().st_mode & 0o777) == 0o700
    assert (token.stat().st_mode & 0o777) == 0o600


def test_secure_tokenstore_missing_dir_is_noop(tmp_path):
    from sleep.services.garmin_api import secure_tokenstore

    secure_tokenstore(tmp_path / "absent")  # ne doit pas lever


def test_login_and_store_persists_via_login_tokenstore(tmp_path, monkeypatch):
    """garminconnect >= 0.3 : les jetons sont écrits par login(tokenstore)."""
    import garminconnect

    from sleep.services.garmin_api import login_and_store

    calls = {}

    class FakeGarmin:
        def __init__(self, email=None, password=None, prompt_mfa=None, **kwargs):
            calls["credentials"] = (email, password)
            calls["prompt_mfa"] = prompt_mfa

        def login(self, tokenstore=None):
            calls["tokenstore"] = tokenstore
            from pathlib import Path

            p = Path(tokenstore)
            p.mkdir(parents=True, exist_ok=True)
            (p / "oauth2_token.json").write_text("{}")

    monkeypatch.setattr(garminconnect, "Garmin", FakeGarmin)

    store_dir = tmp_path / "tokens"
    mfa = lambda: "123456"
    login_and_store("a@b.example", "pw", str(store_dir), prompt_mfa=mfa)

    assert calls["credentials"] == ("a@b.example", "pw")
    assert calls["prompt_mfa"] is mfa
    assert calls["tokenstore"] == str(store_dir)
    token = store_dir / "oauth2_token.json"
    assert (token.stat().st_mode & 0o777) == 0o600  # permissions resserrées après dump
