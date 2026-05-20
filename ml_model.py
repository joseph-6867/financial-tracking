# ============================================================
# ml_model.py — Machine Learning for Expense Prediction
# ============================================================
# Uses simple scikit-learn models to predict future expenses.
# We use LINEAR REGRESSION — a beginner-friendly ML model that
# fits a straight line through historical data points.
#
# Concept:
#   X (input features) = month number (1, 2, 3 ... 12)
#   y (target) = total expense for that month
#   Model learns: "as months go by, spending tends to increase/decrease"
# ============================================================

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_error
from datetime import datetime


# ── Data Preparation ───────────────────────────────────────────

def prepare_monthly_data(expenses: list[dict]) -> pd.DataFrame:
    """
    Aggregate raw expense records into monthly totals.
    Returns DataFrame with columns: month_index, year, month, total_amount
    month_index = sequential number (1=first month in data, 2=second, etc.)
    """
    if not expenses:
        return pd.DataFrame()

    df = pd.DataFrame(expenses)
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    df["year"]  = df["expense_date"].dt.year
    df["month"] = df["expense_date"].dt.month
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # Group by year+month
    monthly = df.groupby(["year", "month"], as_index=False)["amount"].sum()
    monthly = monthly.rename(columns={"amount": "total_amount"})
    monthly = monthly.sort_values(["year", "month"]).reset_index(drop=True)

    # Add sequential index (1, 2, 3, ...) as the ML feature
    monthly["month_index"] = range(1, len(monthly) + 1)

    return monthly


# ── Prediction Model ───────────────────────────────────────────

def train_and_predict(monthly_df: pd.DataFrame, future_months: int = 3) -> dict:
    """
    Train a polynomial regression model on monthly spending data
    and predict spending for the next N months.

    Why Polynomial Regression?
    - Linear regression draws a straight line (may be too simple)
    - Polynomial degree=2 fits a curve — better for seasonal patterns
    - We keep degree=2 to avoid overfitting with limited data

    Returns a dict with:
      - historical: DataFrame of actual values
      - predictions: DataFrame of predicted future months
      - model_score: R² score (0-1, higher = better fit)
      - trend: 'Increasing', 'Decreasing', or 'Stable'
      - avg_monthly: average monthly spend
      - confidence: 'High', 'Medium', or 'Low'
    """
    result = {
        "historical": monthly_df,
        "predictions": pd.DataFrame(),
        "model_score": 0.0,
        "trend": "Insufficient Data",
        "avg_monthly": 0.0,
        "confidence": "Low",
        "message": ""
    }

    if monthly_df.empty:
        result["message"] = "No expense data available for predictions."
        return result

    avg = monthly_df["total_amount"].mean()
    result["avg_monthly"] = round(avg, 2)

    # Need at least 2 data points to fit any model
    if len(monthly_df) < 2:
        result["message"] = "Need at least 2 months of data for predictions."
        result["predictions"] = _simple_prediction(monthly_df, future_months)
        return result

    X = monthly_df["month_index"].values.reshape(-1, 1)
    y = monthly_df["total_amount"].values

    # Use degree-2 polynomial pipeline
    degree = 2 if len(monthly_df) >= 4 else 1
    model = make_pipeline(
        PolynomialFeatures(degree=degree, include_bias=False),
        LinearRegression()
    )

    try:
        model.fit(X, y)

        # Evaluate model quality
        y_pred_train = model.predict(X)
        score = 1 - (np.sum((y - y_pred_train) ** 2) / np.sum((y - y.mean()) ** 2))
        result["model_score"] = round(max(0, min(1, score)), 3)

        # Predict next N months
        last_index = int(monthly_df["month_index"].max())
        future_indices = np.arange(last_index + 1, last_index + future_months + 1).reshape(-1, 1)
        future_amounts = model.predict(future_indices)

        # Build future date labels
        last_row = monthly_df.iloc[-1]
        future_rows = []
        curr_year, curr_month = int(last_row["year"]), int(last_row["month"])

        for i, amt in enumerate(future_amounts):
            curr_month += 1
            if curr_month > 12:
                curr_month = 1
                curr_year += 1
            future_rows.append({
                "year": curr_year,
                "month": curr_month,
                "month_label": f"{_month_abbr(curr_month)} {curr_year}",
                "predicted_amount": round(max(0, float(amt)), 2)  # no negative predictions
            })

        result["predictions"] = pd.DataFrame(future_rows)

        # Determine trend from linear component
        if len(monthly_df) >= 3:
            first_half = monthly_df["total_amount"].iloc[:len(monthly_df)//2].mean()
            second_half = monthly_df["total_amount"].iloc[len(monthly_df)//2:].mean()
            diff_pct = ((second_half - first_half) / max(first_half, 1)) * 100

            if diff_pct > 10:
                result["trend"] = "📈 Increasing"
            elif diff_pct < -10:
                result["trend"] = "📉 Decreasing"
            else:
                result["trend"] = "➡️ Stable"

        # Confidence based on data volume and score
        if len(monthly_df) >= 6 and result["model_score"] >= 0.7:
            result["confidence"] = "High"
        elif len(monthly_df) >= 3:
            result["confidence"] = "Medium"
        else:
            result["confidence"] = "Low"

        result["message"] = (
            f"Prediction based on {len(monthly_df)} months of data. "
            f"Model accuracy: {result['model_score']*100:.0f}%"
        )

    except Exception as e:
        result["message"] = f"Prediction model error: {e}"
        result["predictions"] = _simple_prediction(monthly_df, future_months)

    return result


def _simple_prediction(monthly_df: pd.DataFrame, future_months: int) -> pd.DataFrame:
    """
    Fallback: predict using the average of available months.
    Used when there's not enough data for regression.
    """
    avg = monthly_df["total_amount"].mean() if not monthly_df.empty else 0
    last_row = monthly_df.iloc[-1] if not monthly_df.empty else {"year": datetime.now().year, "month": datetime.now().month}
    rows = []
    curr_year, curr_month = int(last_row["year"]), int(last_row["month"])
    for _ in range(future_months):
        curr_month += 1
        if curr_month > 12:
            curr_month = 1
            curr_year += 1
        rows.append({
            "year": curr_year,
            "month": curr_month,
            "month_label": f"{_month_abbr(curr_month)} {curr_year}",
            "predicted_amount": round(float(avg), 2)
        })
    return pd.DataFrame(rows)


def _month_abbr(month: int) -> str:
    """Return 3-letter month abbreviation. 7 → 'Jul'"""
    import calendar
    return calendar.month_abbr[month]


# ── Spending Pattern Analysis ──────────────────────────────────

def detect_patterns(expenses: list[dict]) -> dict:
    """
    Analyse expense data to find spending patterns.
    Returns a dict with human-readable insights.
    """
    patterns = {
        "top_category": None,
        "highest_day": None,
        "avg_daily": 0.0,
        "busiest_day_of_week": None,
        "insights": []
    }

    if not expenses:
        return patterns

    df = pd.DataFrame(expenses)
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["day_of_week"] = df["expense_date"].dt.day_name()

    # Top spending category
    if "category" in df.columns:
        cat_totals = df.groupby("category")["amount"].sum()
        if not cat_totals.empty:
            top_cat = cat_totals.idxmax()
            top_pct = (cat_totals[top_cat] / cat_totals.sum() * 100)
            patterns["top_category"] = top_cat
            patterns["insights"].append(
                f"💡 Your biggest spending category is **{top_cat}** ({top_pct:.0f}% of total)."
            )

    # Highest single-day spending
    daily = df.groupby("expense_date")["amount"].sum()
    if not daily.empty:
        max_day = daily.idxmax()
        patterns["highest_day"] = str(max_day.date())
        patterns["avg_daily"] = round(daily.mean(), 2)
        patterns["insights"].append(
            f"📅 Your highest spending day was **{max_day.strftime('%b %d, %Y')}** "
            f"(₹{daily[max_day]:,.0f})."
        )

    # Busiest day of week
    dow_totals = df.groupby("day_of_week")["amount"].sum()
    if not dow_totals.empty:
        busiest = dow_totals.idxmax()
        patterns["busiest_day_of_week"] = busiest
        patterns["insights"].append(
            f"📆 You tend to spend the most on **{busiest}s**."
        )

    # Average daily spend
    if patterns["avg_daily"] > 0:
        patterns["insights"].append(
            f"📊 Your average daily spend is **₹{patterns['avg_daily']:,.0f}**."
        )

    return patterns


# ── Category-Level Prediction ──────────────────────────────────

def predict_by_category(expenses: list[dict]) -> dict[str, float]:
    """
    For each category, predict next month's spend using its average.
    Returns dict: {category: predicted_amount}
    Simple but effective for category-level forecasting.
    """
    if not expenses:
        return {}

    df = pd.DataFrame(expenses)
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["year"]  = df["expense_date"].dt.year
    df["month"] = df["expense_date"].dt.month

    # Monthly totals per category
    cat_monthly = df.groupby(["category", "year", "month"])["amount"].sum().reset_index()

    predictions = {}
    for cat in cat_monthly["category"].unique():
        cat_data = cat_monthly[cat_monthly["category"] == cat]["amount"]
        # Predict = weighted average (recent months weighted more)
        n = len(cat_data)
        weights = np.linspace(1, 2, n)  # recent months get weight up to 2×
        weighted_avg = np.average(cat_data.values, weights=weights)
        predictions[cat] = round(float(weighted_avg), 2)

    return predictions
