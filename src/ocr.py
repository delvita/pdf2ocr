from PIL import Image
import pytesseract
import PyPDF2
from pdf2image import convert_from_path
import io
import os
import tempfile
import re
import inspect
import time
from dataclasses import dataclass
from typing import Optional

# Große Raster + 4 Sprachen lassen Tesseract sehr lange rechnen (wirkt wie „Hänger“ / Endlosschleife).
OCR_MAX_DIMENSION = int(os.environ.get("OCR_MAX_DIMENSION", "1600"))
# Harte Obergrenze pro Tesseract-Call, damit n8n-HTTP-Timeout nicht ins Leere läuft.
TESSERACT_TIMEOUT = int(os.environ.get("TESSERACT_TIMEOUT", "90"))
TESSERACT_CONFIG_FAST = os.environ.get("TESSERACT_CONFIG", "--oem 1 --psm 3")
EXTENDED_LANGS = "deu+eng+fra+ita"
PRIMARY_LANGS = "deu+eng"
OCR_LOG_TESSERACT_INFO = os.environ.get("OCR_LOG_TESSERACT_INFO", "1").lower() in ("1", "true", "yes", "on")
_TESSERACT_INFO_LOGGED = False


@dataclass
class OcrResult:
    """Ergebnis für API/n8n: Text, optional PDF-Bytes und vorgeschlagener Dateiname."""
    text: str
    pdf_bytes: Optional[bytes] = None
    file_name: Optional[str] = None


def suggest_filename(text: str, original_filename: str) -> str:
    """Gibt in Stufe 1 den Originalnamen zurück (keine Umbenennung → keine Drive-Konflikte).

    text bleibt für eine spätere Stufe verfügbar; wird hier bewusst nicht genutzt.
    """
    _ = text  # reserviert für spätere Dateinamenfindung aus OCR
    return original_filename or "document.pdf"


def _prepare_image_for_ocr(image):
    """Verkleinert große Seiten für schnellere OCR; Qualität bleibt für Drucksachen meist ausreichend."""
    w, h = image.size
    m = max(w, h)
    if OCR_MAX_DIMENSION <= 0 or m <= OCR_MAX_DIMENSION:
        return image
    scale = OCR_MAX_DIMENSION / float(m)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return image.resize((nw, nh), Image.LANCZOS)


def _ocr_log(stage, **fields):
    payload = " ".join(f"{k}={fields[k]}" for k in sorted(fields.keys()))
    print(f"[OCR] stage={stage} {payload}".strip())


def _log_tesseract_runtime_info_once():
    global _TESSERACT_INFO_LOGGED
    if _TESSERACT_INFO_LOGGED or not OCR_LOG_TESSERACT_INFO:
        return
    _TESSERACT_INFO_LOGGED = True
    try:
        version = str(pytesseract.get_tesseract_version()).replace("\n", " ")
        _ocr_log("tesseract_version", value=version)
    except Exception as e:
        _ocr_log("tesseract_version_error", error_type=type(e).__name__, message=str(e))

    try:
        langs = pytesseract.get_languages(config="")
        _ocr_log("tesseract_languages", count=len(langs), value=",".join(langs))
    except Exception as e:
        _ocr_log("tesseract_languages_error", error_type=type(e).__name__, message=str(e))

    _ocr_log(
        "tesseract_env",
        timeout=TESSERACT_TIMEOUT,
        max_dim=OCR_MAX_DIMENSION,
        tessdata_prefix=os.environ.get("TESSDATA_PREFIX", "<unset>"),
    )


def _tesseract_call_kwargs():
    """timeout nur übergeben, wenn diese pytesseract-Version ihn unterstützt."""
    if TESSERACT_TIMEOUT and TESSERACT_TIMEOUT > 0:
        try:
            sig = inspect.signature(pytesseract.image_to_string)
            if "timeout" in sig.parameters:
                return {"timeout": TESSERACT_TIMEOUT}
        except (TypeError, ValueError):
            pass
    return {}


def _image_to_string(image, lang, config=None):
    cfg = config if config is not None else TESSERACT_CONFIG_FAST
    kw = _tesseract_call_kwargs()
    _log_tesseract_runtime_info_once()
    started = time.time()
    _ocr_log("ocr_attempt_start", op="image_to_string", lang=lang, config=cfg, width=image.size[0], height=image.size[1])
    try:
        result = pytesseract.image_to_string(image, lang=lang, config=cfg, **kw)
        _ocr_log(
            "ocr_attempt_success",
            op="image_to_string",
            lang=lang,
            elapsed_s=f"{time.time() - started:.2f}",
            chars=len(result.strip()) if result else 0,
        )
        return result
    except RuntimeError as e:
        _ocr_log(
            "ocr_attempt_error",
            op="image_to_string",
            lang=lang,
            elapsed_s=f"{time.time() - started:.2f}",
            error_type=type(e).__name__,
            message=str(e),
        )
        return ""
    except TypeError:
        try:
            result = pytesseract.image_to_string(image, lang=lang, config=cfg)
            _ocr_log(
                "ocr_attempt_success",
                op="image_to_string",
                lang=lang,
                elapsed_s=f"{time.time() - started:.2f}",
                chars=len(result.strip()) if result else 0,
                note="fallback_without_timeout_kw",
            )
            return result
        except RuntimeError as e:
            _ocr_log(
                "ocr_attempt_error",
                op="image_to_string",
                lang=lang,
                elapsed_s=f"{time.time() - started:.2f}",
                error_type=type(e).__name__,
                message=str(e),
                note="fallback_without_timeout_kw",
            )
            return ""


def _image_to_data(image, lang, config=None):
    cfg = config if config is not None else TESSERACT_CONFIG_FAST
    kw = _tesseract_call_kwargs()
    _log_tesseract_runtime_info_once()
    started = time.time()
    _ocr_log("ocr_attempt_start", op="image_to_data", lang=lang, config=cfg, width=image.size[0], height=image.size[1])
    try:
        result = pytesseract.image_to_data(
            image, lang=lang, config=cfg, output_type=pytesseract.Output.DICT, **kw
        )
        _ocr_log(
            "ocr_attempt_success",
            op="image_to_data",
            lang=lang,
            elapsed_s=f"{time.time() - started:.2f}",
            words=len(result.get("text", [])),
        )
        return result
    except RuntimeError as e:
        _ocr_log(
            "ocr_attempt_error",
            op="image_to_data",
            lang=lang,
            elapsed_s=f"{time.time() - started:.2f}",
            error_type=type(e).__name__,
            message=str(e),
        )
        return {"text": [], "left": [], "top": [], "width": [], "height": []}
    except TypeError:
        try:
            result = pytesseract.image_to_data(
                image, lang=lang, config=cfg, output_type=pytesseract.Output.DICT
            )
            _ocr_log(
                "ocr_attempt_success",
                op="image_to_data",
                lang=lang,
                elapsed_s=f"{time.time() - started:.2f}",
                words=len(result.get("text", [])),
                note="fallback_without_timeout_kw",
            )
            return result
        except RuntimeError as e:
            _ocr_log(
                "ocr_attempt_error",
                op="image_to_data",
                lang=lang,
                elapsed_s=f"{time.time() - started:.2f}",
                error_type=type(e).__name__,
                message=str(e),
                note="fallback_without_timeout_kw",
            )
            return {"text": [], "left": [], "top": [], "width": [], "height": []}

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
    
    # Wenn die Erkennung zu unsicher ist, zuerst schmal halten (schneller als 4 Sprachen)
    if languages[detected_lang] < 3:
        return PRIMARY_LANGS
    
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
                # Reduziere DPI für schnellere Verarbeitung (200 statt 300)
                images = pdf2image.convert_from_path(
                    original_pdf_path,
                    dpi=200,
                    fmt='jpeg',
                    thread_count=2
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
                    print(f"Extrahiere Positionsdaten für Seite {i+1}...")
                    import time
                    start_time = time.time()

                    lang_pos = detect_language_from_text(page_text)
                    ocr_small = _prepare_image_for_ocr(image)
                    sx_ocr = image.size[0] / float(ocr_small.size[0])
                    sy_ocr = image.size[1] / float(ocr_small.size[1])

                    print(f"Starte OCR für Seite {i+1} (Positionsdaten, lang={lang_pos})...")
                    ocr_data = _image_to_data(ocr_small, lang=lang_pos)
                    print(f"OCR für Seite {i+1} abgeschlossen in {time.time() - start_time:.2f}s")

                    image_width, image_height = image.size
                    scale_x = A4[0] / image_width
                    scale_y = A4[1] / image_height

                    print(f"Bild: {image_width}x{image_height}, PDF: {A4[0]}x{A4[1]}, Scale: {scale_x:.3f}x{scale_y:.3f}")

                    c.setFillColorRGB(0, 0, 0, 0)
                    c.setStrokeColorRGB(0, 0, 0, 0)

                    n_boxes = len(ocr_data['text'])
                    words_added = 0

                    for j in range(n_boxes):
                        text = ocr_data['text'][j].strip()
                        if text:
                            x = ocr_data['left'][j] * sx_ocr
                            y = ocr_data['top'][j] * sy_ocr
                            w = ocr_data['width'][j] * sx_ocr
                            h = ocr_data['height'][j] * sy_ocr

                            pdf_x = x * scale_x
                            pdf_y = A4[1] - (y * scale_y) - (h * scale_y)
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
        started_total = time.time()
        
        # Bild aus Stream öffnen
        image = Image.open(image_stream)
        print(f"Bild geladen: {image.size[0]}x{image.size[1]} Pixel")
        _ocr_log("page_ocr_input", width=image.size[0], height=image.size[1], has_initial_text=1 if bool(initial_text) else 0)
        ocr_image = _prepare_image_for_ocr(image)
        if ocr_image.size != image.size:
            print(f"OCR mit reduzierter Auflösung: {ocr_image.size[0]}x{ocr_image.size[1]} Pixel (max {OCR_MAX_DIMENSION})")
            _ocr_log("page_ocr_resized", width=ocr_image.size[0], height=ocr_image.size[1], max_dim=OCR_MAX_DIMENSION)
        
        # Wenn bereits Text vorhanden ist, verwende ihn für Spracherkennung
        if initial_text:
            detected_lang = detect_language_from_text(initial_text)
            print(f"Sprache erkannt: {detected_lang}")
        else:
            detected_lang = PRIMARY_LANGS
            print(f"Erster OCR-Lauf (schnell): {detected_lang}")
        
        print(f"Führe OCR durch mit Sprachen: {detected_lang}")
        text = _image_to_string(ocr_image, lang=detected_lang)
        print(f"OCR-Ergebnis: {len(text)} Zeichen")
        
        # Bei wenig Treffer: erst alternativer Segmentierungsmodus statt sofort 4 Sprachen
        if not text.strip() or len(text.strip()) < 10:
            print("Wenig Text, versuche PSM 6 (einheitlicher Textblock)...")
            text = _image_to_string(ocr_image, lang=PRIMARY_LANGS, config="--oem 1 --psm 6")
            print(f"OCR PSM 6: {len(text)} Zeichen")

        # Erst danach erweiterte Sprachen (deutlich langsamer)
        if (not text.strip() or len(text.strip()) < 10) and detected_lang != EXTENDED_LANGS:
            print("Wenig Text gefunden, versuche erweiterte Sprachen...")
            text = _image_to_string(ocr_image, lang=EXTENDED_LANGS)
            print(f"OCR mit erweiterten Sprachen: {len(text)} Zeichen")
        
        result = text.strip() if text.strip() else None
        if result:
            print(f"OCR erfolgreich: {len(result)} Zeichen extrahiert")
            _ocr_log("page_ocr_result", status="success", chars=len(result), elapsed_s=f"{time.time() - started_total:.2f}")
        else:
            print("OCR: Kein Text gefunden")
            _ocr_log("page_ocr_result", status="empty", chars=0, elapsed_s=f"{time.time() - started_total:.2f}")
        
        return result
        
    except Exception as e:
        print(f"Fehler beim Verarbeiten des Bildes: {e}")
        _ocr_log("page_ocr_result", status="exception", error_type=type(e).__name__, message=str(e))
        import traceback
        traceback.print_exc()
        return None

def extract_text_from_pdf(file_stream, original_filename="document.pdf"):
    """Extrahiert Text aus einer PDF und liefert immer PDF-Bytes für n8n (application/pdf)."""
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
        
        # PDF mit bereits vorhandenem Text: Original-Bytes zurückgeben (kein JSON-Fallback)
        if text.strip():
            print(f"Direkte PDF-Extraktion erfolgreich: {len(text)} Zeichen")
            file_stream.seek(0)
            pdf_bytes = file_stream.read()
            file_name = suggest_filename(text.strip(), original_filename)
            return OcrResult(text=text.strip(), pdf_bytes=pdf_bytes, file_name=file_name)
        
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
            images = convert_from_path(temp_file_path, dpi=150)  # Schneller, für OCR meist ausreichend
            print(f"PDF zu {len(images)} Bildern konvertiert")
            
            # OCR auf jedes Bild anwenden und Text pro Seite sammeln
            ocr_texts = []  # Liste für Text pro Seite
            ocr_text_combined = ""  # Kombinierter Text für Rückgabe
            
            for i, image in enumerate(images):
                print(f"Verarbeite Bild {i+1}/{len(images)}...")
                _ocr_log("pdf_page_start", page=i + 1, total_pages=len(images), width=image.size[0], height=image.size[1])
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
                    _ocr_log("pdf_page_result", page=i + 1, status="success", chars=len(page_text.strip()))
                else:
                    ocr_texts.append("")
                    print(f"Seite {i+1}: Kein Text durch OCR gefunden")
                    _ocr_log("pdf_page_result", page=i + 1, status="empty", chars=0)
            
            combined_text = ocr_text_combined.strip()
            file_name = suggest_filename(combined_text, original_filename)

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
                    with open(output_pdf_path, 'rb') as f:
                        pdf_data = f.read()
                    
                    if os.path.exists(output_pdf_path):
                        os.unlink(output_pdf_path)
                    
                    return OcrResult(
                        text=combined_text or "Kein Text gefunden.",
                        pdf_bytes=pdf_data,
                        file_name=file_name,
                    )
            
            # Fallback: Original-PDF zurückgeben, damit n8n weiterhin application/pdf erhält
            print("OCR-PDF konnte nicht erzeugt werden – gebe Original-PDF zurück")
            with open(temp_file_path, 'rb') as f:
                original_pdf = f.read()
            return OcrResult(
                text=combined_text or "Kein Text gefunden.",
                pdf_bytes=original_pdf,
                file_name=file_name,
            )
            
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
    """Verarbeitet Bild/PDF und liefert OcrResult (PDF-Bytes + fileName für n8n)."""
    print(f"Verarbeite Datei: {filename}")
    
    # Dateierweiterung ermitteln
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    print(f"Dateierweiterung erkannt: {file_extension}")
    
    if file_extension == 'pdf':
        print("Verarbeite als PDF...")
        result = extract_text_from_pdf(file_stream, original_filename=filename)
        if result is None:
            return OcrResult(
                text="Kein Text gefunden.",
                file_name=suggest_filename("", filename),
            )
        return result

    if file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']:
        print("Verarbeite als Bild...")
        text = extract_text_from_image(file_stream)
        resolved = text.strip() if text and text.strip() else "Kein Text gefunden."
        print(f"Text erfolgreich extrahiert: {len(resolved)} Zeichen")
        return OcrResult(
            text=resolved,
            file_name=suggest_filename(resolved if resolved != "Kein Text gefunden." else "", filename),
        )

    error_msg = (
        "Unterstütztes Dateiformat nicht erkannt. "
        "Unterstützte Formate: PDF, PNG, JPG, JPEG, GIF, BMP, TIFF"
    )
    print(error_msg)
    return OcrResult(text=error_msg, file_name=suggest_filename("", filename or "document.pdf"))