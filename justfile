# garmin-sleep — recettes de développement

default:
    @just --list

# Lancer les tests
test:
    uv run pytest -q

# Appliquer les migrations (crée db.sqlite3 au premier lancement)
migrate:
    uv run python manage.py migrate

# Tableau de bord Django : http://127.0.0.1:8765/
run: migrate
    uv run python manage.py runserver 127.0.0.1:8765

# Importer un export Garmin GDPR dans la base : just import-zip /chemin/export.zip
import-zip zip: migrate
    uv run python manage.py import_zip "{{zip}}"

# Connexion interactive Garmin Connect : identifiants jamais écrits sur disque,
# seuls les jetons OAuth sont stockés dans ./.garmin_tokens (0600)
login:
    uv run python manage.py garmin_login

# Synchroniser les N derniers jours depuis l'API Garmin Connect (défaut : 30)
# Prérequis : `just login` (recommandé) ou .env.local — voir la page /setup/
sync days="30": migrate
    uv run python manage.py sync_garmin --days {{days}}
