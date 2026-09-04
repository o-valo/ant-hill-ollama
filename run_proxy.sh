#!/bin/bash
# Version: 2.0.0-macmini
# Description: Starts the proxy and points it to the Ollama server (10.7.0.93 Mac Mini).
# Hinweis: Auf Systemen mit systemd wird der Dienst "ant-hill-ollama.service" empfohlen
#          (läuft dauerhaft, überlebt Reboots):  sudo systemctl enable --now ant-hill-ollama

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Venv laden
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo "❌ Fehler: venv nicht gefunden."
    exit 1
fi

# --- ZENTRALE KONFIGURATION ---
export OLLAMA_URL="${OLLAMA_URL:-http://10.7.0.93:11434}"      # Mac Mini (10.7.0.79 war offline)
export MODEL_NAME="${MODEL_NAME:-granite4.1:8b}"               # auf 10.7.0.93 vorhandenes Modell
export SPOOFED_MODEL="${SPOOFED_MODEL:-claude-sonnet-4-5}"     # Claude-Code-Katalogname (vorgegaukelt)
export PROXY_PORT=${PROXY_PORT:-11435}
export ANTHROPIC_API_KEY="sk-ant-local-123"

echo "🔍 Prüfe Verbindung zu Ollama unter $OLLAMA_URL..."
if curl -s --max-time 5 --head "$OLLAMA_URL" > /dev/null; then
    echo "✅ Ollama-Server ist erreichbar."
else
    echo "❌ FEHLER: Ollama ($OLLAMA_URL) antwortet nicht!"
    echo "Prüfe die Netzwerkverbindung oder ob Ollama läuft."
    exit 1
fi

echo "🚀 Starte Brücke (v2.3.0) auf Port $PROXY_PORT..."
echo "   Modell: $MODEL_NAME (antwortet als $SPOOFED_MODEL)"
python3 llm_proxy.py >> proxy_output.log 2>&1
#eof
