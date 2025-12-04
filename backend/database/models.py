import uuid
import datetime as dt
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .config import Base


class FoodItem(Base):
    __tablename__ = "food_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    calories = Column(Float)
    protein = Column(Float)
    carbs = Column(Float)
    fats = Column(Float)
    barcode = Column(String, unique=True, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class UserMeal(Base):
    __tablename__ = "user_meals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # use telegram-id / email
    user_id = Column(String, index=True)
    food_id = Column(UUID(as_uuid=True), ForeignKey("food_items.id"))
    weight_in_grams = Column(Float)
    total_calories = Column(Float)
    total_protein = Column(Float)
    total_carbs = Column(Float)
    total_fats = Column(Float)
    time_of_meal = Column(DateTime, default=dt.datetime.utcnow)
    food = relationship("FoodItem")


class SavedMeal(Base):
    __tablename__ = "saved_meals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, index=True)
    meal_name = Column(String)
    # [ {"food_id": "...", "grams": 100}, ... ]
    list_of_food_ids = Column(JSON)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class WeeklyAnalytics(Base):
    __tablename__ = "weekly_analytics"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, index=True)
    date = Column(DateTime, index=True)   # midnight UTC
    total_calories = Column(Float)
    total_protein = Column(Float)
    total_carbs = Column(Float)
    total_fats = Column(Float)
