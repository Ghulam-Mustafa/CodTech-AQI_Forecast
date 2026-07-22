"""
Populates the database with a season's worth of hourly synthetic history so the
ML model has something to train on immediately after setup. In production,
replace this with real ingested history accumulated by the scheduler, or bulk
import a CSV export from your AQI provider.

Run: python -m data.seed_data
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from models import db, AQIReading  # noqa: E402
from data.fetcher import _fetch_mock  # noqa: E402
from config import Config  # noqa: E402


def seed(days: int = 240, city: str = None):
    city = city or Config.DEFAULT_CITY
    app = create_app()
    with app.app_context():
        existing = AQIReading.query.filter_by(city=city).count()
        if existing > 0:
            print(f"{existing} readings already exist for {city}; skipping seed.")
            return

        start = datetime.utcnow() - timedelta(days=days)
        rows = []
        t = start
        while t <= datetime.utcnow():
            reading = _fetch_mock(city, Config.DEFAULT_LAT, Config.DEFAULT_LON, when=t)
            rows.append(AQIReading(**reading))
            t += timedelta(hours=3)  # 8 readings/day keeps seed fast, still plenty for daily models

        db.session.bulk_save_objects(rows)
        db.session.commit()
        print(f"Seeded {len(rows)} readings for {city} covering {days} days.")


if __name__ == "__main__":
    seed()
