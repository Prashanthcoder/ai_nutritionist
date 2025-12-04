from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from database.config import async_session, DATABASE_URL
from database.models import UserMeal, WeeklyAnalytics
from sqlalchemy import select, func, and_
import datetime as dt

celery = Celery("tasks", broker="redis://localhost:6379/0",
                backend="redis://localhost:6379/0")


@celery.task
def build_weekly_analytics():
    async def _run():
        async with async_session() as db:
            users = await db.execute(select(UserMeal.user_id).distinct())
            for (user_id,) in users:
                base = dt.date.today() - dt.timedelta(days=6)
                stmt = select(
                    func.date(UserMeal.time_of_meal),
                    func.sum(UserMeal.total_calories),
                    func.sum(UserMeal.total_protein),
                    func.sum(UserMeal.total_carbs),
                    func.sum(UserMeal.total_fats)
                ).where(
                    and_(UserMeal.user_id == user_id,
                         func.date(UserMeal.time_of_meal) >= base)
                ).group_by(func.date(UserMeal.time_of_meal))
                res = await db.execute(stmt)
                for row in res:
                    date, cal, p, c, f = row
                    wa = WeeklyAnalytics(
                        user_id=user_id,
                        date=dt.datetime.combine(date, dt.time.min),
                        total_calories=cal or 0,
                        total_protein=p or 0,
                        total_carbs=c or 0,
                        total_fats=f or 0
                    )
                    db.add(wa)
            await db.commit()
    asyncio.run(_run())


# celery beat schedule (run once at midnight)
celery.conf.beat_schedule = {
    "analytics-midnight": {
        "task": "workers.analytics.build_weekly_analytics",
        "schedule": 60 * 60 * 24,  # seconds
    }
}
