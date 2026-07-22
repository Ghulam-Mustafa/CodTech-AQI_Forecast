from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AQIReading(db.Model):
    """A single historical or live AQI + environmental-factor observation."""

    __tablename__ = "aqi_readings"

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(120), index=True, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)

    aqi = db.Column(db.Float, nullable=False)
    pm25 = db.Column(db.Float)
    pm10 = db.Column(db.Float)
    no2 = db.Column(db.Float)
    o3 = db.Column(db.Float)
    co = db.Column(db.Float)
    so2 = db.Column(db.Float)

    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    wind_direction = db.Column(db.Float)
    pressure = db.Column(db.Float)

    dominant_pollutant = db.Column(db.String(20))

    def to_dict(self):
        return {
            "id": self.id,
            "city": self.city,
            "timestamp": self.timestamp.isoformat(),
            "aqi": self.aqi,
            "pm25": self.pm25,
            "pm10": self.pm10,
            "no2": self.no2,
            "o3": self.o3,
            "co": self.co,
            "so2": self.so2,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "pressure": self.pressure,
            "dominant_pollutant": self.dominant_pollutant,
        }


class Alert(db.Model):
    """Log of alerts triggered when forecasted AQI crosses the configured threshold."""

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(120), index=True, nullable=False)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    forecast_date = db.Column(db.Date, nullable=False)
    predicted_aqi = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(255))
    acknowledged = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "city": self.city,
            "triggered_at": self.triggered_at.isoformat(),
            "forecast_date": self.forecast_date.isoformat(),
            "predicted_aqi": self.predicted_aqi,
            "category": self.category,
            "message": self.message,
            "acknowledged": self.acknowledged,
        }


class Subscriber(db.Model):
    """A user who wants email alerts for a given city."""

    __tablename__ = "subscribers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    threshold = db.Column(db.Integer, default=150)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("email", "city", name="uq_subscriber_city"),)
