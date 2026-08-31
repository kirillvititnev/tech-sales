#!/usr/bin/env bash
# Bootstrap White Shop on Mac Mini (RU): Docker + Compose(VPN) + Cloudflare Tunnel.
# Usage (from anywhere; prefers existing clone, else clones):
#   ./scripts/mac-mini-bootstrap.sh ~/Downloads/whiteshop-mac-mini-handoff.tgz
set -euo pipefail

HANDOFF="${1:-}"
BRANCH="${WHITESHOP_BRANCH:-feat/bests-multibrand-parser}"
REPO_URL="${WHITESHOP_REPO_URL:-https://github.com/kirillvititnev/tech-sales.git}"
DEFAULT_ROOT="${HOME}/Projects/tech-sales"

die() { echo "error: $*" >&2; exit 1; }
info() { echo "==> $*"; }

[[ -n "$HANDOFF" ]] || die "usage: $0 /path/to/whiteshop-mac-mini-handoff.tgz"
[[ -f "$HANDOFF" ]] || die "handoff archive not found: $HANDOFF"
[[ "$(uname -s)" == "Darwin" ]] || die "this script is for macOS only"

# --- locate / clone repo ---
if [[ -f "./docker-compose.yml" && -f "./scripts/mac-mini-bootstrap.sh" ]]; then
  ROOT="$(cd . && pwd)"
elif [[ -f "${DEFAULT_ROOT}/docker-compose.yml" ]]; then
  ROOT="$DEFAULT_ROOT"
else
  info "Cloning ${REPO_URL} (${BRANCH}) → ${DEFAULT_ROOT}"
  mkdir -p "$(dirname "$DEFAULT_ROOT")"
  git clone --branch "$BRANCH" "$REPO_URL" "$DEFAULT_ROOT"
  ROOT="$DEFAULT_ROOT"
fi
cd "$ROOT"
info "Repo: $ROOT"
git fetch origin "$BRANCH" 2>/dev/null || true
git checkout "$BRANCH" 2>/dev/null || true
git pull --ff-only origin "$BRANCH" 2>/dev/null || true

# --- Homebrew ---
if ! command -v brew >/dev/null 2>&1; then
  info "Installing Homebrew (may prompt for password)"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
fi
command -v brew >/dev/null 2>&1 || die "brew not on PATH after install — open a new terminal and re-run"

# Ensure brew env in this shell
if [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /usr/local/bin/brew ]]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi

info "Installing Docker Desktop + cloudflared + git (idempotent)"
brew install --cask docker >/dev/null || brew install --cask docker
brew install cloudflared git >/dev/null || brew install cloudflared git

# --- Docker Desktop ---
if ! docker info >/dev/null 2>&1; then
  info "Starting Docker Desktop — accept the privilege prompt if shown"
  open -a Docker || die "could not open Docker.app — install Docker Desktop manually, then re-run"
  echo "Waiting for Docker engine…"
  for _ in $(seq 1 90); do
    if docker info >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi
docker info >/dev/null 2>&1 || die "Docker is not ready. Open Docker Desktop, finish setup, then re-run this script."

CLOUDFLARED="$(command -v cloudflared)" || die "cloudflared not found after brew install"
info "cloudflared: $CLOUDFLARED"

# --- unpack handoff ---
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/whiteshop-bootstrap.XXXXXX")"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

info "Unpacking handoff"
tar -C "$STAGE" -xzf "$HANDOFF"
[[ -f "$STAGE/.env" ]] || die "handoff missing .env"
[[ -f "$STAGE/data/telegram.session" ]] || die "handoff missing data/telegram.session"
[[ -f "$STAGE/infra/vpn/xray.config.json" ]] || die "handoff missing infra/vpn/xray.config.json"
[[ -f "$STAGE/infra/tunnel/config.yml" ]] || die "handoff missing infra/tunnel/config.yml"
if grep -qE 'VPN_SERVER_HOST|VPN_UUID|VPN_PUBLIC_KEY' "$STAGE/infra/vpn/xray.config.json"; then
  die "xray.config.json still has placeholders"
fi

mkdir -p "$ROOT/data" "$ROOT/infra/tunnel" "$ROOT/infra/vpn" "${HOME}/.cloudflared" "$ROOT/uploads"

cp "$STAGE/.env" "$ROOT/.env"
chmod 600 "$ROOT/.env"
cp "$STAGE/data/telegram.session" "$ROOT/data/telegram.session"
chmod 600 "$ROOT/data/telegram.session"
if [[ -f "$STAGE/data/telegram.session-journal" ]]; then
  cp "$STAGE/data/telegram.session-journal" "$ROOT/data/telegram.session-journal"
  chmod 600 "$ROOT/data/telegram.session-journal"
fi
cp "$STAGE/infra/vpn/xray.config.json" "$ROOT/infra/vpn/xray.config.json"
chmod 600 "$ROOT/infra/vpn/xray.config.json"

TUNNEL_ID="$(awk '/^tunnel:/{print $2; exit}' "$STAGE/infra/tunnel/config.yml")"
CRED_SRC=""
if [[ -f "$STAGE/credentials/${TUNNEL_ID}.json" ]]; then
  CRED_SRC="$STAGE/credentials/${TUNNEL_ID}.json"
else
  CRED_SRC="$(find "$STAGE/credentials" -name '*.json' -type f | head -1 || true)"
fi
[[ -n "$CRED_SRC" && -f "$CRED_SRC" ]] || die "handoff missing tunnel credentials under credentials/"
CRED_NAME="$(basename "$CRED_SRC")"
cp "$CRED_SRC" "${HOME}/.cloudflared/${CRED_NAME}"
chmod 600 "${HOME}/.cloudflared/${CRED_NAME}"

# Write tunnel config with absolute credentials path for this Mac
{
  echo "tunnel: ${TUNNEL_ID}"
  echo "credentials-file: ${HOME}/.cloudflared/${CRED_NAME}"
  echo ""
  awk 'BEGIN{keep=0} /^ingress:/{keep=1} keep{print}' "$STAGE/infra/tunnel/config.yml"
} > "$ROOT/infra/tunnel/config.yml"
chmod 600 "$ROOT/infra/tunnel/config.yml"

# TELEGRAM_PROXY for docker network xray service
info "Setting TELEGRAM_PROXY=socks5://xray:1080 in .env"
python3 - <<PY
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "secure_env", "${ROOT}/scripts/secure_env.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

path = Path("${ROOT}") / ".env"
text = path.read_text(encoding="utf-8")
text = mod.set_key(text, "TELEGRAM_PROXY", "socks5://xray:1080")
hosts = mod.get_key(text, "ALLOWED_HOSTS") or ""
parts = [h.strip() for h in hosts.split(",") if h.strip()]
if "api" not in parts:
    parts.append("api")
    text = mod.set_key(text, "ALLOWED_HOSTS", ",".join(parts))
path.write_text(text, encoding="utf-8")
path.chmod(0o600)
print("TELEGRAM_PROXY set; ALLOWED_HOSTS includes api")
PY

# Harden remaining empty secrets without rotating live DB passwords from handoff
python3 - <<PY
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "secure_env", "${ROOT}/scripts/secure_env.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

mod.harden_env(
    Path("${ROOT}") / ".env",
    Path("${ROOT}") / ".env.example",
    rotate_postgres=False,
    recreate_redis=False,
)
print("env hardened")
PY

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.mac-mini.yml --profile vpn)

info "Building and starting stack (postgres redis api worker web xray)"
"${COMPOSE[@]}" up -d --build

# --- optional DB restore ---
if [[ -f "$STAGE/db/whiteshop.dump" ]]; then
  info "Restoring database dump"
  # shellcheck disable=SC1091
  set -a
  # shellcheck source=/dev/null
  source <(grep -E '^(POSTGRES_USER|POSTGRES_DB)=' "$ROOT/.env" | sed 's/\r$//')
  set +a
  PG_USER="${POSTGRES_USER:-whiteshop}"
  PG_DB="${POSTGRES_DB:-whiteshop}"
  for _ in $(seq 1 60); do
    if "${COMPOSE[@]}" exec -T postgres pg_isready -U "$PG_USER" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  "${COMPOSE[@]}" exec -T postgres pg_isready -U "$PG_USER" >/dev/null \
    || die "postgres not healthy"
  # Copy dump into container and restore (may replace existing schema)
  docker cp "$STAGE/db/whiteshop.dump" "$("${COMPOSE[@]}" ps -q postgres)":/tmp/whiteshop.dump
  "${COMPOSE[@]}" exec -T postgres \
    pg_restore -U "$PG_USER" -d "$PG_DB" --clean --if-exists /tmp/whiteshop.dump \
    || info "pg_restore finished with warnings (often OK for --clean on fresh DB)"
fi

# --- healthchecks ---
info "Waiting for API /health and web :3000"
ok_api=0
ok_web=0
for _ in $(seq 1 90); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    ok_api=1
  fi
  web_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:3000/" 2>/dev/null || true)"
  if [[ "$web_code" =~ ^(200|301|302|307|308)$ ]]; then
    ok_web=1
  fi
  if [[ "$ok_api" -eq 1 && "$ok_web" -eq 1 ]]; then
    break
  fi
  sleep 3
done
[[ "$ok_api" -eq 1 ]] || die "API health check failed (http://127.0.0.1:8000/health)"
[[ "$ok_web" -eq 1 ]] || die "Web check failed (http://127.0.0.1:3000) — inspect: docker compose logs web"

# --- LaunchAgent for cloudflared ---
info "Installing Cloudflare Tunnel LaunchAgent"
PLIST_SRC="$ROOT/infra/tunnel/launchd/com.whiteshop.cloudflared.plist.example"
PLIST_DST="${HOME}/Library/LaunchAgents/com.whiteshop.cloudflared.plist"
mkdir -p "${HOME}/Library/LaunchAgents" "$ROOT/data"
sed \
  -e "s|__CLOUDFLARED__|${CLOUDFLARED}|g" \
  -e "s|__REPO_ROOT__|${ROOT}|g" \
  "$PLIST_SRC" > "$PLIST_DST"

UID_NUM="$(id -u)"
launchctl bootout "gui/${UID_NUM}/com.whiteshop.cloudflared" 2>/dev/null || true
launchctl bootstrap "gui/${UID_NUM}" "$PLIST_DST" 2>/dev/null \
  || launchctl load -w "$PLIST_DST" 2>/dev/null \
  || info "Could not load LaunchAgent automatically — run: launchctl bootstrap gui/${UID_NUM} ${PLIST_DST}"
launchctl kickstart -k "gui/${UID_NUM}/com.whiteshop.cloudflared" 2>/dev/null || true

# --- power settings (best-effort) ---
info "Disabling sleep on AC power (needs sudo)"
if sudo -n true 2>/dev/null; then
  sudo pmset -c sleep 0 disksleep 0 displaysleep 10 || true
else
  echo "Run once (password):"
  echo "  sudo pmset -c sleep 0 disksleep 0 displaysleep 10"
fi

echo ""
echo "=============================================="
echo " White Shop Mac Mini bootstrap complete"
echo "=============================================="
echo " Local:   http://127.0.0.1:3000"
echo " Public:  https://whiteshop.tech  (via cloudflared)"
echo " Mini App: https://whiteshop.tech/mini  (BotFather)"
echo " Admin:   http://127.0.0.1:3000/admin  (ADMIN_* from .env)"
echo ""
echo " Also do once:"
echo "  1. Docker Desktop → Settings → General → Start Docker Desktop when you log in"
echo "  2. System Settings → Users → automatic login for this user"
echo "  3. Delete handoff archive from Downloads/Desktop"
echo "  4. Confirm tunnel: tail -f ${ROOT}/data/cloudflared.err.log"
echo "  5. Confirm worker: docker compose -f docker-compose.yml -f docker-compose.mac-mini.yml --profile vpn logs -f worker"
echo ""
