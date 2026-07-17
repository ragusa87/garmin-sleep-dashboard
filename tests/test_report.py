import json
import re
from datetime import date
from zoneinfo import ZoneInfo

from garmin_sleep.analysis import analyze
from garmin_sleep.parser import load_export
from garmin_sleep.report import build_html, build_payload
from garmin_sleep.tips import generate_tips

from conftest import sleep_record, uds_record


def _full_pipeline(make_export_zip, n_nights=20):
    records, uds = [], []
    for i in range(n_nights):
        d = date(2026, 3, 1).toordinal() + i
        cal = date.fromordinal(d)
        prev = date.fromordinal(d - 1)
        records.append(
            sleep_record(
                cal.isoformat(),
                f"{prev.isoformat()}T22:30:00.0",
                f"{cal.isoformat()}T06:00:00.0",
            )
        )
        uds.append(uds_record(prev.isoformat()))
    zip_path = make_export_zip(sleep_files=records, uds_files=uds)
    export = load_export(zip_path)
    analysis = analyze(export, ZoneInfo("Europe/Zurich"))
    tips = generate_tips(analysis)
    return build_payload(analysis, tips)


def test_payload_json_serializable(make_export_zip):
    payload = _full_pipeline(make_export_zip)
    text = json.dumps(payload)
    assert payload["period"]["n_nights"] == 20
    assert len(payload["nights"]) == 20
    assert payload["summary"]["avg_score"] == 75
    assert "Lundi" in text


def test_html_selfcontained(make_export_zip):
    payload = _full_pipeline(make_export_zip)
    html = build_html(payload)
    assert '"n_nights": 20'.replace(" ", "") in html.replace(" ", "")
    assert "Chart" in html  # Chart.js embarqué
    # garantie hors-ligne : aucune référence externe http(s)
    external = re.findall(r'(?:src|href)\s*=\s*["\']https?://', html)
    assert external == []


def test_payload_escapes_script_close(make_export_zip):
    payload = _full_pipeline(make_export_zip)
    payload["tips"] = [
        {"id": "x", "priority": 1, "title": "</script>", "body": "b", "evidence": {}}
    ]
    html = build_html(payload)
    # le JSON injecté ne doit pas fermer la balise <script>
    assert html.count("</script>") == html.count("<script")


def test_days_limit(make_export_zip):
    records = []
    for i in range(40):
        cal = date.fromordinal(date(2026, 3, 1).toordinal() + i)
        prev = date.fromordinal(cal.toordinal() - 1)
        records.append(
            sleep_record(
                cal.isoformat(),
                f"{prev.isoformat()}T22:30:00.0",
                f"{cal.isoformat()}T06:00:00.0",
            )
        )
    export = load_export(make_export_zip(sleep_files=records))
    analysis = analyze(export, ZoneInfo("Europe/Zurich"), days_limit=10)
    assert len(analysis.nights) == 10


def test_payload_spo2_section(make_export_zip):
    payload = _full_pipeline(make_export_zip)
    assert "spo2" in payload
    assert payload["nights"][0]["spo2_low"] == 88
    [month] = payload["spo2"]["monthly"]
    assert month["n"] == 20
    assert month["below_85"] == 0
    json.dumps(payload["spo2"])
