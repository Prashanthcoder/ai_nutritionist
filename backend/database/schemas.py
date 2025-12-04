from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from uuid import UUID


class FoodOut(BaseModel):
    id: UUID
    name: str
    calories: float
    protein: float
    carbs: float
    fats: float
    barcode: Optional[str] = None
    image_url: Optional[str] = None


class MealLogIn(BaseModel):
    user_id: str
    food_id: UUID
    weight: float = Field(gt=0)


class MealLogOut(BaseModel):
    success: bool
    meal_id: UUID
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fats: float


class SavedMealIn(BaseModel):
    user_id: str
    meal_name: str
    foods: List[MealLogIn]


class SavedMealOut(BaseModel):
    id: UUID
    meal_name: str
    foods: List[FoodOut]


class ProgressPoint(BaseModel):
    date: str
    calories: float


class WSMessage(BaseModel):
    event: str
    payload: dict
