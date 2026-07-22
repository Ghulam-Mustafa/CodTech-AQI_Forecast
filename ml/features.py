import pandas as pd
import numpy as np


def readings_to_frame(readings: list) -> pd.DataFrame:
    """Convert a list of AQIReading ORM objects into a clean, time-indexed DataFrame."""
    df = pd.DataFrame([r.to_dict() for r in readings])
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")
    # Resample to daily means so forecasts are day-granularity (matches the UI's "next N days")
    daily = df.resample("D").mean(numeric_only=True)
    daily = daily.interpolate(limit_direction="both")
    return daily


def build_features(daily: pd.DataFrame, lags=(1, 2, 3, 7)) -> pd.DataFrame:
    """Adds lag, rolling, and calendar features. Returns a frame ready for supervised learning."""
    df = daily.copy()

    for lag in lags:
        df[f"aqi_lag_{lag}"] = df["aqi"].shift(lag)

    df["aqi_roll_mean_3"] = df["aqi"].shift(1).rolling(3).mean()
    df["aqi_roll_mean_7"] = df["aqi"].shift(1).rolling(7).mean()
    df["aqi_roll_std_7"] = df["aqi"].shift(1).rolling(7).std()
    df["aqi_diff_1"] = df["aqi"].shift(1) - df["aqi"].shift(2)

    df["day_of_week"] = df.index.dayofweek
    df["day_of_year"] = df.index.dayofyear
    df["month"] = df.index.month
    df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365.25)

    # Environmental factors of the day itself (assumed forecastable/available at predict time
    # via a weather forecast API; here we fall back to their own lag/seasonal average if absent)
    env_cols = ["temperature", "humidity", "wind_speed", "pressure"]
    for col in env_cols:
        if col in df.columns:
            df[f"{col}_lag_1"] = df[col].shift(1)

    return df


FEATURE_COLUMNS = [
    "aqi_lag_1", "aqi_lag_2", "aqi_lag_3", "aqi_lag_7",
    "aqi_roll_mean_3", "aqi_roll_mean_7", "aqi_roll_std_7", "aqi_diff_1",
    "day_of_week", "day_of_year", "month", "doy_sin", "doy_cos",
    "temperature_lag_1", "humidity_lag_1", "wind_speed_lag_1", "pressure_lag_1",
]
