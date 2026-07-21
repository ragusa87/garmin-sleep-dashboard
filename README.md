# garmin-sleep

> This is a vibe-coded app ! Not reviewed


Tableau de bord local d'analyse du sommeil à partir de vos données Garmin.
Application Django avec base **SQLite** locale ; les données arrivent soit d'un
**export GDPR (zip)**, soit directement de l'**API Garmin Connect**.
Tout se passe sur votre machine : aucune donnée n'est envoyée nulle part
(la synchronisation API parle uniquement aux serveurs Garmin).

## Démarrage rapide (Justfile)

Depuis le dossier `sleep-app`, avec [just](https://github.com/casey/just) :

```bash
just login                           # connexion Garmin interactive (une seule fois)
just sync                            # synchroniser les 30 derniers jours via l'API
just sync 90                         # … ou les 90 derniers jours
just import-zip /chemin/export.zip   # ou : charger un export GDPR dans la base
just run                             # tableau de bord : http://127.0.0.1:8765/
just test                            # suite pytest
```

### Connexion à Garmin Connect

Garmin ne propose pas de clé API personnelle (son API officielle est réservée
aux partenaires approuvés), l'application utilise donc le flux de connexion de
l'app mobile. Deux façons de s'authentifier :

- **`just login` (recommandé)** — e-mail et mot de passe demandés au clavier
  (saisie masquée, MFA supporté), **jamais écrits sur disque** ; seuls les
  jetons de session OAuth sont conservés dans `./.garmin_tokens`
  (permissions `0600`, révocables en changeant le mot de passe du compte).
- **`.env.local`** (usage non interactif : cron, conteneur) — fichier à la
  racine du projet, jamais commité, avec `GARMIN_EMAIL=` et `GARMIN_PASSWORD=` ;
  à éviter si possible, le mot de passe est alors en clair sur disque.

La page `http://127.0.0.1:8765/setup/` (lien « ⚙️ Configuration » du tableau de
bord) affiche ces instructions et l'état de la configuration ; le tableau de
bord y redirige tant que la base est vide. **Tout reste dans le dossier du
projet**, rien n'est lu ni écrit ailleurs (compatible conteneur). Les deux
sources (zip et API) peuvent être combinées librement : l'écriture est un
upsert par date.

## Le tableau de bord

`http://127.0.0.1:8765/` affiche :

- des cartes de synthèse (score moyen, durée, régularité du coucher, jetlag social) ;
- des **conseils personnalisés** basés sur vos propres données, avec les chiffres qui les justifient ;
- les graphiques : stades de sommeil empilés + tendances 7/30 jours, score, heure de coucher,
  profil par jour de la semaine ;
- une section **Oxymétrie nocturne (SpO2)** : minima et moyenne par nuit avec seuils 85/80 %,
  tableau mensuel des désaturations, et alerte si la tendance se dégrade sur 30 jours
  (utile pour le suivi d'un traitement de l'apnée du sommeil — PPC ou orthèse d'avancée
  mandibulaire). Cette section n'apparaît que si la montre a mesuré la SpO2 ;
- les corrélations entre la journée (pas, intensité, stress, Body Battery, FC au repos)
  et la nuit qui suit.

### Options (paramètres d'URL)

| Paramètre | Effet |
|---|---|
| `?days=30` | limiter l'analyse aux N derniers jours |
| `?tz=Europe/Paris` | fuseau horaire local (défaut : Europe/Zurich) |

Le payload brut est disponible en JSON sur `/api/payload.json` (mêmes paramètres),
et les données se parcourent dans l'admin Django (`/admin/`, après
`uv run python manage.py createsuperuser`).

### Variables d'environnement

Définies dans `.env.local` (chargé par les settings, l'environnement réel
garde la priorité) ou dans l'environnement :

| Variable | Effet |
|---|---|
| `GARMIN_EMAIL` / `GARMIN_PASSWORD` | identifiants Garmin Connect (fallback non interactif ; préférer `just login`) |
| `GARMIN_TOKENSTORE` | dossier des jetons (défaut : `./.garmin_tokens`) |
| `DATABASE_NAME` | chemin du fichier SQLite (défaut : `db.sqlite3`) |
| `GARMIN_SLEEP_TZ` | fuseau horaire par défaut (défaut : `Europe/Zurich`) |

## Rafraîchir avec de nouvelles données

- **API** : `just sync` — les derniers jours sont mis à jour dans la base.
- **Export GDPR** : demander un export sur
  <https://www.garmin.com/fr-FR/account/datamanagement/exportdata/>, télécharger
  le zip reçu par e-mail, puis `just import-zip /chemin/export.zip`
  (aucune extraction nécessaire).

## Développement

```bash
cd sleep-app
uv run pytest                     # tests
uv run python manage.py runserver # lancement direct
```

Architecture : le cœur d'analyse reste un paquet de fonctions pures
(`src/garmin_sleep` : `parser.py` → `metrics.py` → `analysis.py` → `tips.py` →
`report.py`), sans dépendance à Django. L'application Django (`config/`, `sleep/`)
l'entoure : modèles ORM (`sleep/models.py`), conversions ORM ↔ dataclasses
(`sleep/converters.py`), upsert (`sleep/services/store.py`), client API
(`sleep/services/garmin_api.py`), commandes `import_zip` / `sync_garmin`, et une
vue qui rend le tableau de bord existant. Chart.js est embarqué
(`static/chart.umd.js`) — le tableau de bord fonctionne hors ligne.
