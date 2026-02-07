# utils/validation.py
import re

def clean_date(txt):
    m = re.search(r"(\d{2})\D(\d{2})\D(\d{4})", txt)
    return f"{m[1]}/{m[2]}/{m[3]}" if m else ""

def clean_sex(txt):
    txt = txt.upper()
    if "F" in txt: return "FEMALE"
    if "M" in txt: return "MALE"
    return ""

def clean_license(txt):
    return re.sub(r"[^A-Z0-9-]", "", txt.upper())

def validate(data):
    errors = []
    if not data.get("name"): errors.append("NAME")
    if not data.get("licenseNumber"): errors.append("LICENSE")
    if not data.get("dateOfBirth"): errors.append("DOB")
    return errors
