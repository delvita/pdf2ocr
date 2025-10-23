from flask import Flask, request, jsonify, redirect
from flasgger import Swagger
from .ocr import process_image
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
        description: Extrahiert Text aus einem hochgeladenen Bild mittels OCR
        security:
          - ApiKeyAuth: []
          - BearerAuth: []
        parameters:
          - in: formData
            name: file
            type: file
            required: true
            description: Bilddatei für OCR-Verarbeitung
        responses:
          200:
            description: Text erfolgreich extrahiert
            schema:
              type: object
              properties:
                text:
                  type: string
                  example: "Dies ist der extrahierte Text aus dem Bild."
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
                text = process_image(file)
                return jsonify({'text': text}), 200
        except Exception as e:
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