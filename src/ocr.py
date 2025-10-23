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

def create_pdf_with_text(original_pdf_path, extracted_texts, output_path):
    """Erstellt eine neue PDF mit dem extrahierten Text als durchsuchbaren Text."""
    try:
        print(f"Erstelle PDF mit integriertem Text: {output_path}")
        
        # Alternative Lösung: Erstelle eine neue PDF mit dem Text als unsichtbaren Layer
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import Color
        import tempfile
        
        # Erstelle eine temporäre PDF mit dem Text
        temp_pdf_path = tempfile.mktemp(suffix='.pdf')
        
        # Originale PDF lesen
        with open(original_pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Neue PDF erstellen
            pdf_writer = PyPDF2.PdfWriter()
            
            # Für jede Seite
            for i, page in enumerate(pdf_reader.pages):
                print(f"Verarbeite Seite {i+1} für Textintegration...")
                
                # Text für diese Seite hinzufügen (falls vorhanden)
                if i < len(extracted_texts) and extracted_texts[i]:
                    page_text = extracted_texts[i]
                    print(f"Integriere Text für Seite {i+1}: {len(page_text)} Zeichen")
                    
                    # Erstelle eine neue PDF-Seite mit dem Text als unsichtbaren Layer
                    try:
                        # Erstelle eine temporäre PDF mit dem Text
                        temp_text_pdf = tempfile.mktemp(suffix='.pdf')
                        
                        # Erstelle eine PDF mit dem Text (unsichtbar)
                        c = canvas.Canvas(temp_text_pdf, pagesize=letter)
                        
                        # Text als unsichtbaren Layer hinzufügen
                        c.setFillColor(Color(1, 1, 1, 0))  # Transparent
                        c.setFont("Helvetica", 1)  # Sehr kleine Schrift
                        
                        # Text in sehr kleinen Zeilen hinzufügen
                        lines = page_text.split('\n')
                        y = 10
                        for line in lines:
                            if line.strip():
                                c.drawString(0, y, line)
                                y += 1
                        
                        c.save()
                        
                        # Lade die Text-PDF
                        text_pdf_reader = PyPDF2.PdfReader(temp_text_pdf)
                        text_page = text_pdf_reader.pages[0]
                        
                        # Merge die Text-Seite mit der Original-Seite
                        page.merge_page(text_page)
                        
                        # Aufräumen
                        os.unlink(temp_text_pdf)
                        
                        print(f"Text für Seite {i+1} als unsichtbaren Layer integriert")
                        
                    except Exception as e:
                        print(f"Fehler beim Hinzufügen von Text zu Seite {i+1}: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Seite zur neuen PDF hinzufügen
                pdf_writer.add_page(page)
        
        # Neue PDF speichern
        with open(output_path, 'wb') as output_file:
            pdf_writer.write(output_file)
        
        print(f"PDF mit integriertem Text erstellt: {output_path}")
        return True
        
    except Exception as e:
        print(f"Fehler beim Erstellen der PDF mit Text: {e}")
        import traceback
        traceback.print_exc()
        return False

def extract_text_with_language_detection(image_stream, initial_text=""):
    """Extrahiert Text mit automatischer Spracherkennung."""
    try:
        print(f"OCR-Verarbeitung gestartet...")
        
        # Bild aus Stream öffnen
        image = Image.open(image_stream)
        print(f"Bild geladen: {image.size[0]}x{image.size[1]} Pixel")
        
        # Wenn bereits Text vorhanden ist, verwende ihn für Spracherkennung
        if initial_text:
            detected_lang = detect_language_from_text(initial_text)
            print(f"Sprache erkannt: {detected_lang}")
        else:
            # Erst mit Standard-Sprachen versuchen
            detected_lang = 'deu+eng+fra+ita'
            print(f"Verwende Standard-Sprachen: {detected_lang}")
        
        # OCR mit erkannten Sprachen
        print(f"Führe OCR durch mit Sprachen: {detected_lang}")
        text = pytesseract.image_to_string(image, lang=detected_lang)
        print(f"OCR-Ergebnis: {len(text)} Zeichen")
        
        # Falls wenig Text gefunden wurde, mit allen Sprachen erneut versuchen
        if not text.strip() or len(text.strip()) < 10:
            print("Wenig Text gefunden, versuche mit allen Sprachen...")
            text = pytesseract.image_to_string(image, lang='deu+eng+fra+ita')
            print(f"OCR mit allen Sprachen: {len(text)} Zeichen")
        
        result = text.strip() if text.strip() else None
        if result:
            print(f"OCR erfolgreich: {len(result)} Zeichen extrahiert")
        else:
            print("OCR: Kein Text gefunden")
        
        return result
        
    except Exception as e:
        print(f"Fehler beim Verarbeiten des Bildes: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_text_from_pdf(file_stream):
    """Extrahiert Text aus einer PDF-Datei."""
    try:
        print(f"PDF-Verarbeitung gestartet...")
        
        # Zuerst versuchen, Text direkt aus der PDF zu extrahieren
        file_stream.seek(0)  # Stream zurücksetzen
        pdf_reader = PyPDF2.PdfReader(file_stream)
        text = ""
        
        print(f"PDF hat {len(pdf_reader.pages)} Seiten")
        
        for i, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text += page_text + "\n"
                    print(f"Seite {i+1}: {len(page_text)} Zeichen extrahiert")
                else:
                    print(f"Seite {i+1}: Kein Text gefunden")
            except Exception as e:
                print(f"Fehler bei Seite {i+1}: {e}")
        
        # Wenn Text gefunden wurde, zurückgeben
        if text.strip():
            print(f"Direkte PDF-Extraktion erfolgreich: {len(text)} Zeichen")
            return text.strip()
        
        print("Kein Text durch direkte Extraktion gefunden, versuche OCR...")
        
        # Falls kein Text gefunden wurde, PDF zu Bildern konvertieren und OCR anwenden
        file_stream.seek(0)  # Stream zurücksetzen
        
        # Temporäre Datei erstellen
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_stream.read())
            temp_file_path = temp_file.name
        
        print(f"Temporäre PDF-Datei erstellt: {temp_file_path}")
        
        try:
            # PDF zu Bildern konvertieren
            print("Konvertiere PDF zu Bildern...")
            images = convert_from_path(temp_file_path, dpi=300)  # Höhere DPI für bessere OCR
            print(f"PDF zu {len(images)} Bildern konvertiert")
            
            # OCR auf jedes Bild anwenden und Text pro Seite sammeln
            ocr_texts = []  # Liste für Text pro Seite
            ocr_text_combined = ""  # Kombinierter Text für Rückgabe
            
            for i, image in enumerate(images):
                print(f"Verarbeite Bild {i+1}/{len(images)}...")
                # Verwende bereits extrahierten Text für Spracherkennung
                initial_text = text if i == 0 else ""
                
                # Konvertiere PIL Image zu Bytes für OCR
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                page_text = extract_text_with_language_detection(img_bytes, initial_text)
                
                if page_text and page_text.strip():
                    ocr_texts.append(page_text.strip())
                    ocr_text_combined += f"--- Seite {i+1} ---\n{page_text.strip()}\n\n"
                    print(f"Seite {i+1}: {len(page_text)} Zeichen durch OCR extrahiert")
                else:
                    ocr_texts.append("")
                    print(f"Seite {i+1}: Kein Text durch OCR gefunden")
            
            # Erstelle PDF mit integriertem Text
            if any(ocr_texts):  # Falls mindestens eine Seite Text hat
                output_pdf_path = temp_file_path.replace('.pdf', '_with_text.pdf')
                success = create_pdf_with_text(temp_file_path, ocr_texts, output_pdf_path)
                
                if success:
                    print(f"PDF mit integriertem Text erstellt: {output_pdf_path}")
                    # Lese die neue PDF und gib sie zurück
                    with open(output_pdf_path, 'rb') as f:
                        pdf_data = f.read()
                    
                    # Temporäre Dateien löschen
                    if os.path.exists(output_pdf_path):
                        os.unlink(output_pdf_path)
                    
                    return pdf_data  # Gib PDF-Daten zurück statt Text
            
            result = ocr_text_combined.strip() if ocr_text_combined.strip() else None
            if result:
                print(f"OCR erfolgreich: {len(result)} Zeichen insgesamt")
            else:
                print("OCR: Kein Text gefunden")
            
            return result
            
        finally:
            # Temporäre Datei löschen
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                print(f"Temporäre Datei gelöscht: {temp_file_path}")
                
    except Exception as e:
        print(f"Fehler beim Verarbeiten der PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_text_from_image(image_stream):
    """Extrahiert Text aus einem Bild mit automatischer Spracherkennung."""
    return extract_text_with_language_detection(image_stream)

def process_file(file_stream, filename):
    """Verarbeitet eine Datei (Bild oder PDF) und gibt den extrahierten Text zurück."""
    print(f"Verarbeite Datei: {filename}")
    
    # Dateierweiterung ermitteln
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    print(f"Dateierweiterung erkannt: {file_extension}")
    
    if file_extension == 'pdf':
        print("Verarbeite als PDF...")
        # PDF verarbeiten
        text = extract_text_from_pdf(file_stream)
    elif file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']:
        print("Verarbeite als Bild...")
        # Bild verarbeiten
        text = extract_text_from_image(file_stream)
    else:
        error_msg = f"Unterstütztes Dateiformat nicht erkannt. Unterstützte Formate: PDF, PNG, JPG, JPEG, GIF, BMP, TIFF"
        print(error_msg)
        return error_msg
    
    if text:
        print(f"Text erfolgreich extrahiert: {len(text)} Zeichen")
        return text
    
    print("Kein Text gefunden.")
    return "Kein Text gefunden."