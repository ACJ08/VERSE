#!/usr/bin/env bash
# =============================================================================
# VERSE — Stop all running services
# Kills any process bound to the four VERSE ports.
# =============================================================================

PORTS=(5173 8000 8100 8200)
NAMES=("Frontend" "Continuity Engine" "Script Intelligence" "Vision Pipeline")

echo ""
for i in "${!PORTS[@]}"; do
  port="${PORTS[$i]}"
  name="${NAMES[$i]}"
  pids=$(lsof -ti :"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill 2>/dev/null && \
      echo -e "\033[0;32m  ✓\033[0m Stopped $name (port $port, PID $pids)" || \
      echo -e "\033[0;31m  ✗\033[0m Failed to stop $name (port $port)"
  else
    echo -e "\033[0;33m  –\033[0m $name not running (port $port)"
  fi
done
echo ""
