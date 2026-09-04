#!/usr/bin/env python3
# Version: 3.0.0-ant-hill-conf
# Description: Production Stable. SSE-Streaming (Anthropic-Format), double-v1,
#              Tool-Mapping, /v1/api/hello-Healthcheck, count_tokens,
#              Modell-Spoofing und Konfiguration über ant-hill.conf.
#
# Neu in v3.0: Die Brücke kann beliebige OpenAI-kompatible Endpunkte ansprechen
#   (Ollama, llm-bahnhof, OpenAI, ...) - gesteuert über ant-hill.conf.
#   Mehrere Endpunkte = automatischer Fallback in der angegebenen Reihenfolge.
#
# Fix v2.2: Moderne Claude-Code-Versionen senden stream:true und erwarten eine
#      SSE-Antwort (text/event-stream). Vorher antwortete der Proxy immer mit
#      plain JSON -> Claude Code wartete ewig auf Events (= "Spinning").

import os, requests, uuid, json, re
from datetime import datetime
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# --- KONFIGURATION (ant-hill.conf) ---
# Priorität:  ant-hill.conf  >  Umgebungsvariablen  >  Defaults
CONF_FILE = os.getenv("ANT_HILL_CONF",
                      os.path.join(os.path.dirname(os.path.abspath(__file__)), "ant-hill.conf"))

DEFAULT_TIMEOUT = 400
FALLBACK_MODEL = "granite4.1:8b"          # Default, falls nirgends ein Modell steht
FALLBACK_SPOOF = "claude-sonnet-4-5"      # Claude-Code-Katalogname
FALLBACK_PORT = 11435
FALLBACK_LOG = "proxy_output.log"

def load_config():
    """Liest die ant-hill.conf (KEY=VALUE, # Kommentare). Fehlt die Datei -> {}."""
    cfg = {}
    try:
        with open(CONF_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return cfg

def conf_value(cfg, key, env=None, default=None):
    """Wert mit Priorität: conf-Datei > Env-Variable > Default."""
    if key in cfg and cfg[key] != "":
        return cfg[key]
    if env and os.getenv(env):
        return os.getenv(env)
    return default

def normalize_chat_url(base):
    """Macht aus einer Basis-URL die komplette /chat/completions-URL."""
    base = base.strip().rstrip("/")
    if not base:
        return base
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"

def parse_endpoints(cfg):
    """Baut die Endpunkt-Liste aus ENDPOINT_01=URL|Key|Modell|Timeout Zeilen.
    Reihenfolge = Fallback-Reihenfolge (numerisch sortiert)."""
    numbered = []
    for k, v in cfg.items():
        m = re.match(r"^ENDPOINT_(\d+)$", k.strip().upper())
        if m:
            numbered.append((int(m.group(1)), v))
    numbered.sort(key=lambda x: x[0])

    endpoints = []
    for _, raw in numbered:
        parts = [p.strip() for p in raw.split("|")]
        url = normalize_chat_url(parts[0]) if parts and parts[0] else ""
        if not url:
            continue
        key = parts[1] if len(parts) > 1 and parts[1] else ""
        model = parts[2] if len(parts) > 2 and parts[2] else ""
        timeout = DEFAULT_TIMEOUT
        if len(parts) > 3 and parts[3]:
            try:
                timeout = int(parts[3])
            except ValueError:
                pass
        endpoints.append({"url": url, "key": key, "model": model, "timeout": timeout})
    return endpoints

# --- Konfiguration auflösen ---
_cfg = load_config()

# Endpunkte: aus conf, sonst einzelner Endpunkt aus Env (Rückwärtskompatibilität)
ENDPOINTS = parse_endpoints(_cfg)
if not ENDPOINTS:
    env_url = os.getenv("OLLAMA_URL", "")
    if env_url:
        ENDPOINTS = [{
            "url": normalize_chat_url(env_url),
            "key": os.getenv("OLLAMA_API_KEY", ""),
            "model": os.getenv("MODEL_NAME", FALLBACK_MODEL),
            "timeout": DEFAULT_TIMEOUT,
        }]

# Modell je Endpunkt: eigene conf-Angabe > MODEL_NAME (conf/env) > Default
_MODEL_DEFAULT = conf_value(_cfg, "MODEL_NAME", "MODEL_NAME", FALLBACK_MODEL)
for ep in ENDPOINTS:
    if not ep["model"]:
        ep["model"] = _MODEL_DEFAULT

# Modellname, den Claude Code im Response sieht ("vorgegaukelt").
# Claude Code v2.x kennt nur seinen internen Katalog - unbekannte Namen
# erzeugen Warnungen. Der Proxy antwortet daher mit einem Katalog-Namen,
# nutzt intern aber das echte Modell des gewählten Endpunkts.
SPOOFED_MODEL = conf_value(_cfg, "SPOOFED_MODEL", "SPOOFED_MODEL", FALLBACK_SPOOF)
PORT = int(conf_value(_cfg, "PROXY_PORT", "PROXY_PORT", str(FALLBACK_PORT)))
LOG_FILE = conf_value(_cfg, "PROXY_LOG", "PROXY_LOG", FALLBACK_LOG)

def log_event(msg):
    """Protokolliert Ereignisse mit Zeitstempel."""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except: pass
    print(msg)

# --- HELFER ---
def sse_event(event, data):
    """Formatiert ein SSE-Event im Anthropic-Stil."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

def convert_to_anthropic(ollama_data, respond_model=None):
    """Konvertiert Ollama/OpenAI in Anthropic-Format mit Tool-Mapping."""
    try:
        choice = ollama_data['choices'][0]
        message = choice['message']
        usage = ollama_data.get('usage', {})

        anthropic_resp = {
            "id": f"msg_{uuid.uuid4().hex}",
            "type": "message",
            "role": "assistant",
            "model": respond_model or SPOOFED_MODEL,
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

def anthropic_to_sse(anthropic_resp):
    """Wandelt eine komplette Anthropic-Antwort in SSE-Events um."""
    if anthropic_resp is None:
        yield sse_event("error", {"type": "error", "error": {"type": "api_error", "message": "Konvertierung fehlgeschlagen"}})
        return

    msg = {
        "id": anthropic_resp["id"],
        "type": "message",
        "role": "assistant",
        "model": anthropic_resp["model"],
        "content": [],
        "stop_reason": None,
        "stop_sequence": None,
        "usage": {"input_tokens": anthropic_resp["usage"]["input_tokens"], "output_tokens": 0},
    }
    yield sse_event("message_start", {"type": "message_start", "message": msg})

    for idx, block in enumerate(anthropic_resp["content"]):
        if block["type"] == "text":
            cb = {"type": "text", "text": ""}
            yield sse_event("content_block_start", {"type": "content_block_start", "index": idx, "content_block": cb})
            yield sse_event("content_block_delta", {"type": "content_block_delta", "index": idx,
                                                    "delta": {"type": "text_delta", "text": block["text"]}})
        elif block["type"] == "tool_use":
            cb = {"type": "tool_use", "id": block["id"], "name": block["name"], "input": {}}
            yield sse_event("content_block_start", {"type": "content_block_start", "index": idx, "content_block": cb})
            yield sse_event("content_block_delta", {"type": "content_block_delta", "index": idx,
                                                    "delta": {"type": "input_json_delta",
                                                              "partial_json": json.dumps(block["input"])}})
        yield sse_event("content_block_stop", {"type": "content_block_stop", "index": idx})

    yield sse_event("message_delta", {"type": "message_delta",
                                      "delta": {"stop_reason": anthropic_resp["stop_reason"], "stop_sequence": None},
                                      "usage": {"output_tokens": anthropic_resp["usage"]["output_tokens"]}})
    yield sse_event("message_stop", {"type": "message_stop"})

def build_ollama_payload(ant_data, model):
    """Baut den OpenAI-kompatiblen Payload für den Endpunkt aus dem Anthropic-Request."""
    system_text = "Du bist ein hilfreicher Terminal-Assistent für Olav. Antworte auf Deutsch. " \
                  "Wenn dir Werkzeuge (Tools) angeboten werden, nutze sie, wenn es die Aufgabe verlangt."
    ant_system = ant_data.get("system")
    if isinstance(ant_system, str):
        system_text = ant_system
    elif isinstance(ant_system, list):
        parts = []
        for b in ant_system:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    parts.append(b.get("text", ""))
                elif isinstance(b.get("content"), str):
                    parts.append(b["content"])
        if parts:
            system_text = "\n".join(parts)

    messages = [{"role": "system", "content": system_text}]

    for m in ant_data.get("messages", []):
        role = m["role"]
        content = m.get("content", "")

        # Anthropic-Content-Blöcke -> Text (tool_result / tool_use als Text darstellen)
        if isinstance(content, list):
            texts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    texts.append(block.get("text", ""))
                elif btype == "tool_result":
                    inner = block.get("content", "")
                    if isinstance(inner, list):
                        inner = " ".join(b.get("text", "") for b in inner if isinstance(b, dict))
                    texts.append(f"[Tool-Ergebnis von {block.get('tool_use_id','?')}]: {inner}")
                elif btype == "tool_use":
                    texts.append(f"[Tool-Aufruf {block.get('name','?')}({json.dumps(block.get('input',{}), ensure_ascii=False)})]")
                else:
                    texts.append(str(block))
            content = "\n".join(texts)

        messages.append({"role": role, "content": str(content)})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    tools = ant_data.get("tools")
    if tools:
        converted = []
        for t in tools:
            if not isinstance(t, dict):
                continue
            converted.append({
                "type": "function",
                "function": {
                    "name": t.get("name", "unknown_tool"),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                }
            })
        if converted:
            payload["tools"] = converted

    max_tokens = ant_data.get("max_tokens")
    if max_tokens:
        payload["max_tokens"] = int(max_tokens)

    return payload

def call_endpoint(ep, payload):
    """Ruft einen OpenAI-kompatiblen Endpunkt auf. Key -> Authorization-Header."""
    headers = {"Content-Type": "application/json"}
    if ep.get("key"):
        key = ep["key"]
        headers["Authorization"] = f"Bearer {key}" if not key.lower().startswith("bearer ") else key
    return requests.post(ep["url"], json=payload, headers=headers, timeout=ep.get("timeout", DEFAULT_TIMEOUT))

# --- ENDPUNKTE ---

# Health Check / Root (Verhindert 404 bei HEAD Anfragen)
@app.route('/', methods=['GET', 'HEAD'])
@app.route('/v1', methods=['GET', 'HEAD'])
@app.route('/v1/v1', methods=['GET', 'HEAD'])
@app.route('/v1/api/hello', methods=['GET', 'HEAD'])   # Claude-Code-Healthcheck
@app.route('/v1/v1/api/hello', methods=['GET', 'HEAD'])
def health_check():
    return jsonify({"status": "ok", "message": "Heinzelmännchen-Brücke ist aktiv"}), 200

# Nachrichten-Endpoint (Streaming + Non-Streaming, Fallback über alle Endpunkte)
@app.route('/v1/messages', methods=['POST'])
@app.route('/v1/v1/messages', methods=['POST'])
def proxy_messages():
    try:
        ant_data = request.get_json()
        want_stream = bool(ant_data.get("stream", False))

        if not ENDPOINTS:
            return jsonify({"error": "Kein Endpunkt konfiguriert. Bitte ant-hill.conf prüfen."}), 503

        errors = []
        for ep in ENDPOINTS:
            try:
                payload = build_ollama_payload(ant_data, ep["model"])
                resp = call_endpoint(ep, payload)
                resp.raise_for_status()
                anthropic_resp = convert_to_anthropic(resp.json(), respond_model=SPOOFED_MODEL)

                if anthropic_resp is None:
                    raise Exception("Antwort-Konvertierung fehlgeschlagen")

                if want_stream:
                    return Response(anthropic_to_sse(anthropic_resp), mimetype="text/event-stream",
                                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
                return jsonify(anthropic_resp)
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                log_event(f"💥 Endpunkt {ep['url']} fehlgeschlagen: {msg}")
                errors.append({"endpoint": ep["url"], "error": msg})
                continue  # nächster Endpunkt (Fallback)

        return jsonify({"error": "Alle Endpunkte fehlgeschlagen", "tried": errors}), 503
    except Exception as e:
        log_event(f"💥 Proxy-Fehler: {e}")
        return jsonify({"error": str(e)}), 500

# Token-Zählung (wird von neueren Claude-Code-Versionen abgefragt)
@app.route('/v1/messages/count_tokens', methods=['POST'])
@app.route('/v1/v1/messages/count_tokens', methods=['POST'])
def count_tokens():
    try:
        data = request.get_json() or {}
        text = ""
        for m in data.get("messages", []):
            c = m.get("content")
            if isinstance(c, str):
                text += c
            elif isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "text":
                        text += b.get("text", "")
        est = max(1, len(text) // 4)  # grobe Schätzung (Chars/4)
        return jsonify({"input_tokens": est, "output_tokens": 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Modell-Liste
# Liefert den (bekannten) Spoof-Namen plus die echten Modelle aller Endpunkte.
@app.route('/v1/models', methods=['GET'])
@app.route('/v1/v1/models', methods=['GET'])
def list_models():
    ids = [SPOOFED_MODEL] + [ep["model"] for ep in ENDPOINTS]
    seen = set(); data = []
    for mid in ids:
        if mid and mid not in seen:
            seen.add(mid)
            data.append({"id": mid, "object": "model"})
    return jsonify({"data": data})

if __name__ == '__main__':
    ep_list = ", ".join(f"{ep['model']} @ {ep['url']}" for ep in ENDPOINTS) or "KEINE"
    log_event(f"🚀 Brücke gestartet (v3.0.0-conf): [{ep_list}] (antwortet als {SPOOFED_MODEL})")
    app.run(host='0.0.0.0', port=PORT)
#eof
