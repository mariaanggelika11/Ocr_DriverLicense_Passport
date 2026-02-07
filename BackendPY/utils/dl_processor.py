# utils/dl_processor.py
import re
import cv2

from utils.state_templates import STATE_TEMPLATES
from utils.ocr_utils import enhance_for_ocr, read_text
from utils.validation import clean_date, clean_sex, clean_license, validate

VALID_STATES = {"Maryland", "Virginia"}


# -----------------------
# Utils
# -----------------------
def crop_rel(img, box):
    h, w, _ = img.shape
    x1 = max(0, int(box[0] * w))
    y1 = max(0, int(box[1] * h))
    x2 = min(w, int(box[2] * w))
    y2 = min(h, int(box[3] * h))
    return img[y1:y2, x1:x2]


def detect_state(full_text):
    for line in full_text:
        for s in VALID_STATES:
            if re.search(rf"\b{s}\b", line, re.I):
                return s
    return ""


def draw_debug_overlay(image, template, state):
    """
    Simpan image dengan bounding box template
    untuk debugging koordinat
    """
    debug = image.copy()
    h, w, _ = image.shape

    for field, box in template.items():
        x1 = int(box[0] * w)
        y1 = int(box[1] * h)
        x2 = int(box[2] * w)
        y2 = int(box[3] * h)

        cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            debug,
            field,
            (x1, max(15, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    cv2.imwrite(
        f"debug_{state}.jpg",
        cv2.cvtColor(debug, cv2.COLOR_RGB2BGR)
    )


# -----------------------
# Main Processor
# -----------------------
def process_driving_license(image_rgb, reader):
    # --- OCR full image (hanya untuk detect state) ---
    full_text = reader.readtext(image_rgb, detail=0)
    state = detect_state(full_text)

    if state not in STATE_TEMPLATES:
        return {
            "success": False,
            "error": "STATE_NOT_SUPPORTED"
        }

    template = STATE_TEMPLATES[state]

    # DEBUG: simpan overlay bounding box
    draw_debug_overlay(image_rgb, template, state)

    result = {
        "StateName": state,
        "licenseNumber": "",
        "name": "",
        "dateOfBirth": "",
        "sex": "",
        "address": ""
    }

    # --- OCR per field (template-based) ---
    for field, box in template.items():
        crop = crop_rel(image_rgb, box)

        # Safety check
        if crop.size == 0:
            continue

        crop = enhance_for_ocr(crop)
        txt = read_text(crop, reader)
        txt = txt.strip()

        # -----------------
        # Cleaning & Guard
        # -----------------
        if field == "licenseNumber":
            txt = clean_license(txt)
            # guard: license terlalu pendek = noise
            if len(txt) < 8:
                txt = ""

        elif field == "dateOfBirth":
            txt = clean_date(txt)

        elif field == "sex":
            txt = clean_sex(txt)

        elif field == "name":
            txt = txt.upper()
            # buang noise umum
            if any(k in txt for k in ["ISSUED", "LICENSE", "DRIVER", "IDENTIFICATION"]):
                txt = ""

        elif field == "address":
            txt = txt.upper()
            if len(txt) < 10:
                txt = ""

        result[field] = txt.upper()

    # -----------------------
    # Validation & Confidence
    # -----------------------
    errors = validate(result)

    if len(errors) == 0:
        confidence = "HIGH"
    elif len(errors) == 1:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    result["confidence"] = confidence
    result["errors"] = errors
    result["success"] = True

    return result
