"""
Trains two models on daily-aggregated AQI history:
  1. XGBoost regressor on lag/rolling/calendar/environmental features (primary forecaster)
  2. SARIMA on the AQI series alone (interpretable baseline, also used to sanity-check XGBoost)

Both are persisted to ml/artifacts/ via joblib so the Flask app can load them without retraining.

Run: python -m ml.train
"""
import os
import sys
import warnings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
warnings.filterwarnings("ignore")

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from statsmodels.tsa.statespace.sarimax import SARIMAX

from app import create_app
from models import AQIReading
from ml.features import readings_to_frame, build_features, FEATURE_COLUMNS
from config import Config

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    HAS_XGB = False


def load_daily_frame(city: str):
    app = create_app()
    with app.app_context():
        readings = AQIReading.query.filter_by(city=city).order_by(AQIReading.timestamp).all()
    if not readings:
        raise RuntimeError(f"No readings found for '{city}'. Run `python -m data.seed_data` first.")
    return readings_to_frame(readings)


def train_gbm(df_feat):
    df_feat = df_feat.dropna(subset=FEATURE_COLUMNS + ["aqi"])
    X, y = df_feat[FEATURE_COLUMNS], df_feat["aqi"]

    if HAS_XGB:
        model = XGBRegressor(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, random_state=42,
        )
    else:
        model = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42)

    # Time-series cross-validation (no shuffling — respects chronology)
    tscv = TimeSeriesSplit(n_splits=5)
    maes, rmses = [], []
    for train_idx, test_idx in tscv.split(X):
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        preds = model.predict(X.iloc[test_idx])
        maes.append(mean_absolute_error(y.iloc[test_idx], preds))
        rmses.append(np.sqrt(mean_squared_error(y.iloc[test_idx], preds)))

    # Final fit on all available data
    model.fit(X, y)
    metrics = {
        "mae": float(np.mean(maes)),
        "rmse": float(np.mean(rmses)),
        "mape": float(np.mean(np.abs((y - model.predict(X)) / y.replace(0, np.nan))) * 100),
        "n_samples": int(len(X)),
        "backend": "xgboost" if HAS_XGB else "sklearn-gbr",
    }
    return model, metrics


def train_sarima(df_feat):
    series = df_feat["aqi"].dropna()
    model = SARIMAX(series, order=(2, 1, 2), seasonal_order=(1, 0, 1, 7),
                     enforce_stationarity=False, enforce_invertibility=False)
    fitted = model.fit(disp=False)
    return fitted


def main(city: str = None):
    city = city or Config.DEFAULT_CITY
    os.makedirs(Config.MODEL_DIR, exist_ok=True)

    daily = load_daily_frame(city)
    df_feat = build_features(daily)

    gbm, gbm_metrics = train_gbm(df_feat)
    sarima = train_sarima(df_feat)

    joblib.dump(gbm, os.path.join(Config.MODEL_DIR, f"{city}_gbm.joblib"))
    sarima.save(os.path.join(Config.MODEL_DIR, f"{city}_sarima.pkl"))
    joblib.dump(
        {"last_known": daily.tail(10), "metrics": gbm_metrics},
        os.path.join(Config.MODEL_DIR, f"{city}_meta.joblib"),
    )

    print(f"Trained models for {city}")
    print(f"  GBM  -> MAE={gbm_metrics['mae']:.2f}  RMSE={gbm_metrics['rmse']:.2f}  "
          f"MAPE={gbm_metrics['mape']:.1f}%  ({gbm_metrics['backend']}, n={gbm_metrics['n_samples']})")
    print(f"  SARIMA(2,1,2)x(1,0,1,7) fitted, AIC={sarima.aic:.1f}")


if __name__ == "__main__":
    main()
