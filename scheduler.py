from apscheduler.schedulers.background import BackgroundScheduler

from models import db, AQIReading
from data.fetcher import fetch_current, FetchError


def ingest_once(app):
    """Fetches one fresh reading for the app's default city and stores it.
    In a multi-city deployment, loop over a list of (city, lat, lon) tuples here."""
    with app.app_context():
        cfg = app.config
        try:
            reading = fetch_current(cfg["DEFAULT_CITY"], cfg["DEFAULT_LAT"], cfg["DEFAULT_LON"], app.config_obj)
            db.session.add(AQIReading(**reading))
            db.session.commit()
        except FetchError as e:
            print(f"[scheduler] fetch failed: {e}")


def init_scheduler(app):
    scheduler = BackgroundScheduler(daemon=True)
    interval = app.config.get("FETCH_INTERVAL_MINUTES", 60)
    scheduler.add_job(lambda: ingest_once(app), "interval", minutes=interval, id="aqi_ingest")
    scheduler.start()
    return scheduler
