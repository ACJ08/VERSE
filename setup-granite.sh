#!/usr/bin/env bash
# =============================================================================
# VERSE — Granite model setup script
#
# Downloads the IBM Granite 3.3 2B Q4_K_M GGUF model and installs
# llama-cpp-python (CPU-only build) into the script-intelligence venv so
# that the Granite LLM server in start.sh can run locally.
#
# Usage:
#   chmod +x setup-granite.sh
#   ./setup-granite.sh
#
# Environment variables (all optional):
#   GRANITE_MODEL_PATH   Override the destination path for the model file.
#                        Default: ~/.cache/verse/models/granite-3.3-2b-Q4_K_M.gguf
#   VERSE_SKIP_LLAMA     Set to "1" to skip llama-cpp-python installation
#                        (useful if you already have it installed).
# =============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${BOLD}[setup-granite]${NC} $*"; }
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $*"; }
err()  { echo -e "${RED}  ✗${NC} $*"; exit 1; }

# ─── Config ───────────────────────────────────────────────────────────────────

MODEL_DIR="${GRANITE_MODEL_PATH:-$HOME/.cache/verse/models}"
# If GRANITE_MODEL_PATH points to the file itself (not just a directory), split it
if [[ "${GRANITE_MODEL_PATH:-}" == *.gguf ]]; then
  MODEL_FILE="$GRANITE_MODEL_PATH"
  MODEL_DIR="$(dirname "$MODEL_FILE")"
else
  MODEL_FILE="${MODEL_DIR}/granite-3.3-2b-Q4_K_M.gguf"
fi

# Hugging Face Hub repo and filename
HF_REPO="ibm-granite/granite-3.3-2b-instruct-GGUF"
HF_FILE="granite-3.3-2b-instruct-Q4_K_M.gguf"
HF_URL="https://huggingface.co/${HF_REPO}/resolve/main/${HF_FILE}"

SCRIPT_VENV="$ROOT/script-intelligence/.venv"

# ─── Banner ───────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║       VERSE — Granite Model Setup                ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
log "Model destination : ${CYAN}${MODEL_FILE}${NC}"
log "HuggingFace source: ${CYAN}${HF_URL}${NC}"
echo ""

# ─── 1. Download model ────────────────────────────────────────────────────────

if [[ -f "$MODEL_FILE" ]]; then
  ok "Model already present at ${MODEL_FILE} — skipping download."
else
  log "Creating model directory…"
  mkdir -p "$MODEL_DIR"

  log "Downloading Granite 3.3 2B (Q4_K_M, ~1.4 GB) — this may take a while…"
  if command -v curl &>/dev/null; then
    curl -L --progress-bar -o "$MODEL_FILE" "$HF_URL"
  elif command -v wget &>/dev/null; then
    wget --show-progress -q -O "$MODEL_FILE" "$HF_URL"
  else
    err "Neither curl nor wget found. Install one and re-run this script."
  fi
  ok "Model downloaded to ${MODEL_FILE}"
fi

# ─── 2. Install llama-cpp-python ──────────────────────────────────────────────

if [[ "${VERSE_SKIP_LLAMA:-0}" == "1" ]]; then
  warn "VERSE_SKIP_LLAMA=1 — skipping llama-cpp-python installation."
else
  if [[ ! -d "$SCRIPT_VENV" ]]; then
    log "script-intelligence venv not found — creating it…"
    python3 -m venv "$SCRIPT_VENV"
  fi

  log "Installing llama-cpp-python (CPU-only build) into script-intelligence venv…"
  CMAKE_ARGS="-DLLAMA_BLAS=OFF -DLLAMA_CUBLAS=OFF" \
    "$SCRIPT_VENV/bin/pip" install --upgrade llama-cpp-python[server] -q
  ok "llama-cpp-python installed."
fi

# ─── 3. Persist GRANITE_MODEL_PATH for convenience ───────────────────────────

ENV_FILE="$ROOT/.env.local"
if [[ -f "$ENV_FILE" ]]; then
  if grep -q "^GRANITE_MODEL_PATH=" "$ENV_FILE"; then
    # Update existing line
    sed -i "s|^GRANITE_MODEL_PATH=.*|GRANITE_MODEL_PATH=${MODEL_FILE}|" "$ENV_FILE"
    ok "Updated GRANITE_MODEL_PATH in .env.local"
  else
    echo "GRANITE_MODEL_PATH=${MODEL_FILE}" >> "$ENV_FILE"
    ok "Added GRANITE_MODEL_PATH to .env.local"
  fi
else
  echo "GRANITE_MODEL_PATH=${MODEL_FILE}" > "$ENV_FILE"
  ok "Created .env.local with GRANITE_MODEL_PATH"
fi

# ─── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${GREEN}Setup complete!${NC}"
echo ""
echo -e "  Model path : ${CYAN}${MODEL_FILE}${NC}"
echo -e "  Start VERSE: ${BOLD}./start.sh${NC}  (Granite LLM server will auto-start)"
echo ""
echo -e "  To skip Granite (use heuristic fallback): ${BOLD}./start.sh --no-script${NC}"
echo ""
