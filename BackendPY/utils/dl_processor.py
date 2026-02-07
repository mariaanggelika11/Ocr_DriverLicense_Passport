import cv2
import re
import datetime
import numpy as np
import pytesseract
import easyocr

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

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
# ZONE FALLBACK (RELATIVE)
# dipakai HANYA jika YOLO box gagal
# -----------------------
ZONE_FALLBACK = {
    "Maryland": {
        "name": (0.30, 0.40, 0.65, 0.60),
        "dateOfBirth": (0.30, 0.65, 0.55, 0.80),
        "sex": (0.48, 0.65, 0.60, 0.80),
    },
    "Virginia": {
        "name": (0.25, 0.38, 0.65, 0.58),
        "dateOfBirth": (0.25, 0.62, 0.55, 0.78),
        "sex": (0.50, 0.62, 0.60, 0.78),
    }
}

# -----------------------
# Helpers
# -----------------------
def crop_rel(img, box):
    h, w, _ = img.shape
    x1 = max(0, int(box[0] * w))
    y1 = max(0, int(box[1] * h))
    x2 = min(w, int(box[2] * w))
    y2 = min(h, int(box[3] * h))
    return img[y1:y2, x1:x2]


def enhance_for_ocr(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(2.0, (8, 8))
    enhanced = clahe.apply(gray)
    return cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )


def read_text(img, reader):
    try:
        res = reader.readtext(img, detail=0, paragraph=False)
        if res:
            return " ".join(res).strip()
    except Exception:
        pass

    if ALLOW_TESSERACT_FALLBACK:
        return pytesseract.image_to_string(img, config="--oem 1 --psm 7").strip()

    return ""


def clean_license_number(txt):
    txt = re.sub(r"[^A-Z0-9-]", "", txt.upper()).replace("O", "0")
    m = re.match(r"^([A-Z])(\d{12})$", txt)
    if m:
        p, d = m.groups()
        parts = [d[i:i+3] for i in range(0, len(d), 3)]
        txt = p + "-" + "-".join(parts)
        print(f"[DEBUG] Reformatted licenseNumber -> {txt}")
    return txt


def clean_date(txt):
    m = re.search(r"(\d{2})\D(\d{2})\D(\d{4})", txt)
    if m:
        d, m_, y = m.groups()
        return f"{d}/{m_}/{y}"
    return ""


def clean_sex(txt):
    t = txt.strip().upper()
    if t.startswith("F"):
        return "Female"
    if t.startswith("M"):
        return "Male"
    return ""


def fix_address_with_zip(address, lines):
    m = re.search(r"\b(\d{9})\b", address)
    if m:
        raw = m.group(1)
        fixed = raw[:5] + "-" + raw[5:]
        for l in lines:
            z = re.search(r"\b\d{5}-\d{4}\b", l)
            if z:
                return address.replace(raw, z.group(0))
        return address.replace(raw, fixed)
    return address


# -----------------------
# Main Processing
# -----------------------
def process_driving_license(image_rgb, model, reader, conf=0.35, iou=0.45):
    results = model.predict(source=image_rgb, conf=conf, iou=iou, verbose=False)
    boxes = results[0].boxes
    names = model.names

    fields = ["StateName", "address", "dateOfBirth", "firstName",
              "lastName", "licenseNumber", "sex"]

    data_out = {f: "" for f in fields}
    dob_from_box = ""

    print("\n========== DEBUG START ==========")
    print(f"Total detected boxes: {len(boxes)}")

    for i, box in enumerate(boxes):
        try:
            cls_name = names[int(box.cls.item())]
        except Exception:
            continue

        if cls_name not in fields:
            continue

        x1, y1, x2, y2 = box.xyxy.cpu().numpy().reshape(-1).astype(int)
        crop = image_rgb[y1:y2, x1:x2]

        txt = read_text(crop, reader)
        txt = re.sub(r"[^A-Za-z0-9\s/]", "", txt)

        if cls_name == "licenseNumber":
            txt = clean_license_number(txt)
        elif cls_name == "sex":
            txt = clean_sex(txt)
        elif cls_name == "dateOfBirth":
            dob_from_box = clean_date(txt)
            continue

        if not data_out[cls_name] or len(txt) > len(data_out[cls_name]):
            data_out[cls_name] = txt

        print(f"[BOX {i}] Field: {cls_name}, Text: {txt}")

    print("========== DEBUG END ==========\n")

    # ---------- OCR FULL ----------
    try:
        full_text = reader.readtext(image_rgb, detail=0, paragraph=False)
    except Exception:
        full_text = []

    # ---------- STATE ----------
    st = data_out["StateName"].title()
    if st not in VALID_STATES:
        for l in full_text:
            for vs in VALID_STATES:
                if re.search(rf"\b{vs}\b", l, re.I):
                    st = vs
                    break
    data_out["StateName"] = st if st in VALID_STATES else ""

    # ---------- DOB / SEX ----------
    if st == "West Virginia" and dob_from_box:
        data_out["dateOfBirth"] = dob_from_box
    else:
        for l in full_text:
            if not data_out["dateOfBirth"]:
                d = clean_date(l)
                if d:
                    data_out["dateOfBirth"] = d
            if not data_out["sex"]:
                if re.search(r"\bM\b", l): data_out["sex"] = "Male"
                if re.search(r"\bF\b", l): data_out["sex"] = "Female"

    # ---------- ADDRESS ZIP FIX ----------
    if data_out["address"]:
        data_out["address"] = fix_address_with_zip(data_out["address"], full_text)

    # ===============================
    # ZONE FALLBACK (HANYA JIKA GAGAL)
    # ===============================
    zones = ZONE_FALLBACK.get(st, {})


    # 2. Jika masih kosong → BARU pakai zone heuristic
    if not data_out["firstName"] or not data_out["lastName"]:
        z = ZONE_FALLBACK.get(st, {}).get("name")
        if z:
            crop = crop_rel(image_rgb, z)
            lines = reader.readtext(crop, detail=0)

            clean = []
            for l in lines:
                l = l.upper().strip()
                if l.isalpha() and len(l) >= 3:
                    if not re.search(r"(LICENSE|IDENTIFIER|FDIC|ADDRESS|DATE|SEX|DL)", l):
                        clean.append(l)

            # Maryland biasanya: LAST dulu, lalu FIRST
            if len(clean) == 1 and not data_out["lastName"]:
                data_out["lastName"] = clean[0]
            elif len(clean) >= 2:
                if not data_out["lastName"]:
                    data_out["lastName"] = clean[0]
                if not data_out["firstName"]:
                    data_out["firstName"] = clean[1]

    # DOB
    if not data_out["dateOfBirth"]:
        z = zones.get("dateOfBirth")
        if z:
            crop = crop_rel(image_rgb, z)
            lines = reader.readtext(crop, detail=0)
            for l in lines:
                d = clean_date(l)
                if d:
                    data_out["dateOfBirth"] = d
                    break

    # SEX
    if not data_out["sex"]:
        z = zones.get("sex")
        if z:
            crop = crop_rel(image_rgb, z)
            lines = reader.readtext(crop, detail=0)
            for l in lines:
                if re.search(r"\bM\b", l): data_out["sex"] = "Male"
                if re.search(r"\bF\b", l): data_out["sex"] = "Female"

    # ---------- NORMALIZE ----------
    for k in data_out:
        if isinstance(data_out[k], str):
            data_out[k] = data_out[k].upper()

    return data_out
