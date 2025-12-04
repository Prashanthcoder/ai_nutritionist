from fastapi import WebSocket
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import random
from typing import List
from uuid import UUID
import datetime as dt
from sqlalchemy.ext.asyncio import AsyncSession
from database.config import async_session, Base, engine
from database.models import FoodItem, UserMeal, SavedMeal, WeeklyAnalytics
from database.schemas import *
from database.crud import *
from database.websocket import manager
from ml.weight import predict_weight
from ml.classify import classify_food
from workers.analytics import build_weekly_analytics
from PIL import Image
import io
import redis
import json

app = FastAPI()

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"]
)

# -------------------------
# USER MODEL
# -------------------------


class UserProfile(BaseModel):
    age: int
    height: float
    weight: float
    gender: str
    activity: str
    goal: str


# -------------------------
# NUTRITION API
# -------------------------
@app.post("/nutrition")
def nutrition(user: UserProfile):

    h = user.height / 100
    bmi = round(user.weight / (h**2), 2)

    if user.gender == "male":
        bmr = 10*user.weight + 6.25*user.height - 5*user.age + 5
    else:
        bmr = 10*user.weight + 6.25*user.height - 5*user.age - 161

    multiplier = {"low": 1.2, "medium": 1.55, "high": 1.9}
    calories = round(bmr * multiplier.get(user.activity, 1.2))

    if user.goal == "weight_loss":
        calories -= 400
    elif user.goal == "muscle_gain":
        calories += 400

    if user.goal == "weight_loss":
        diet = "High protein, salads, fruits, avoid sugar & fried foods."
    elif user.goal == "muscle_gain":
        diet = "Protein heavy: Eggs, chicken, paneer, rice, nuts."
    else:
        diet = "Balanced diet with vegetables, carbs and protein."

    return {
        "bmi": bmi,
        "bmr": round(bmr),
        "daily_calories": calories,
        "diet_plan": diet
    }


# -------------------------
# FOOD SCANNER FAKE AI
# -------------------------
foods = [
    ("Idli", 280, "Good carbs, low fat."),
    ("Dosa", 350, "Moderate calories, avoid excess chutney."),
    ("Rice & Dal", 420, "Good protein but control rice."),
    ("Chapati + Sabzi", 360, "Balanced meal."),
    ("Fried Snack", 500, "Reduce junk food intake."),
    ("Chicken Curry", 480, "High protein, good for muscle gain."),
    ("Paneer Dish", 450, "Vegetarian protein source."),
]


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):

    food = random.choice(foods)

    return {
        "food": food[0],
        "calories": food[1],
        "tips": food[2]
    }


@app.get("/foods")
def foods(query: str = Query(...)):
    # dummy list
    return [{"name": q, "calories": 120, "protein": 10, "carbs": 15, "fats": 4} for q in [query, query+" 2"]]


@app.post("/meal/log")
def meal_log(data: dict):
    # store in DB here
    return {"ok": True}


@app.get("/meal/today")
def meal_today():
    # return logged meals
    return {"meals": []}


@app.get("/ai/suggest")
def ai_suggest():
    return {"suggestion": "Add a protein source to hit your goal!"}


async def get_db():
    async with async_session() as session:
        yield session

# ---------- UTIL ----------


def std_resp(data, status: str = "success"):
    return {"status": status, "data": data, "server_time": dt.datetime.utcnow().isoformat()}

# ---------- LIFECYCLE ----------


@app.on_event("startup")
async def on_start():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ---------- 1. FOOD SEARCH ----------


@app.get("/foods", response_model=dict)
async def foods(query: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    items = await get_foods_by_query(db, query)
    return std_resp([FoodOut.from_orm(i).dict() for i in items])

# ---------- 2. LOG MEAL ----------


@app.post("/log-meal", response_model=dict)
async def log_meal_endpoint(payload: MealLogIn, db: AsyncSession = Depends(get_db)):
    meal = await log_meal(db, payload)   # CRUD function
    await manager.send_personal(
        json.dumps({"event": "meal_update", "payload": {
                   "meal_id": str(meal.id), "calories": meal.total_calories}}),
        payload.user_id
    )
    return std_resp(MealLogOut(
        success=True,
        meal_id=meal.id,
        total_calories=meal.total_calories,
        total_protein=meal.total_protein,
        total_carbs=meal.total_carbs,
        total_fats=meal.total_fats
    ).dict())
# ---------- 3. TODAY MEALS ----------


@app.get("/meal/today", response_model=dict)
async def meal_today(user_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    meals = await get_today_meals(db, user_id)
    return std_resp([{
        "id": str(m.id),
        "food": m.food.name,
        "grams": m.weight_in_grams,
        "calories": m.total_calories,
        "macros": {"protein": m.total_protein, "carbs": m.total_carbs, "fats": m.total_fats},
        "time": m.time_of_meal.isoformat()
    } for m in meals])

# ---------- 4. SAVED MEALS ----------


@app.post("/saved-meals", response_model=dict)
async def create_saved(data: SavedMealIn, db: AsyncSession = Depends(get_db)):
    sm = await save_meal(db, data.user_id, data.meal_name, data.foods)
    return std_resp({"id": str(sm.id), "meal_name": sm.meal_name})


@app.get("/saved-meals", response_model=dict)
async def list_saved(user_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    meals = await get_saved_meals(db, user_id)
    return std_resp([{"id": str(m.id), "meal_name": m.meal_name, "foods": m.list_of_food_ids} for m in meals])


@app.delete("/saved-meals/{meal_id}", response_model=dict)
async def delete_saved(meal_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = await db.get(SavedMeal, meal_id)
    if not stmt:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(stmt)
    await db.commit()
    return std_resp({"deleted": str(meal_id)})

# ---------- 5. PROGRESS GRAPH ----------


@app.get("/progress", response_model=dict)
async def progress(user_id: str = Query(...), days: int = Query(30, ge=1), db: AsyncSession = Depends(get_db)):
    data = await get_progress(db, user_id, days)
    return std_resp(data)

# ---------- 6. WEEKLY ANALYTICS ----------


@app.get("/weekly-analytics", response_model=dict)
async def weekly(user_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    rows = await get_weekly_analytics(db, user_id)
    return std_resp([{
        "date": r.date.strftime("%Y-%m-%d"),
        "total_calories": r.total_calories,
        "total_protein": r.total_protein,
        "total_carbs": r.total_carbs,
        "total_fats": r.total_fats
    } for r in rows])

# ---------- 7. AI SUGGEST ----------


@app.get("/ai/suggest", response_model=dict)
async def suggest(user_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    # dummy logic
    meals = await get_today_meals(db, user_id)
    total_p = sum(m.total_protein for m in meals)
    if total_p < 50:
        return std_resp({"suggestion": "Add a protein source (eggs, peanut-butter) to hit your goal!"})
    return std_resp({"suggestion": "Great macro balance today!"})

# ---------- 8. ML WEIGHT ----------


@app.post("/predict-weight", response_model=dict)
async def predict_weight(file: UploadFile = File(...)):
    image = Image.open(io.BytesIO(await file.read()))
    weight = predict_weight(image)
    return std_resp({"weight": weight})

# ---------- 9. ML CLASSIFY ----------


@app.post("/classify-food", response_model=dict)
async def classify_food(file: UploadFile = File(...)):
    image = Image.open(io.BytesIO(await file.read()))
    name, conf = classify_food(image)
    return std_resp({"food_name": name, "confidence": conf})

# ---------- 10. BARCODE ----------


@app.get("/barcode/{code}", response_model=dict)
async def barcode(code: str, db: AsyncSession = Depends(get_db)):
    food = await db.scalar(select(FoodItem).where(FoodItem.barcode == code))
    if food:
        return std_resp({"food_name": food.name, "calories": food.calories,
                         "macros": {"protein": food.protein, "carbs": food.carbs, "fats": food.fats}})
    # fallback Nutritionix (needs API key) – dummy here
    return std_resp({"food_name": "Unknown", "calories": 0, "macros": {"protein": 0, "carbs": 0, "fats": 0}})

# ---------- 11. WEBSOCKET ----------


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        await manager.disconnect(user_id)


@app.post("/seed", response_model=dict)
async def seed(db: AsyncSession = Depends(get_db)):
    samples = [
        {"name": "rice", "calories": 130, "protein": 2.7, "carbs": 28, "fats": 0.3},
        {"name": "chicken breast", "calories": 165,
            "protein": 31, "carbs": 0, "fats": 3.6},
        {"name": "apple", "calories": 52, "protein": 0.3, "carbs": 14, "fats": 0.2},
        {"name": "egg", "calories": 155, "protein": 13, "carbs": 1.1, "fats": 11},
    ]
    for s in samples:
        db.add(FoodItem(**s))
    await db.commit()
    return {"status": "success", "data": "seeded"}
