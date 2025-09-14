import io, base64, os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import numpy as np
import cv2
import pytesseract
from fastapi.middleware.cors import CORSMiddleware
import easyocr
from ultralytics import YOLO
import re

# import processor
from utils.passport_processor import process_passport
from utils.dl_processor import process_driving_license

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

passport_model = YOLO("models/passport_model.pt")
driving_model = YOLO("models/dl_model.pt")
reader = easyocr.Reader(['en'])

# ----------------------
# OCR helper
# ----------------------
def extract_text(img: np.ndarray) -> str:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return pytesseract.image_to_string(gray).lower()

# ----------------------
# Enhanced Deteksi tipe dokumen
# ----------------------
def detect_doc_type(img: np.ndarray, text: str):
    # 1) Hitung confidence dari kedua model
    passport_pred = passport_model.predict(source=img, conf=0.25, iou=0.35, verbose=False)
    passport_boxes = passport_pred[0].boxes if passport_pred[0].boxes is not None else []
    passport_conf = max([float(b.conf.item()) for b in passport_boxes], default=0.0)
    passport_count = len(passport_boxes)

    driving_pred = driving_model.predict(source=img, conf=0.25, iou=0.35, verbose=False)
    driving_boxes = driving_pred[0].boxes if driving_pred[0].boxes is not None else []
    driving_conf = max([float(b.conf.item()) for b in driving_boxes], default=0.0)
    driving_count = len(driving_boxes)

    # 2) Keyword analysis dengan scoring
    passport_keywords = {
        "passport": 3, "given names": 2, "surname": 2, "nationality": 2, 
        "authority": 2, "place of birth": 2, "date of birth": 1
    }
    
    driving_keywords = {
        "driver": 3, "driving": 3, "license": 3, "dl": 2, "dmv": 2, 
        "identification": 2, "state": 2, "endors": 1, "restrict": 1
    }

    passport_score = 0
    driving_score = 0
    
    for keyword, weight in passport_keywords.items():
        if keyword in text:
            passport_score += weight
    
    for keyword, weight in driving_keywords.items():
        if keyword in text:
            driving_score += weight

    # 3) Pattern matching untuk nomor dokumen
    passport_no_pattern = r'[A-Z]{1,2}[0-9]{6,8}'
    driving_no_pattern = r'[A-Z]{1,3}[0-9]{4,10}|[0-9]{7,12}'
    
    passport_no_match = len(re.findall(passport_no_pattern, text.upper()))
    driving_no_match = len(re.findall(driving_no_pattern, text.upper()))

    # 4) Decision logic dengan multiple factors
    factors = []
    
    # Factor 1: YOLO confidence
    if passport_conf > driving_conf + 0.1:
        factors.append(("yolo_confidence", "passport"))
    elif driving_conf > passport_conf + 0.1:
        factors.append(("yolo_confidence", "driving_license"))
    
    # Factor 2: Number of detected boxes
    if passport_count > driving_count + 2:
        factors.append(("box_count", "passport"))
    elif driving_count > passport_count + 2:
        factors.append(("box_count", "driving_license"))
    
    # Factor 3: Keyword scoring
    if passport_score > driving_score + 3:
        factors.append(("keywords", "passport"))
    elif driving_score > passport_score + 3:
        factors.append(("keywords", "driving_license"))
    
    # Factor 4: Document number pattern
    if passport_no_match > driving_no_match:
        factors.append(("doc_pattern", "passport"))
    elif driving_no_match > passport_no_match:
        factors.append(("doc_pattern", "driving_license"))

    # Count votes
    passport_votes = sum(1 for _, vote in factors if vote == "passport")
    driving_votes = sum(1 for _, vote in factors if vote == "driving_license")
    
    # 5) Make decision
    reason_parts = []
    if passport_votes > driving_votes:
        doc_type = "passport"
        reason_parts.append(f"Passport wins with {passport_votes} votes vs {driving_votes}")
    elif driving_votes > passport_votes:
        doc_type = "driving_license"
        reason_parts.append(f"Driving license wins with {driving_votes} votes vs {passport_votes}")
    else:
        # Tie breaker: use confidence
        if passport_conf > driving_conf:
            doc_type = "passport"
            reason_parts.append(f"Tie broken by confidence: passport {passport_conf:.2f} > driving {driving_conf:.2f}")
        else:
            doc_type = "driving_license"
            reason_parts.append(f"Tie broken by confidence: driving {driving_conf:.2f} > passport {passport_conf:.2f}")
    
    # Add details to reason
    reason_parts.append(f"Passport conf: {passport_conf:.2f}, boxes: {passport_count}")
    reason_parts.append(f"Driving conf: {driving_conf:.2f}, boxes: {driving_count}")
    reason_parts.append(f"Passport keywords: {passport_score}, Driving keywords: {driving_score}")
    
    reason = " | ".join(reason_parts)
    
    # Warning jika confidence rendah
    warning = None
    if max(passport_conf, driving_conf) < 0.3:
        warning = "Low detection confidence - results may be unreliable"
    
    return doc_type, reason, warning

# ----------------------
# API Endpoint
# ----------------------
@app.post("/detect")
async def detect_document(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        npimg = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # OCR text
        text = extract_text(img)

        # tentukan tipe dokumen
        doc_type, reason, warning = detect_doc_type(img_rgb, text)

        # panggil processor sesuai tipe
        if doc_type == "passport":
            parsed = process_passport(img_rgb, passport_model, reader)
        elif doc_type == "driving_license":
            parsed = process_driving_license(img_rgb, driving_model, reader)
        else:
            parsed = {}

        return JSONResponse({
            "success": True,
            "detected_type": doc_type,
            "decision_reason": reason,
            "warning": warning,
            "parsed": parsed
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)