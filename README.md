# PDF Kompressor

Minimalistische Web-App zur PDF-Komprimierung mit automatischem File-Cleanup.

## Features

- Drag & Drop Upload
- Automatische Komprimierung mit Ghostscript (ebook-Preset)
- Direkter Download der komprimierten Datei
- Automatisches Löschen aller Dateien sofort nach Download
- Keine Persistenz, keine Speicherung

## Tech Stack

- Python 3.11 + Flask
- Ghostscript für PDF-Komprimierung
- Gunicorn als Production Server
- Docker für Deployment

## Lokale Entwicklung

```bash
# Voraussetzung: Ghostscript installiert
# macOS: brew install ghostscript
# Ubuntu: apt-get install ghostscript

# Virtual Environment erstellen
python -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# App starten (Passwort als Env-Variable)
PDF_PASSWORD=deinpasswort python app.py
```

App läuft auf http://localhost:8000

## Docker Build

```bash
docker build -t pdf-compressor .
docker run -p 8000:8000 -e PDF_PASSWORD=deinpasswort pdf-compressor
```

## Dokploy Deployment

### 1. Repository verbinden

1. In Dokploy: **Projects** → **New Project**
2. **Add Service** → **Application**
3. Provider: **GitHub** (oder Git URL)
4. Repository auswählen/URL eingeben
5. Branch: `main`

### 2. Build-Einstellungen

- **Build Type**: Dockerfile
- **Dockerfile Path**: `Dockerfile`

### 3. Domain konfigurieren

1. Tab **Domains** → **Add Domain**
2. Domain eingeben (z.B. `pdf.example.com`)
3. HTTPS aktivieren (Let's Encrypt)
4. Port: `8000`

### 4. Ressourcen (optional)

Unter **Advanced** → **Resources**:
- Memory Limit: 512MB (empfohlen)
- CPU Limit: 1.0

### 5. Deploy

**Deploy** Button klicken. Done.

## Traefik Labels (für manuelles Setup)

Falls du Traefik manuell konfigurierst:

```yaml
services:
  pdf-compressor:
    image: pdf-compressor
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.pdf.rule=Host(`pdf.example.com`)"
      - "traefik.http.routers.pdf.entrypoints=websecure"
      - "traefik.http.routers.pdf.tls.certresolver=letsencrypt"
      - "traefik.http.services.pdf.loadbalancer.server.port=8000"
    restart: unless-stopped
```

## Auto-Cleanup Verhalten

Die App löscht Dateien automatisch:

1. **Sofort nach Download**: Original und komprimierte Datei werden aus dem Speicher gelöscht, bevor die Response gesendet wird (BytesIO-Ansatz)
2. **Beim App-Start**: Alte Temp-Files (älter als 1 Stunde) werden entfernt
3. **Beim Shutdown**: Alle verbleibenden Temp-Files werden gelöscht

Es werden **keine Dateien dauerhaft gespeichert**.

## Limits

- Max. Dateigröße: 50 MB
- Nur PDF-Dateien erlaubt
- Timeout: 120 Sekunden pro Komprimierung

## Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/` | GET | Web-Interface |
| `/health` | GET | Health-Check für Container-Orchestration |
| `/compress` | POST | PDF-Upload und Komprimierung |

## Sicherheit

- File-Extension Whitelist (nur .pdf)
- Magic-Byte Validierung (prüft PDF-Header)
- UUID-basierte Dateinamen (kein Directory Traversal)
- File-Size Check vor Verarbeitung
- Non-root User im Container
