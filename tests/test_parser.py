from datetime import date, datetime, timezone

from garmin_sleep.parser import load_export, parse_sleep_records, _parse_gmt

from conftest import sleep_record, uds_record


def test_parse_gmt():
    dt = _parse_gmt("2026-07-17T00:32:15.0")
    assert dt == datetime(2026, 7, 17, 0, 32, 15, tzinfo=timezone.utc)


def test_retro_only_record_skipped():
    assert parse_sleep_records([{"retro": False}]) == []


def test_missing_optional_fields_tolerated():
    rec = sleep_record("2026-01-02", "2026-01-01T22:00:00.0", "2026-01-02T06:00:00.0")
    del rec["remSleepSeconds"]
    del rec["sleepScores"]
    del rec["spo2SleepSummary"]
    [night] = parse_sleep_records([rec])
    assert night.rem_s is None
    assert night.scores is None
    assert night.avg_spo2 is None
    assert night.total_sleep_s == 4800 + 15000


def test_load_export_globs_and_dedupes(make_export_zip):
    older = sleep_record(
        "2026-01-15", "2026-01-14T22:00:00.0", "2026-01-15T06:00:00.0", deepSleepSeconds=1000
    )
    newer = sleep_record(
        "2026-01-15", "2026-01-14T22:00:00.0", "2026-01-15T06:00:00.0", deepSleepSeconds=2000
    )
    zip_path = make_export_zip(
        sleep_files={
            "2025-10-01_2026-01-15_123456_sleepData.json": [older],
            "2026-01-14_2026-04-01_123456_sleepData.json": [newer],
            "2025-06-01_2025-10-01_123456_sleepData.json": [{"retro": False}],
        },
        uds_files=[uds_record("2026-01-14")],
    )
    export = load_export(zip_path)
    assert len(export.nights) == 1
    assert export.nights[0].deep_s == 2000  # le fichier le plus récent gagne
    assert date(2026, 1, 14) in export.days


def test_uds_parsing(make_export_zip):
    zip_path = make_export_zip(
        uds_files=[uds_record("2026-01-14", restingHeartRate=0)]
    )
    export = load_export(zip_path)
    day = export.days[date(2026, 1, 14)]
    assert day.resting_hr is None  # 0 = montre non portée
    assert day.avg_stress == 30  # agrégat TOTAL, pas AWAKE
    assert day.intensity_min == 30
    assert day.bb_charged == 60


def test_night_properties():
    rec = sleep_record("2026-01-02", "2026-01-01T22:00:00.0", "2026-01-02T06:00:00.0")
    [night] = parse_sleep_records([rec])
    assert night.in_bed_s == 8 * 3600
    assert night.total_sleep_s == 4800 + 15000 + 5400
    assert abs(night.efficiency - night.total_sleep_s / night.in_bed_s) < 1e-9
