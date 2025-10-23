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

def create_pdf_with_text(original_pdf_path, extracted_texts, output_path, images_cache=None):
    """Erstellt eine neue PDF mit dem extrahierten Text als durchsuchbaren Text."""
    try:
        print(f"Erstelle PDF mit integriertem Text: {output_path}")
        print(f"Original PDF: {original_pdf_path}")
        print(f"Extracted texts: {len(extracted_texts)} Seiten")
        
        # Prüfe ob Original-PDF existiert
        if not os.path.exists(original_pdf_path):
            print(f"FEHLER: Original PDF existiert nicht: {original_pdf_path}")
            return False

        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.colors import Color
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import tempfile
        import pdf2image

        # Konvertiere PDF zu Bildern (oder verwende Cache)
        if images_cache:
            print(f"Verwende gecachte Bilder: {len(images_cache)} Seiten")
            images = images_cache
        else:
            print("Konvertiere PDF zu Bildern...")
            try:
                images = pdf2image.convert_from_path(
                    original_pdf_path,
                    dpi=300,
                    fmt='jpeg',
                    thread_count=1
                )
                print(f"Anzahl Bilder: {len(images)}")
                
                if not images:
                    print("FEHLER: Keine Bilder aus PDF konvertiert")
                    return False
                    
            except Exception as e:
                print(f"FEHLER beim Konvertieren der PDF zu Bildern: {e}")
                import traceback
                traceback.print_exc()
                return False

        # Erstelle eine neue PDF mit ReportLab
        print("Erstelle neue PDF mit ReportLab...")
        try:
            c = canvas.Canvas(output_path, pagesize=A4)
        except Exception as e:
            print(f"FEHLER beim Erstellen des Canvas: {e}")
            return False

        # Für jede Seite
        for i, image in enumerate(images):
            print(f"Verarbeite Seite {i+1} für Textintegration...")

            # Text für diese Seite hinzufügen (falls vorhanden)
            page_text = ""
            if i < len(extracted_texts) and extracted_texts[i]:
                page_text = extracted_texts[i]
                print(f"Integriere Text für Seite {i+1}: {len(page_text)} Zeichen")

            # Neue Seite starten
            if i > 0:
                c.showPage()

            # Bild als Hintergrund hinzufügen
            temp_image_path = None
            try:
                # Speichere das PIL-Bild temporär
                temp_image_path = tempfile.mktemp(suffix='.jpg')
                print(f"Speichere Bild temporär: {temp_image_path}")
                image.save(temp_image_path, 'JPEG', quality=95)
                
                # Prüfe ob Bild gespeichert wurde
                if not os.path.exists(temp_image_path):
                    print(f"FEHLER: Temporäres Bild wurde nicht gespeichert: {temp_image_path}")
                    continue

                # Bild zur PDF hinzufügen
                print(f"Füge Bild zur PDF hinzu: {temp_image_path}")
                c.drawImage(temp_image_path, 0, 0, width=A4[0], height=A4[1])
                print(f"Bild erfolgreich zur PDF hinzugefügt")

            except Exception as e:
                print(f"FEHLER beim Hinzufügen des Bildes zu Seite {i+1}: {e}")
                import traceback
                traceback.print_exc()
                temp_image_path = None

            # Text als durchsuchbaren Layer hinzufügen mit OCR-Positionsdaten
            if page_text.strip():
                try:
                    # Führe OCR mit Positionsdaten durch
                    print(f"Extrahiere Positionsdaten für Seite {i+1}...")
                    
                    # Verwende pytesseract um Wort-Positionen zu erhalten
                    import pytesseract
                    from PIL import Image
                    
                    # Lade das Bild für OCR mit Positionsdaten
                    ocr_data = pytesseract.image_to_data(image, lang='deu+eng+fra+ita', output_type=pytesseract.Output.DICT)
                    
                    # Skalierungsfaktor berechnen (Bild zu PDF)
                    image_width, image_height = image.size
                    scale_x = A4[0] / image_width
                    scale_y = A4[1] / image_height
                    
                    print(f"Bild: {image_width}x{image_height}, PDF: {A4[0]}x{A4[1]}, Scale: {scale_x:.3f}x{scale_y:.3f}")
                    
                    # Text unsichtbar machen (transparent) aber durchsuchbar
                    c.setFillColorRGB(0, 0, 0, 0)  # Vollständig transparent
                    c.setStrokeColorRGB(0, 0, 0, 0)  # Keine Umrandung
                    
                    # Gehe durch alle erkannten Wörter und platziere sie an der richtigen Position
                    n_boxes = len(ocr_data['text'])
                    words_added = 0
                    
                    for j in range(n_boxes):
                        text = ocr_data['text'][j].strip()
                        if text:  # Nur nicht-leere Wörter
                            # Position und Größe aus OCR-Daten
                            x = ocr_data['left'][j]
                            y = ocr_data['top'][j]
                            w = ocr_data['width'][j]
                            h = ocr_data['height'][j]
                            
                            # Skaliere auf PDF-Koordinaten
                            pdf_x = x * scale_x
                            pdf_y = A4[1] - (y * scale_y) - (h * scale_y)  # PDF-Y ist von unten
                            pdf_h = h * scale_y
                            
                            # Berechne Schriftgröße basierend auf Höhe
                            font_size = max(1, pdf_h * 0.8)  # 80% der Höhe
                            
                            # Setze Schrift
                            c.setFont("Helvetica", font_size)
                            
                            # Zeichne Text an der exakten Position
                            c.drawString(pdf_x, pdf_y, text)
                            words_added += 1
                    
                    print(f"Text für Seite {i+1}: {words_added} Wörter an exakten Positionen hinzugefügt")

                except Exception as e:
                    print(f"Fehler beim Hinzufügen von Text mit Positionsdaten zu Seite {i+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Fallback: Text ohne Positionsdaten hinzufügen
                    print(f"Fallback: Füge Text ohne Positionsdaten hinzu...")
                    try:
                        c.setFillColor(Color(0, 0, 0, 0))
                        c.setFont("Helvetica", 1)
                        lines = page_text.split('\n')
                        y_position = A4[1] - 10
                        for line in lines:
                            line = line.strip()
                            if line:
                                c.drawString(0, y_position, line)
                                y_position -= 2
                        print(f"Fallback erfolgreich für Seite {i+1}")
                    except Exception as e2:
                        print(f"Auch Fallback fehlgeschlagen: {e2}")

            # Temporäre Bild-Datei aufräumen
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.unlink(temp_image_path)
                except:
                    pass

        # PDF speichern
        print("Speichere PDF...")
        try:
            c.save()
            print(f"PDF erfolgreich gespeichert: {output_path}")
            
            # Prüfe ob PDF erstellt wurde
            if not os.path.exists(output_path):
                print(f"FEHLER: PDF wurde nicht erstellt: {output_path}")
                return False
                
            # Prüfe PDF-Größe
            file_size = os.path.getsize(output_path)
            print(f"PDF-Größe: {file_size} Bytes")
            
            if file_size == 0:
                print("FEHLER: PDF ist leer (0 Bytes)")
                return False
                
            print(f"PDF mit integriertem Text erfolgreich erstellt: {output_path}")
            return True
            
        except Exception as e:
            print(f"FEHLER beim Speichern der PDF: {e}")
            import traceback
            traceback.print_exc()
            return False

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
            print(f"DEBUG: OCR-Texte vorhanden: {any(ocr_texts)}")
            print(f"DEBUG: Anzahl OCR-Texte: {len(ocr_texts)}")
            if any(ocr_texts):  # Falls mindestens eine Seite Text hat
                output_pdf_path = temp_file_path.replace('.pdf', '_with_text.pdf')
                print(f"DEBUG: Erstelle PDF mit Text: {output_pdf_path}")
                # Verwende die bereits konvertierten Bilder (Cache)
                success = create_pdf_with_text(temp_file_path, ocr_texts, output_pdf_path, images_cache=images)
                print(f"DEBUG: PDF-Erstellung erfolgreich: {success}")
                
                if success:
                    print(f"PDF mit integriertem Text erstellt: {output_pdf_path}")
                    # Lese die neue PDF und gib sie zurück
                    with open(output_pdf_path, 'rb') as f:
                        pdf_data = f.read()
                    
                    # Temporäre Dateien löschen
                    if os.path.exists(output_pdf_path):
                        os.unlink(output_pdf_path)
                    
                    return pdf_data  # Gib PDF-Daten zurück statt Text
            
            # Fallback: Wenn keine PDF erstellt werden konnte, gib Text zurück
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