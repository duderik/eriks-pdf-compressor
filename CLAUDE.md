# PDF Kompressor

Interne Web-App zur PDF-Komprimierung mit Ghostscript.

## Tech Stack

- **Backend**: Python 3.11 + Flask
- **PDF-Komprimierung**: Ghostscript
- **Server**: Gunicorn (4 Workers, 120s Timeout)
- **Deployment**: Docker → Dokploy

## Projektstruktur

```
app.py              # Einzige Python-Datei (inkl. inline HTML/CSS/JS)
Dockerfile          # Python 3.11-slim + Ghostscript
requirements.txt    # flask, gunicorn
```

## Wichtige Konfiguration

- **Max File Size**: 250 MB
- **Passwort**: Env-Variable `PDF_PASSWORD` (Session-Cookie, 3 Monate gültig)
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
PDF_PASSWORD=deinpasswort python app.py
# → http://localhost:8000
```

## Docker

```bash
docker build -t pdf-compressor .
docker run -p 8000:8000 -e PDF_PASSWORD=deinpasswort pdf-compressor
```

## Endpoints

| Endpoint | Methode | Auth | Beschreibung |
|----------|---------|------|--------------|
| `/` | GET | Ja | Web-Interface (oder Login) |
| `/login` | POST | Nein | Passwort-Prüfung |
| `/health` | GET | Nein | Health-Check |
| `/compress` | POST | Ja | PDF komprimieren |
