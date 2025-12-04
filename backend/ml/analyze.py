# ml/analyze.py
from fastapi import UploadFile, File
from ml.scanner import scan_food
from main import std_resp   # or wherever you placed std_resp


async def analyze(file: UploadFile = File(...)):
    contents = await file.read()
    result = scan_food(contents)
    return std_resp(result)
