# ============================================================
# charts.py — Plotly Chart Generators
# ============================================================
# Each function returns a Plotly figure object that can be
# rendered with st.plotly_chart(fig, use_container_width=True)
#
# Why Plotly? It creates interactive charts (hover, zoom, pan)
# that look great in Streamlit without any extra setup.
# ============================================================

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from utils import CATEGORY_COLORS, month_name


# ── Shared theme settings ──────────────────────────────────────
CHART_THEME = {
    "paper_bgcolor": "rgba(0,0,0,0)",   # transparent background
    "plot_bgcolor":  "rgba(0,0,0,0)",
    "font":          {"family": "Inter, sans-serif", "size": 12},
    "margin":        {"t": 40, "b": 40, "l": 20, "r": 20},
}


def _apply_theme(fig: go.Figure) -> go.Figure:
    """Apply the shared chart theme to any figure."""
    fig.update_layout(
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font=CHART_THEME["font"],
        margin=CHART_THEME["margin"],
    )
    return fig


def _get_color(category: str) -> str:
    """Return chart colour for a category, fallback to grey."""
    return CATEGORY_COLORS.get(category, "#999999")


# ── Pie Chart: Spending by Category ───────────────────────────

def pie_chart_by_category(grouped_df: pd.DataFrame, title: str = "Spending by Category") -> go.Figure:
    """
    Donut-style pie chart showing category breakdown.
    grouped_df must have columns: category, amount
    """
    if grouped_df.empty:
        return _empty_chart("No expense data available")

    colors = [_get_color(c) for c in grouped_df["category"]]

    fig = go.Figure(data=[go.Pie(
        labels=grouped_df["category"],
        values=grouped_df["amount"],
        hole=0.45,                     # Makes it a donut chart
        marker=dict(colors=colors, line=dict(color="#fff", width=2)),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>₹%{value:,.2f}<br>%{percent}<extra></extra>"
    )])

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        showlegend=True,
        legend=dict(orientation="v", x=1.05, y=0.5),
        **{k: v for k, v in CHART_THEME.items() if k != "margin"},
        margin={"t": 50, "b": 20, "l": 0, "r": 120},
        height=380,
    )
    return fig


# ── Bar Chart: Monthly Expenses ────────────────────────────────

def bar_chart_monthly(monthly_df: pd.DataFrame, title: str = "Monthly Expenses") -> go.Figure:
    """
    Vertical bar chart showing total spend per month.
    monthly_df must have columns: month_year, amount
    """
    if monthly_df.empty:
        return _empty_chart("No monthly data available")

    fig = go.Figure(data=[go.Bar(
        x=monthly_df["month_year"],
        y=monthly_df["amount"],
        marker=dict(
            color=monthly_df["amount"],
            colorscale="Blues",
            showscale=False,
            line=dict(color="rgba(255,255,255,0.3)", width=1)
        ),
        text=[f"₹{v:,.0f}" for v in monthly_df["amount"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>₹%{y:,.2f}<extra></extra>"
    )])

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        xaxis=dict(title="Month", showgrid=False),
        yaxis=dict(title="Amount (₹)", showgrid=True, gridcolor="#eee"),
        height=370,
        **CHART_THEME
    )
    return fig


# ── Line Chart: Daily Spending Trend ──────────────────────────

def line_chart_daily(daily_df: pd.DataFrame, title: str = "Daily Spending Trend") -> go.Figure:
    """
    Smooth line chart showing spending day-by-day.
    daily_df must have columns: expense_date, amount
    """
    if daily_df.empty:
        return _empty_chart("No daily data available")

    fig = go.Figure()

    # Shaded area below the line
    fig.add_trace(go.Scatter(
        x=daily_df["expense_date"],
        y=daily_df["amount"],
        mode="lines+markers",
        name="Daily Spend",
        line=dict(color="#4ECDC4", width=2.5, shape="spline"),
        marker=dict(size=6, color="#4ECDC4"),
        fill="tozeroy",
        fillcolor="rgba(78,205,196,0.15)",
        hovertemplate="<b>%{x|%b %d}</b><br>₹%{y:,.2f}<extra></extra>"
    ))

    # Rolling 7-day average line
    if len(daily_df) >= 7:
        rolling = daily_df["amount"].rolling(7, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=daily_df["expense_date"],
            y=rolling,
            mode="lines",
            name="7-Day Avg",
            line=dict(color="#FF6B6B", width=1.5, dash="dot"),
            hovertemplate="7-Day Avg: ₹%{y:,.2f}<extra></extra>"
        ))

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        xaxis=dict(title="Date", showgrid=False),
        yaxis=dict(title="Amount (₹)", showgrid=True, gridcolor="#eee"),
        legend=dict(x=0, y=1.1, orientation="h"),
        height=350,
        **CHART_THEME
    )
    return fig


# ── Grouped Bar: Current vs Previous Month ────────────────────

def bar_chart_comparison(
    curr_by_cat: pd.DataFrame,
    prev_by_cat: pd.DataFrame,
    curr_label: str = "This Month",
    prev_label: str = "Last Month",
) -> go.Figure:
    """
    Side-by-side bar chart comparing two months by category.
    Both DataFrames must have columns: category, amount
    """
    all_cats = sorted(set(
        list(curr_by_cat["category"] if not curr_by_cat.empty else []) +
        list(prev_by_cat["category"] if not prev_by_cat.empty else [])
    ))

    if not all_cats:
        return _empty_chart("No comparison data available")

    # Map category → amount (default 0 if missing)
    curr_map = dict(zip(curr_by_cat["category"], curr_by_cat["amount"])) if not curr_by_cat.empty else {}
    prev_map = dict(zip(prev_by_cat["category"], prev_by_cat["amount"])) if not prev_by_cat.empty else {}

    curr_vals = [curr_map.get(c, 0) for c in all_cats]
    prev_vals = [prev_map.get(c, 0) for c in all_cats]

    fig = go.Figure(data=[
        go.Bar(
            name=prev_label,
            x=all_cats,
            y=prev_vals,
            marker_color="#B0C4DE",
            hovertemplate="<b>%{x}</b><br>" + prev_label + ": ₹%{y:,.2f}<extra></extra>"
        ),
        go.Bar(
            name=curr_label,
            x=all_cats,
            y=curr_vals,
            marker_color="#4ECDC4",
            hovertemplate="<b>%{x}</b><br>" + curr_label + ": ₹%{y:,.2f}<extra></extra>"
        ),
    ])

    fig.update_layout(
        barmode="group",
        title=dict(text="Month-over-Month Comparison", x=0.5, xanchor="center"),
        xaxis=dict(title="Category", showgrid=False),
        yaxis=dict(title="Amount (₹)", showgrid=True, gridcolor="#eee"),
        legend=dict(x=0, y=1.1, orientation="h"),
        height=380,
        **CHART_THEME
    )
    return fig


# ── Budget Progress Gauge ──────────────────────────────────────

def gauge_chart_budget(spent: float, budget: float, title: str = "Budget Usage") -> go.Figure:
    """
    Gauge (speedometer-style) chart showing budget consumption.
    Green = safe, Yellow = near limit, Red = over budget.
    """
    if budget <= 0:
        return _empty_chart("Set a monthly budget to see gauge")

    pct = min((spent / budget) * 100, 150)  # Cap at 150% for display

    # Colour based on usage
    if pct < 70:
        bar_color = "#2ecc71"   # Green
    elif pct < 90:
        bar_color = "#f39c12"   # Orange
    else:
        bar_color = "#e74c3c"   # Red

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=spent,
        delta={"reference": budget, "valueformat": ",.0f", "prefix": "₹"},
        number={"prefix": "₹", "valueformat": ",.2f"},
        title={"text": title, "font": {"size": 14}},
        gauge={
            "axis": {"range": [0, budget * 1.2], "tickformat": ",.0f"},
            "bar": {"color": bar_color, "thickness": 0.75},
            "bgcolor": "white",
            "borderwidth": 2,
            "bordercolor": "#ddd",
            "steps": [
                {"range": [0, budget * 0.7],  "color": "#e8f8f5"},
                {"range": [budget * 0.7, budget], "color": "#fef9e7"},
                {"range": [budget, budget * 1.2], "color": "#fdedec"},
            ],
            "threshold": {
                "line": {"color": "#e74c3c", "width": 3},
                "thickness": 0.75,
                "value": budget
            }
        }
    ))

    fig.update_layout(
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        margin={"t": 40, "b": 20, "l": 40, "r": 40}
    )
    return fig


# ── ML Prediction Line Chart ───────────────────────────────────

def prediction_chart(historical_df: pd.DataFrame, predictions_df: pd.DataFrame) -> go.Figure:
    """
    Line chart combining actual historical data with ML predictions.
    historical_df: columns month_label (or year+month), total_amount
    predictions_df: columns month_label, predicted_amount
    """
    fig = go.Figure()

    # Build x-labels for historical
    if not historical_df.empty:
        import calendar
        hist_labels = [
            f"{calendar.month_abbr[int(r['month'])]} {int(r['year'])}"
            for _, r in historical_df.iterrows()
        ]
        fig.add_trace(go.Scatter(
            x=hist_labels,
            y=historical_df["total_amount"],
            mode="lines+markers",
            name="Actual",
            line=dict(color="#4ECDC4", width=2.5),
            marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>Actual: ₹%{y:,.2f}<extra></extra>"
        ))

    # Prediction trace (dashed orange)
    if not predictions_df.empty:
        # Connect historical last point to first prediction for continuity
        x_pred = list(predictions_df["month_label"])
        y_pred = list(predictions_df["predicted_amount"])

        if not historical_df.empty:
            x_pred = [hist_labels[-1]] + x_pred
            y_pred = [float(historical_df["total_amount"].iloc[-1])] + y_pred

        fig.add_trace(go.Scatter(
            x=x_pred,
            y=y_pred,
            mode="lines+markers",
            name="Predicted",
            line=dict(color="#FF6B6B", width=2, dash="dash"),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate="<b>%{x}</b><br>Predicted: ₹%{y:,.2f}<extra></extra>"
        ))

    fig.update_layout(
        title=dict(text="Expense Forecast (ML Prediction)", x=0.5, xanchor="center"),
        xaxis=dict(title="Month", showgrid=False),
        yaxis=dict(title="Amount (₹)", showgrid=True, gridcolor="#eee"),
        legend=dict(x=0, y=1.1, orientation="h"),
        height=370,
        **CHART_THEME
    )
    return fig


# ── Category Trend Lines ───────────────────────────────────────

def multi_line_category_trend(expenses: list[dict]) -> go.Figure:
    """
    Multiple line chart showing monthly trend per category.
    Useful for seeing which categories are growing over time.
    """
    if not expenses:
        return _empty_chart("No data for category trends")

    import calendar
    df = pd.DataFrame(expenses)
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["month_label"] = df["expense_date"].apply(
        lambda d: f"{calendar.month_abbr[d.month]} {d.year}"
    )

    cat_monthly = df.groupby(["month_label", "category"])["amount"].sum().reset_index()

    fig = go.Figure()
    for cat in cat_monthly["category"].unique():
        cat_df = cat_monthly[cat_monthly["category"] == cat].sort_values("month_label")
        fig.add_trace(go.Scatter(
            x=cat_df["month_label"],
            y=cat_df["amount"],
            mode="lines+markers",
            name=cat,
            line=dict(color=_get_color(cat), width=2),
            marker=dict(size=6),
            hovertemplate=f"<b>{cat}</b><br>%{{x}}: ₹%{{y:,.2f}}<extra></extra>"
        ))

    fig.update_layout(
        title=dict(text="Category Spending Trends", x=0.5, xanchor="center"),
        xaxis=dict(title="Month", showgrid=False),
        yaxis=dict(title="Amount (₹)", showgrid=True, gridcolor="#eee"),
        legend=dict(orientation="h", y=-0.3),
        height=380,
        **CHART_THEME
    )
    return fig


# ── Empty State Chart ──────────────────────────────────────────

def _empty_chart(message: str = "No data available") -> go.Figure:
    """Return a blank figure with a centred message when there's no data."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color="#999")
    )
    fig.update_layout(
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
