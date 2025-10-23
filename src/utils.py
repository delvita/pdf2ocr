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