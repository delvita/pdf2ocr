import os
from functools import wraps
from flask import request, jsonify


def preprocess_image(image_path):
    # Hier können Funktionen zur Bildvorverarbeitung hinzugefügt werden
    pass


def save_file(file, upload_folder):
    # Speichert die hochgeladene Datei im angegebenen Verzeichnis
    file_path = os.path.join(upload_folder, file.filename)
    file.save(file_path)
    return file_path


def allowed_file(filename):
    # Überprüft, ob die Datei eine erlaubte Erweiterung hat
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_api_key_from_request():
    """Lese den API Key aus Headern: X-API-Key oder Authorization: Bearer <key>"""
    # Zuerst X-API-Key
    key = request.headers.get('X-API-Key')
    if key:
        return key

    # Dann Authorization: Bearer <key>
    auth = request.headers.get('Authorization')
    if auth and auth.lower().startswith('bearer '):
        return auth.split(None, 1)[1].strip()

    return None


def require_api_key(func):
    """Decorator, der einen API-Key prüft, wenn die Umgebungsvariable API_KEY gesetzt ist.

    Verhalten:
    - Wenn API_KEY nicht gesetzt ist: erlaubt alle Anfragen (abwärtskompatibel).
    - Wenn API_KEY gesetzt ist: fordert Header `X-API-Key: <key>` oder `Authorization: Bearer <key>`.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        configured = os.getenv('API_KEY')
        if not configured:
            # Kein API-Key konfiguriert -> erlauben
            return func(*args, **kwargs)

        provided = _get_api_key_from_request()
        if not provided or provided != configured:
            return jsonify({'error': 'Unauthorized'}), 401

        return func(*args, **kwargs)

    return wrapper