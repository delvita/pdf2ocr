from flask import Flask, request, jsonify, redirect, Response
from flasgger import Swagger
from .ocr import process_file, OcrResult
from .utils import require_api_key

app = Flask(__name__)

# Swagger configuration with security definitions
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key für Authentifizierung"
        },
        "BearerAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Bearer Token für Authentifizierung (Format: Bearer <key>)"
        }
    }
}

swagger = Swagger(app, config=swagger_config)


@app.route('/apidocs')
def apidocs():
    """Redirect to Swagger UI"""
    return redirect('/apidocs/')


@app.route('/')
def root():
    """
    Root endpoint - gibt keine Informationen zurück
    """
    return "", 404


@app.route('/api/ocr', methods=['POST'])
@require_api_key
def ocr_endpoint():
        """
        OCR Text Extraction
        ---
        tags:
          - OCR
        summary: Extract text from image
        description: |
          Extrahiert Text aus hochgeladenen Dateien mittels OCR.
          
          **Unterstützte Formate:**
          - **PDF**: Direkte Textextraktion oder OCR nach Bildkonvertierung
          - **Bilder**: PNG, JPG, JPEG, GIF, BMP, TIFF
          
          **Verarbeitung:**
          - PDFs werden zuerst auf eingebetteten Text geprüft
          - Falls kein Text gefunden wird, werden PDF-Seiten zu Bildern konvertiert und OCR angewendet
          - Bilder werden direkt mit OCR verarbeitet
          
          **Automatische Spracherkennung:**
          - Erkennt automatisch Deutsch, Englisch, Französisch und Italienisch
          - Optimiert OCR-Genauigkeit basierend auf erkannten Sprachen
          - Fallback auf Mehrsprachen-Modus bei unsicherer Erkennung

          **n8n-Kompatibilität:**
          - PDF-Uploads liefern immer `Content-Type: application/pdf`
          - Vorgeschlagener Dateiname in Header `fileName` und JSON-Feld `fileName` (bei Bildern)
        security:
          - ApiKeyAuth: []
          - BearerAuth: []
        parameters:
          - in: formData
            name: file
            type: file
            required: true
            description: Datei für OCR-Verarbeitung (PDF oder Bild)
        responses:
          200:
            description: |
              **Für PDF-Dateien**: PDF mit integriertem durchsuchbarem Text wird als Download zurückgegeben
              **Für Bilder**: Extrahierter Text wird als JSON zurückgegeben
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    text:
                      type: string
                      example: "Dies ist der extrahierte Text aus der Datei."
                    fileName:
                      type: string
                      example: "Rechnung_12345.pdf"
                    success:
                      type: boolean
                description: "Für Bilddateien - extrahierter Text"
              application/pdf:
                schema:
                  type: string
                  format: binary
                description: "Für PDF-Dateien - PDF mit integriertem durchsuchbarem Text"
          400:
            description: Ungültige Anfrage
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "No file part"
          401:
            description: Nicht autorisiert
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Unauthorized"
          500:
            description: Server-Fehler
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "OCR processing failed"
        """
        if 'file' not in request.files:
                return jsonify({'error': 'No file part', 'success': False}), 400

        file = request.files['file']
    
        if file.filename == '':
                return jsonify({'error': 'No selected file', 'success': False}), 400

        try:
                print(f"API: Verarbeite Datei {file.filename}")
                result = process_file(file.stream, file.filename)

                # Abwärtskompatibilität falls noch rohe bytes/str zurückkommen
                if isinstance(result, bytes):
                    result = OcrResult(
                        text="",
                        pdf_bytes=result,
                        file_name=file.filename.replace(".pdf", "_with_text.pdf"),
                    )
                elif isinstance(result, str):
                    result = OcrResult(text=result, file_name=file.filename)
                elif not isinstance(result, OcrResult):
                    return jsonify({'error': 'Unexpected OCR result', 'success': False}), 500

                file_name = result.file_name or file.filename

                # PDF-Pfad: immer application/pdf + fileName-Header für n8n IF/Google Drive
                if result.pdf_bytes:
                    print(f"API: PDF-Antwort: {len(result.pdf_bytes)} Bytes, fileName={file_name}")
                    return Response(
                        result.pdf_bytes,
                        mimetype='application/pdf',
                        headers={
                            'Content-Type': 'application/pdf',
                            'Content-Disposition': f'attachment; filename="{file_name}"',
                            'fileName': file_name,
                            'X-File-Name': file_name,
                            'X-OCR-Text-Length': str(len(result.text or "")),
                            'Access-Control-Expose-Headers': 'fileName, X-File-Name, Content-Disposition, Content-Type',
                        }
                    )

                print(f"API: Text-Ergebnis: {len(result.text) if result.text else 0} Zeichen, fileName={file_name}")
                return jsonify({
                    'success': True,
                    'text': result.text,
                    'fileName': file_name,
                }), 200
        except Exception as e:
                print(f"API: Fehler: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': str(e), 'success': False}), 500


@app.route('/health', methods=['GET'])
def health():
    """
    Health Check
    ---
    tags:
      - System
    summary: Service Health Status
    description: Überprüft den Gesundheitszustand der Anwendung
    responses:
      200:
        description: Service ist gesund und funktionsfähig
        schema:
          type: object
          properties:
            status:
              type: string
              example: "ok"
            timestamp:
              type: string
              example: "2025-10-23T19:09:00Z"
    """
    import datetime
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }), 200


if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000)
