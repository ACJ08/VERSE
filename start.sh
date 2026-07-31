#!/usr/bin/env bash
# =============================================================================
# VERSE — Unified startup script
# Starts all four services and the frontend from a single command.
#
# Usage:
#   ./start.sh              # start everything
#   ./start.sh --no-vision  # skip vision_pipeline (heavy ML deps)
#   ./start.sh --no-script  # skip script-intelligence
#   ./start.sh --fe-only    # frontend + continuity-engine only
#
# Open: http://localhost:5173
# =============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m';  GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';  BOLD='\033[1m';  NC='\033[0m'

log()  { echo -e "${BOLD}[VERSE]${NC} $*"; }
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $*"; }
err()  { echo -e "${RED}  ✗${NC} $*"; }

# ── Flags ─────────────────────────────────────────────────────────────────────
RUN_SCRIPT=true
RUN_VISION=true
for arg in "$@"; do
  case $arg in
    --no-script) RUN_SCRIPT=false ;;
    --no-vision) RUN_VISION=false ;;
    --fe-only)   RUN_SCRIPT=false; RUN_VISION=false ;;
  esac
done

# ── PID tracking — used by trap to kill everything on Ctrl+C ─────────────────
PIDS=()

cleanup() {
  echo ""
  log "Shutting down all services…"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null && ok "Killed PID $pid" || true
  done
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── Port helpers ──────────────────────────────────────────────────────────────
port_free() {
  ! lsof -ti :"$1" >/dev/null 2>&1
}

kill_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Port $port busy — killing existing process(es): $pids"
    echo "$pids" | xargs kill 2>/dev/null || true
    sleep 1
  fi
}

# ── Venv bootstrap helper ─────────────────────────────────────────────────────
# Creates .venv if absent, then installs from requirements.txt.
ensure_venv() {
  local dir="$1"
  local name="$2"
  local req="$dir/requirements.txt"

  if [[ ! -d "$dir/.venv" ]]; then
    log "Creating virtualenv for ${CYAN}$name${NC}…"
    python3 -m venv "$dir/.venv"
  fi

  if [[ -f "$req" ]]; then
    log "Installing deps for ${CYAN}$name${NC} (may take a moment on first run)…"
    "$dir/.venv/bin/pip" install -q -r "$req"
    ok "$name deps ready"
  fi
}

# ── Service launcher ──────────────────────────────────────────────────────────
# Streams coloured output prefixed with the service name.
start_service() {
  local label="$1"   # display name
  local colour="$2"  # ANSI colour code
  local port="$3"
  local dir="$4"
  local cmd="$5"     # command to run (relative to dir, after activating .venv)

  kill_port "$port"

  (
    cd "$dir"
    source ".venv/bin/activate"
    eval "$cmd" 2>&1 | while IFS= read -r line; do
      echo -e "${colour}[${label}]${NC} $line"
    done
  ) &

  PIDS+=($!)
  ok "${label} started on ${BOLD}http://localhost:${port}${NC}  (PID ${PIDS[-1]})"
}

# =============================================================================
# BANNER
# =============================================================================
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║        VERSE — AI Film Continuity Platform       ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# Pre-export service URLs so child processes inherit them.
# These are also written into each service's own .env file; exporting here is
# the safety net for environments where .env files are not present.
# Shell variables win over .env because load_dotenv(override=False) is used.
# =============================================================================
export SCRIPT_SERVICE_URL="${SCRIPT_SERVICE_URL:-http://localhost:8100}"
export VISION_SERVICE_URL="${VISION_SERVICE_URL:-http://localhost:8200}"
export CONTINUITY_ENGINE_URL="${CONTINUITY_ENGINE_URL:-http://localhost:8000}"

# =============================================================================
# 0. Granite LLM server  (port 11435)  — llama-cpp-python, CPU-only
#    Serves the local IBM Granite model to the Script Intelligence service.
#    Skipped automatically if the model file is absent.
# =============================================================================
_GRANITE_MODEL="${GRANITE_MODEL_PATH:-$HOME/.cache/verse/models/granite-3.3-2b-Q4_K_M.gguf}"
_GRANITE_VENV="$ROOT/script-intelligence/.venv"

if [[ -f "$_GRANITE_MODEL" ]] && [[ -d "$_GRANITE_VENV" ]]; then
  # Kill anything already holding port 11435
  lsof -ti :11435 | xargs kill 2>/dev/null; sleep 1

  log "Starting ${BOLD}Granite LLM server${NC} on port 11435 (CPU-only, model: $(basename "$_GRANITE_MODEL"))…"
  (
    "$_GRANITE_VENV/bin/python" -m llama_cpp.server \
      --model "$_GRANITE_MODEL" \
      --host 127.0.0.1 \
      --port 11435 \
      --n_ctx 2048 \
      --n_threads 4 \
      --verbose false 2>&1 | while IFS= read -r line; do
        echo -e "\033[0;35m[GRANITE]\033[0m $line"
    done
  ) &
  PIDS+=($!)
  ok "Granite LLM server started on ${BOLD}http://localhost:11435/v1${NC}  (PID ${PIDS[-1]})"
  # Allow model to load before the script-intelligence service requests it
  sleep 5
else
  if [[ ! -f "$_GRANITE_MODEL" ]]; then
    warn "Granite model not found at $_GRANITE_MODEL — script-intelligence will use heuristic fallback."
    warn "To enable AI analysis: run './setup-granite.sh' or set GRANITE_MODEL_PATH."
  fi
fi

# =============================================================================
# 1. Continuity Engine  (port 8000)  — always started
# =============================================================================
log "Starting ${BOLD}Continuity Engine${NC} on port 8000…"
ensure_venv "$ROOT/continuity-engine" "continuity-engine"
start_service "ENGINE" "$BLUE" 8000 "$ROOT/continuity-engine" \
  "uvicorn main:app --reload --port 8000"

# Give the engine a moment to bind before dependents start
sleep 2

# =============================================================================
# 2. Script Intelligence  (port 8100)  — team 1
# =============================================================================
if $RUN_SCRIPT; then
  log "Starting ${BOLD}Script Intelligence${NC} on port 8100…"
  if [[ -f "$ROOT/script-intelligence/requirements.txt" ]]; then
    ensure_venv "$ROOT/script-intelligence" "script-intelligence"
    start_service "SCRIPT" "$GREEN" 8100 "$ROOT/script-intelligence" \
      "uvicorn app.main:app --reload --port 8100"
  else
    warn "script-intelligence/requirements.txt not found — skipping"
  fi
else
  warn "Script Intelligence skipped (--no-script)"
  unset SCRIPT_SERVICE_URL  # Engine must not try to call a service that is not running
fi

# =============================================================================
# 3. Vision Pipeline  (port 8200)  — team 2
# =============================================================================
if $RUN_VISION; then
  log "Starting ${BOLD}Vision Pipeline${NC} on port 8200…"
  if [[ -f "$ROOT/vision_pipeline/requirements.txt" ]]; then
    ensure_venv "$ROOT/vision_pipeline" "vision_pipeline"
    start_service "VISION" "$YELLOW" 8200 "$ROOT/vision_pipeline" \
      "uvicorn service:app --reload --port 8200"
  else
    warn "vision_pipeline/requirements.txt not found — skipping"
  fi
else
  warn "Vision Pipeline skipped (--no-vision)"
  unset VISION_SERVICE_URL  # Engine must not try to call a service that is not running
fi

# =============================================================================
# 4. Frontend  (port 5173)  — always started
# =============================================================================
log "Starting ${BOLD}Frontend${NC} on port 5173…"
kill_port 5173
(
  cd "$ROOT"
  pnpm dev 2>&1 | while IFS= read -r line; do
    echo -e "${CYAN}[FRONTEND]${NC} $line"
  done
) &
PIDS+=($!)
ok "Frontend started on ${BOLD}http://localhost:5173${NC}  (PID ${PIDS[-1]})"

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}All services running — open: http://localhost:5173${NC}"
echo ""
echo -e "  ${CYAN}Frontend   ${NC}→  http://localhost:5173"
echo -e "  ${BLUE}Engine     ${NC}→  http://localhost:8000/docs"
[[ "$RUN_SCRIPT" == true ]] && \
  echo -e "  ${GREEN}Script API ${NC}→  http://localhost:8100/docs"
[[ "$RUN_VISION" == true ]] && \
  echo -e "  ${YELLOW}Vision API ${NC}→  http://localhost:8200/docs"
[[ -f "$_GRANITE_MODEL" ]] && \
  echo -e "  \033[0;35mGranite LLM${NC}→  http://localhost:11435/v1/models"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${NC} to stop all services."
echo ""

# Wait for all background jobs so the script doesn't exit
wait
