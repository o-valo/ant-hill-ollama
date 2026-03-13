#!/bin/bash
# Version: 2.0.7-persistent
# Description: Starts the proxy if not running and launches Claude CLI.

# Verzeichnis-Erkennung (ersetzt /home/olav/...)
PROXY_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PORT=11435

# Prüfen, ob der Proxy bereits auf dem Port lauscht
if ! lsof -i:$PORT -t >/dev/null; then
    echo "📡 Ubot-Bridge: Proxy läuft nicht. Starte in $PROXY_DIR..."
    bash "$PROXY_DIR/run_proxy.sh" &
    # Wir lassen ihn im Hintergrund laufen ("persist")
    disown
    sleep 2
else
    echo "✅ Ubot-Bridge: Proxy ist bereits aktiv auf Port $PORT."
fi

# Umgebung setzen
export ANTHROPIC_BASE_URL="http://127.0.0.1:$PORT/v1"
export ANTHROPIC_API_KEY="sk-ant-ollama-local"
export CLAUDE_CODE_DISABLE_ANALYTICS=true
export CLAUDE_CODE_NO_STREAM=true

echo "🚀 Claude Code wird gestartet..."

# Claude starten
claude "$@"

echo "👋 Claude beendet. Der Proxy läuft im Hintergrund weiter."
# EOF
