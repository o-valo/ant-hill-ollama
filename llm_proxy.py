#!/usr/bin/env python3
# Version: 2.1.3-ant-hill-final-health
# Description: Production Stable. Handles double-v1, Tool-Mapping and Health Checks.

import os, requests, uuid, json
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- KONFIGURATION ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.7.0.79:11434")
SELECTED_MODEL = os.getenv("MODEL_NAME", "opencode-Granit:latest")
PORT = int(os.getenv("PROXY_PORT", 11435))
LOG_FILE = os.getenv("PROXY_LOG", "proxy_output.log")

def log_event(msg):
    """Protokolliert Ereignisse mit Zeitstempel."""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except: pass
    print(msg)

def convert_to_anthropic(ollama_data):
    """Konvertiert Ollama/OpenAI in Anthropic-Format mit Tool-Mapping."""
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

        if message.get('content'):
            anthropic_resp["content"].append({"type": "text", "text": message['content']})

        if message.get('tool_calls'):
            for tc in message['tool_calls']:
                t_args = tc['function']['arguments']
                if isinstance(t_args, str): t_args = json.loads(t_args)
                
                # Mapping: Granite/Standard -> Claude Code
                if "path" in t_args: t_args["file_path"] = t_args.pop("path")
                if "filePath" in t_args: t_args["file_path"] = t_args.pop("filePath")
                
                anthropic_resp["content"].append({
                    "type": "tool_use",
                    "id": tc.get('id', f"tool_{uuid.uuid4().hex[:8]}"),
                    "name": tc['function']['name'],
                    "input": t_args
                })
            anthropic_resp["stop_reason"] = "tool_use"
        
        return anthropic_resp
    except Exception as e:
        log_event(f"❌ Konvertierungs-Fehler: {e}")
        return None

# --- ENDPUNKTE ---

# Health Check / Root (Verhindert 404 bei HEAD Anfragen)
@app.route('/', methods=['GET', 'HEAD'])
@app.route('/v1', methods=['GET', 'HEAD'])
@app.route('/v1/v1', methods=['GET', 'HEAD'])
def health_check():
    return jsonify({"status": "ok", "message": "Heinzelmännchen-Brücke ist aktiv"}), 200

# Nachrichten-Endpoint
@app.route('/v1/messages', methods=['POST'])
@app.route('/v1/v1/messages', methods=['POST'])
def proxy_messages():
    try:
        ant_data = request.get_json()
        messages = [{"role": "system", "content": "Du bist ein hilfreicher Terminal-Assistent für Olav. Antworte auf Deutsch."}]
        
        for m in ant_data.get("messages", []):
            messages.append({"role": m["role"], "content": str(m.get("content", ""))})

        payload = {
            "model": SELECTED_MODEL,
            "messages": messages,
            "stream": False,
            "tools": [{
                "type": "function",
                "function": {
                    "name": t["name"],
                    "parameters": t.get("input_schema", {})
                }
            } for t in ant_data.get("tools", [])] if "tools" in ant_data else None
        }

        resp = requests.post(f"{OLLAMA_URL}/v1/chat/completions", json=payload, timeout=400)
        resp.raise_for_status()
        return jsonify(convert_to_anthropic(resp.json()))
    except Exception as e:
        log_event(f"💥 Proxy-Fehler: {e}")
        return jsonify({"error": str(e)}), 500

# Modell-Liste
@app.route('/v1/models', methods=['GET'])
@app.route('/v1/v1/models', methods=['GET'])
def list_models():
    return jsonify({"data": [{"id": SELECTED_MODEL, "object": "model"}]})

if __name__ == '__main__':
    log_event(f"🚀 Brücke gestartet: {SELECTED_MODEL} @ {OLLAMA_URL}")
    app.run(host='0.0.0.0', port=PORT)
#eof
