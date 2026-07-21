"""Vues : le tableau de bord existant, alimenté par la base SQLite."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from garmin_sleep.analysis import analyze
from garmin_sleep.report import build_html, build_payload
from garmin_sleep.tips import generate_tips

from . import models as orm
from .converters import load_export_from_db
from .services.garmin_api import has_tokens


def _build(request) -> dict | None:
    """Payload du tableau de bord depuis la base ; None si base vide."""
    try:
        tz = ZoneInfo(request.GET.get("tz", settings.TIME_ZONE))
    except ZoneInfoNotFoundError:
        tz = ZoneInfo(settings.TIME_ZONE)
    try:
        days_limit = int(request.GET["days"])
    except (KeyError, ValueError):
        days_limit = None
    else:
        if days_limit < 1:  # ?days=0 ou négatif → toutes les nuits
            days_limit = None

    export = load_export_from_db()
    if not export.nights:
        return None
    analysis = analyze(export, tz, days_limit=days_limit)
    return build_payload(analysis, generate_tips(analysis))


def dashboard(request) -> HttpResponse:
    payload = _build(request)
    if payload is None:
        return redirect("sleep:setup")
    return HttpResponse(build_html(payload, setup_url=reverse("sleep:setup")))


def setup(request) -> HttpResponse:
    """Instructions de configuration (.env.local) et état de l'application."""
    return render(
        request,
        "sleep/setup.html",
        {
            "has_credentials": bool(settings.GARMIN_EMAIL and settings.GARMIN_PASSWORD),
            "has_tokens": has_tokens(settings.GARMIN_TOKENSTORE),
            "n_nights": orm.SleepNight.objects.count(),
            "tokenstore": settings.GARMIN_TOKENSTORE,
        },
    )


def payload_json(request) -> JsonResponse:
    payload = _build(request)
    if payload is None:
        return JsonResponse({"error": "aucune donnée en base"}, status=404)
    return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
