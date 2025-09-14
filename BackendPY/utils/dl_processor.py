import cv2
import re
import difflib
import numpy as np
import pytesseract

# -----------------------
# StateName Normalization
# -----------------------
VALID_STATES = [
    "Virginia", "Maryland", "California", "New York", "Texas", "Florida",
    "Pennsylvania", "Illinois", "Ohio", "Georgia", "North Carolina",
    "Michigan", "New Jersey", "Washington", "Oregon", "Nevada",
    "Colorado", "Arizona", "Massachusetts", "Arkansas", "Indiana",
    "West Virginia"   # ditambahkan ke daftar valid
]

STATE_FIXES = {
    "Virqinia": "Virginia",
    "Virqina": "Virginia",
    "Virgnia": "Virginia",
    "Virgina": "Virginia",
    "Viginia": "Virginia",
    "Marvland": "Maryland",
    "Mavland": "Maryland",
    "Califomia": "California",
    "gARKANSAS": "Arkansas",
}

def normalize_state_name(text: str) -> str:
    if not text:
        return text
    if text in STATE_FIXES:
        return STATE_FIXES[text]
    match = difflib.get_close_matches(text, VALID_STATES, n=1, cutoff=0.75)
    if match:
        return match[0]
    return text

# -----------------------
# Address Cleaner
# -----------------------
def clean_address(txt: str) -> str:
    if not txt:
        return ""

    txt = re.sub(
        r'\b(Address|Addr|Auuress|Addres|Adrs|Adress|Adaress|Adarss)\b',
        '',
        txt,
        flags=re.IGNORECASE
    )

    words = txt.split()
    cleaned_words = []
    for w in words:
        match = difflib.get_close_matches(w, ["Address"], n=1, cutoff=0.75)
        if match:
            continue
        cleaned_words.append(w)

    txt = " ".join(cleaned_words)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt

def is_valid_us_address(txt: str) -> bool:
    if not txt:
        return False
    if re.match(r'^\d{1,6}\s+[A-Za-z]', txt):
        return True
    if re.match(r'^(P\.?O\.?|PO)\s+Box\s+\d+', txt, re.IGNORECASE):
        return True
    if re.match(r'^(RR|Rural Route)', txt, re.IGNORECASE):
        return True
    return False

def extract_zip_code(txt: str) -> str:
    match = re.search(r'\b\d{5}(?:-\d{4})?\b', txt)
    return match.group(0) if match else ""

# -----------------------
# Helper functions
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
        cfg = '--oem 1 --psm 7'
        txt = pytesseract.image_to_string(img_crop, config=cfg)
        return txt.strip()
    return ""

def clean_date(txt):
    match = re.search(r'(\d{2})\D(\d{2})\D(\d{4})', txt)
    if match:
        d, m, y = match.groups()
        return f"{d}/{m}/{y}"
    return ""

def clean_sex(txt):
    txt = txt.strip().upper()
    if txt.startswith("F"): return "Female"
    if txt.startswith("M"): return "Male"
    return ""

def clean_license_number(txt):
    txt = re.sub(r'[^A-Z0-9-]', '', txt.upper())
    txt = txt.replace("O", "0")
    return txt

# -----------------------
# Fallback DOB & SEX
# -----------------------
def fallback_extract_dob_sex(full_text_lines):
    dob = ""
    sex = ""
    for line in full_text_lines:
        candidate = clean_date(line)
        if re.match(r'\d{2}/\d{2}/\d{4}', candidate):
            dob = candidate
            break
    for i, line in enumerate(full_text_lines):
        l = line.lower().replace(":", "")
        if "sex" in l or "gender" in l:
            parts = line.strip().split()
            if len(parts) > 1:
                sex = clean_sex(parts[-1])
                break
            elif i+1 < len(full_text_lines):
                sex = clean_sex(full_text_lines[i+1].strip())
                break
    return dob, sex

def extract_license_number(full_text_lines):
    joined = " ".join(full_text_lines).upper()
    norm = joined.replace("O", "0").replace("Q", "0")
    match_md = re.search(r'\bS-\d{3}-\d{3}-\d{3}-\d{3}\b', norm)
    if match_md:
        return match_md.group(0)
    match_va = re.search(r'\b[A-Z]{1,2}\d{6,}\b', norm)
    if match_va:
        return match_va.group(0)
    return ""

# -----------------------
# Main Processor
# -----------------------
def process_driving_license(image_rgb, model, reader,
                            conf=0.35, iou=0.45,
                            allow_tesseract_fallback=True, debug=True):
    annotated = image_rgb.copy()
    results = model.predict(source=image_rgb, conf=conf, iou=iou, verbose=False)
    boxes = results[0].boxes
    names = model.names

    fields = ["StateName", "address", "dateOfBirth", "firstName",
              "lastName", "licenseNumber", "sex", "zipCode"]
    data_out = {f: "" for f in fields}
    candidates = {f: [] for f in fields}
    name_candidates = []
    address_candidates = []

    if debug:
        print("========== DEBUG START ==========")
        print(f"Total detected boxes: {len(boxes)}")

    # --- 1) Extract field candidates ---
    for idx, box in enumerate(boxes):
        try:
            cls_id = int(box.cls.item())
            cls_name = names.get(cls_id, str(cls_id))
        except Exception:
            continue

        coords = box.xyxy.cpu().numpy().reshape(-1).astype(int)
        x1, y1, x2, y2 = coords
        pad = 6
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(image_rgb.shape[1], x2 + pad), min(image_rgb.shape[0], y2 + pad)
        crop = image_rgb[y1:y2, x1:x2]

        txt_raw = read_text(crop, reader, allow_tesseract_fallback=allow_tesseract_fallback)
        txt_clean = re.sub(r'[^A-Za-z0-9\s/<>-]', '', txt_raw)

        if cls_name == "sex":
            txt_clean = clean_sex(txt_clean)
        elif cls_name == "licenseNumber":
            txt_clean = clean_license_number(txt_clean)
        elif cls_name == "address":
            txt_clean = clean_address(txt_clean)

        candidate = {
            "txt": txt_clean.strip(),
            "coords": coords,
            "y_center": (y1 + y2) / 2,
            "idx": idx,
            "cls": cls_name
        }
        candidates.setdefault(cls_name, []).append(candidate)

        if cls_name == "address":
            address_candidates.append(candidate)

        if cls_name in ("firstName", "lastName"):
            name_candidates.append(candidate)

        if cls_name not in ("firstName", "lastName", "address"):
            if not data_out.get(cls_name) or len(txt_clean) > len(data_out[cls_name]):
                data_out[cls_name] = txt_clean.strip()

        if debug:
            print(f"[BOX {idx}] Field: {cls_name}, Text: {txt_clean.strip()}")

    # --- 2) Address resolution ---
    if address_candidates:
        valid_addrs = [a["txt"] for a in address_candidates if is_valid_us_address(a["txt"])]
        if valid_addrs:
            data_out["address"] = max(valid_addrs, key=len)
        else:
            data_out["address"] = max([a["txt"] for a in address_candidates], key=len)
        zip_code = extract_zip_code(data_out["address"])
        if zip_code:
            data_out["zipCode"] = zip_code

    # --- 3) Full image OCR for fallback DOB/sex/licenseNumber ---
    try:
        full_text = reader.readtext(image_rgb, detail=0, paragraph=False)
    except Exception:
        full_text = []

    # khusus West Virginia -> jangan override DOB
    if data_out.get("StateName", "").strip().upper() == "WEST VIRGINIA":
        if debug:
            print(">> State = West Virginia, DOB hanya dari box, skip fallback OCR DOB")
    else:
        dob_ocr, sex_fallback = fallback_extract_dob_sex(full_text)
        if dob_ocr:
            data_out["dateOfBirth"] = dob_ocr
        if not data_out.get("sex") and sex_fallback:
            data_out["sex"] = sex_fallback

    license_fb = extract_license_number(full_text)
    if license_fb:
        data_out["licenseNumber"] = license_fb

    # --- 4) Name resolution ---
    if name_candidates:
        valid = [c for c in name_candidates if c["txt"]]
        fn, ln = "", ""
        for c in valid:
            if c["cls"] == "firstName" and not fn:
                fn = c["txt"]
            elif c["cls"] == "lastName" and not ln:
                ln = c["txt"]

        if (not fn or not ln) and len(valid) >= 2:
            valid_sorted = sorted(valid, key=lambda x: x["y_center"])
            if not ln:
                ln = valid_sorted[0]["txt"]
            if not fn:
                fn = valid_sorted[-1]["txt"]

        if not ln and fn and " " in fn:
            parts = fn.split()
            fn, ln = parts[0], " ".join(parts[1:])
        if not fn and ln and " " in ln:
            parts = ln.split()
            ln, fn = parts[-1], " ".join(parts[:-1])

        data_out["firstName"] = fn.strip()
        data_out["lastName"] = ln.strip()

    # --- 5) Normalize StateName ---
    if data_out.get("StateName"):
        data_out["StateName"] = normalize_state_name(data_out["StateName"])

    if debug:
        print("\n[Final extracted fields]")
        for k, v in data_out.items():
            print(f"  {k}: {v}")
        print("========== DEBUG END ==========")

    return data_out
