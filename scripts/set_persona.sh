#!/usr/bin/env bash
set -euo pipefail

ENGINE_URL="${ENGINE_URL:-http://localhost:5001}"
USER_ID="${1:?Usage: set_persona <user_id> O C E A N}"
O="${2:?}"
C="${3:?}"
E="${4:?}"
A="${5:?}"
N="${6:?}"

# Crea si no existe (idempotente)
curl -s -X POST "$ENGINE_URL/api/personas/" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\"}" >/dev/null || true

update() {
  local trait="$1"; local value="$2"
  curl -s -X PUT "$ENGINE_URL/api/personas/$USER_ID" \
    -H "Content-Type: application/json" \
    -d "{\"trait\":\"$trait\",\"value\":$value}" >/dev/null
}

update openness          "$O"
update conscientiousness "$C"
update extraversion      "$E"
update agreeableness     "$A"
update neuroticism       "$N"
echo "Persona $USER_ID actualizada: O=$O C=$C E=$E A=$A N=$N"
