# AQI Forecast — Air Quality Index Forecasting Web App(Intern ID : CITS7455)

A Flask-based web application that displays current Air Quality Index (AQI) readings
and forecasts the next 5–7 days using a hybrid machine learning model (gradient-boosted
trees + SARIMA), with alerting and interactive visualizations.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Flask App (app.py)                    │
│  ┌───────────┐  ┌────────────────┐  ┌──────────────────┐    │
│  │ Dashboard │  │ REST API        │  │ Alerts engine     │    │
│  │ (Jinja2)  │  │ /api/current    │  │ (alerts.py)       │    │
│  │           │  │ /api/forecast   │  │                    │    │
│  │           │  │ /api/history    │  │                    │    │
│  └───────────┘  └────────────────┘  └──────────────────┘    │
└──────────────┬───────────────────────────────┬───────────────┘
               │                                │
       ┌───────▼────────┐              ┌────────▼─────────┐
       │  SQLAlchemy /    │              │  ML layer (ml/)   │
       │  SQLite/Postgres │              │  features, train,  │
       │  (models.py)     │              │  predict           │
       └───────▲────────┘              └────────▲─────────┘
               │                                │
       ┌───────┴────────────────────────────────┴─────────┐
       │   Scheduler (APScheduler, scheduler.py)            │
       │   → data/fetcher.py → WAQI / OpenWeatherMap / mock  │
       └──────────────────────────────────────────────────┘
```

- **Frontend**: server-rendered Jinja2 template + vanilla JS + Chart.js (no separate
  frontend build step required).
- **Backend**: Flask, single Python codebase — web routes, ML pipeline, scheduler, and
  alerting all live together, so there's no cross-service serialization to manage.
- **Database**: SQLite by default (`instance/aqi.db`); swap `DATABASE_URL` for Postgres
  in production.
- **ML pipeline**: `ml/features.py` builds lag/rolling/calendar features from daily-
  aggregated history; `ml/train.py` fits an XGBoost regressor (falls back to
  scikit-learn's GradientBoostingRegressor if XGBoost isn't installed) plus a SARIMA
  baseline; `ml/predict.py` recursively forecasts the next N days and blends both
  models' outputs with an uncertainty band.
- **Data ingestion**: `data/fetcher.py` supports three backends — WAQI, OpenWeatherMap,
  or a built-in synthetic "mock" generator (default) so the app runs immediately without
  any API key.
- **Alerts**: `alerts.py` checks each forecast day against a configurable AQI threshold
  (global default or per-subscriber) and logs + emails alerts via Flask-Mail.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit values as needed
```

### 1. Seed historical data (for demo / model bootstrapping)

The app ships with a synthetic data generator so it works out of the box without any
external API key:

```bash
python -m data.seed_data
```

This populates ~240 days of realistic hourly-resampled AQI + weather history for the
city set in `DEFAULT_CITY` (`.env`). To use real historical data instead, replace this
step with a bulk import from your AQI provider's export, or let the scheduler
accumulate live readings over time before training.

### 2. Train the forecasting model

```bash
python -m ml.train
```

This fits the XGBoost + SARIMA models and saves them to `ml/artifacts/`. Prints
cross-validated MAE/RMSE/MAPE so you can gauge forecast quality before deploying.

### 3. Run the app

```bash
python app.py
```

## Switching to a live data source

By default `AQI_DATA_SOURCE=mock` in `.env`. To go live:

- **WAQI** (aqicn.org — free token, good India/global city coverage):
  set `AQI_DATA_SOURCE=waqi` and `WAQI_API_TOKEN=<your token>`.
- **OpenWeatherMap** (Air Pollution + Weather APIs — free tier key):
  set `AQI_DATA_SOURCE=openweather` and `OPENWEATHER_API_KEY=<your key>`.

Re-run `python -m data.seed_data` won't overwrite existing data (it skips seeding if
rows already exist for the city) — once live ingestion has accumulated a few weeks of
real readings, retrain with `python -m ml.train` for a model based on real data.

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/current?city=<name>` | GET | Latest AQI reading, category, color, and health advisory |
| `/api/forecast?city=<name>&days=<1-14>` | GET | N-day forecast with confidence bounds; also triggers alert checks |
| `/api/history?city=<name>&days=<n>` | GET | Raw historical readings for the trailing N days |
| `/api/alerts?city=<name>` | GET | Most recent 20 triggered alerts |
| `/api/subscribe` | POST | `{ "email": "...", "city": "...", "threshold": 150 }` — subscribe to email alerts |

## How to use the dashboard

1. Enter a city name (must match a city with ingested/seeded data) and click **Load**.
2. The top card shows the current AQI, color-coded category (EPA bands: Good →
   Hazardous), and a plain-language health advisory.
3. The **7-Day Forecast** chart shows the blended model prediction with a shaded
   uncertainty band; point colors match the AQI category for that day.
4. The **30-Day History** chart gives context for whether current conditions are
   typical or unusual.
5. Enter an email and threshold under **Alerts** to subscribe — you'll be notified
   (and see entries appear in the Alerts list) whenever the forecast crosses your
   threshold for any of the upcoming days.

## Notes on model quality

- The AQI scale used is the US EPA 0–500 scale; swap `utils.py`'s `AQI_BANDS` for
  CPCB's Indian National AQI breakpoints if that's the target audience.
- The recursive multi-day forecast persists the last known weather values forward as a
  simplification — for production accuracy, feed a genuine weather *forecast* (not just
  the latest observation) into the environmental lag features at predict time.
- Retrain periodically (e.g., weekly, via a cron job calling `python -m ml.train`) as
  more real ingested history accumulates.
