# 🐝 ant-hill-ollama (Die Heinzelmännchen-Brücke)

[DE] Ein spezialisierter Middleware-Proxy, der **Claude Code** und lokale **Ollama-Modelle** verheiratet. Wie die Heinzelmännchen aus der Sage erledigt dieser Proxy die schwere Protokoll-Arbeit im Verborgenen.

[EN] A specialized middleware proxy marrying **Claude Code** to local **Ollama models**. Like the "Heinzelmännchen" (legendary helpful spirits) of German folklore, this proxy handles the complex protocol translation silently in the background.

---

## ⚡ Quick Start / Schnelleinrichtung

```bash
# 1. Repository klonen & Umgebung erstellen
git clone [https://github.com/o-valo/ant-hill-ollama.git](https://github.com/o-valo/ant-hill-ollama.git)
cd ant-hill-ollama
python3 -m venv venv
source venv/bin/activate

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. Die Heinzelmännchen wecken
./start-claude.sh

```
📖 Description / Beschreibung
[DE] Die unsichtbare Arbeit

Wenn Claude Code versucht, Werkzeuge (Tools) zu benutzen, spricht es eine Sprache, die lokale Modelle oft missverstehen. Die Heinzelmännchen-Brücke tritt hier als Vermittler auf:

    Parameter-Veredelung: Er mappt im Hintergrund Parameter (z. B. path -> file_path), damit Dateizugriffe sofort klappen.

    Protokoll-Diplomatie: Er übersetzt zwischen der Anthropic-API und dem Ollama-Endpoint.

    Stille Persistenz: Einmal gestartet, bleibt der Dienst im Hintergrund aktiv, um jede weitere Sitzung sofort zu unterstützen.

[EN] The Silent Helper

Claude Code's strict tool-calling requirements are translated in real-time to match the capabilities of local LLM endpoints:

    Parameter Mapping: Seamlessly renames arguments for file operations.

    Compatibility: Bridges the gap between Anthropic's protocol and local Ollama APIs.

🛠 Komponenten / Components

    llm_proxy.py: Der Kern-Übersetzer (Flask-basiert).

    run_proxy.sh: Startet den Dienst sicher und portabel.

    start-claude.sh: Der bequeme Einstiegspunkt für die Arbeit.

👤 Author

Olav (o-valo) GitHub Profile
📜 Lizenz / License

MIT License - "Andere Leute sollen auch Spaß daran haben!" :-)


---

### 2. Mini-Update für die `llm_proxy.py` (Header)
Damit die Log-Datei auch den richtigen Namen zeigt:
```python
# ... (Anfang der Datei)
VERSION = "1.7.6-ant-hill"
# ...
if __name__ == '__main__':
    log_event(f"--- ant-hill-ollama (Heinzelmännchen-Brücke) {VERSION} gestartet ---")
    app.run(host='0.0.0.0', port=PORT)




