from flask import Flask, request, jsonify, redirect
from flasgger import Swagger
from .ocr import process_file
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
    Root endpoint with API information
    ---
    tags:
      - General
    summary: API Information
    description: Gibt grundlegende Informationen über die API zurück
    responses:
      200:
        description: API-Informationen erfolgreich abgerufen
        schema:
          type: object
          properties:
            message:
              type: string
              example: "PDF to OCR API"
            version:
              type: string
              example: "1.0.0"
            endpoints:
              type: object
              properties:
                api_docs:
                  type: string
                  example: "/apidocs/"
                ocr:
                  type: string
                  example: "/api/ocr"
                health:
                  type: string
                  example: "/health"
    """
    return jsonify({
        "message": "PDF to OCR API",
        "version": "1.0.0",
        "endpoints": {
            "api_docs": "/apidocs/",
            "ocr": "/api/ocr",
            "health": "/health"
        }
    }), 200


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
                return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
    
        if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400

        try:
                print(f"API: Verarbeite Datei {file.filename}")
                result = process_file(file.stream, file.filename)
                
                # Prüfe ob Ergebnis PDF-Daten oder Text ist
                if isinstance(result, bytes):
                    print(f"API: PDF mit integriertem Text erstellt: {len(result)} Bytes")
                    # Gib PDF-Datei zurück
                    from flask import Response
                    return Response(
                        result,
                        mimetype='application/pdf',
                        headers={
                            'Content-Disposition': f'attachment; filename="{file.filename.replace(".pdf", "_with_text.pdf")}"'
                        }
                    )
                else:
                    print(f"API: Text-Ergebnis: {len(result) if result else 0} Zeichen")
                    return jsonify({'text': result}), 200
        except Exception as e:
                print(f"API: Fehler: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500


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