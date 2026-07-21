"""manage.py garmin_login — connexion interactive, seuls les jetons sont stockés."""

import getpass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...services.garmin_api import login_and_store


class Command(BaseCommand):
    help = (
        "Connexion interactive à Garmin Connect : identifiants saisis au clavier, "
        "jamais écrits sur disque ; seuls les jetons OAuth sont stockés (0600)."
    )

    def handle(self, *args, **options):
        email = input("E-mail Garmin Connect : ").strip()
        password = getpass.getpass("Mot de passe (non affiché, non stocké) : ")
        if not (email and password):
            raise CommandError("e-mail et mot de passe requis.")
        try:
            login_and_store(
                email,
                password,
                settings.GARMIN_TOKENSTORE,
                prompt_mfa=lambda: input("Code MFA : ").strip(),
            )
        except Exception as exc:
            if "429" in str(exc):
                raise CommandError(
                    "Garmin limite les connexions depuis cette IP (HTTP 429). "
                    "Ce n'est pas un problème d'identifiants : attendre ~1 heure "
                    "(ou changer de réseau) puis relancer `just login`. Une fois "
                    "obtenus, les jetons restent valables environ un an."
                ) from exc
            raise CommandError(f"connexion refusée : {exc}") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Connecté. Jetons stockés dans {settings.GARMIN_TOKENSTORE} — "
                "lancer `just sync` pour récupérer les données."
            )
        )
