import cv2
import re
import numpy as np
import pytesseract
import easyocr

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

ALLOW_TESSERACT_FALLBACK = True

VALID_STATES = {
    "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut",
    "Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa",
    "Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan",
    "Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada",
    "New Hampshire","New Jersey","New Mexico","New York","North Carolina",
    "North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island",
    "South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont",
    "Virginia","Washington","West Virginia","Wisconsin","Wyoming"
}

NAME_BLACKLIST = {
    "DL","LICENSE","DRIVER","DRIVERS","NAME",
    "SEX","HEIGHT","WEIGHT","EYES","HAIR",
    "ORGAN","DONOR","ENDORSEMENT","ENDORSEMENTS"
}

# ------------------------------------------------
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
    txt = re.sub(r"[^A-Z0-9]", "", txt.upper()).replace("O", "0")
    m = re.match(r"^([A-Z])(\d{12})$", txt)
    if m:
        p, d = m.groups()
        parts = [d[i:i+3] for i in range(0, len(d), 3)]
        return p + "-" + "-".join(parts)
    return txt

def clean_date(txt):
    m = re.search(r"(\d{2})\D(\d{2})\D(\d{4})", txt)
    if m:
        d, m_, y = m.groups()
        return f"{d}/{m_}/{y}"
    return ""

def clean_sex(txt):
    t = txt.strip().upper()
    if t == "M":
        return "MALE"
    if t == "F":
        return "FEMALE"
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

# ------------------------------------------------
def process_driving_license(image_rgb, model, reader, conf=0.35, iou=0.45):

    results = model.predict(image_rgb, conf=conf, iou=iou, verbose=False)
    boxes = results[0].boxes
    names = model.names

    data_out = {
        "StateName": "",
        "address": "",
        "dateOfBirth": "",
        "firstName": "",
        "lastName": "",
        "licenseNumber": "",
        "sex": ""
    }

    print("\n========== DEBUG START ==========")
    print("YOLO PHASE")
    print("Total YOLO boxes:", len(boxes))

    # ---------------- YOLO ----------------
    for i, box in enumerate(boxes):
        cls = names[int(box.cls.item())]
        if cls not in data_out:
            continue

        x1, y1, x2, y2 = box.xyxy.cpu().numpy().reshape(-1).astype(int)
        crop = image_rgb[y1:y2, x1:x2]

        raw = read_text(crop, reader)
        txt = re.sub(r"[^A-Za-z0-9\s/]", "", raw).strip()

        print("YOLO BOX", i)
        print(" field :", cls)
        print(" raw   :", raw)
        print(" clean :", txt)

        if cls == "licenseNumber":
            txt = clean_license_number(txt)

        elif cls == "sex":
            txt = clean_sex(txt)

        elif cls == "dateOfBirth":
            d = clean_date(txt)
            if d:
                data_out["dateOfBirth"] = d
                print(" saved dateOfBirth from YOLO")
            continue

        if txt and not data_out[cls]:
            data_out[cls] = txt
            print(" saved", cls, "from YOLO")

    # ---------------- OCR ----------------
    print("\nOCR FALLBACK PHASE")
    full_text = reader.readtext(image_rgb, detail=0, paragraph=False)

    print("Full OCR lines")
    for l in full_text:
        print(" ", l)

    # ---- State fallback
    if not data_out["StateName"]:
        for l in full_text:
            for vs in VALID_STATES:
                if re.search(rf"\b{vs}\b", l, re.I):
                    data_out["StateName"] = vs.upper()
                    print(" state recovered from OCR:", vs)
                    break

    # ---- DOB & SEX fallback
    for l in full_text:
        if not data_out["dateOfBirth"]:
            d = clean_date(l)
            if d:
                data_out["dateOfBirth"] = d
                print(" dateOfBirth recovered from OCR")

        if not data_out["sex"]:
            if re.fullmatch(r"\bM\b", l.strip()):
                data_out["sex"] = "MALE"
            elif re.fullmatch(r"\bF\b", l.strip()):
                data_out["sex"] = "FEMALE"

    if data_out["address"]:
        data_out["address"] = fix_address_with_zip(data_out["address"], full_text)

    # ---------------- NAME FALLBACK (FIXED) ----------------
    if not data_out["lastName"] or not data_out["firstName"]:
        print("Resolving name from OCR (STRICT + FILTERED)")

        caps = []

        for l in full_text:
            token = l.strip().upper()

            if not token:
                continue
            if not token.isalpha():
                continue
            if len(token) <= 2:
                continue
            if token in NAME_BLACKLIST:
                continue
            if token in VALID_STATES:
                continue
            if token == data_out["StateName"]:
                continue

            caps.append(token)

        print(" filtered name candidates:", caps)

        if not data_out["lastName"] and len(caps) >= 1:
            data_out["lastName"] = caps[0]
            print(" lastName from OCR:", caps[0])

        if not data_out["firstName"] and len(caps) >= 2:
            data_out["firstName"] = caps[1]
            print(" firstName from OCR:", caps[1])

    # ---------------- FINAL ----------------
    for k in data_out:
        if isinstance(data_out[k], str):
            data_out[k] = data_out[k].upper().strip()

    print("\nFINAL RESULT")
    for k, v in data_out.items():
        print(" ", k, ":", v)

    print("========== DEBUG END ==========\n")
    return data_out
