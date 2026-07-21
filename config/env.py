"""Chargement minimal d'un fichier .env (stdlib uniquement, testable seul)."""

from __future__ import annotations

import os
from pathlib import Path


def read_env_file(path: Path | str) -> dict[str, str]:
    """Parse un fichier KEY=VALUE ; lignes vides, commentaires et guillemets tolérés."""
    values: dict[str, str] = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            values[key] = value
    return values


def load_env_file(path: Path | str) -> None:
    """Injecte le fichier dans os.environ ; l'environnement réel garde la priorité."""
    for key, value in read_env_file(path).items():
        os.environ.setdefault(key, value)
