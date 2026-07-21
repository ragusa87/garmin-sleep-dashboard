"""Récupération via l'API Garmin Connect (bibliothèque garminconnect).

Deux couches indépendantes :
- mappers purs `api_sleep_to_night` / `api_stats_to_day` (JSON API -> dataclasses),
  testables sans réseau, aussi tolérants que parser.py (`.get()` partout) ;
- `connect_client` / `fetch_range`, seuls points de contact avec le réseau.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from garmin_sleep.models import DailySummary, SleepNight, SleepScores


def _parse_ts(value) -> datetime | None:
    """Timestamp API : epoch en millisecondes, ou chaîne type export GDPR."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _score_value(scores: dict, *keys):
    """Un score API est un entier direct ou un objet {"value": ...}."""
    for key in keys:
        v = scores.get(key)
        if isinstance(v, dict):
            v = v.get("value")
        if v is not None:
            return v
    return None


def _parse_scores(dto: dict) -> SleepScores | None:
    raw = dto.get("sleepScores")
    if not raw:
        return None
    return SleepScores(
        overall=_score_value(raw, "overall", "overallScore"),
        quality=_score_value(raw, "quality", "qualityScore"),
        duration=_score_value(raw, "totalDuration", "durationScore"),
        recovery=_score_value(raw, "recovery", "recoveryScore"),
        deep=_score_value(raw, "deepPercentage", "deepScore"),
        rem=_score_value(raw, "remPercentage", "remScore"),
        feedback=dto.get("sleepScoreFeedback") or raw.get("feedback"),
        insight=dto.get("sleepScoreInsight") or raw.get("insight"),
    )


def api_sleep_to_night(payload: dict) -> SleepNight | None:
    """Réponse de get_sleep_data(date) -> SleepNight, ou None si nuit vide."""
    dto = (payload or {}).get("dailySleepDTO") or {}
    cal = dto.get("calendarDate")
    start = _parse_ts(dto.get("sleepStartTimestampGMT"))
    end = _parse_ts(dto.get("sleepEndTimestampGMT"))
    if not (cal and start and end):
        return None  # jour sans mesure de sommeil
    return SleepNight(
        calendar_date=date.fromisoformat(cal),
        start_gmt=start,
        end_gmt=end,
        deep_s=dto.get("deepSleepSeconds") or 0,
        light_s=dto.get("lightSleepSeconds") or 0,
        rem_s=dto.get("remSleepSeconds"),
        awake_s=dto.get("awakeSleepSeconds") or 0,
        unmeasurable_s=dto.get("unmeasurableSleepSeconds") or 0,
        awake_count=dto.get("awakeCount"),
        avg_sleep_stress=dto.get("avgSleepStress"),
        restless_moments=dto.get("restlessMomentsCount"),
        avg_spo2=dto.get("averageSpO2Value"),
        lowest_spo2=dto.get("lowestSpO2Value"),
        avg_sleep_hr=dto.get("averageSpO2HRSleep"),
        scores=_parse_scores(dto),
    )


def api_stats_to_day(payload: dict) -> DailySummary | None:
    """Réponse de get_stats(date) -> DailySummary, ou None si jour vide."""
    payload = payload or {}
    cal = payload.get("calendarDate")
    if not cal:
        return None
    resting_hr = payload.get("restingHeartRate")
    if not resting_hr:  # 0 = montre non portée, même règle que parser.py
        resting_hr = None
    return DailySummary(
        calendar_date=date.fromisoformat(cal),
        resting_hr=resting_hr,
        steps=payload.get("totalSteps"),
        moderate_min=payload.get("moderateIntensityMinutes"),
        vigorous_min=payload.get("vigorousIntensityMinutes"),
        avg_stress=payload.get("averageStressLevel"),
        bb_charged=payload.get("bodyBatteryChargedValue"),
        bb_drained=payload.get("bodyBatteryDrainedValue"),
    )


def secure_tokenstore(tokenstore: str) -> None:
    """Permissions restrictives : dossier 0700, fichiers de jetons 0600."""
    path = Path(tokenstore)
    if not path.is_dir():
        return
    path.chmod(0o700)
    for f in path.iterdir():
        if f.is_file():
            f.chmod(0o600)


def has_tokens(tokenstore: str) -> bool:
    path = Path(tokenstore)
    return path.is_dir() and any(f.is_file() for f in path.iterdir())


def login_and_store(email: str, password: str, tokenstore: str, prompt_mfa=None):
    """Login complet : ne persiste QUE les jetons OAuth, jamais les identifiants.

    garminconnect >= 0.3 : login(tokenstore) écrit lui-même les jetons dans le
    dossier après une connexion par identifiants (plus d'attribut .garth).
    """
    from garminconnect import Garmin  # import local : le réseau reste optionnel

    client = Garmin(email=email, password=password, prompt_mfa=prompt_mfa)
    client.login(tokenstore)
    secure_tokenstore(tokenstore)
    return client


def connect_client(email: str | None, password: str | None, tokenstore: str):
    """Session Garmin Connect : reprend les jetons stockés, sinon login complet."""
    from garminconnect import Garmin  # import local : le réseau reste optionnel

    try:
        client = Garmin()
        client.login(tokenstore)
        return client
    except Exception:
        if not (email and password):
            raise RuntimeError(
                "Aucun jeton Garmin valide : lancer `just login` (recommandé, "
                "identifiants jamais écrits sur disque) — ou renseigner "
                "GARMIN_EMAIL/GARMIN_PASSWORD dans .env.local. Voir la page /setup/."
            )
    return login_and_store(email, password, tokenstore)


def fetch_range(
    client, start: date, end: date
) -> tuple[list[SleepNight], list[DailySummary]]:
    """Récupère nuits et journées pour chaque date de [start, end] (bornes incluses)."""
    nights: list[SleepNight] = []
    days: list[DailySummary] = []
    current = start
    while current <= end:
        iso = current.isoformat()
        night = api_sleep_to_night(client.get_sleep_data(iso))
        if night:
            nights.append(night)
        day = api_stats_to_day(client.get_stats(iso))
        if day:
            days.append(day)
        current += timedelta(days=1)
    return nights, days
