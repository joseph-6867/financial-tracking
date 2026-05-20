# ============================================================
# dashboard.py — Expense Analytics Dashboard
# ============================================================
# Renders the main app after login. Contains:
#   • Overview KPI cards
#   • Add / Edit / Delete expense forms
#   • Budget management
#   • Search & filter
#   • Chart visualisations
#   • ML predictions tab
#   • Login history tab
#   • Settings & email tab
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date, datetime

from database import (
    db_get_expenses, db_add_expense, db_update_expense, db_delete_expense,
    db_get_budget, db_set_budget, db_get_login_history
)
from utils import (
    EXPENSE_CATEGORIES, CATEGORY_NAMES,
    expenses_to_dataframe, calculate_total, group_by_category,
    group_by_day, group_by_month, search_expenses,
    dataframe_to_csv_bytes, get_budget_status, format_currency,
    get_current_month_year, get_previous_month_year, month_name
)
from charts import (
    pie_chart_by_category, bar_chart_monthly, line_chart_daily,
    bar_chart_comparison, gauge_chart_budget, prediction_chart,
    multi_line_category_trend
)
from ml_model import prepare_monthly_data, train_and_predict, detect_patterns, predict_by_category
from email_service import send_monthly_summary, send_budget_alert, send_prediction_report


# ── Dashboard Entry Point ──────────────────────────────────────

def render_dashboard():
    """
    Main dashboard renderer. Called from app.py after login.
    Uses Streamlit tabs to organise sections.
    """
    user_id  = st.session_state.user_id
    username = st.session_state.username
    email    = st.session_state.email

    curr_month, curr_year = get_current_month_year()

    # ── Sidebar ──────────────────────────────────────────────
    _render_sidebar(user_id, curr_month, curr_year, email, username)

    # ── Page Header ──────────────────────────────────────────
    st.title(f"👋 Welcome back, {username}!")
    st.caption(f"📅 {datetime.now().strftime('%A, %B %d, %Y')}")
    st.divider()

    # ── Main Tabs ─────────────────────────────────────────────
    tabs = st.tabs([
        "📊 Overview",
        "➕ Add Expense",
        "📋 My Expenses",
        "🔮 Predictions",
        "🔐 Login History",
        "⚙️ Settings"
    ])

    with tabs[0]:
        _tab_overview(user_id, curr_month, curr_year)

    with tabs[1]:
        _tab_add_expense(user_id)

    with tabs[2]:
        _tab_expense_list(user_id, curr_month, curr_year)

    with tabs[3]:
        _tab_predictions(user_id, email, username)

    with tabs[4]:
        _tab_login_history(user_id)

    with tabs[5]:
        _tab_settings(user_id, email, username, curr_month, curr_year)


# ── Sidebar ───────────────────────────────────────────────────

def _render_sidebar(user_id, curr_month, curr_year, email, username):
    """Sidebar: quick stats, budget setter, logout."""
    with st.sidebar:
        st.markdown("## 💰 Expense Tracker")
        st.caption(f"Logged in as **{username}**")
        st.divider()

        # Quick budget input
        st.markdown("### 🎯 Monthly Budget")
        budget_rec = db_get_budget(user_id, curr_year, curr_month)
        current_budget = budget_rec["budget_amount"] if budget_rec else 0.0

        new_budget = st.number_input(
            f"Budget for {month_name(curr_month)} {curr_year}",
            min_value=0.0, value=float(current_budget), step=500.0,
            format="%.2f", key="sidebar_budget"
        )
        if st.button("💾 Save Budget", use_container_width=True):
            if db_set_budget(user_id, curr_year, curr_month, new_budget):
                st.success("Budget saved!")
            else:
                st.error("Failed to save budget.")

        st.divider()

        # Quick stats
        expenses = db_get_expenses(user_id, {"month": curr_month, "year": curr_year})
        total = sum(float(e.get("amount", 0)) for e in expenses)
        status, color, pct = get_budget_status(total, new_budget)

        st.metric("💸 This Month", format_currency(total))
        if new_budget > 0:
            st.metric("📊 Budget Used", f"{pct:.1f}%", delta=f"{pct-100:.1f}%" if pct > 100 else None)
            if color == "green":
                st.success(status)
            elif color == "orange":
                st.warning(status)
            else:
                st.error(status)

        st.divider()

        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            from auth import clear_session
            clear_session()
            st.rerun()


# ── TAB: Overview ─────────────────────────────────────────────

def _tab_overview(user_id, curr_month, curr_year):
    """KPI cards, charts, and month comparison."""

    # Fetch current and previous month data
    prev_month, prev_year = get_previous_month_year(curr_month, curr_year)
    curr_expenses = db_get_expenses(user_id, {"month": curr_month, "year": curr_year})
    prev_expenses = db_get_expenses(user_id, {"month": prev_month, "year": prev_year})

    curr_df = expenses_to_dataframe(curr_expenses)
    prev_df = expenses_to_dataframe(prev_expenses)

    curr_total = calculate_total(curr_df)
    prev_total = calculate_total(prev_df)

    budget_rec = db_get_budget(user_id, curr_year, curr_month)
    budget = budget_rec["budget_amount"] if budget_rec else 0.0
    status, color, pct = get_budget_status(curr_total, budget)

    # ── KPI Cards ──
    st.subheader(f"📅 {month_name(curr_month)} {curr_year} Overview")
    c1, c2, c3, c4 = st.columns(4)

    delta_vs_prev = curr_total - prev_total
    with c1:
        st.metric(
            "💸 Total Spent",
            format_currency(curr_total),
            delta=f"{format_currency(abs(delta_vs_prev))} {'more' if delta_vs_prev > 0 else 'less'} than last month",
            delta_color="inverse"
        )
    with c2:
        st.metric("🧾 Transactions", len(curr_expenses))
    with c3:
        avg = curr_total / len(curr_expenses) if curr_expenses else 0
        st.metric("📊 Avg / Expense", format_currency(avg))
    with c4:
        remaining = budget - curr_total if budget > 0 else 0
        st.metric("🎯 Budget Left", format_currency(max(0, remaining)))

    st.divider()

    # ── Budget Alert ──
    if budget > 0:
        if color == "green":
            st.success(f"{status} — You've used **{pct:.1f}%** of your ₹{budget:,.0f} budget.")
        elif color == "orange":
            st.warning(f"{status} — You've used **{pct:.1f}%** of your ₹{budget:,.0f} budget. Watch your spending!")
        else:
            st.error(f"{status} — Spent ₹{curr_total:,.2f} against ₹{budget:,.2f} budget ({pct:.1f}% used).")

    # ── Charts Row 1: Pie + Gauge ──
    curr_grouped = group_by_category(curr_df)

    r1c1, r1c2 = st.columns([3, 2])
    with r1c1:
        st.plotly_chart(
            pie_chart_by_category(curr_grouped, f"Spending by Category — {month_name(curr_month)}"),
            use_container_width=True
        )
    with r1c2:
        st.plotly_chart(
            gauge_chart_budget(curr_total, budget),
            use_container_width=True
        )
        if not curr_grouped.empty:
            st.markdown("**Category Totals**")
            for _, row in curr_grouped.iterrows():
                st.markdown(
                    f"- **{row['category']}**: {format_currency(row['amount'])} ({row['percentage']}%)"
                )

    # ── Charts Row 2: Daily Line + Month Comparison ──
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        daily_df = group_by_day(curr_df)
        st.plotly_chart(line_chart_daily(daily_df), use_container_width=True)

    with r2c2:
        prev_grouped = group_by_category(prev_df)
        st.plotly_chart(
            bar_chart_comparison(
                curr_grouped, prev_grouped,
                curr_label=month_name(curr_month),
                prev_label=month_name(prev_month)
            ),
            use_container_width=True
        )

    # ── Monthly Bar Chart (all time) ──
    all_expenses = db_get_expenses(user_id)
    all_df = expenses_to_dataframe(all_expenses)
    monthly_df = group_by_month(all_df)
    st.plotly_chart(bar_chart_monthly(monthly_df, "Monthly Spending History"), use_container_width=True)


# ── TAB: Add Expense ──────────────────────────────────────────

def _tab_add_expense(user_id):
    """Form for adding or editing an expense."""
    edit_id = st.session_state.get("edit_expense_id")

    if edit_id:
        st.subheader("✏️ Edit Expense")
        # Pre-load existing data
        existing_exps = db_get_expenses(user_id)
        existing = next((e for e in existing_exps if str(e["id"]) == str(edit_id)), None)
    else:
        st.subheader("➕ Add New Expense")
        existing = None

    with st.form("expense_form", clear_on_submit=not edit_id):
        col1, col2 = st.columns(2)

        with col1:
            amount = st.number_input(
                "💰 Amount (₹)*",
                min_value=0.01, step=10.0,
                value=float(existing["amount"]) if existing else 10.0,
                format="%.2f"
            )
            category_display = st.selectbox(
                "📂 Category*",
                EXPENSE_CATEGORIES,
                index=_category_index(existing.get("category", "") if existing else "")
            )

        with col2:
            description = st.text_input(
                "📝 Description*",
                value=existing.get("description", "") if existing else "",
                placeholder="e.g. Lunch at restaurant"
            )
            expense_date = st.date_input(
                "📅 Date*",
                value=pd.to_datetime(existing["expense_date"]).date() if existing else date.today()
            )

        notes = st.text_area(
            "📌 Notes (optional)",
            value=existing.get("notes", "") if existing else "",
            placeholder="Any additional details...",
            height=80
        )

        col_a, col_b = st.columns(2)
        submitted = col_a.form_submit_button(
            "💾 Update Expense" if edit_id else "✅ Add Expense",
            use_container_width=True, type="primary"
        )
        cancel = col_b.form_submit_button("❌ Cancel", use_container_width=True)

    if cancel:
        st.session_state.edit_expense_id = None
        st.rerun()

    if submitted:
        # Strip emoji prefix before storing
        cat_clean = category_display.split(" ", 1)[1] if " " in category_display else category_display

        if not description.strip():
            st.error("Please enter a description.")
            return

        expense_data = {
            "amount": amount,
            "category": cat_clean,
            "description": description.strip(),
            "date": str(expense_date),
            "notes": notes.strip()
        }

        if edit_id:
            success = db_update_expense(edit_id, user_id, expense_data)
            if success:
                st.success("✅ Expense updated successfully!")
                st.session_state.edit_expense_id = None
                st.rerun()
            else:
                st.error("Failed to update expense. Please try again.")
        else:
            result = db_add_expense(user_id, expense_data)
            if result:
                st.success(f"✅ Added: {description} — {format_currency(amount)}")
                st.balloons()
            else:
                st.error("Failed to add expense. Please try again.")


def _category_index(category_name: str) -> int:
    """Find the index of a category in the EXPENSE_CATEGORIES list."""
    for i, cat in enumerate(EXPENSE_CATEGORIES):
        if category_name.lower() in cat.lower():
            return i
    return 0


# ── TAB: Expense List ──────────────────────────────────────────

def _tab_expense_list(user_id, curr_month, curr_year):
    """Searchable, filterable expense table with edit/delete."""
    st.subheader("📋 Expense History")

    # ── Filters ──
    fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 1])
    with fc1:
        search_q = st.text_input("🔍 Search", placeholder="Search description, category...")
    with fc2:
        filter_month = st.selectbox(
            "Month", ["All"] + [str(m) for m in range(1, 13)],
            index=curr_month
        )
    with fc3:
        filter_year = st.selectbox("Year", list(range(2022, curr_year + 1)), index=curr_year - 2022)
    with fc4:
        filter_cat = st.selectbox("Category", ["All"] + CATEGORY_NAMES)

    # Build filters dict
    filters = {"year": filter_year}
    if filter_month != "All":
        filters["month"] = int(filter_month)
    if filter_cat != "All":
        filters["category"] = filter_cat

    expenses = db_get_expenses(user_id, filters)
    df = expenses_to_dataframe(expenses)

    if search_q:
        df = search_expenses(df, search_q)

    if df.empty:
        st.info("📭 No expenses found for the selected filters.")
        return

    total = calculate_total(df)
    st.metric(f"Total ({len(df)} records)", format_currency(total))

    # ── Download button ──
    csv_bytes = dataframe_to_csv_bytes(df)
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv_bytes,
        file_name=f"expenses_{filter_year}_{filter_month}.csv",
        mime="text/csv"
    )

    st.divider()

    # ── Expense Rows ──
    for _, row in df.iterrows():
        exp_date = pd.to_datetime(row["expense_date"]).strftime("%b %d, %Y")
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 1, 1])
            c1.markdown(f"**{exp_date}**")
            c2.markdown(f"🏷️ {row.get('category', 'N/A')}")
            c3.markdown(f"{row.get('description', '')}")
            c4.markdown(f"**{format_currency(row['amount'])}**")

            with c5:
                edit_col, del_col = st.columns(2)
                if edit_col.button("✏️", key=f"edit_{row['id']}", help="Edit"):
                    st.session_state.edit_expense_id = str(row["id"])
                    st.rerun()
                if del_col.button("🗑️", key=f"del_{row['id']}", help="Delete"):
                    if db_delete_expense(str(row["id"]), user_id):
                        st.success("Deleted!")
                        st.rerun()

            if row.get("notes"):
                st.caption(f"📌 {row['notes']}")
            st.divider()


# ── TAB: Predictions ──────────────────────────────────────────

def _tab_predictions(user_id, email, username):
    """ML predictions and spending pattern insights."""
    st.subheader("🔮 AI-Powered Expense Predictions")
    st.info(
        "**How it works:** We use Polynomial Regression (a Machine Learning model) "
        "on your past monthly expense totals to predict future spending. "
        "More data = more accurate predictions!"
    )

    all_expenses = db_get_expenses(user_id)

    if len(all_expenses) < 5:
        st.warning("📊 Add more expenses (at least 5 records across 2+ months) for predictions to work.")
        return

    # Run ML model
    monthly_df   = prepare_monthly_data(all_expenses)
    ml_result    = train_and_predict(monthly_df, future_months=3)
    patterns     = detect_patterns(all_expenses)
    cat_preds    = predict_by_category(all_expenses)

    # ── Summary Metrics ──
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📈 Trend", ml_result["trend"])
    m2.metric("📊 Avg Monthly", format_currency(ml_result["avg_monthly"]))
    m3.metric("🎯 Model Accuracy", f"{ml_result['model_score']*100:.0f}%")
    m4.metric("🔬 Confidence", ml_result["confidence"])

    st.caption(ml_result["message"])
    st.divider()

    # ── Forecast Chart ──
    st.plotly_chart(
        prediction_chart(ml_result["historical"], ml_result["predictions"]),
        use_container_width=True
    )

    # ── Next 3 Months Table ──
    if not ml_result["predictions"].empty:
        st.subheader("📅 Next 3 Months Forecast")
        for _, row in ml_result["predictions"].iterrows():
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"**{row['month_label']}**")
            col2.markdown(f"**{format_currency(row['predicted_amount'])}**")

    st.divider()

    # ── Category-level predictions ──
    if cat_preds:
        st.subheader("📂 Category-Level Predictions (Next Month)")
        cols = st.columns(3)
        for i, (cat, amt) in enumerate(cat_preds.items()):
            cols[i % 3].metric(f"{cat}", format_currency(amt))

    # ── Spending Patterns ──
    if patterns["insights"]:
        st.subheader("💡 Spending Insights")
        for insight in patterns["insights"]:
            st.markdown(f"- {insight}")

    # ── Category trend chart ──
    st.plotly_chart(multi_line_category_trend(all_expenses), use_container_width=True)

    # ── Send prediction email ──
    st.divider()
    if st.button("📧 Email Prediction Report to Me", use_container_width=True):
        preds_list = ml_result["predictions"].to_dict("records") if not ml_result["predictions"].empty else []
        ok, msg = send_prediction_report(
            email, username,
            preds_list,
            ml_result["trend"],
            ml_result["avg_monthly"],
            patterns["insights"]
        )
        if ok:
            st.success("✅ Prediction report sent to your email!")
        else:
            st.error(f"Failed to send email: {msg}")


# ── TAB: Login History ────────────────────────────────────────

def _tab_login_history(user_id):
    """Show recent login sessions for security transparency."""
    st.subheader("🔐 Login History")
    st.caption("Recent logins to your account. Review for any suspicious activity.")

    history = db_get_login_history(user_id, limit=15)

    if not history:
        st.info("No login history found.")
        return

    for i, entry in enumerate(history):
        ts = entry.get("created_at", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts = dt.strftime("%B %d, %Y at %I:%M %p UTC")
            except Exception:
                pass

        with st.expander(f"🟢 Login #{i+1} — {ts}", expanded=(i == 0)):
            st.markdown(f"**Date/Time:** {ts}")
            st.markdown(f"**IP Address:** {entry.get('ip_address', 'N/A')}")
            st.markdown(f"**Device/Browser:** {entry.get('user_agent', 'N/A')[:120]}")


# ── TAB: Settings ─────────────────────────────────────────────

def _tab_settings(user_id, email, username, curr_month, curr_year):
    """Email reports, budget management, account info."""
    st.subheader("⚙️ Settings & Reports")

    # ── Account Info ──
    with st.expander("👤 Account Information"):
        st.markdown(f"**Username:** {username}")
        st.markdown(f"**Email:** {email}")
        st.markdown(f"**User ID:** `{user_id}`")

    # ── Send Monthly Summary ──
    st.subheader("📧 Email Reports")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 Monthly Summary Email**")
        selected_month = st.selectbox("Select Month", range(1, 13),
                                       format_func=month_name, index=curr_month - 1, key="sum_month")
        selected_year  = st.selectbox("Select Year",  list(range(2022, curr_year + 1)),
                                       index=curr_year - 2022, key="sum_year")

        if st.button("📤 Send Monthly Summary", use_container_width=True):
            expenses = db_get_expenses(user_id, {"month": selected_month, "year": selected_year})
            df = expenses_to_dataframe(expenses)
            total = calculate_total(df)
            cat_grouped = group_by_category(df)
            budget_rec = db_get_budget(user_id, selected_year, selected_month)
            budget = budget_rec["budget_amount"] if budget_rec else 0.0

            cat_dict = dict(zip(cat_grouped["category"], cat_grouped["amount"])) if not cat_grouped.empty else {}

            top_exp = None
            if expenses:
                top_exp = max(expenses, key=lambda e: float(e.get("amount", 0)))

            ok, msg = send_monthly_summary(
                email, username,
                month_name(selected_month), selected_year,
                total, budget, cat_dict, top_exp
            )
            if ok:
                st.success("✅ Monthly summary email sent!")
            else:
                st.error(f"Failed: {msg}")

    with col2:
        st.markdown("**🚨 Budget Alert Email**")
        expenses = db_get_expenses(user_id, {"month": curr_month, "year": curr_year})
        total = sum(float(e.get("amount", 0)) for e in expenses)
        budget_rec = db_get_budget(user_id, curr_year, curr_month)
        budget = budget_rec["budget_amount"] if budget_rec else 0.0
        _, _, pct = get_budget_status(total, budget)

        st.info(f"Current month: {format_currency(total)} spent, {pct:.1f}% of budget")

        if st.button("📤 Send Budget Alert Email", use_container_width=True):
            if budget <= 0:
                st.warning("Please set a monthly budget first (use the sidebar).")
            else:
                ok, msg = send_budget_alert(email, username, total, budget, pct)
                if ok:
                    st.success("✅ Budget alert email sent!")
                else:
                    st.error(f"Failed: {msg}")

    # ── SMTP Config Info ──
    with st.expander("📬 Email Configuration Help"):
        st.markdown("""
        **To enable email features:**
        1. Copy `.env.example` to `.env`
        2. Fill in your Gmail address and App Password
        3. For Gmail App Password: go to `myaccount.google.com → Security → App Passwords`
        4. Enable 2-Factor Authentication first
        5. Create an App Password for "Mail"
        6. Paste it as `SMTP_PASSWORD` in your `.env` file

        > ⚠️ Never commit your `.env` file to GitHub!
        """)
