import os

from flask import Flask, jsonify, render_template, request
from flask_mail import Mail

from config import Config
from models import db, AQIReading, Alert, Subscriber
from utils import classify_aqi, health_advisory


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config_obj = config_class  # plain attribute access, used by fetcher/scheduler

    os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)
    db.init_app(app)
    Mail(app)

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def register_routes(app):

    @app.route("/")
    def dashboard():
        return render_template("dashboard.html", default_city=app.config["DEFAULT_CITY"])

    @app.route("/api/current")
    def api_current():
        city = request.args.get("city", app.config["DEFAULT_CITY"])
        latest = (
            AQIReading.query.filter_by(city=city)
            .order_by(AQIReading.timestamp.desc())
            .first()
        )
        if not latest:
            return jsonify({"error": f"No data for '{city}' yet."}), 404
        category, color = classify_aqi(latest.aqi)
        data = latest.to_dict()
        data.update({
            "category": category,
            "color": color,
            "advisory": health_advisory(category),
        })
        return jsonify(data)

    @app.route("/api/history")
    def api_history():
        city = request.args.get("city", app.config["DEFAULT_CITY"])
        days = int(request.args.get("days", 30))
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = (
            AQIReading.query.filter(AQIReading.city == city, AQIReading.timestamp >= cutoff)
            .order_by(AQIReading.timestamp)
            .all()
        )
        return jsonify([r.to_dict() for r in rows])

    @app.route("/api/forecast")
    def api_forecast():
        from ml.features import readings_to_frame
        from ml.predict import forecast, ModelNotTrainedError
        from alerts import check_and_log_alerts

        city = request.args.get("city", app.config["DEFAULT_CITY"])
        horizon = min(int(request.args.get("days", 7)), 14)

        readings = AQIReading.query.filter_by(city=city).order_by(AQIReading.timestamp).all()
        if not readings:
            return jsonify({"error": f"No historical data for '{city}'. Run the seeder first."}), 404

        daily = readings_to_frame(readings)
        try:
            preds = forecast(city, daily, horizon=horizon)
        except ModelNotTrainedError as e:
            return jsonify({"error": str(e)}), 400

        for p in preds:
            category, color = classify_aqi(p["predicted_aqi"])
            p["category"] = category
            p["color"] = color

        triggered = check_and_log_alerts(city, preds, app.config["ALERT_THRESHOLD_AQI"])
        return jsonify({
            "city": city,
            "horizon_days": horizon,
            "forecast": preds,
            "new_alerts": [a.to_dict() for a in triggered],
        })

    @app.route("/api/alerts")
    def api_alerts():
        city = request.args.get("city", app.config["DEFAULT_CITY"])
        rows = Alert.query.filter_by(city=city).order_by(Alert.triggered_at.desc()).limit(20).all()
        return jsonify([a.to_dict() for a in rows])

    @app.route("/api/subscribe", methods=["POST"])
    def api_subscribe():
        payload = request.get_json(force=True)
        email = payload.get("email")
        city = payload.get("city", app.config["DEFAULT_CITY"])
        threshold = int(payload.get("threshold", app.config["ALERT_THRESHOLD_AQI"]))
        if not email:
            return jsonify({"error": "email is required"}), 400

        existing = Subscriber.query.filter_by(email=email, city=city).first()
        if existing:
            existing.threshold = threshold
        else:
            db.session.add(Subscriber(email=email, city=city, threshold=threshold))
        db.session.commit()
        return jsonify({"status": "subscribed", "city": city, "threshold": threshold})


if __name__ == "__main__":
    application = create_app()
    from scheduler import init_scheduler
    init_scheduler(application)
    application.run(debug=False, host="0.0.0.0", port=5000)
