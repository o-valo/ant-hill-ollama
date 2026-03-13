#!/bin/bash
# Version: 1.1.0-universal
# Description: Starts the Flask proxy in its local virtual environment.

# Ermittelt das Verzeichnis, in dem dieses Skript liegt
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Wechselt in das Verzeichnis, damit Flask die Pfade (z.B. logs) korrekt setzt
cd "$SCRIPT_DIR"

# Aktiviert das virtuelle Environment relativ zum Skript-Pfad
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo "❌ Fehler: venv nicht gefunden in $SCRIPT_DIR"
    echo "Bitte führen Sie zuerst 'python3 -m venv venv' aus."
    exit 1
fi

# Setzt Standardwerte, falls keine Umgebungsvariablen definiert sind
export OLLAMA_URL="${OLLAMA_URL:-http://10.7.0.79:11434}"
export MODEL_NAME="${MODEL_NAME:-qwen3.5:9b-q8_0}"
export PROXY_PORT="${PROXY_PORT:-11435}"

echo "🚀 Starte Proxy auf Port $PROXY_PORT..."
echo "🔗 Verbinde mit Ollama unter $OLLAMA_URL"

# Startet den Flask-Proxy
python3 llm_proxy.py >> proxy_output.log 2>&1
