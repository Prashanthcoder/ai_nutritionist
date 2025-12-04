# ml/scanner.py
from ultralytics import YOLO
from PIL import Image
import io

model = YOLO("yolov8x.pt")          # or yolov8n.pt for speed
FOOD_CLASS_IDS = [46, 47, 48, 49, 50, 51, 52, 53,
                  54, 55, 56, 57, 58, 59, 60]  # COCO food classes

MACRO_MAP = {
    "apple":     {"protein": 0.3, "carbs": 14, "fats": 0.2},
    "banana":    {"protein": 1.1, "carbs": 23, "fats": 0.3},
    "pizza":     {"protein": 12,  "carbs": 34, "fats": 10},
    "sandwich":  {"protein": 15,  "carbs": 30, "fats": 8},
    "carrot":    {"protein": 0.9, "carbs": 10, "fats": 0.2},
    # default fallback
    "default":   {"protein": 5,   "carbs": 20, "fats": 5}
}


def scan_food(image_bytes: bytes) -> dict:
    img = Image.open(io.BytesIO(image_bytes))
    results = model(img, verbose=False)
    boxes = results[0].boxes
    food_boxes = [b for b in boxes if int(b.cls) in FOOD_CLASS_IDS]

    if not food_boxes:
        return {"food": "unknown", "calories": 0, "macros": MACRO_MAP["default"], "tips": "No food detected – try another angle."}

    largest = max(food_boxes, key=lambda b: b.conf)
    label = results[0].names[int(largest.cls)]
    conf = float(largest.conf)
    calories = {"apple": 52, "banana": 89, "pizza": 285,
                "sandwich": 250, "carrot": 41}.get(label, 120)
    macros = MACRO_MAP.get(label, MACRO_MAP["default"])

    return {
        "food": label,
        "calories": calories,
        "macros": macros,
        "confidence": round(conf, 2),
        "tips": f"Detected {label} – log it!"
    }
