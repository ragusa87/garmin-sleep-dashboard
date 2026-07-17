# garmin-sleep

> This is a vibe-coded app ! Not reviewed


Tableau de bord local d'analyse du sommeil à partir d'un export de données Garmin (GDPR).
Tout se passe sur votre machine : aucune donnée n'est envoyée nulle part.

## Utilisation

```bash
uvx --from /chemin/vers/sleep-app garmin-sleep /chemin/vers/export-garmin.zip
```

Le navigateur s'ouvre sur `http://127.0.0.1:8765/` avec :

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

### Options

| Option | Effet |
|---|---|
| `--port 8080` | changer le port du serveur local (défaut : 8765) |
| `--no-browser` | ne pas ouvrir le navigateur, afficher seulement l'URL |
| `--days 30` | limiter l'analyse aux N derniers jours |
| `--tz Europe/Paris` | fuseau horaire local (défaut : Europe/Zurich) |

## Rafraîchir avec de nouvelles données

1. Demander un nouvel export : <https://www.garmin.com/fr-FR/account/datamanagement/exportdata/>
2. Télécharger le zip reçu par e-mail (aucune extraction nécessaire).
3. Relancer la commande `uvx` ci-dessus en pointant sur le nouveau zip.

## Développement

```bash
cd sleep-app
uv run pytest          # tests
uv run garmin-sleep …  # lancement direct
```

Architecture : `parser.py` (lecture tolérante du zip) → `metrics.py` (fonctions pures) →
`analysis.py` (agrégation) → `tips.py` (règles de conseils) → `report.py` (payload + HTML) →
`server.py` (HTTP local). Chart.js est embarqué dans le paquet (`static/chart.umd.js`) —
le tableau de bord fonctionne hors ligne.
