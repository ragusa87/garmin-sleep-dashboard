# garmin-sleep — recettes de développement

default:
    @just --list

# Lancer les tests
test:
    uv run pytest -q

# Tableau de bord avec le dernier export *.zip trouvé ici (ou dans le dossier parent)
run *args:
    #!/usr/bin/env bash
    set -euo pipefail
    shopt -s nullglob
    candidates=(./*.zip ../*.zip)
    if [ ${#candidates[@]} -eq 0 ]; then
        echo "Aucun export *.zip trouvé dans $(realpath .) ni $(realpath ..)" >&2
        exit 1
    fi
    zip=$(ls -t "${candidates[@]}" | head -1)
    echo "Export utilisé : ${zip}"
    uvx --refresh --from . garmin-sleep "${zip}" {{args}}

# Tableau de bord avec un zip précis : just run-zip /chemin/export.zip [--days 30 …]
run-zip zip *args:
    uvx --refresh --from . garmin-sleep "{{zip}}" {{args}}
