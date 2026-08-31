#!/usr/bin/env bash
# Pack secrets for AirDrop → Mac Mini (RU) bootstrap.
# Usage (from repo root):
#   ./scripts/pack-mac-mini-handoff.sh
#   ./scripts/pack-mac-mini-handoff.sh --with-db
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WITH_DB=0
OUT="${HOME}/Desktop/whiteshop-mac-mini-handoff.tgz"
for arg in "$@"; do
  case "$arg" in
    --with-db) WITH_DB=1 ;;
    --out=*) OUT="${arg#--out=}" ;;
    -h|--help)
      echo "Usage: $0 [--with-db] [--out=/path/to/handoff.tgz]"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg" >&2
      exit 1
      ;;
  esac
done

die() { echo "error: $*" >&2; exit 1; }
need() { [[ -f "$1" ]] || die "missing required file: $1"; }

need "$ROOT/.env"
need "$ROOT/data/telegram.session"
need "$ROOT/infra/tunnel/config.yml"
need "$ROOT/infra/vpn/xray.config.json"

# Refuse placeholder xray configs
if grep -qE 'VPN_SERVER_HOST|VPN_UUID|VPN_PUBLIC_KEY|VPN_SNI_DOMAIN' "$ROOT/infra/vpn/xray.config.json"; then
  die "infra/vpn/xray.config.json still has VPN_* placeholders — fill VLESS Reality first (see infra/vpn/README.md)"
fi

TUNNEL_ID="$(awk '/^tunnel:/{print $2; exit}' "$ROOT/infra/tunnel/config.yml")"
[[ -n "$TUNNEL_ID" && "$TUNNEL_ID" != "TUNNEL_ID" ]] || die "could not read tunnel id from infra/tunnel/config.yml"

CREDS_SRC=""
for candidate in \
  "${HOME}/.cloudflared/${TUNNEL_ID}.json" \
  "$(awk -F': ' '/^credentials-file:/{print $2; exit}' "$ROOT/infra/tunnel/config.yml")"; do
  if [[ -n "$candidate" && -f "$candidate" ]]; then
    CREDS_SRC="$candidate"
    break
  fi
done
[[ -n "$CREDS_SRC" ]] || die "tunnel credentials not found (~/.cloudflared/${TUNNEL_ID}.json)"

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/whiteshop-handoff.XXXXXX")"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

mkdir -p "$STAGE/data" "$STAGE/infra/tunnel" "$STAGE/infra/vpn" "$STAGE/credentials" "$STAGE/db"

cp "$ROOT/.env" "$STAGE/.env"
chmod 600 "$STAGE/.env"
cp "$ROOT/data/telegram.session" "$STAGE/data/telegram.session"
chmod 600 "$STAGE/data/telegram.session"
if [[ -f "$ROOT/data/telegram.session-journal" ]]; then
  cp "$ROOT/data/telegram.session-journal" "$STAGE/data/telegram.session-journal"
  chmod 600 "$STAGE/data/telegram.session-journal"
fi

cp "$ROOT/infra/vpn/xray.config.json" "$STAGE/infra/vpn/xray.config.json"
chmod 600 "$STAGE/infra/vpn/xray.config.json"

cp "$CREDS_SRC" "$STAGE/credentials/${TUNNEL_ID}.json"
chmod 600 "$STAGE/credentials/${TUNNEL_ID}.json"

# Relative credentials path inside archive; bootstrap rewrites to $HOME/.cloudflared
{
  echo "tunnel: ${TUNNEL_ID}"
  echo "credentials-file: ./credentials/${TUNNEL_ID}.json"
  echo ""
  # Keep ingress block from existing config (from first blank-line-separated ingress:)
  awk '
    BEGIN { keep=0 }
    /^ingress:/ { keep=1 }
    keep { print }
  ' "$ROOT/infra/tunnel/config.yml"
} > "$STAGE/infra/tunnel/config.yml"
chmod 600 "$STAGE/infra/tunnel/config.yml"

if [[ "$WITH_DB" -eq 1 ]]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck source=/dev/null
  source <(grep -E '^(POSTGRES_USER|POSTGRES_PASSWORD|POSTGRES_DB)=' "$ROOT/.env" | sed 's/\r$//')
  set +a
  PG_USER="${POSTGRES_USER:-whiteshop}"
  PG_DB="${POSTGRES_DB:-whiteshop}"
  echo "Dumping postgres (${PG_DB}) …"
  if docker compose -f "$ROOT/docker-compose.yml" ps --status running --services 2>/dev/null | grep -qx postgres; then
    docker compose -f "$ROOT/docker-compose.yml" exec -T postgres \
      pg_dump -U "$PG_USER" -d "$PG_DB" -Fc \
      > "$STAGE/db/whiteshop.dump" \
      || die "pg_dump via docker failed — is postgres up? (make up)"
  else
    PGPASSWORD="${POSTGRES_PASSWORD:?}" pg_dump \
      -h 127.0.0.1 -p 5433 \
      -U "$PG_USER" \
      -d "$PG_DB" \
      -Fc \
      -f "$STAGE/db/whiteshop.dump" \
      || die "pg_dump failed — start postgres (make up) or install client tools"
  fi
  chmod 600 "$STAGE/db/whiteshop.dump"
fi

{
  echo "whiteshop mac-mini handoff"
  echo "created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "tunnel_id=${TUNNEL_ID}"
  echo "with_db=${WITH_DB}"
  echo "files:"
  (cd "$STAGE" && find . -type f | sort)
} > "$STAGE/MANIFEST.txt"

mkdir -p "$(dirname "$OUT")"
tar -C "$STAGE" -czf "$OUT" .
chmod 600 "$OUT"

echo ""
echo "Packed: $OUT"
echo "AirDrop this file to the Mac Mini, then on the Mini:"
echo "  cd ~/Projects/tech-sales   # or clone first"
echo "  ./scripts/mac-mini-bootstrap.sh \"$OUT\""
echo "Delete the archive from Desktop/Downloads after a successful bootstrap."
