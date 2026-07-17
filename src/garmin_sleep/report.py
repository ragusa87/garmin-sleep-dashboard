"""Transformation de l'Analysis en payload JSON + rendu HTML autonome."""

from __future__ import annotations

import json
from importlib import resources

from .analysis import Analysis
from .tips import Tip

WEEKDAYS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

CORR_LABELS_FR = {
    "steps": "Pas (veille)",
    "intensity_min": "Minutes intensives (veille)",
    "avg_stress": "Stress moyen (veille)",
    "bb_charged": "Body Battery rechargée (veille)",
    "resting_hr": "FC au repos (veille)",
}


def _offset_to_clock(offset_min: float | None) -> str | None:
    if offset_min is None:
        return None
    total = (offset_min + 18 * 60) % 1440
    return f"{int(total // 60):02d}:{int(total % 60):02d}"


def build_payload(analysis: Analysis, tips: list[Tip]) -> dict:
    nights_payload = []
    by_date = {n.calendar_date: n for n in analysis.nights}
    for row in analysis.night_rows:
        n = by_date[row.calendar_date]
        nights_payload.append(
            {
                "date": row.calendar_date.isoformat(),
                "total_h": round(row.total_h, 2),
                "deep_h": round(n.deep_s / 3600, 2),
                "light_h": round(n.light_s / 3600, 2),
                "rem_h": round((n.rem_s or 0) / 3600, 2),
                "awake_h": round(n.awake_s / 3600, 2),
                "score": n.scores.overall if n.scores else None,
                "bedtime_offset_min": round(
                    (row.bedtime_local.hour * 60 + row.bedtime_local.minute - 18 * 60) % 1440, 1
                ),
                "bedtime_clock": row.bedtime_local.strftime("%H:%M"),
                "efficiency": round(row.efficiency * 100, 1) if row.efficiency else None,
                "spo2_avg": round(n.avg_spo2, 1) if n.avg_spo2 is not None else None,
                "spo2_low": n.lowest_spo2,
            }
        )

    return {
        "tz": analysis.tz_name,
        "period": {
            "start": analysis.nights[0].calendar_date.isoformat() if analysis.nights else None,
            "end": analysis.nights[-1].calendar_date.isoformat() if analysis.nights else None,
            "n_nights": len(analysis.nights),
        },
        "summary": {
            "avg_score": round(analysis.avg_score, 1) if analysis.avg_score is not None else None,
            "avg_total_h_30d": (
                round(analysis.avg_total_h_30d, 2)
                if analysis.avg_total_h_30d is not None
                else None
            ),
            "median_bedtime": _offset_to_clock(analysis.median_bedtime_offset_min),
            "bedtime_std_min": (
                round(analysis.bedtime_std_min) if analysis.bedtime_std_min is not None else None
            ),
            "social_jetlag_min": (
                round(analysis.social_jetlag_min)
                if analysis.social_jetlag_min is not None
                else None
            ),
            "avg_deep_pct": (
                round(analysis.avg_deep_pct, 1) if analysis.avg_deep_pct is not None else None
            ),
            "avg_rem_pct": (
                round(analysis.avg_rem_pct, 1) if analysis.avg_rem_pct is not None else None
            ),
            "avg_spo2": round(analysis.avg_spo2, 1) if analysis.avg_spo2 is not None else None,
            "low_spo2_share": (
                round(analysis.low_spo2_night_share * 100)
                if analysis.low_spo2_night_share is not None
                else None
            ),
        },
        "spo2": {
            "monthly": [
                {
                    "month": m.month,
                    "n": m.n,
                    "avg": round(m.avg_spo2, 1) if m.avg_spo2 is not None else None,
                    "median_low": m.median_lowest,
                    "below_85": (
                        round(m.share_below_85 * 100) if m.share_below_85 is not None else None
                    ),
                    "below_80": (
                        round(m.share_below_80 * 100) if m.share_below_80 is not None else None
                    ),
                }
                for m in analysis.monthly_spo2
            ],
            "recent_low_share": (
                round(analysis.spo2_low_share_recent * 100)
                if analysis.spo2_low_share_recent is not None
                else None
            ),
            "prev_low_share": (
                round(analysis.spo2_low_share_prev * 100)
                if analysis.spo2_low_share_prev is not None
                else None
            ),
        },
        "nights": nights_payload,
        "trends": {
            "total_h_7d": [[d.isoformat(), round(v, 2)] for d, v in analysis.trend_total_h_7d],
            "total_h_30d": [[d.isoformat(), round(v, 2)] for d, v in analysis.trend_total_h_30d],
            "score_7d": [[d.isoformat(), round(v, 1)] for d, v in analysis.trend_score_7d],
            "score_30d": [[d.isoformat(), round(v, 1)] for d, v in analysis.trend_score_30d],
        },
        "weekday": [
            {
                "label": WEEKDAYS_FR[w.weekday],
                "n": w.n,
                "avg_total_h": round(w.avg_total_h, 2),
                "avg_score": round(w.avg_score, 1) if w.avg_score is not None else None,
                "avg_bedtime": _offset_to_clock(w.avg_bedtime_offset_min),
            }
            for w in analysis.weekday
        ],
        "correlations": [
            {
                "label": CORR_LABELS_FR.get(c.variable, c.variable),
                "target": "Durée" if c.target == "total_h" else "Score",
                "r": round(c.r, 3) if c.r is not None else None,
                "n": c.n,
            }
            for c in analysis.correlations
        ],
        "tips": [
            {
                "id": t.id,
                "priority": t.priority,
                "title": t.title,
                "body": t.body,
                "evidence": t.evidence,
            }
            for t in tips
        ],
    }


def build_html(payload: dict) -> str:
    pkg = resources.files("garmin_sleep")
    template = (pkg / "templates" / "dashboard.html").read_text(encoding="utf-8")
    chartjs = (pkg / "static" / "chart.umd.js").read_text(encoding="utf-8")
    # </script> dans les chaînes JSON casserait le tag <script> englobant
    payload_js = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("/*{{CHARTJS}}*/", chartjs).replace('"{{PAYLOAD}}"', payload_js)
