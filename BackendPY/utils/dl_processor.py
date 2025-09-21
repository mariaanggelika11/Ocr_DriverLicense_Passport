import cv2
import re
import datetime
import numpy as np
import pytesseract
import easyocr

# -----------------------
# CONFIG
# -----------------------
ALLOW_TESSERACT_FALLBACK = True

# -----------------------
# US VALID STATES
# -----------------------
VALID_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
}

# -----------------------
# Helpers
# -----------------------
def enhance_for_ocr(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    th = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return th

def read_text(img_crop, reader, allow_tesseract_fallback=True):
    try:
        result = reader.readtext(img_crop, detail=0, paragraph=False)
        if result:
            return " ".join(result).strip()
    except Exception:
        pass
    if allow_tesseract_fallback:
        cfg = "--oem 1 --psm 7"
        txt = pytesseract.image_to_string(img_crop, config=cfg)
        return txt.strip()
    return ""

def clean_license_number(txt):
    txt = re.sub(r"[^A-Z0-9-]", "", txt.upper())
    txt = txt.replace("O", "0")

    # Jika formatnya 1 huruf + 12 digit angka
    m = re.match(r"^([A-Z])(\d{12})$", txt)
    if m:
        prefix, digits = m.groups()
        # Format: S-000-000-000-000 (huruf depan + 4 blok 3 digit)
        parts = [digits[i:i+3] for i in range(0, len(digits), 3)]
        txt = prefix + "-" + "-".join(parts)
        print(f"[DEBUG] Reformatted licenseNumber -> {txt}")

    return txt


def clean_date(txt):
    match = re.search(r"(\d{2})\D(\d{2})\D(\d{4})", txt)
    if match:
        d, m, y = match.groups()
        return f"{d}/{m}/{y}"
    return ""

def clean_sex(txt):
    txt = txt.strip().upper()
    if txt.startswith("F"): return "Female"
    if txt.startswith("M"): return "Male"
    return txt

# -----------------------
# Fix ZIP in Address
# -----------------------
def fix_address_with_zip(address_text, ocr_lines):
    """
    Perbaiki ZIP code di address jika formatnya salah (misal 253171234 -> 25317-1234).
    """
    m = re.search(r"\b(\d{9})\b", address_text)
    if m:
        raw_zip = m.group(1)
        fixed_zip = raw_zip[:5] + "-" + raw_zip[5:]

        # Cari baris OCR full text yang punya ZIP format benar
        for line in ocr_lines:
            if re.search(r"\b\d{5}-\d{4}\b", line):
                better_zip = re.search(r"\b\d{5}-\d{4}\b", line).group(0)
                address_text = address_text.replace(raw_zip, better_zip)
                print(f"[DEBUG] Fixed ZIP from {raw_zip} -> {better_zip}")
                break
        else:
            address_text = address_text.replace(raw_zip, fixed_zip)
            print(f"[DEBUG] Fixed ZIP from {raw_zip} -> {fixed_zip}")
    return address_text

# -----------------------
# Fallback DOB & Sex
# -----------------------
def fallback_extract_dob_sex(full_text_lines):
    dob = ""
    sex = ""

    print("\n[DEBUG] OCR full image lines:")
    for i, line in enumerate(full_text_lines):
        print(f"{i}: {line}")

    for line in full_text_lines:
        candidate = clean_date(line)
        if re.match(r"\d{2}/\d{2}/\d{4}", candidate):
            dob = candidate
            break

    for i, line in enumerate(full_text_lines):
        l = line.lower().replace(":", "")
        if "sex" in l:
            parts = line.strip().split()
            if len(parts) > 1:
                sex = clean_sex(parts[-1])
                break
            elif i+1 < len(full_text_lines):
                sex = clean_sex(full_text_lines[i+1].strip())
                break
    return dob, sex
# -----------------------
# Main Processing
# -----------------------
def process_driving_license(image_rgb, model, reader, conf=0.35, iou=0.45, allow_tesseract_fallback=True):
    """
    Input:
      - image_rgb: numpy array RGB
      - model: YOLO model for Driving License (sudah di-load di main.py)
      - reader: easyocr.Reader instance
    Returns:
      dict hasil parsing
    """
    results = model.predict(source=image_rgb, conf=conf, iou=iou, verbose=False)
    boxes = results[0].boxes
    names = model.names

    fields = ["StateName", "address", "dateOfBirth", "firstName",
              "lastName", "licenseNumber", "sex"]

    data_out = {f: "" for f in fields}
    dob_from_box = ""  # khusus DOB hasil box, untuk kasus West Virginia

    print("\n========== DEBUG START ==========")
    print(f"Total detected boxes: {len(boxes)}")

    for i, box in enumerate(boxes):
        try:
            cls_id = int(box.cls.item())
            cls_name = names.get(cls_id, str(cls_id))
        except Exception:
            continue
        if cls_name not in fields:
            continue

        coords = box.xyxy.cpu().numpy().reshape(-1).astype(int)
        x1, y1, x2, y2 = coords
        crop = image_rgb[y1:y2, x1:x2]

        txt = read_text(crop, reader, allow_tesseract_fallback=allow_tesseract_fallback)
        txt = re.sub(r"[^A-Za-z0-9\s/]", "", txt)

        if cls_name == "licenseNumber":
            txt = clean_license_number(txt)
        elif cls_name == "sex":
            txt = clean_sex(txt)
        elif cls_name == "dateOfBirth":
            # simpan DOB dari box, jangan langsung masukkan
            dob_from_box = clean_date(txt)
            continue

        if not data_out[cls_name] or len(txt) > len(data_out[cls_name]):
            data_out[cls_name] = txt

        # Debug print hasil OCR box
        print(f"[BOX {i}] Field: {cls_name}, Text: {txt}")

    print("========== DEBUG END ==========\n")

    # OCR full text untuk fallback
    try:
        full_text = reader.readtext(image_rgb, detail=0, paragraph=False)
    except Exception:
        full_text = []

    # --- Validasi StateName ---
    state_name_raw = data_out.get("StateName", "").strip()
    state_name_norm = state_name_raw.title()  # normalisasi huruf besar/kecil

    if state_name_norm in VALID_STATES:
        # Kalau dari box sudah valid → langsung pakai
        data_out["StateName"] = state_name_norm
    else:
        # Kalau tidak valid → fallback cari dari OCR full text
        found_state = ""
        for line in full_text:
            for vs in VALID_STATES:
                if re.search(rf"\b{re.escape(vs)}\b", line, re.IGNORECASE):
                    found_state = vs
                    break
            if found_state:
                break
        data_out["StateName"] = found_state if found_state in VALID_STATES else ""


    # --- DOB & Sex ---
    if data_out["StateName"] == "West Virginia":
        # Khusus West Virginia → ambil DOB dari box
        data_out["dateOfBirth"] = dob_from_box
    else:
        # Normal fallback DOB & sex
        dob_ocr, sex_fallback = fallback_extract_dob_sex(full_text)
        if dob_ocr:
            data_out["dateOfBirth"] = dob_ocr
        if not data_out.get("sex") and sex_fallback:
            data_out["sex"] = sex_fallback

    # Fix address ZIP kalau ada masalah
    if data_out.get("address"):
        data_out["address"] = fix_address_with_zip(data_out["address"], full_text)

    return data_out
