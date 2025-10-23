from flask import Flask, request, jsonify, redirect
from flasgger import Swagger
from .ocr import process_image
from .utils import require_api_key

app = Flask(__name__)

# OpenAPI Specification
openapi_spec = {
    "openapi": "3.0.0",
    "info": {
        "title": "PDF to OCR API",
        "description": "Eine REST API zum Extrahieren von Text aus Bildern und PDFs mittels OCR (Optical Character Recognition)",
        "version": "1.0.0",
        "contact": {
            "name": "Software By Mike",
            "email": "mike@mf1.ch"
        },
        "license": {
            "name": "MIT"
        }
    },
    "servers": [
        {
            "url": "https://pdf2ocr.wah.ch",
            "description": "Production server"
        }
    ],
    "components": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API Key für Authentifizierung"
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API Key",
                "description": "Bearer Token für Authentifizierung"
            }
        },
        "schemas": {
            "OCRResponse": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Extrahierter Text aus dem Bild"
                    }
                },
                "required": ["text"]
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "Fehlermeldung"
                    }
                },
                "required": ["error"]
            },
            "HealthResponse": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "example": "ok",
                        "description": "Status der Anwendung"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Zeitstempel des Health Checks"
                    }
                },
                "required": ["status", "timestamp"]
            },
            "APIInfoResponse": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "example": "PDF to OCR API"
                    },
                    "version": {
                        "type": "string",
                        "example": "1.0.0"
                    },
                    "endpoints": {
                        "type": "object",
                        "properties": {
                            "api_docs": {
                                "type": "string",
                                "example": "/apidocs/"
                            },
                            "ocr": {
                                "type": "string",
                                "example": "/api/ocr"
                            },
                            "health": {
                                "type": "string",
                                "example": "/health"
                            }
                        }
                    }
                }
            }
        }
    },
    "security": [
        {"ApiKeyAuth": []},
        {"BearerAuth": []}
    ]
}

# Configure Swagger with proper settings
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
    "specs": openapi_spec
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
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/APIInfoResponse'
            example:
              message: "PDF to OCR API"
              version: "1.0.0"
              endpoints:
                api_docs: "/apidocs/"
                ocr: "/api/ocr"
                health: "/health"
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
          Extrahiert Text aus einem hochgeladenen Bild mittels OCR (Optical Character Recognition).
          
          **Unterstützte Formate:**
          - PNG
          - JPG/JPEG
          - GIF
          
          **Authentifizierung:**
          - API Key über Header `X-API-Key` oder `Authorization: Bearer <key>`
          - Nur erforderlich wenn `API_KEY` Umgebungsvariable gesetzt ist
        security:
          - ApiKeyAuth: []
          - BearerAuth: []
        requestBody:
          required: true
          content:
            multipart/form-data:
              schema:
                type: object
                properties:
                  file:
                    type: string
                    format: binary
                    description: Bilddatei für OCR-Verarbeitung
                required:
                  - file
        responses:
          200:
            description: Text erfolgreich extrahiert
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/OCRResponse'
                example:
                  text: "Dies ist der extrahierte Text aus dem Bild."
          400:
            description: Ungültige Anfrage (fehlende Datei oder ungültiges Format)
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/ErrorResponse'
                example:
                  error: "No file part"
          401:
            description: Nicht autorisiert (fehlender oder ungültiger API Key)
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/ErrorResponse'
                example:
                  error: "Unauthorized"
          500:
            description: Server-Fehler bei der OCR-Verarbeitung
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/ErrorResponse'
                example:
                  error: "OCR processing failed"
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
    description: |
      Überprüft den Gesundheitszustand der Anwendung.
      
      **Verwendung:**
      - Docker Healthcheck
      - Load Balancer Health Monitoring
      - Service Discovery
    responses:
      200:
        description: Service ist gesund und funktionsfähig
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/HealthResponse'
            example:
              status: "ok"
              timestamp: "2025-10-23T19:09:00Z"
    """
    import datetime
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }), 200


if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000)