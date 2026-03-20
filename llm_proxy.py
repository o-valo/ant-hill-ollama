#!/usr/bin/env python3
# Version: 2.0.8-ant-hill-stable-ultra
# Description: Final Stable Build. Bridges Ollama (Qwen) to Anthropic (Claude Code).
# Features: 32k Context, Usage/Token-Metadata Fix, Parameter Mapping (file_path).
# Status: Production Ready for Ubot/nki Environment.

import os, requests, uuid, json
from datetime import datetime
from flask import Flask, request, Response, jsonify

VERSION = "2.0.8-ant-hill-stable-ultra"
app = Flask(__name__)

# --- KONFIGURATION ---
# Standardmäßig auf nki-Server (10.7.0.79), konfigurierbar via ENV
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.7.0.79:11434")
SELECTED_MODEL = os.getenv("MODEL_NAME", "qwen3.5:9b-q8_0")
PORT = int(os.getenv("PROXY_PORT", 11435))
LOG_FILE = os.getenv("PROXY_LOG", "proxy_output.log")

# Ressourcen-Management
CONTEXT_WINDOW = int(os.getenv("NUM_CTX", 32768))
MAX_PREDICT = int(os.getenv("NUM_PREDICT", 4096))

def log_event(msg):
    """Protokolliert Ereignisse mit Zeitstempel."""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception as e:
        print(f"Logging-Fehler: {e}")
    print(msg)

def convert_to_anthropic(ollama_data):
    """
    Konvertiert das Ollama/OpenAI-Format in das von Claude Code erwartete Anthropic-Format.
    Inklusive 'usage'-Objekt zur Vermeidung von 'input_tokens' Fehlern.
    """
    try:
        choice = ollama_data['choices'][0]
        message = choice['message']
        usage = ollama_data.get('usage', {})
        
        anthropic_resp = {
            "id": f"msg_{uuid.uuid4().hex}",
            "type": "message",
            "role": "assistant",
            "model": SELECTED_MODEL,
            "content": [],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0)
            }
        }

        # Text-Inhalt verarbeiten
        if message.get('content'):
            anthropic_resp["content"].append({"type": "text", "text": message['content']})

        # Tool-Calls verarbeiten und Parameter mappen
        if message.get('tool_calls'):
            for tc in message['tool_calls']:
                t_name = tc['function']['name']
                t_args = tc['function']['arguments']
                if isinstance(t_args, str): 
                    t_args = json.loads(t_args)
                
                # WICHTIG: Claude Code verlangt 'file_path' statt 'path'
                if "path" in t_args:
                    t_args["file_path"] = t_args.pop("path")
                if "text" in t_args and "content" not in t_args:
                    t_args["content"] = t_args.pop("text")
                
                anthropic_resp["content"].append({
                    "type": "tool_use",
                    "id": tc.get('id', f"tool_{uuid.uuid4().hex[:8]}"),
                    "name": t_name,
                    "input": t_args
                })
            anthropic_resp["stop_reason"] = "tool_use"
            log_event(f"🎯 Tool-Einsatz: {t_name}")

        # Fail-Safe für leeren Content
        if not anthropic_resp["content"]:
            anthropic_resp["content"].append({"type": "text", "text": "Task processed."})

        return anthropic_resp
    except Exception as e:
        log_event(f"❌ Konvertierungs-Fehler: {e}")
        return None

@app.route('/v1/messages', methods=['POST'])
def proxy_anthropic_messages():
    """Haupt-Endpoint für Claude Code Anfragen."""
    try:
        ant_data = request.get_json()
        available_tools = ant_data.get("tools", [])
        tool_names = [t['name'] for t in available_tools] if available_tools else []
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

        messages = []
        # System-Instruktionen zur Steuerung des Modells
        system_instr = (
            f"\n\nSystem: Heute ist {now_str}. Verfügbare Tools: {tool_names}. "
            f"Kontext-Limit: {CONTEXT_WINDOW}. "
            "Nutze zwingend 'file_path' für Dateioperationen. Antworte präzise."
        )
        
        orig_sys = ant_data.get("system", "")
        if isinstance(orig_sys, list): 
            orig_sys = orig_sys[0].get("text", "")
        
        messages.append({"role": "system", "content": str(orig_sys) + system_instr})
        
        # Verlauf mappen
        for m in ant_data.get("messages", []):
            messages.append({"role": m["role"], "content": str(m.get("content", ""))})

        ollama_payload = {
            "model": SELECTED_MODEL,
            "messages": messages,
            "stream": False,
            "temperature": 0.0,
            "options": {
                "num_ctx": CONTEXT_WINDOW,
                "num_predict": MAX_PREDICT
            },
            "tools": [{
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", "Aktion ausführen"),
                    "parameters": t.get("input_schema", {})
                }
            } for t in available_tools] if available_tools else None
        }

        # Anfrage an nki-Server senden
        resp = requests.post(f"{OLLAMA_URL}/v1/chat/completions", json=ollama_payload, timeout=400)
        resp.raise_for_status()
        
        return jsonify(convert_to_anthropic(resp.json()))

    except Exception as e:
        log_event(f"💥 Proxy-Fehler: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    log_event(f"--- ant-hill-stable-ultra {VERSION} gestartet ---")
    log_event(f"📍 Ziel-Modell: {SELECTED_MODEL} auf {OLLAMA_URL}")
    app.run(host='0.0.0.0', port=PORT)

# EOF
