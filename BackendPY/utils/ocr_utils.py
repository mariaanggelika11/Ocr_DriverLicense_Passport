# utils/ocr_utils.py
import cv2
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def enhance_for_ocr(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

def read_text(img, reader):
    try:
        res = reader.readtext(img, detail=0)
        if res:
            return " ".join(res)
    except:
        pass
    return pytesseract.image_to_string(img, config="--psm 7")
