#!/bin/bash
# Version: 2.0.8-stable
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

export ANTHROPIC_BASE_URL="http://127.0.0.1:$PORT/v1"
export ANTHROPIC_API_KEY="sk-ant-ollama-local"
export CLAUDE_CODE_DISABLE_ANALYTICS=true
export CLAUDE_CODE_NO_STREAM=true

echo "🚀 Claude Code wird gestartet..."
claude "$@"

echo "👋 Claude beendet. Die Heinzelmännchen-Brücke bleibt im Hintergrund aktiv."
# EOF
