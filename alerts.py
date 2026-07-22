from datetime import date

from models import db, Alert, Subscriber
from utils import classify_aqi, health_advisory


def check_and_log_alerts(city: str, forecast: list, default_threshold: int):
    """Compares each forecast day against subscriber thresholds (falling back to the
    global default) and logs + emails an alert the first time a day crosses it."""
    triggered = []
    subscribers = Subscriber.query.filter_by(city=city).all()
    thresholds = {s.threshold for s in subscribers} or {default_threshold}

    for day in forecast:
        predicted = day["predicted_aqi"]
        category, _ = classify_aqi(predicted)
        for threshold in thresholds:
            if predicted < threshold:
                continue
            forecast_date = date.fromisoformat(day["date"])
            exists = Alert.query.filter_by(city=city, forecast_date=forecast_date).first()
            if exists:
                continue
            alert = Alert(
                city=city,
                forecast_date=forecast_date,
                predicted_aqi=predicted,
                category=category,
                message=health_advisory(category),
            )
            db.session.add(alert)
            triggered.append(alert)

    if triggered:
        db.session.commit()
        _notify_subscribers(city, triggered, subscribers)
    return triggered


def _notify_subscribers(city, triggered_alerts, subscribers):
    """Sends email via Flask-Mail if configured; otherwise logs to console.
    Kept best-effort so a missing SMTP config never breaks the ingestion job."""
    from flask import current_app
    from flask_mail import Message

    if not subscribers:
        return
    try:
        mail = current_app.extensions.get("mail")
        if mail is None or not current_app.config.get("MAIL_USERNAME"):
            for a in triggered_alerts:
                print(f"[ALERT] {city} {a.forecast_date}: {a.category} (AQI {a.predicted_aqi})")
            return
        for sub in subscribers:
            relevant = [a for a in triggered_alerts if a.predicted_aqi >= sub.threshold]
            if not relevant:
                continue
            body_lines = [f"{a.forecast_date}: {a.category} (AQI {a.predicted_aqi}) — {a.message}" for a in relevant]
            msg = Message(
                subject=f"Air quality alert for {city}",
                recipients=[sub.email],
                body="\n".join(body_lines),
            )
            mail.send(msg)
    except Exception as e:  # pragma: no cover - best-effort notification path
        print(f"Alert notification failed: {e}")
