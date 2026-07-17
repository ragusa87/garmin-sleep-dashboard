"""Point d'entrée : garmin-sleep <export.zip>"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .analysis import analyze
from .parser import load_export
from .report import build_html, build_payload
from .server import serve
from .tips import generate_tips


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="garmin-sleep",
        description="Analyse du sommeil à partir d'un export Garmin (zip GDPR) — "
        "tableau de bord local, aucune donnée n'est envoyée.",
    )
    ap.add_argument("zip", type=Path, help="chemin vers l'export Garmin (.zip)")
    ap.add_argument("--port", type=int, default=8765, help="port du serveur local (défaut : 8765)")
    ap.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    ap.add_argument("--days", type=int, default=None, metavar="N", help="limiter aux N derniers jours")
    ap.add_argument("--tz", default="Europe/Zurich", help="fuseau horaire local (défaut : Europe/Zurich)")
    args = ap.parse_args(argv)

    if not args.zip.is_file():
        ap.error(f"fichier introuvable : {args.zip}")
    try:
        tz = ZoneInfo(args.tz)
    except ZoneInfoNotFoundError:
        ap.error(f"fuseau horaire inconnu : {args.tz}")

    export = load_export(args.zip)
    if not export.nights:
        print(
            "Aucune donnée de sommeil trouvée dans ce zip "
            "(attendu : DI_CONNECT/DI-Connect-Wellness/*_sleepData.json).",
            file=sys.stderr,
        )
        return 1

    analysis = analyze(export, tz, days_limit=args.days)
    tips = generate_tips(analysis)
    html = build_html(build_payload(analysis, tips))
    print(f"{len(analysis.nights)} nuits analysées, {len(tips)} conseil(s).")
    serve(html, port=args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
