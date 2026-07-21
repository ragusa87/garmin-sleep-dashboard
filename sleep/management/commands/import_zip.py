"""manage.py import_zip <export.zip> — charge un export GDPR dans la base."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from garmin_sleep.parser import load_export

from ...models import Source
from ...services import store


class Command(BaseCommand):
    help = "Importe un export Garmin GDPR (zip) dans la base SQLite."

    def add_arguments(self, parser):
        parser.add_argument("zip", type=Path, help="chemin vers l'export Garmin (.zip)")

    def handle(self, *args, **options):
        zip_path: Path = options["zip"]
        if not zip_path.is_file():
            raise CommandError(f"fichier introuvable : {zip_path}")

        export = load_export(zip_path)
        if not export.nights:
            raise CommandError(
                "Aucune donnée de sommeil trouvée dans ce zip "
                "(attendu : DI_CONNECT/DI-Connect-Wellness/*_sleepData.json)."
            )

        n_nights = store.upsert_nights(export.nights, Source.ZIP)
        n_days = store.upsert_days(list(export.days.values()), Source.ZIP)
        self.stdout.write(
            self.style.SUCCESS(f"{n_nights} nuit(s) et {n_days} journée(s) importées.")
        )
