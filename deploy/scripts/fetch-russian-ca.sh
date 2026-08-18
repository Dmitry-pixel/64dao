#!/usr/bin/env bash
#
# Загрузка корневого и выпускающего сертификатов НУЦ Минцифры России
# в backend/certs/ для сборки backend-образа.
#
# Вендорим файлы в репозиторий, а не качаем при docker build:
#   - сборка не зависит от доступности gu-st.ru;
#   - смена сертификата видна в git diff;
#   - отпечатки сверяются один раз и фиксируются.
#
# Запуск из корня репозитория:
#   ./deploy/scripts/fetch-russian-ca.sh
#
set -euo pipefail

ROOT_URL="https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt"
SUB_URL="https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="$REPO_ROOT/backend/certs"
mkdir -p "$DEST"

fetch() {
  local url="$1" out="$2"
  echo "→ $url"
  curl -fsSL --retry 3 --retry-delay 2 -o "$out.tmp" "$url"

  if ! openssl x509 -in "$out.tmp" -noout >/dev/null 2>&1; then
    echo "ОШИБКА: $url вернул не PEM-сертификат." >&2
    head -c 200 "$out.tmp" >&2; echo >&2
    rm -f "$out.tmp"; exit 1
  fi

  if ! openssl x509 -in "$out.tmp" -noout -text | grep -q "CA:TRUE"; then
    echo "ОШИБКА: $url — не CA-сертификат." >&2
    rm -f "$out.tmp"; exit 1
  fi

  mv "$out.tmp" "$out"
}

fetch "$ROOT_URL" "$DEST/russian_trusted_root_ca.crt"
fetch "$SUB_URL"  "$DEST/russian_trusted_sub_ca.crt"

echo
echo "=== СВЕРЬТЕ с https://www.gosuslugi.ru/crt ==="
for f in "$DEST"/russian_trusted_root_ca.crt "$DEST"/russian_trusted_sub_ca.crt; do
  echo "--- $(basename "$f")"
  openssl x509 -in "$f" -noout -subject -issuer -serial -dates -fingerprint -sha256
  echo
done
