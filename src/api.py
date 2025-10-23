from flask import Flask, request, jsonify
from flasgger import Swagger
from .ocr import process_image
from .utils import require_api_key

app = Flask(__name__)
swagger = Swagger(app)


@app.route('/api/ocr', methods=['POST'])
@require_api_key
def ocr_endpoint():
        """
        OCR endpoint
        ---
        consumes:
            - multipart/form-data
        parameters:
            - in: formData
                name: file
                type: file
                required: true
                description: Image file to perform OCR on
        responses:
            200:
                description: OCR result
                schema:
                    type: object
                    properties:
                        text:
                            type: string
            400:
                description: Bad request (missing file)
            401:
                description: Unauthorized (missing/invalid API key)
            500:
                description: Server error
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
    """Health check endpoint for Docker/Coolify
    ---
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
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