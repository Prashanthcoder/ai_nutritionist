from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from .models import FoodItem, UserMeal, SavedMeal, WeeklyAnalytics
from .schemas import MealLogIn, SavedMealIn
import datetime as dt


async def get_foods_by_query(db: AsyncSession, q: str, limit: int = 10):
    stmt = select(FoodItem).where(FoodItem.name.ilike(f"%{q}%")).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


async def get_food_by_id(db: AsyncSession, food_id):
    return await db.get(FoodItem, food_id)

# AFTER (fixed)


async def log_meal(db: AsyncSession, payload: MealLogIn) -> UserMeal:
    food = await get_food_by_id(db, payload.food_id)
    if not food:
        raise ValueError("Food not found")
    scale = payload.weight / 100
    meal = UserMeal(
        user_id=payload.user_id,
        food_id=payload.food_id,
        weight_in_grams=payload.weight,
        total_calories=food.calories * scale,
        total_protein=food.protein * scale,
        total_carbs=food.carbs * scale,
        total_fats=food.fats * scale
    )
    db.add(meal)
    await db.commit()
    await db.refresh(meal)
    return meal


async def get_today_meals(db: AsyncSession, user_id: str):
    today = dt.date.today()
    stmt = select(UserMeal).where(
        and_(UserMeal.user_id == user_id, func.date(
            UserMeal.time_of_meal) == today)
    ).order_by(UserMeal.time_of_meal.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


async def save_meal(db: AsyncSession, user_id: str, name: str, foods: list):
    sm = SavedMeal(user_id=user_id, meal_name=name,
                   list_of_food_ids=[f.dict() for f in foods])
    db.add(sm)
    await db.commit()
    await db.refresh(sm)
    return sm


async def get_saved_meals(db: AsyncSession, user_id: str):
    stmt = select(SavedMeal).where(SavedMeal.user_id ==
                                   user_id).order_by(SavedMeal.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


async def get_progress(db: AsyncSession, user_id: str, days: int = 30):
    stmt = (
        select(func.date(UserMeal.time_of_meal),
               func.sum(UserMeal.total_calories))
        .where(UserMeal.user_id == user_id)
        .group_by(func.date(UserMeal.time_of_meal))
        .order_by(func.date(UserMeal.time_of_meal).desc())
        .limit(days)
    )
    res = await db.execute(stmt)
    return [{"date": str(r[0]), "calories": r[1]} for r in res.all()]


async def get_weekly_analytics(db: AsyncSession, user_id: str):
    stmt = select(WeeklyAnalytics).where(WeeklyAnalytics.user_id ==
                                         user_id).order_by(WeeklyAnalytics.date.desc()).limit(4)
    res = await db.execute(stmt)
    return res.scalars().all()
