"""
PDF Compressor - Minimalistic PDF compression web app
Uses Ghostscript with customizable DPI and quality settings
Auto-deletes files immediately after download
"""

import os
import uuid
import subprocess
import atexit
import glob
import time
import hashlib
from typing import Optional
from io import BytesIO
from flask import Flask, request, send_file, jsonify, make_response, redirect

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
MAX_FILE_SIZE = 250 * 1024 * 1024  # 250MB
TEMP_DIR = "/tmp/pdf-compressor"
ALLOWED_EXTENSIONS = {".pdf"}
PDF_MAGIC_BYTES = b"%PDF-"

# Auth (password from environment variable)
PASSWORD = os.environ.get("PDF_PASSWORD")
if not PASSWORD:
    raise RuntimeError("PDF_PASSWORD environment variable is required")
AUTH_TOKEN = hashlib.sha256(f"pdf-compressor-{PASSWORD}".encode()).hexdigest()
COOKIE_MAX_AGE = 60 * 60 * 24 * 90  # 3 months

# DPI presets (None = don't change)
DPI_PRESETS = {
    "unchanged": None,
    "print": 300,
    "ebook": 150,
    "screen": 72,
}

# Quality presets (JPEG quality 0-100)
QUALITY_PRESETS = {
    "very_high": 95,
    "high": 80,
    "medium": 60,
}

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)


def cleanup_old_files(max_age_seconds: int = 3600) -> None:
    """Remove temp files older than max_age_seconds (default 1 hour)"""
    now = time.time()
    for filepath in glob.glob(os.path.join(TEMP_DIR, "*.pdf")):
        try:
            if now - os.path.getmtime(filepath) > max_age_seconds:
                os.remove(filepath)
        except OSError:
            pass


def cleanup_all_files() -> None:
    """Remove all temp files (called on shutdown)"""
    for filepath in glob.glob(os.path.join(TEMP_DIR, "*.pdf")):
        try:
            os.remove(filepath)
        except OSError:
            pass


# Cleanup old files on startup and register shutdown cleanup
cleanup_old_files()
atexit.register(cleanup_all_files)


def is_authenticated() -> bool:
    """Check if user has valid auth cookie"""
    return request.cookies.get("auth") == AUTH_TOKEN


def is_valid_pdf(file_stream) -> bool:
    """Check if file starts with PDF magic bytes"""
    header = file_stream.read(5)
    file_stream.seek(0)
    return header == PDF_MAGIC_BYTES


def compress_pdf(input_path: str, output_path: str, dpi: Optional[int] = None, jpeg_quality: int = 80) -> bool:
    """Compress PDF using Ghostscript with custom settings"""
    # Calculate QFactor (0.1 = best quality, 1.0 = worst)
    qfactor = (100 - jpeg_quality) / 100 * 0.9 + 0.1

    cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        # JPEG compression quality
        "-dAutoFilterColorImages=false",
        "-dAutoFilterGrayImages=false",
        "-dColorImageFilter=/DCTEncode",
        "-dGrayImageFilter=/DCTEncode",
        "-c",
        f"<< /ColorACSImageDict << /QFactor {qfactor:.2f} /Blend 1 /HSamples [1 1 1 1] /VSamples [1 1 1 1] >> /GrayACSImageDict << /QFactor {qfactor:.2f} /Blend 1 /HSamples [1 1 1 1] /VSamples [1 1 1 1] >> >> setdistillerparams",
        "-f",
    ]

    # Only add DPI settings if specified
    if dpi is not None:
        # Insert DPI settings before -c
        dpi_settings = [
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            "-dColorImageDownsampleType=/Bicubic",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dMonoImageDownsampleType=/Bicubic",
            f"-dColorImageResolution={dpi}",
            f"-dGrayImageResolution={dpi}",
            f"-dMonoImageResolution={dpi}",
        ]
        # Insert before JPEG settings
        idx = cmd.index("-dAutoFilterColorImages=false")
        for i, setting in enumerate(dpi_settings):
            cmd.insert(idx + i, setting)

    cmd.append(input_path)

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def safe_remove(filepath: str) -> None:
    """Safely remove a file, ignoring errors"""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass


LOGIN_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Kompressor - Login</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 360px;
            width: 100%;
            text-align: center;
        }
        h1 { color: #333; margin-bottom: 8px; font-size: 24px; }
        .subtitle { color: #666; margin-bottom: 32px; font-size: 14px; }
        .error {
            background: #fff5f5;
            border: 1px solid #fed7d7;
            color: #c53030;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        input[type="password"] {
            width: 100%;
            padding: 14px 16px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            margin-bottom: 16px;
            transition: border-color 0.2s;
        }
        input[type="password"]:focus {
            outline: none;
            border-color: #4a90d9;
        }
        .btn {
            background: #4a90d9;
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.2s;
            width: 100%;
        }
        .btn:hover { background: #3a7bc8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>PDF Kompressor</h1>
        <p class="subtitle">Bitte Passwort eingeben</p>
        {{ERROR}}
        <form method="POST" action="/login">
            <input type="password" name="password" placeholder="Passwort" autofocus required>
            <button type="submit" class="btn">Anmelden</button>
        </form>
    </div>
</body>
</html>"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Kompressor</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 480px;
            width: 100%;
            text-align: center;
        }
        h1 { color: #333; margin-bottom: 8px; font-size: 24px; }
        .subtitle { color: #666; margin-bottom: 24px; font-size: 14px; }
        .settings {
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
            justify-content: center;
        }
        .setting {
            flex: 1;
            max-width: 180px;
        }
        .setting label {
            display: block;
            font-size: 12px;
            color: #666;
            margin-bottom: 6px;
            text-align: left;
        }
        .setting select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            background: white;
            cursor: pointer;
            transition: border-color 0.2s;
        }
        .setting select:hover { border-color: #4a90d9; }
        .setting select:focus { outline: none; border-color: #4a90d9; }
        .dropzone {
            border: 2px dashed #ccc;
            border-radius: 12px;
            padding: 48px 24px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: #fafafa;
        }
        .dropzone:hover, .dropzone.dragover {
            border-color: #4a90d9;
            background: #f0f7ff;
        }
        .dropzone-text { color: #666; font-size: 16px; }
        .dropzone-hint { color: #999; font-size: 12px; margin-top: 8px; }
        .hidden { display: none !important; }
        .progress {
            margin-top: 24px;
            padding: 24px;
            background: #f8f9fa;
            border-radius: 12px;
        }
        .spinner {
            width: 40px; height: 40px;
            border: 3px solid #e0e0e0;
            border-top-color: #4a90d9;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .result {
            margin-top: 24px;
            padding: 24px;
            background: #f0fff4;
            border-radius: 12px;
            border: 1px solid #c6f6d5;
        }
        .result.error {
            background: #fff5f5;
            border-color: #fed7d7;
        }
        .result h3 { color: #276749; margin-bottom: 16px; }
        .result.error h3 { color: #c53030; }
        .stats {
            display: flex;
            justify-content: space-around;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .stat { text-align: center; }
        .stat-value { font-size: 20px; font-weight: 600; color: #333; }
        .stat-label { font-size: 12px; color: #666; margin-top: 4px; }
        .savings {
            font-size: 14px;
            color: #276749;
            background: #c6f6d5;
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 16px;
        }
        .btn {
            background: #4a90d9;
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #3a7bc8; }
        .btn-secondary {
            background: transparent;
            color: #666;
            margin-top: 12px;
            padding: 10px 24px;
        }
        .btn-secondary:hover { background: #f0f0f0; }
        input[type="file"] { display: none; }
        @media (max-width: 400px) {
            .settings { flex-direction: column; align-items: center; }
            .setting { max-width: 100%; width: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>PDF Kompressor</h1>
        <p class="subtitle">Ziehe eine PDF-Datei hierher oder klicke zum Auswählen</p>

        <div class="settings" id="settings">
            <div class="setting">
                <label for="dpi">Auflösung</label>
                <select id="dpi">
                    <option value="unchanged" selected>Nicht verändern</option>
                    <option value="print">Druck (300 DPI)</option>
                    <option value="ebook">E-Book (150 DPI)</option>
                    <option value="screen">Screen (72 DPI)</option>
                </select>
            </div>
            <div class="setting">
                <label for="quality">Qualität</label>
                <select id="quality">
                    <option value="very_high">Sehr hoch</option>
                    <option value="high" selected>Hoch</option>
                    <option value="medium">Mittel</option>
                </select>
            </div>
        </div>

        <div class="dropzone" id="dropzone">
            <p class="dropzone-text">PDF hier ablegen</p>
            <p class="dropzone-hint">Maximal 250 MB</p>
        </div>
        <input type="file" id="fileInput" accept=".pdf">

        <div class="progress hidden" id="progress">
            <div class="spinner"></div>
            <p>Komprimiere PDF...</p>
        </div>

        <div class="result hidden" id="result">
            <h3 id="resultTitle">Fertig!</h3>
            <div id="resultContent"></div>
        </div>
    </div>

    <script>
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const progress = document.getElementById('progress');
        const result = document.getElementById('result');
        const resultTitle = document.getElementById('resultTitle');
        const resultContent = document.getElementById('resultContent');
        const settings = document.getElementById('settings');
        const dpiSelect = document.getElementById('dpi');
        const qualitySelect = document.getElementById('quality');

        dropzone.addEventListener('click', () => fileInput.click());

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) handleFile(files[0]);
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
        });

        function formatSize(bytes) {
            return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        }

        function handleFile(file) {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                showError('Nur PDF-Dateien sind erlaubt.');
                return;
            }
            if (file.size > 250 * 1024 * 1024) {
                showError('Datei ist zu groß (max. 250 MB).');
                return;
            }

            const originalSize = file.size;
            dropzone.classList.add('hidden');
            settings.classList.add('hidden');
            result.classList.add('hidden');
            progress.classList.remove('hidden');

            const formData = new FormData();
            formData.append('file', file);
            formData.append('dpi', dpiSelect.value);
            formData.append('quality', qualitySelect.value);

            fetch('/compress', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => { throw new Error(data.error); });
                }
                const compressedSize = parseInt(response.headers.get('X-Compressed-Size') || '0');
                return response.blob().then(blob => ({ blob, compressedSize }));
            })
            .then(({ blob, compressedSize }) => {
                progress.classList.add('hidden');
                result.classList.remove('hidden');
                result.classList.remove('error');
                resultTitle.textContent = 'Fertig!';

                const savings = ((1 - compressedSize / originalSize) * 100).toFixed(1);
                const downloadUrl = URL.createObjectURL(blob);
                const fileName = file.name.replace('.pdf', '_komprimiert.pdf');

                resultContent.innerHTML = `
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-value">${formatSize(originalSize)}</div>
                            <div class="stat-label">Original</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">${formatSize(compressedSize)}</div>
                            <div class="stat-label">Komprimiert</div>
                        </div>
                    </div>
                    <div class="savings">${savings}% kleiner</div><br>
                    <a href="${downloadUrl}" download="${fileName}" class="btn">Download</a>
                    <br><button class="btn btn-secondary" onclick="reset()">Weitere Datei</button>
                `;
            })
            .catch(error => {
                showError(error.message || 'Ein Fehler ist aufgetreten.');
            });
        }

        function showError(message) {
            progress.classList.add('hidden');
            dropzone.classList.add('hidden');
            settings.classList.add('hidden');
            result.classList.remove('hidden');
            result.classList.add('error');
            resultTitle.textContent = 'Fehler';
            resultContent.innerHTML = `
                <p style="margin-bottom: 16px; color: #c53030;">${message}</p>
                <button class="btn btn-secondary" onclick="reset()">Erneut versuchen</button>
            `;
        }

        function reset() {
            fileInput.value = '';
            dropzone.classList.remove('hidden');
            settings.classList.remove('hidden');
            result.classList.add('hidden');
            progress.classList.add('hidden');
        }
    </script>
</body>
</html>"""


@app.route("/")
def index():
    if not is_authenticated():
        return LOGIN_TEMPLATE.replace("{{ERROR}}", "")
    return HTML_TEMPLATE


@app.route("/login", methods=["POST"])
def login():
    password = request.form.get("password", "")
    if password == PASSWORD:
        response = make_response(redirect("/"))
        response.set_cookie("auth", AUTH_TOKEN, max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax")
        return response
    return LOGIN_TEMPLATE.replace("{{ERROR}}", '<div class="error">Falsches Passwort</div>')


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/compress", methods=["POST"])
def compress():
    if not is_authenticated():
        return jsonify({"error": "Nicht autorisiert"}), 401

    if "file" not in request.files:
        return jsonify({"error": "Keine Datei hochgeladen"}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"error": "Keine Datei ausgewählt"}), 400

    # Check extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Nur PDF-Dateien sind erlaubt"}), 400

    # Check file size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)

    if size > MAX_FILE_SIZE:
        return jsonify({"error": "Datei ist zu groß (max. 250 MB)"}), 400

    if size == 0:
        return jsonify({"error": "Datei ist leer"}), 400

    # Validate PDF magic bytes
    if not is_valid_pdf(file):
        return jsonify({"error": "Ungültige PDF-Datei"}), 400

    # Get compression settings
    dpi_preset = request.form.get("dpi", "unchanged")
    quality_preset = request.form.get("quality", "high")

    dpi = DPI_PRESETS.get(dpi_preset)
    jpeg_quality = QUALITY_PRESETS.get(quality_preset, 80)

    # Generate unique filenames
    file_id = str(uuid.uuid4())
    input_path = os.path.join(TEMP_DIR, f"{file_id}_input.pdf")
    output_path = os.path.join(TEMP_DIR, f"{file_id}_output.pdf")

    try:
        # Save uploaded file
        file.save(input_path)

        # Compress PDF
        if not compress_pdf(input_path, output_path, dpi=dpi, jpeg_quality=jpeg_quality):
            return jsonify({"error": "Komprimierung fehlgeschlagen"}), 500

        # Check if output exists
        if not os.path.exists(output_path):
            return jsonify({"error": "Komprimierung fehlgeschlagen"}), 500

        # Read compressed file into memory
        compressed_size = os.path.getsize(output_path)
        with open(output_path, "rb") as f:
            compressed_data = BytesIO(f.read())

        # Delete temp files immediately
        safe_remove(input_path)
        safe_remove(output_path)

        # Send from memory
        compressed_data.seek(0)
        response = send_file(
            compressed_data,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="compressed.pdf",
        )
        response.headers["X-Compressed-Size"] = str(compressed_size)
        response.headers["Access-Control-Expose-Headers"] = "X-Compressed-Size"
        return response

    except Exception as e:
        # Cleanup on error
        safe_remove(input_path)
        safe_remove(output_path)
        return jsonify({"error": "Ein Fehler ist aufgetreten"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
