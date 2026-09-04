# 🐝 ant-hill-ollama
**The "Heinzelmännchen-Bridge" between Anthropic's Claude Extension and your local Ollama.**

---

### 🌟 Help us grow!
If this project helps you save API costs or enables your local workflow:
* **Give us a Star!** ⭐ It helps others find this tool and keeps the development of new features alive.
* **Feedback welcome:** Open an issue if you have ideas or found a bug.

---

# 🐝 ant-hill-ollama (Die Heinzelmännchen-Brücke)

[DE] Ein spezialisierter Middleware-Proxy, der **Claude Code** und lokale **Ollama-Modelle** (oder beliebige OpenAI-kompatible Endpunkte) verheiratet. Wie die Heinzelmännchen aus der Sage erledigt dieser Proxy die schwere Protokoll-Arbeit im Verborgenen.

[EN] A specialized middleware proxy marrying **Claude Code** to local **Ollama models** or any OpenAI-compatible endpoint. Like the "Heinzelmännchen" (legendary helpful spirits) of German folklore, this proxy handles the complex protocol translation silently in the background.

---

## ✨ Features (v3.0.0)

- **SSE-Streaming im Anthropic-Format** (`message_start` → … → `message_stop`) – nötig für Claude Code v2.x, behebt das endlose „Spinning"
- **Modell-Spoofing:** antwortet mit einem Katalog-Namen (z. B. `claude-sonnet-4-5`), nutzt intern ein beliebiges Ollama-Modell
- **Beliebige OpenAI-kompatible Endpunkte** über `ant-hill.conf` (Ollama, LLM-Bahnhof, Groq, OpenRouter …)
- **Fallback-Kette:** mehrere Endpunkte – bei Fehlern wird automatisch der nächste probiert
- **Tool-Mapping** (Parameter-Veredelung, z. B. `path` → `file_path`) für Claude Codes Tool-Aufrufe
- **Endpunkte:** `/v1/messages`, `/v1/v1/messages`, `/v1/models`, `/v1/api/hello` (Healthcheck), `/v1/messages/count_tokens`
- **systemd-Dienst** `ant-hill-ollama.service` – läuft dauerhaft, überlebt Reboots

---

## ⚡ Quick Start / Schnelleinrichtung

```bash
# 1. Repository klonen & Umgebung erstellen
git clone https://github.com/o-valo/ant-hill-ollama.git
cd ant-hill-ollama
python3 -m venv venv
source venv/bin/activate

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. Konfiguration anpassen (Endpunkte, Modell, Port)
cp ant-hill.conf.example ant-hill.conf   # falls vorhanden, sonst ant-hill.conf editieren

# 4. Die Heinzelmännchen wecken
./start-claude.sh
```

## ⚙️ Konfiguration (`ant-hill.conf`)

```ini
# Format: ENDPOINT_XX=URL|API-KEY|MODELL|TIMEOUT-Sekunden
ENDPOINT_01=http://10.7.0.93:11434||granite4.1:8b|400
# ENDPOINT_02=http://localhost:8000/v1||mein-modell|120   # 2. Endpunkt = Fallback

SPOOFED_MODEL=claude-sonnet-4-5   # Name, den Claude Code kennt (wird vorgegaukelt)
PROXY_PORT=11435
```

- **URL** wird automatisch um `/v1/chat/completions` ergänzt (mit oder ohne `/v1`)
- **API-Key** optional (leer = kein Auth-Header, z. B. lokales Ollama)
- **Mehrere `ENDPOINT_XX` = Fallback-Kette:** EP1 zuerst, bei Fehlern automatisch EP2, EP3 …
- Priorität: `ant-hill.conf` > Umgebungsvariablen (`OLLAMA_URL`, `MODEL_NAME`, …) > Defaults

## 🛠 Dauerhaft als Dienst (systemd)

```bash
sudo cp ant-hill-ollama.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ant-hill-ollama
# Status prüfen:
systemctl status ant-hill-ollama
```

---

📖 Description / Beschreibung
[DE] Die unsichtbare Arbeit

Wenn Claude Code versucht, Werkzeuge (Tools) zu benutzen, spricht es eine Sprache, die lokale Modelle oft missverstehen. Die Heinzelmännchen-Brücke tritt hier als Vermittler auf:

    Parameter-Veredelung: Er mappt im Hintergrund Parameter (z. B. path -> file_path), damit Dateizugriffe sofort klappen.

    Protokoll-Diplomatie: Er übersetzt zwischen der Anthropic-API und dem Ollama-Endpoint (inkl. SSE-Streaming).

    Stille Persistenz: Als systemd-Dienst gestartet, bleibt die Brücke im Hintergrund aktiv, um jede weitere Sitzung sofort zu unterstützen.

[EN] The Silent Helper

Claude Code's strict tool-calling requirements are translated in real-time to match the capabilities of local LLM endpoints:

    Parameter Mapping: Seamlessly renames arguments for file operations.

    Compatibility: Bridges the gap between Anthropic's protocol and local Ollama APIs (incl. SSE streaming).

    Persistence: As a systemd service, the bridge stays active in the background to support every new session instantly.

🛠 Komponenten / Components

    llm_proxy.py: Der Kern-Übersetzer (Flask-basiert, SSE-Streaming, Conf-Parser).

    ant-hill.conf: Zentrale Konfiguration (Endpunkte, API-Keys, Modell, Spoof-Name, Port).

    run_proxy.sh: Startet den Dienst sicher und portabel.

    start-claude.sh: Der bequeme Einstiegspunkt für die Arbeit mit Claude Code.

    ant-hill-ollama.service: systemd-Vorlage für dauerhaften Betrieb.

👤 Author

Olav (o-valo) – [github.com/o-valo](https://github.com/o-valo)
📜 Lizenz / License

MIT License - "Andere Leute sollen auch Spaß daran haben!" :-)

Powered by AI
