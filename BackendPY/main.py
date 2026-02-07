# main.py
from fastapi import FastAPI, UploadFile, File
import cv2
import numpy as np
import easyocr
from utils.dl_processor import process_driving_license

app = FastAPI()
reader = easyocr.Reader(['en'])

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    img_bytes = await file.read()
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

    if img is None:
        return {"success": False, "error": "INVALID_IMAGE"}

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    parsed = process_driving_license(img, reader)

    return parsed
