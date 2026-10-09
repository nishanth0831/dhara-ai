import io
import os
import re
import shutil
from typing import Dict, Set

import pytesseract
from PIL import Image

# On Windows, try common install path if tesseract is not in PATH
if os.name == "nt":
    if not shutil.which("tesseract"):
        _tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in _tesseract_paths:
            if os.path.isfile(p):
                pytesseract.pytesseract.tesseract_cmd = p
                break


def extract_text_from_image_bytes(data: bytes) -> str:
    """Perform OCR on raw image bytes and return extracted text.
    Uses PSM 6 (block of text) for better accuracy on soil cards.
    """
    img = Image.open(io.BytesIO(data))
    try:
        text = pytesseract.image_to_string(img, config="--psm 6")
    except Exception:
        text = pytesseract.image_to_string(img)
    return text or ""


def extract_text_from_file_bytes(data: bytes, filename: str) -> str:
    """Handle images and PDFs. For PDFs convert each page to an image.

    Requires `pdf2image` if the input is PDF; the caller must have it installed
    (see requirements.txt).
    """
    if filename.lower().endswith(".pdf"):
        try:
            from pdf2image import convert_from_bytes
        except ImportError as e:
            raise RuntimeError(
                "pdf2image is required for PDF OCR; install pdf2image"
            ) from e
        pages = convert_from_bytes(data, dpi=200)
        text = ""
        for page in pages:
            try:
                text += pytesseract.image_to_string(page, config="--psm 6")
            except Exception:
                text += pytesseract.image_to_string(page)
        return text or ""
    else:
        return extract_text_from_image_bytes(data)


def parse_soil_card_text(text: str) -> Dict[str, any]:
    """Extract known fields from the raw OCR text.

    Supports multiple formats: N/P/K with : or =, NPK as 120-80-60,
    Nitrogen/Phosphorus/Potassium, organisation/org/lab names, ISAAMW card IDs.
    """
    result: Dict[str, any] = {"organization": None, "card_id": None, "npk": {}}
    if not text or not isinstance(text, str):
        return result

    t = text.strip()

    # Card ID: ISAAMW + 4+ digits (allow optional spaces/hyphens)
    m = re.search(r"(ISAAMW\s*\-?\s*[0-9]{4,})", t, re.IGNORECASE)
    if m:
        result["card_id"] = re.sub(r"[\s\-]", "", m.group(1)).upper()

    # N, P, K - multiple patterns
    npk: Dict[str, float] = {}
    patterns = [
        (r"N\s*[:=\-]\s*([0-9]+(?:\.[0-9]+)?)", "N"),
        (r"P\s*[:=\-]\s*([0-9]+(?:\.[0-9]+)?)", "P"),
        (r"K\s*[:=\-]\s*([0-9]+(?:\.[0-9]+)?)", "K"),
        (r"Nitrogen\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)", "N"),
        (r"Phosphorus?\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)", "P"),
        (r"Potassium\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)", "K"),
    ]
    for pat, key in patterns:
        m2 = re.search(pat, t, re.IGNORECASE)
        if m2 and key not in npk:
            try:
                npk[key] = float(m2.group(1))
            except ValueError:
                pass

    # NPK as "120-80-60" or "120:80:60" or "120 80 60"
    npk_triple = re.search(r"([0-9]+)\s*[\-\:]\s*([0-9]+)\s*[\-\:]\s*([0-9]+)", t)
    if npk_triple and len(npk) < 3:
        try:
            vals = [float(npk_triple.group(1)), float(npk_triple.group(2)), float(npk_triple.group(3))]
            if "N" not in npk:
                npk["N"] = vals[0]
            if "P" not in npk:
                npk["P"] = vals[1]
            if "K" not in npk:
                npk["K"] = vals[2]
        except (ValueError, IndexError):
            pass

    # Standalone N P K numbers (e.g. "N 120 P 80 K 60" without separator)
    for nutrient, key in [("N", "N"), ("P", "P"), ("K", "K")]:
        if key not in npk:
            m3 = re.search(rf"{nutrient}\s+([0-9]+(?:\.[0-9]+)?)", t, re.IGNORECASE)
            if m3:
                try:
                    npk[key] = float(m3.group(1))
                except ValueError:
                    pass

    result["npk"] = npk

    # Organisation name - multiple patterns
    org_patterns = [
        r"Organization\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Org(?:anisation)?\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Laboratory\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Lab\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Name\s*[:\-]\s*(.+?)(?:\n|$)",
    ]
    for pat in org_patterns:
        m4 = re.search(pat, t, re.IGNORECASE | re.DOTALL)
        if m4:
            org = m4.group(1).strip()
            if org and len(org) > 2 and not org.isdigit():
                result["organization"] = org[:80]
                break

    return result


def validate_card_id(card_id: str | None, existing_last4: Set[str]) -> bool:
    """Simple validation rule for a soil card identifier.

    - Must start with ISAAMW (case insensitive)
    - Last four characters must be digits
    - The last four digits must not already be in `existing_last4`
    """
    if not card_id:
        return False
    cid = card_id.upper()
    if not cid.startswith("ISAAMW"):
        return False
    last4 = cid[-4:]
    if not last4.isdigit():
        return False
    if last4 in existing_last4:
        return False
    return True
