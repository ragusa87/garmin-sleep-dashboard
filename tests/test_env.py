"""Parseur .env.local (config/env.py)."""

import os

from config.env import load_env_file, read_env_file


def test_read_env_file_parses_values(tmp_path):
    f = tmp_path / ".env.local"
    f.write_text(
        "# commentaire\n"
        "\n"
        "GARMIN_EMAIL=vous@example.com\n"
        "GARMIN_PASSWORD='avec espace et #'\n"
        'QUOTED="double"\n'
        "ligne sans egal\n"
        " ESPACES = valeur \n"
    )
    assert read_env_file(f) == {
        "GARMIN_EMAIL": "vous@example.com",
        "GARMIN_PASSWORD": "avec espace et #",
        "QUOTED": "double",
        "ESPACES": "valeur",
    }


def test_read_env_file_missing_file_is_empty(tmp_path):
    assert read_env_file(tmp_path / "absent") == {}


def test_load_env_file_does_not_override_real_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DEJA_LA", "env")
    monkeypatch.delenv("NOUVELLE", raising=False)
    f = tmp_path / ".env.local"
    f.write_text("DEJA_LA=fichier\nNOUVELLE=fichier\n")

    load_env_file(f)
    try:
        assert os.environ["DEJA_LA"] == "env"
        assert os.environ["NOUVELLE"] == "fichier"
    finally:
        os.environ.pop("NOUVELLE", None)
