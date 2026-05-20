# ============================================================
# utils.py — Shared Utility Functions
# ============================================================
# Small helper functions used across multiple modules.
# Keeping them here avoids duplicate code (DRY principle).
# ============================================================

import pandas as pd
from datetime import datetime, date
import calendar
import io


# ── Category Constants ─────────────────────────────────────────

EXPENSE_CATEGORIES = [
    "🍔 Food",
    "✈️ Travel",
    "🛍️ Shopping",
    "💡 Bills",
    "🏥 Healthcare",
    "🎭 Entertainment",
    "📦 Other"
]

# Clean names without emojis (for DB storage and filtering)
CATEGORY_NAMES = [c.split(" ", 1)[1] for c in EXPENSE_CATEGORIES]

# Colour map used in charts (category → hex colour)
CATEGORY_COLORS = {
    "Food":          "#FF6B6B",
    "Travel":        "#4ECDC4",
    "Shopping":      "#45B7D1",
    "Bills":         "#96CEB4",
    "Healthcare":    "#FFEAA7",
    "Entertainment": "#DDA0DD",
    "Other":         "#B0C4DE",
}


# ── Date Helpers ───────────────────────────────────────────────

def get_current_month_year() -> tuple[int, int]:
    """Return (month, year) for today's date. Example: (7, 2024)"""
    now = datetime.now()
    return now.month, now.year


def get_previous_month_year(month: int, year: int) -> tuple[int, int]:
    """
    Given a month and year, return the previous month and year.
    Handles January → December of previous year correctly.
    Example: (1, 2024) → (12, 2023)
    """
    if month == 1:
        return 12, year - 1
    return month - 1, year


def month_name(month: int) -> str:
    """Convert month number to full name. Example: 7 → 'July'"""
    return calendar.month_name[month]


def format_currency(amount: float, symbol: str = "₹") -> str:
    """Format a float as a currency string. Example: 1234.5 → '₹1,234.50'"""
    return f"{symbol}{amount:,.2f}"


def days_in_month(month: int, year: int) -> int:
    """Return the number of days in a given month/year."""
    return calendar.monthrange(year, month)[1]


# ── DataFrame Helpers ──────────────────────────────────────────

def expenses_to_dataframe(expenses: list[dict]) -> pd.DataFrame:
    """
    Convert a list of expense dicts (from DB) into a clean pandas DataFrame.
    Also normalises category names (strips emoji prefix if present).
    """
    if not expenses:
        return pd.DataFrame(columns=["id", "amount", "category", "description", "expense_date", "notes"])

    df = pd.DataFrame(expenses)

    # Normalise column names
    if "expense_date" in df.columns:
        df["expense_date"] = pd.to_datetime(df["expense_date"])

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # Strip any emoji prefixes from category (stored clean in DB)
    if "category" in df.columns:
        df["category"] = df["category"].astype(str)

    return df


def calculate_total(df: pd.DataFrame) -> float:
    """Sum the 'amount' column of a DataFrame. Returns 0 if empty."""
    if df.empty or "amount" not in df.columns:
        return 0.0
    return float(df["amount"].sum())


def group_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Group expenses by category and sum amounts.
    Returns a DataFrame with columns: category, amount, percentage
    """
    if df.empty:
        return pd.DataFrame(columns=["category", "amount", "percentage"])

    grouped = df.groupby("category", as_index=False)["amount"].sum()
    total = grouped["amount"].sum()
    grouped["percentage"] = (grouped["amount"] / total * 100).round(1) if total > 0 else 0
    grouped = grouped.sort_values("amount", ascending=False)
    return grouped


def group_by_day(df: pd.DataFrame) -> pd.DataFrame:
    """
    Group expenses by day (for line chart of daily spending).
    """
    if df.empty or "expense_date" not in df.columns:
        return pd.DataFrame(columns=["expense_date", "amount"])

    df = df.copy()
    df["expense_date"] = pd.to_datetime(df["expense_date"]).dt.date
    grouped = df.groupby("expense_date", as_index=False)["amount"].sum()
    grouped = grouped.sort_values("expense_date")
    return grouped


def group_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    Group expenses by month/year (for bar chart of monthly spending).
    """
    if df.empty or "expense_date" not in df.columns:
        return pd.DataFrame(columns=["month_year", "amount"])

    df = df.copy()
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    df["month_year"] = df["expense_date"].dt.to_period("M").astype(str)
    grouped = df.groupby("month_year", as_index=False)["amount"].sum()
    grouped = grouped.sort_values("month_year")
    return grouped


# ── Search & Filter ────────────────────────────────────────────

def search_expenses(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Case-insensitive search across description, category, and notes columns.
    Returns filtered DataFrame.
    """
    if df.empty or not query.strip():
        return df

    query = query.lower()
    mask = (
        df.get("description", pd.Series(dtype=str)).str.lower().str.contains(query, na=False) |
        df.get("category",    pd.Series(dtype=str)).str.lower().str.contains(query, na=False) |
        df.get("notes",       pd.Series(dtype=str)).str.lower().str.contains(query, na=False)
    )
    return df[mask]


# ── Export ─────────────────────────────────────────────────────

def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    Convert DataFrame to CSV bytes for Streamlit's st.download_button.
    Formats the expense_date column nicely.
    """
    export_df = df.copy()

    if "expense_date" in export_df.columns:
        export_df["expense_date"] = pd.to_datetime(
            export_df["expense_date"]
        ).dt.strftime("%Y-%m-%d")

    # Drop internal DB columns for clean export
    cols_to_drop = [c for c in ["id", "user_id", "created_at", "updated_at"] if c in export_df.columns]
    export_df = export_df.drop(columns=cols_to_drop)

    return export_df.to_csv(index=False).encode("utf-8")


def get_budget_status(total_spent: float, budget: float) -> tuple[str, str, float]:
    """
    Calculate budget usage and return status info.
    Returns: (status_label, color, percentage_used)
    status_label: 'Under Budget', 'Near Limit', 'Over Budget'
    color: green / orange / red
    """
    if budget <= 0:
        return "No Budget Set", "blue", 0.0

    pct = (total_spent / budget) * 100

    if pct >= 100:
        return "🚨 Over Budget", "red", pct
    elif pct >= 80:
        return "⚠️ Near Limit", "orange", pct
    else:
        return "✅ Under Budget", "green", pct


def clean_category(category: str) -> str:
    """
    Remove emoji prefix from display category name.
    Example: '🍔 Food' → 'Food'
    """
    if " " in category:
        parts = category.split(" ", 1)
        # If first part looks like an emoji (short), return second part
        if len(parts[0]) <= 2:
            return parts[1]
    return category
