#!/usr/bin/env python3
# Version: 1.7.5-universal
# Status: GitHub Ready - No hardcoded paths

import os, requests, uuid, json
from flask import Flask, request, Response, jsonify

VERSION = "1.7.5-universal"
app = Flask(__name__)

# Konfiguration über Umgebungsvariablen oder Standardwerte
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.7.0.79:11434")
SELECTED_MODEL = os.getenv("MODEL_NAME", "qwen3.5:9b-q8_0")
PORT = int(os.getenv("PROXY_PORT", 11435))
LOG_FILE = os.getenv("PROXY_LOG", "proxy_output.log")

def log_event(msg):
    """Schreibt Ereignisse in die Log-Datei und auf die Konsole."""
    with open(LOG_FILE, "a") as f:
        f.write(f"{msg}\n")
    print(msg)

def convert_to_anthropic(ollama_data):
    """Übersetzt das Ollama/OpenAI-Format zurück in das Anthropic-Format."""
    try:
        choice = ollama_data['choices'][0]
        message = choice['message']
        
        anthropic_resp = {
            "id": f"msg_{uuid.uuid4().hex}",
            "type": "message",
            "role": "assistant",
            "model": SELECTED_MODEL,
            "content": [],
            "stop_reason": "end_turn"
        }

        if message.get('content'):
            anthropic_resp["content"].append({"type": "text", "text": message['content']})

        if message.get('tool_calls'):
            for tc in message['tool_calls']:
                t_name = tc['function']['name']
                t_args = tc['function']['arguments']
                
                # Falls arguments ein String ist (JSON), umwandeln
                if isinstance(t_args, str):
                    t_args = json.loads(t_args)
                
                # --- PARAMETER MAPPING (Der Claude-Fix) ---
                # Wandelt 'path' in 'file_path' um, falls Claude das erwartet
                if "path" in t_args and "file_path" not in t_args:
                    log_event(f"🔧 Mapping: 'path' -> 'file_path' für Tool {t_name}")
                    t_args["file_path"] = t_args.pop("path")
                
                anthropic_resp["content"].append({
                    "type": "tool_use",
                    "id": tc.get('id', f"tool_{uuid.uuid4().hex[:8]}"),
                    "name": t_name,
                    "input": t_args
                })
            anthropic_resp["stop_reason"] = "tool_use"
            log_event(f"🎯 Tool gerufen: {t_name}")

        return anthropic_resp
    except Exception as e:
        log_event(f"❌ Konvertierungs-Fehler: {e}")
        return None

@app.route('/v1/messages', methods=['POST'])
def proxy_anthropic_messages():
    try:
        ant_data = request.get_json()
        available_tools = ant_data.get("tools", [])
        
        # Tool-Namen für das System-Prompt sammeln
        tool_names = [t['name'] for t in available_tools] if available_tools else []
        if tool_names:
            log_event(f"🛠️ Verfügbare Tools: {', '.join(tool_names)}")

        messages = []
        # Verstärkter System-Prompt für präzise Tool-Nutzung
        system_instr = (
            f"\n\nCRITICAL: You have tools available: {tool_names}. "
            "When using 'Read' or 'Write', the parameter for the file is 'file_path', NOT 'path'. "
            "Use the tools directly without preamble."
        )
        
        orig_sys = ant_data.get("system", "")
        if isinstance(orig_sys, list): 
            orig_sys = orig_sys[0].get("text", "")
        
        messages.append({"role": "system", "content": str(orig_sys) + system_instr})
        
        for m in ant_data.get("messages", []):
            messages.append({"role": m["role"], "content": str(m.get("content", ""))})

        ollama_payload = {
            "model": SELECTED_MODEL,
            "messages": messages,
            "stream": False,
            "temperature": 0.0,
            "tools": [{
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", "Execute task"),
                    "parameters": t.get("input_schema", {})
                }
            } for t in available_tools] if available_tools else None
        }

        resp = requests.post(f"{OLLAMA_URL}/v1/chat/completions", json=ollama_payload, timeout=120)
        resp.raise_for_status()
        
        return jsonify(convert_to_anthropic(resp.json()))

    except Exception as e:
        log_event(f"💥 Proxy-Fehler: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    log_event(f"--- Claude-Ollama-Bridge {VERSION} gestartet ---")
    app.run(host='0.0.0.0', port=PORT)
# EOF
