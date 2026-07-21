"""Garde-fous des réglages : DJANGO_SECRET_KEY obligatoire hors debug."""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _import_settings(extra_env: dict[str, str]) -> subprocess.CompletedProcess:
    # Sous-processus : l'import de config.settings est un effet de bord global,
    # impossible à rejouer proprement dans le processus de test.
    env = {**os.environ, **extra_env}
    return subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def test_secret_key_required_when_debug_off():
    # DJANGO_SECRET_KEY="" prime sur un éventuel .env.local (setdefault)
    proc = _import_settings({"DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": ""})
    assert proc.returncode != 0
    assert "DJANGO_SECRET_KEY" in proc.stderr


def test_dev_fallback_key_allowed_in_debug():
    proc = _import_settings({"DJANGO_DEBUG": "1", "DJANGO_SECRET_KEY": ""})
    assert proc.returncode == 0, proc.stderr


def test_explicit_secret_key_accepted_when_debug_off():
    proc = _import_settings({"DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": "s3cret"})
    assert proc.returncode == 0, proc.stderr
