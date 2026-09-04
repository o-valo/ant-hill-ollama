#!/bin/bash
# Version: 3.0.0-conf
# Description: Checks proxy and launches Claude Code CLI.

PROXY_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PORT=11435

if ! lsof -i:$PORT -t >/dev/null; then
    echo "📡 ant-hill-ollama: Proxy ist nicht aktiv. Starte Brücke..."
    bash "$PROXY_DIR/run_proxy.sh" &
    disown
    sleep 2
else
    echo "✅ ant-hill-ollama: Die Heinzelmännchen-Brücke steht bereits (Port $PORT)."
fi

# Brücke läuft als systemd-Dienst "ant-hill-ollama" (empfohlen) oder via run_proxy.sh.
# Modellname = Katalogname, den Claude Code kennt; der Proxy mappt intern auf das echte Ollama-Modell.
export ANTHROPIC_BASE_URL="http://127.0.0.1:$PORT/v1"
export ANTHROPIC_API_KEY="sk-ant-ollama-local"
export ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-claude-sonnet-4-5}"
export CLAUDE_CODE_DISABLE_ANALYTICS=true
# Hinweis: CLAUDE_CODE_NO_STREAM wird NICHT mehr gesetzt - die Brücke unterstützt
# seit v2.2.0 SSE-Streaming im Anthropic-Format (war die Ursache des "Spinning").

echo "🚀 Claude Code wird gestartet (Modell: $ANTHROPIC_MODEL)..."
claude "$@"

echo "👋 Claude beendet. Die Heinzelmännchen-Brücke bleibt im Hintergrund aktiv."
# EOF
