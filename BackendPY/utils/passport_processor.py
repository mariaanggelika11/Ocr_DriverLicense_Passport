import cv2, re, datetime
import pytesseract
import numpy as np

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

def clean_passport_number(txt):
    txt = re.sub(r"[^A-Z0-9]", "", txt.upper())
    txt = txt.replace("O", "0")
    return txt

def clean_date(txt):
    txt = txt.strip()
    # format dd/mm/yyyy atau dd-mm-yyyy
    match = re.search(r"(\d{2})\D(\d{2})\D(\d{4})", txt)
    if match:
        d, m, y = match.groups()
        return f"{d}/{m}/{y}"
    # format dd MON yyyy
    match = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})", txt)
    if match:
        d, mon, y = match.groups()
        try:
            date_obj = datetime.datetime.strptime(f"{d} {mon} {y}", "%d %b %Y")
            return date_obj.strftime("%d/%m/%Y")
        except:
            try:
                date_obj = datetime.datetime.strptime(f"{d} {mon} {y}", "%d %B %Y")
                return date_obj.strftime("%d/%m/%Y")
            except:
                pass
    return ""

def clean_gender(txt):
    txt = txt.strip().upper()
    if txt.startswith("F"): return "Female"
    if txt.startswith("M"): return "Male"
    return txt

# -----------------------
# Fallback DOB & Gender
# -----------------------
def fallback_extract_dob_gender(full_text_lines):
    dob = ""
    gender = ""
    # cari DOB
    for line in full_text_lines:
        candidate = clean_date(line)
        if re.match(r"\d{2}/\d{2}/\d{4}", candidate):
            dob = candidate
            break
    # cari Gender
    for i, line in enumerate(full_text_lines):
        l = line.lower().replace(":", "")
        if "sex" in l or "gender" in l:
            parts = line.strip().split()
            if len(parts) > 1:
                gender = clean_gender(parts[-1])
                break
            elif i+1 < len(full_text_lines):
                gender = clean_gender(full_text_lines[i+1].strip())
                break
    return dob, gender

# -----------------------
# Main Processing
# -----------------------
def process_passport(image_rgb, model, reader, conf=0.35, iou=0.45, allow_tesseract_fallback=True):
    """
    Input:
      - image_rgb: numpy array RGB
      - model: YOLO model for passport (loaded)
      - reader: easyocr.Reader instance
    Returns: dict (parsed fields), annotated_rgb (numpy)
    """
    annotated = image_rgb.copy()
    results = model.predict(source=image_rgb, conf=conf, iou=iou, verbose=False)
    boxes = results[0].boxes
    names = model.names

    # hanya ambil field tertentu
    fields_map = {
        "Authority": "authority",
        "Date of Birth": "dateOfBirth",
        "Gender": "gender",
        "Given Names": "givenNames",
        "Nationality": "nationality",
        "Passport No-": "passportNumber",
        "Place of birth": "placeOfBirth",
        "Surname": "surname"
    }
    data_out = {v: "" for v in fields_map.values()}

    for box in boxes:
        try:
            cls_id = int(box.cls.item())
            cls_name = names.get(cls_id, str(cls_id))
        except Exception:
            continue
        if cls_name not in fields_map:
            continue
        if cls_name == "Date of Birth":
            continue  # DOB ambil dari fallback

        coords = box.xyxy.cpu().numpy().reshape(-1).astype(int)
        x1, y1, x2, y2 = coords
        crop = image_rgb[y1:y2, x1:x2]
        txt = read_text(crop, reader, allow_tesseract_fallback=allow_tesseract_fallback)
        txt = re.sub(r"[^A-Za-z0-9\s/<>-]", "", txt)

        # cleaning khusus
        if cls_name == "Passport No-":
            txt = clean_passport_number(txt)
        elif cls_name == "Gender":
            txt = clean_gender(txt)

        key = fields_map[cls_name]
        if not data_out[key] or len(txt) > len(data_out[key]):
            data_out[key] = txt

        # gambar bbox
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            annotated, cls_name, (x1, max(15, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
        )

    # Full OCR fallback untuk DOB dan Gender
    try:
        full_text = reader.readtext(image_rgb, detail=0, paragraph=False)
    except Exception:
        full_text = []
    dob_ocr, gender_fallback = fallback_extract_dob_gender(full_text)
    if dob_ocr:
        data_out["dateOfBirth"] = dob_ocr
    if not data_out.get("gender") and gender_fallback:
        data_out["gender"] = gender_fallback

    return data_out
