# AGENTS.md — garmin-sleep

Instructions pour les agents IA travaillant sur ce projet.

## Le projet en une phrase

Application **Django + SQLite** locale : les données de sommeil arrivent d'un export
Garmin GDPR (zip) **ou** de l'API Garmin Connect, sont stockées en base, et un
tableau de bord HTML avec conseils personnalisés en **français** est servi par Django.

## Commandes

```bash
just test                  # suite pytest (rapide, < 1 s)
just run                   # migrate + runserver sur http://127.0.0.1:8765/
just login                 # connexion Garmin interactive (jetons seuls stockés)
just sync [90]             # synchroniser N jours via l'API Garmin Connect
just import-zip export.zip # charger un export GDPR dans la base
uv run pytest tests/test_tips.py -q   # un seul fichier de tests
```

Pas de docker ici (exception à la convention habituelle) : uv directement.
Authentification API : `just login` (recommandé — getpass + MFA, identifiants
jamais sur disque, jetons 0600 dans `./.garmin_tokens`) ; fallback non
interactif `GARMIN_EMAIL`/`GARMIN_PASSWORD` dans `.env.local` (chargé par
`config/env.py`, jamais commité). Garmin n'a pas de clé API personnelle (API
officielle réservée aux partenaires). La page `/setup/` documente tout ça,
et le tableau de bord y lie (« ⚙️ Configuration », via `build_html(setup_url=…)`).

## Architecture (flux de données)

```
zip GDPR ──► garmin_sleep.parser ─┐
                                  ├─► sleep/services/store.py (upsert) ─► SQLite
API Garmin ► sleep/services/garmin_api.py ┘
SQLite ─► sleep/converters.py ─► garmin_sleep.analysis ─► tips ─► report ─► vue Django
```

Deux couches strictement séparées :

- **`src/garmin_sleep`** — cœur pur, AUCUNE dépendance à Django. `models.py`
  (dataclasses gelées), `parser.py` (lecture tolérante du zip), `metrics.py`
  (fonctions pures, tz explicite), `analysis.py` (objet `Analysis` gelé),
  `tips.py` (une règle = une fonction dans `RULES`), `report.py` (payload + HTML).
- **Application Django** — `config/` (réglages, SQLite `db.sqlite3`) et `sleep/` :
  - `models.py` — miroir ORM des dataclasses, `unique=True` sur `calendar_date`,
    champ `source` (`zip`/`api`). Aucune logique métier.
  - `converters.py` — ORM ↔ dataclasses ; `load_export_from_db()` reconstruit
    l'`ExportData` attendu par `analyze()`.
  - `services/store.py` — upsert idempotent par `calendar_date`, point d'entrée
    unique des deux sources.
  - `services/garmin_api.py` — mappers **purs** JSON API → dataclasses (testables
    sans réseau) séparés du client (`connect_client`/`fetch_range`, seuls points
    de contact réseau ; import de `garminconnect` local à la fonction).
  - `management/commands/` — `import_zip`, `sync_garmin`.
  - `views.py` — reconstruit l'analyse depuis la base et rend le HTML existant
    (`report.build_html`) ; `?days=` et `?tz=` en paramètres d'URL. Base vide →
    redirection vers `/setup/` (instructions `.env.local`, état de la config).
- `garmin_sleep/templates/dashboard.html` — page unique ; placeholders
  `/*{{CHARTJS}}*/` et `"{{PAYLOAD}}"` remplacés par `report.build_html()`.
- `garmin_sleep/static/chart.umd.js` — Chart.js v4 vendorisé. **Jamais de CDN ni de
  ressource externe** : un test (`test_html_selfcontained`) garantit le hors ligne.
- `cli.py`/`server.py` — ancien mode standalone (zip → serveur éphémère), conservé.

## Conventions non négociables

1. **Tests écrits en même temps que le code**, pas après. Chaque nouvelle métrique,
   règle, champ de payload, mapper API ou vue a son test (fixtures synthétiques :
   zip dans `conftest.py`, JSON API dans `test_garmin_api.py` ; `pytest-django`
   avec `@pytest.mark.django_db` pour tout ce qui touche l'ORM).
2. **Unités petites et découplées** : pas d'état global, tz et données en paramètres.
   Le cœur `garmin_sleep` ne doit jamais importer Django ni `garminconnect`.
3. Tout texte visible par l'utilisateur (dashboard, conseils, commandes, README)
   est en **français**.
4. Dépendances runtime : `django`, `garminconnect`, `tzdata`. Ne rien ajouter
   sans raison forte.
5. **Bump de version** (`pyproject.toml` + `__init__.py`) à chaque changement livré.
6. Jamais d'identifiants en dur : `.env.local` ou variables d'environnement
   (`GARMIN_EMAIL`, `GARMIN_PASSWORD`), jetons via garth dans `GARMIN_TOKENSTORE`.
7. **Aucune lecture/écriture hors du dossier du projet** (l'app doit pouvoir
   tourner en conteneur) : secrets dans `./.env.local`, jetons dans
   `./.garmin_tokens`, base dans `./db.sqlite3`.

## Pièges du domaine (appris sur les vraies données)

- `calendarDate` = date du **matin** (réveil) ; le coucher appartient à la veille.
- Timestamps Garmin en **GMT** : export zip au format `"2026-07-17T00:32:15.0"`,
  API en **epoch millisecondes** — `garmin_api._parse_ts` accepte les deux.
  Conversion locale via `zoneinfo` (défaut Europe/Zurich, `?tz=`).
- Régularité du coucher : axe circulaire « minutes depuis 18:00 »
  (`bedtime_offset_min`), sinon 23:30 et 00:30 semblent distants de 23 h.
- `remSleepSeconds`, `sleepScores`, `spo2SleepSummary` peuvent manquer (anciens
  firmwares) ; un fichier sleepData peut être juste `[{"retro": false}]` ; côté
  API, un jour sans mesure a un `dailySleepDTO` sans timestamps → skip.
- Les scores API sont des objets `{"value": …}` (`overall`, `totalDuration`,
  `remPercentage`, `deepPercentage`), pas les entiers plats de l'export
  (`overallScore`, …) — `_score_value` tolère les deux.
- Les noms de fichiers sleepData contiennent un id utilisateur numérique, les
  fichiers UDS non ; les périodes des fichiers se chevauchent aux bornes.
  En base : upsert par `calendar_date`, le dernier écrit gagne.
- `restingHeartRate` = 0 signifie « montre non portée » → traiter comme None
  (règle appliquée aux deux sources).
- SpO2 poignet : bruité ; raisonner en récurrence/tendance (parts de nuits < 85 %,
  < 80 %), jamais sur une valeur isolée. Corrélations : `min_n = 14`.
- Santé : les conseils informent, ils ne prescrivent pas — les cas médicaux
  (apnée, désaturations) renvoient vers un professionnel.
