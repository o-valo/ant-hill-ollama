#!/bin/bash
# Version: 1.1.4-nki-fix
# Description: Starts the proxy and points it to the nki-Server.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Venv laden
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo "❌ Fehler: venv nicht gefunden."
    exit 1
fi

# --- ZENTRALE KONFIGURATION (nki-Server) ---
export OLLAMA_URL="http://10.7.0.79:11434"
export MODEL_NAME="opencode-Granit:latest"
export PROXY_PORT=11435
export ANTHROPIC_API_KEY="sk-ant-local-123"

echo "🔍 Prüfe Verbindung zu nki-Ollama unter $OLLAMA_URL..."
if curl -s --max-time 5 --head "$OLLAMA_URL" > /dev/null; then
    echo "✅ nki-Server ist erreichbar."
else
    echo "❌ FEHLER: nki-Server (10.7.0.79) antwortet nicht!"
    echo "Prüfe die Netzwerkverbindung oder ob Ollama auf .79 läuft."
    exit 1
fi

echo "🚀 Starte Brücke auf Port $PROXY_PORT..."
python3 llm_proxy.py >> proxy_output.log 2>&1
#eof
