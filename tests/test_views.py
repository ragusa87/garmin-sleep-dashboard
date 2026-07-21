"""Vues Django : tableau de bord et payload JSON depuis la base."""

import pytest

from sleep.services import store

from test_store import make_day, make_night


@pytest.mark.django_db
def test_dashboard_empty_db_redirects_to_setup(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.url == "/setup/"


@pytest.mark.django_db
def test_setup_page_recommends_interactive_login(client, settings, tmp_path):
    settings.GARMIN_EMAIL = None
    settings.GARMIN_PASSWORD = None
    settings.GARMIN_TOKENSTORE = str(tmp_path / "tokens")  # absents
    html = client.get("/setup/").content.decode()
    assert "just login" in html
    assert ".env.local" in html
    assert "clé API personnelle" in html
    assert "absents" in html


@pytest.mark.django_db
def test_setup_page_shows_state_without_leaking_secrets(client, settings, tmp_path):
    settings.GARMIN_EMAIL = "mon-adresse-reelle@prive.example"
    settings.GARMIN_PASSWORD = "secret"
    tokens = tmp_path / "tokens"
    tokens.mkdir()
    (tokens / "oauth2_token.json").write_text("{}")
    settings.GARMIN_TOKENSTORE = str(tokens)
    store.upsert_nights([make_night()], source="api")

    html = client.get("/setup/").content.decode()
    assert "présents" in html  # jetons et identifiants détectés
    assert "secret" not in html  # jamais de secret affiché
    assert "mon-adresse-reelle" not in html
    assert ">1</strong>" in html  # nuits en base


@pytest.mark.django_db
def test_dashboard_renders_selfcontained_html(client):
    store.upsert_nights([make_night("2026-07-17"), make_night("2026-07-18")], source="api")
    store.upsert_days([make_day("2026-07-17"), make_day("2026-07-18")], source="api")

    resp = client.get("/")
    html = resp.content.decode()
    assert resp.status_code == 200
    assert "2026-07-18" in html
    assert '<a href="/setup/">' in html  # lien vers la configuration
    assert "http://" not in html.replace("http://www.w3.org", "")  # pas de CDN

    resp = client.get("/", {"days": "1", "tz": "Europe/Zurich"})
    assert resp.status_code == 200


@pytest.mark.django_db
def test_dashboard_ignores_invalid_days_param(client):
    store.upsert_nights([make_night("2026-07-17"), make_night("2026-07-18")], source="api")
    store.upsert_days([make_day("2026-07-17"), make_day("2026-07-18")], source="api")

    for days in ("-1", "0", "abc"):
        resp = client.get("/", {"days": days})
        assert resp.status_code == 200, f"days={days}"
        assert "2026-07-17" in resp.content.decode()  # limite ignorée → tout l'historique


@pytest.mark.django_db
def test_payload_json(client):
    store.upsert_nights([make_night()], source="api")
    resp = client.get("/api/payload.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"]["n_nights"] == 1
    assert data["nights"][0]["date"] == "2026-07-18"


@pytest.mark.django_db
def test_payload_json_empty_db_is_404(client):
    assert client.get("/api/payload.json").status_code == 404
