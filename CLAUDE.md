# PDF Kompressor

Interne Web-App zur PDF-Komprimierung mit Ghostscript.

## Tech Stack

- **Backend**: Python 3.9+ / Flask
- **PDF-Komprimierung**: Ghostscript
- **Server**: Gunicorn (4 Workers, 120s Timeout)
- **Deployment**: Docker → Dokploy

## Projektstruktur

```
app.py              # Einzige Python-Datei (inkl. inline HTML/CSS/JS)
Dockerfile          # Python 3.11-slim + Ghostscript
requirements.txt    # flask, gunicorn
.gitignore          # venv, __pycache__, etc.
.dockerignore       # Build-Optimierung
```

## Environment-Variablen

| Variable | Pflicht | Beschreibung |
|----------|---------|--------------|
| `LOGIN_PASSWORD` | Ja | Login-Passwort (App startet nicht ohne) |

## Wichtige Konfiguration

- **Max File Size**: 250 MB
- **Session-Cookie**: 3 Monate gültig
- **Temp-Verzeichnis**: `/tmp/pdf-compressor`

## Komprimierungsoptionen

### Auflösung (DPI)
- `unchanged`: Keine Änderung (Standard)
- `print`: 300 DPI
- `ebook`: 150 DPI
- `screen`: 72 DPI

### Qualität (JPEG)
- `very_high`: 95%
- `high`: 80% (Standard)
- `medium`: 60%

## File Cleanup

- Dateien werden sofort nach Download aus Memory gelöscht (BytesIO-Ansatz)
- Beim App-Start: Alte Temp-Files (>1h) werden entfernt
- Beim Shutdown: Alle Temp-Files werden gelöscht

## Lokale Entwicklung

```bash
# Ghostscript muss installiert sein
brew install ghostscript

# venv + dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Server starten
LOGIN_PASSWORD=deinpasswort python app.py
# → http://localhost:8000
```

## Docker

```bash
docker build -t pdf-compressor .
docker run -p 8000:8000 -e LOGIN_PASSWORD=deinpasswort pdf-compressor
```

## Dokploy Deployment

1. GitHub-Repo verbinden
2. Build Type: Dockerfile
3. Environment: `LOGIN_PASSWORD=deinpasswort`
4. Domain + HTTPS konfigurieren
5. Deploy

## Endpoints

| Endpoint | Methode | Auth | Beschreibung |
|----------|---------|------|--------------|
| `/` | GET | Ja | Web-Interface (oder Login) |
| `/login` | POST | Nein | Passwort-Prüfung |
| `/health` | GET | Nein | Health-Check |
| `/compress` | POST | Ja | PDF komprimieren |

## Security

- Passwort nicht im Code, nur als Env-Variable
- Session-Cookie: httponly, samesite=Lax
- PDF Magic-Byte Validation
- UUID-basierte Temp-Dateinamen
- Non-root User im Container
