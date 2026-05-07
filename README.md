# pdf2ocr Project

## Overview
The pdf2ocr project is a Flask-based application that utilizes Tesseract for Optical Character Recognition (OCR) to extract text from images. This project provides a simple interface for users to upload images and receive the extracted text.

## Project Structure
```
pdf2ocr
├── app.py                # Entry point of the application, starts the Flask server
├── requirements.txt      # Lists Python dependencies required for the project
├── Dockerfile            # Instructions for building the Docker image
├── src                   # Source code directory
│   ├── ocr.py           # Contains OCR processing logic
│   ├── api.py           # Defines API endpoints for the application
│   ├── utils.py         # Utility functions for image processing and file handling
│   └── templates
│       └── index.html   # HTML template for the user interface
├── tests                 # Directory for test files
│   └── test_ocr.py      # Tests for OCR functions
├── .devcontainer         # Development container configuration
│   └── devcontainer.json
├── docker-compose.yml    # Defines services needed for the application
├── .gitignore            # Files and directories to be ignored by Git
└── README.md             # Documentation for the project
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd pdf2ocr
   ```

2. Build the Docker image:
   ```
   docker build -t pdf2ocr .
   ```

3. Run the application using Docker Compose:
   ```
   docker-compose up
   ```

## Usage
- Access the application in your web browser at `http://localhost:5000`.
- Upload an image file to extract text using the OCR functionality.

## Curl-Beispiel: Übermittlung und Response
Kurze Anleitung, wie ein Bild per curl an den OCR-Endpoint geschickt wird und welche Antworten zu erwarten sind.

1) Beispiel-Aufruf (multipart/form-data):
```bash
curl -v -X POST "http://localhost:5000/api/ocr" \
  -H "Accept: application/json" \
  -F "file=@/pfad/zum/bild.png"
```
- Verwende den korrekten Pfad zur Bilddatei.
- Falls dein API-Pfad anders lautet, passe `/api/ocr` entsprechend an.

2) Beispiel einer erfolgreichen JSON-Antwort (HTTP 200):
```json
{
  "success": true,
  "text": "Erkannter Text aus dem Bild...",
  "language": "eng",
  "pages": 1
}
```

3) Beispiel einer Fehlerantwort (z. B. fehlende Datei, HTTP 400):
```json
{
  "success": false,
  "error": "No file part in the request" 
}
```

4) Hinweise
- Bei größeren Dateien oder mehreren Seiten kann die Verarbeitung länger dauern; der Response-Body enthält das erkannte Textfeld.
- Optional: füge `-H "Authorization: Bearer <token>"` hinzu, falls der Server Authentifizierung verlangt.

## Testing
To run the tests for the OCR functions, navigate to the `tests` directory and execute:
```
pytest test_ocr.py
```

## API-Key Schutz (optional)
Du kannst einen API-Key setzen, damit der OCR-Webhook nur von berechtigten Clients aufgerufen werden kann. Wenn kein Key gesetzt ist, bleibt die API offen (abwärtskompatibel).

- Lokales Setzen der Umgebungsvariable (Linux/macOS):
```bash
export API_KEY="mein-sehr-geheimer-key"
python app.py
```

- Oder mit Docker Compose: lege eine `.env` Datei an oder setze die Variable in der Umgebung bevor du `docker-compose up` ausführst:
```
API_KEY=mein-sehr-geheimer-key
```

Beispiel-curl mit Header `X-API-Key`:
```bash
curl -X POST http://localhost:5000/api/ocr \
  -H "X-API-Key: mein-sehr-geheimer-key" \
  -F "file=@/pfad/zum/bild.png"
```

Oder mit `Authorization: Bearer`:
```bash
curl -X POST http://localhost:5000/api/ocr \
  -H "Authorization: Bearer mein-sehr-geheimer-key" \
  -F "file=@/pfad/zum/bild.png"
```

Wenn der key fehlt oder falsch ist, liefert der Server HTTP 401.

## Swagger / API-Dokumentation
Nachdem die App gestartet ist, ist die Swagger UI unter folgender URL erreichbar:

- http://localhost:5000/apidocs/

Dort kannst du die `/api/ocr`-Route testen und das erwartete Form-Data (file) direkt im Browser senden.

## Deployment: Coolify / Production
Kurze Anleitung, wie du die Anwendung in Coolify oder allgemein in einer Produktionsumgebung betreiben kannst.

1) `.env.example` kopieren und anpassen:
```bash
cp .env.example .env
# Bearbeite .env und setze API_KEY
```

2) Coolify: In Coolify wähle dein Git-Repository und verwende den Standard-Build. Unsere Einstellungen sind production-freundlich:
- Der `Dockerfile` ist multi-stage und erzeugt ein schlankes Runtime-Image.
- `Procfile` ist vorhanden, Coolify verwendet es falls nötig; das Default-CMD ist `gunicorn -w 4 -b 0.0.0.0:5000 src.api:app`.

3) Lokale Entwicklung mit Docker Compose (optional):
- `docker-compose.override.yml` mountet das Quellverzeichnis und startet Gunicorn in Entwicklungsmodus.

4) Healthchecks
- Der Service hat einen `/health` Endpoint. Coolify kann diesen Endpoint für Healthchecks nutzen.

5) Hinweise
- Entferne in der produktiven Umgebung das Volume-Mount, damit die gebaute Image-Nutzung konsistent bleibt (das Standard `docker-compose.yml` enthält bereits ein kommentiertes Beispiel).


## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.