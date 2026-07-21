"""manage.py sync_garmin — récupère les derniers jours via l'API Garmin Connect."""

from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...models import Source
from ...services import store
from ...services.garmin_api import connect_client, fetch_range


class Command(BaseCommand):
    help = (
        "Synchronise nuits et journées depuis l'API Garmin Connect "
        "(identifiants via GARMIN_EMAIL / GARMIN_PASSWORD, jetons réutilisés ensuite)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=30, metavar="N",
            help="nombre de jours à synchroniser en remontant depuis aujourd'hui (défaut : 30)",
        )

    def handle(self, *args, **options):
        try:
            client = connect_client(
                settings.GARMIN_EMAIL, settings.GARMIN_PASSWORD, settings.GARMIN_TOKENSTORE
            )
        except Exception as exc:
            raise CommandError(f"connexion Garmin impossible : {exc}") from exc

        end = date.today()
        start = end - timedelta(days=options["days"] - 1)
        self.stdout.write(f"Synchronisation du {start} au {end}…")
        try:
            nights, days = fetch_range(client, start, end)
        except Exception as exc:
            raise CommandError(f"échec de la récupération : {exc}") from exc

        n_nights = store.upsert_nights(nights, Source.API)
        n_days = store.upsert_days(days, Source.API)
        self.stdout.write(
            self.style.SUCCESS(f"{n_nights} nuit(s) et {n_days} journée(s) synchronisées.")
        )
