#!/usr/bin/env bash
set -euo pipefail

API="https://api.annie-ai.app"

new_user() {
  local email="$1" pass="$2" name="$3" tenant="$4"
  echo "[*] Usuario admin: $email (tenant=$tenant)"
  curl -sS -X POST "$API/api/v1/admin/users" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"$pass\",\"full_name\":\"$name\",\"tenant_id\":\"$tenant\",\"role\":\"admin\"}"
  echo
}

test_login() {
  local email="$1" pass="$2" tenant="$3"
  echo "    - Test login → $email @ $tenant"
  curl -sS -X POST "$API/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"$pass\",\"tenant_id\":\"$tenant\"}" \
  | jq '{ok, role, token_head: (.token | split(".")[0]) }'
}

echo "==> Creando/actualizando usuarios admin"
new_user "felipe.ahumada@soft-innova.com" "F.6a1p3c4" "Felipe Ahumada" "soft-tech"
new_user "annie-ai@soft-innova.com"       "F.6a1p3c4" "Annie-AI Admin" "annie"
new_user "vicky@soft-innova.com"          "F.6a1p3c4" "Vicky-AI Admin" "vicky-ai"
new_user "demo@demo.com"                  "Demo123"   "Demo Admin"     "demo-annie"
new_user "isabel.martinez@soft-innova.com" "Telco123" "Isabel Martinez" "telco-sa"

echo "==> Probando logins"
test_login "felipe.ahumada@soft-innova.com" "F.6a1p3c4" "soft-tech"
test_login "annie-ai@soft-innova.com"       "F.6a1p3c4" "annie"
test_login "vicky@soft-innova.com"          "F.6a1p3c4" "vicky-ai"
test_login "demo@demo.com"                  "Demo123"   "demo-annie"
test_login "isabel.martinez@soft-innova.com" "Telco123" "telco-sa"

echo "==> Listo."
