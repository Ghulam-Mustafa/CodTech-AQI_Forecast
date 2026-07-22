import os
import warnings

import joblib
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAXResults

from ml.features import build_features, FEATURE_COLUMNS
from config import Config

warnings.filterwarnings("ignore")


class ModelNotTrainedError(Exception):
    pass


def _artifact_paths(city):
    base = Config.MODEL_DIR
    return (
        os.path.join(base, f"{city}_gbm.joblib"),
        os.path.join(base, f"{city}_sarima.pkl"),
        os.path.join(base, f"{city}_meta.joblib"),
    )


def has_trained_model(city: str) -> bool:
    return all(os.path.exists(p) for p in _artifact_paths(city))


def forecast(city: str, daily_history: pd.DataFrame, horizon: int = 7) -> list:
    """Recursively forecasts `horizon` future days using the GBM as the primary
    forecaster and blends in the SARIMA estimate for extra stability, since neither
    model alone handles both nonlinear feature interactions and pure AR structure well."""
    gbm_path, sarima_path, meta_path = _artifact_paths(city)
    if not has_trained_model(city):
        raise ModelNotTrainedError(f"No trained model for '{city}'. Run `python -m ml.train` first.")

    gbm = joblib.load(gbm_path)
    sarima = SARIMAXResults.load(sarima_path)

    sarima_fc = sarima.get_forecast(steps=horizon)
    sarima_mean = sarima_fc.predicted_mean
    sarima_ci = sarima_fc.conf_int(alpha=0.2)  # 80% interval

    working = daily_history.copy()
    last_env = working.iloc[-1][["temperature", "humidity", "wind_speed", "pressure"]]

    results = []
    for step in range(horizon):
        feat_frame = build_features(working)
        row = feat_frame.iloc[[-1]].copy()

        # Persist last known environmental readings forward (a real deployment would
        # substitute a weather-forecast API here instead of a naive persistence assumption)
        for col in ["temperature", "humidity", "wind_speed", "pressure"]:
            row[f"{col}_lag_1"] = last_env[col]

        next_date = working.index[-1] + pd.Timedelta(days=1)
        row["day_of_week"] = next_date.dayofweek
        row["day_of_year"] = next_date.dayofyear
        row["month"] = next_date.month
        row["doy_sin"] = np.sin(2 * np.pi * next_date.dayofyear / 365.25)
        row["doy_cos"] = np.cos(2 * np.pi * next_date.dayofyear / 365.25)

        X = row[FEATURE_COLUMNS].ffill(axis=0).bfill(axis=0)
        gbm_pred = float(gbm.predict(X)[0])
        sarima_pred = float(sarima_mean.iloc[step])

        # Weighted blend: GBM captures nonlinear/environmental effects, SARIMA anchors
        # the pure autoregressive trend — blending reduces variance from either alone.
        blended = 0.65 * gbm_pred + 0.35 * sarima_pred
        blended = max(5.0, blended)

        lo = max(5.0, min(blended, float(sarima_ci.iloc[step, 0])) - abs(gbm_pred - sarima_pred) * 0.5)
        hi = max(blended, float(sarima_ci.iloc[step, 1])) + abs(gbm_pred - sarima_pred) * 0.5

        results.append({
            "date": next_date.date().isoformat(),
            "predicted_aqi": round(blended, 1),
            "lower_bound": round(lo, 1),
            "upper_bound": round(hi, 1),
            "gbm_estimate": round(gbm_pred, 1),
            "sarima_estimate": round(sarima_pred, 1),
        })

        # Append the blended prediction as the new "known" point so the next
        # iteration's lag features roll forward (recursive multi-step forecasting)
        new_row = working.iloc[[-1]].copy()
        new_row.index = [next_date]
        new_row["aqi"] = blended
        working = pd.concat([working, new_row])

    return results
