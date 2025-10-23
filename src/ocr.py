from PIL import Image
import pytesseract
import PyPDF2
from pdf2image import convert_from_path
import io
import os
import tempfile
import re

def detect_language_from_text(text):
    """Erkennt die Sprache des Textes basierend auf charakteristischen Zeichen und Wörtern."""
    if not text or len(text.strip()) < 10:
        return 'deu+eng'  # Standard-Fallback
    
    text_lower = text.lower()
    
    # Deutsche Indikatoren
    german_indicators = [
        r'\b(der|die|das|und|oder|mit|von|zu|in|auf|für|ist|sind|haben|werden|können|müssen|sollen)\b',
        r'[äöüß]',  # Deutsche Umlaute
        r'\b(ich|du|er|sie|es|wir|ihr|sie)\b'
    ]
    
    # Französische Indikatoren
    french_indicators = [
        r'\b(le|la|les|de|du|des|et|ou|avec|pour|dans|sur|est|sont|avoir|être|pouvoir|devoir)\b',
        r'[àâäéèêëïîôöùûüÿç]',  # Französische Akzente
        r'\b(je|tu|il|elle|nous|vous|ils|elles)\b'
    ]
    
    # Italienische Indikatoren
    italian_indicators = [
        r'\b(il|la|lo|gli|le|di|del|della|e|o|con|per|in|su|è|sono|avere|essere|potere|dovere)\b',
        r'[àèéìíîòóù]',  # Italienische Akzente
        r'\b(io|tu|lui|lei|noi|voi|loro)\b'
    ]
    
    # Englische Indikatoren
    english_indicators = [
        r'\b(the|and|or|with|for|in|on|at|to|of|is|are|have|will|can|must|should)\b',
        r'\b(i|you|he|she|it|we|they)\b'
    ]
    
    # Zähle Indikatoren für jede Sprache
    languages = {
        'deu': sum(len(re.findall(pattern, text_lower)) for pattern in german_indicators),
        'fra': sum(len(re.findall(pattern, text_lower)) for pattern in french_indicators),
        'ita': sum(len(re.findall(pattern, text_lower)) for pattern in italian_indicators),
        'eng': sum(len(re.findall(pattern, text_lower)) for pattern in english_indicators)
    }
    
    # Finde die Sprache mit den meisten Indikatoren
    detected_lang = max(languages, key=languages.get)
    
    # Wenn die Erkennung zu unsicher ist, verwende Mehrsprachen-Modus
    if languages[detected_lang] < 3:
        return 'deu+eng+fra+ita'  # Alle verfügbaren Sprachen
    
    # Kombiniere die zwei häufigsten Sprachen
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_langs) >= 2 and sorted_langs[1][1] > 0:
        return f"{sorted_langs[0][0]}+{sorted_langs[1][0]}"
    
    return detected_lang

def extract_text_with_language_detection(image_stream, initial_text=""):
    """Extrahiert Text mit automatischer Spracherkennung."""
    try:
        # Bild aus Stream öffnen
        image = Image.open(image_stream)
        
        # Wenn bereits Text vorhanden ist, verwende ihn für Spracherkennung
        if initial_text:
            detected_lang = detect_language_from_text(initial_text)
        else:
            # Erst mit Standard-Sprachen versuchen
            detected_lang = 'deu+eng+fra+ita'
        
        # OCR mit erkannten Sprachen
        text = pytesseract.image_to_string(image, lang=detected_lang)
        
        # Falls wenig Text gefunden wurde, mit allen Sprachen erneut versuchen
        if not text.strip() or len(text.strip()) < 10:
            text = pytesseract.image_to_string(image, lang='deu+eng+fra+ita')
        
        return text.strip() if text.strip() else None
        
    except Exception as e:
        print(f"Fehler beim Verarbeiten des Bildes: {e}")
        return None

def extract_text_from_pdf(file_stream):
    """Extrahiert Text aus einer PDF-Datei."""
    try:
        # Zuerst versuchen, Text direkt aus der PDF zu extrahieren
        pdf_reader = PyPDF2.PdfReader(file_stream)
        text = ""
        
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        # Wenn Text gefunden wurde, zurückgeben
        if text.strip():
            return text.strip()
        
        # Falls kein Text gefunden wurde, PDF zu Bildern konvertieren und OCR anwenden
        file_stream.seek(0)  # Stream zurücksetzen
        
        # Temporäre Datei erstellen
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_stream.read())
            temp_file_path = temp_file.name
        
        try:
            # PDF zu Bildern konvertieren
            images = convert_from_path(temp_file_path)
            
            # OCR auf jedes Bild anwenden mit automatischer Spracherkennung
            ocr_text = ""
            detected_language = None
            
            for i, image in enumerate(images):
                # Verwende bereits extrahierten Text für Spracherkennung
                initial_text = text if i == 0 else ""
                page_text = extract_text_with_language_detection(image, initial_text)
                
                if page_text.strip():
                    ocr_text += f"--- Seite {i+1} ---\n{page_text.strip()}\n\n"
            
            return ocr_text.strip() if ocr_text.strip() else None
            
        finally:
            # Temporäre Datei löschen
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        print(f"Fehler beim Verarbeiten der PDF: {e}")
        return None

def extract_text_from_image(image_stream):
    """Extrahiert Text aus einem Bild mit automatischer Spracherkennung."""
    return extract_text_with_language_detection(image_stream)

def process_file(file_stream, filename):
    """Verarbeitet eine Datei (Bild oder PDF) und gibt den extrahierten Text zurück."""
    # Dateierweiterung ermitteln
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if file_extension == 'pdf':
        # PDF verarbeiten
        text = extract_text_from_pdf(file_stream)
    elif file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']:
        # Bild verarbeiten
        text = extract_text_from_image(file_stream)
    else:
        return f"Unterstütztes Dateiformat nicht erkannt. Unterstützte Formate: PDF, PNG, JPG, JPEG, GIF, BMP, TIFF"
    
    if text:
        return text
    return "Kein Text gefunden."