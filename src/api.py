from flask import Flask, request, jsonify
from flasgger import Swagger
from src.ocr import process_image
from src.utils import require_api_key

app = Flask(__name__)
Swagger(app)


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
        """Simple health endpoint used by Docker/Coolify healthchecks."""
        return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000)