from PIL import Image
import pytesseract

def extract_text_from_image(image_path):
    """Extrahiert Text aus einem Bild mit Tesseract OCR."""
    try:
        # Bild öffnen
        image = Image.open(image_path)
        # Text extrahieren
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Fehler beim Verarbeiten des Bildes: {e}")
        return None

def process_image(image_path):
    """Verarbeitet das Bild und gibt den extrahierten Text zurück."""
    text = extract_text_from_image(image_path)
    if text:
        return text.strip()
    return "Kein Text gefunden."