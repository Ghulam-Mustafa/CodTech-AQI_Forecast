import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'aqi.db')}"
    )
    # print(os.environ.get("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- External data source ---
    # Set AQI_DATA_SOURCE to "waqi" or "openweather" to use a live API.
    # Defaults to "mock" so the app runs out of the box without any API key.
    AQI_DATA_SOURCE = os.environ.get("AQI_DATA_SOURCE", "mock")
    WAQI_API_TOKEN = os.environ.get("WAQI_API_TOKEN", "")
    OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

    DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Hyderabad")
    DEFAULT_LAT = float(os.environ.get("DEFAULT_LAT", "17.3850"))
    DEFAULT_LON = float(os.environ.get("DEFAULT_LON", "78.4867"))

    # Fetch cadence in minutes for the scheduled ingestion job
    FETCH_INTERVAL_MINUTES = int(os.environ.get("FETCH_INTERVAL_MINUTES", "60"))

    # Alerting
    ALERT_THRESHOLD_AQI = int(os.environ.get("ALERT_THRESHOLD_AQI", "150"))  # "Unhealthy" (US EPA scale)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")

    MODEL_DIR = os.path.join(BASE_DIR, "ml", "artifacts")
