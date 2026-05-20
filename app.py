# ============================================================
# app.py — Main Streamlit Application Entry Point
# ============================================================
# Run with:  streamlit run app.py
#
# This file:
#   1. Configures the Streamlit page
#   2. Initialises session state
#   3. Routes between: Home Page → Login/Register → Dashboard
# ============================================================

import streamlit as st

# ── Page Configuration (must be the FIRST Streamlit command!) ──
st.set_page_config(
    page_title="💰 Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com",
        "Report a bug": None,
        "About": "# Expense Tracker\nBuilt with Streamlit + Supabase + ML"
    }
)

# Import our modules after page config
from auth import init_session_state, is_authenticated, register_user, login_user, set_session
from dashboard import render_dashboard


# ── Initialise session on every run ────────────────────────────
init_session_state()


# ═══════════════════════════════════════════════════════════════
#  HOME PAGE
# ═══════════════════════════════════════════════════════════════

def render_home():
    """
    The landing page shown to users who are NOT logged in.
    Explains the app and provides Login / Register buttons.
    """
    # ── Hero Section ──────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center; padding: 40px 20px 20px;">
            <h1 style="font-size:3rem; margin-bottom:0.2em">💰 Expense Tracker</h1>
            <p style="font-size:1.2rem; color:#666; margin:0 auto; max-width:600px">
                Take control of your finances with smart tracking, 
                AI-powered predictions, and beautiful analytics.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── CTA Buttons ───────────────────────────────────────────
    _, c1, c2, _ = st.columns([2, 1, 1, 2])
    with c1:
        if st.button("🚀 Get Started — Register", use_container_width=True, type="primary"):
            st.session_state.current_page = "register"
            st.rerun()
    with c2:
        if st.button("🔑 Login to Dashboard", use_container_width=True):
            st.session_state.current_page = "login"
            st.rerun()

    st.divider()

    # ── Feature Cards ─────────────────────────────────────────
    st.subheader("✨ What You Can Do")
    f1, f2, f3 = st.columns(3)

    with f1:
        st.markdown("""
        **📊 Track Expenses**
        - Add expenses with categories: Food, Travel, Shopping, Bills, Healthcare, Entertainment
        - Edit & delete anytime
        - Filter by month, year, category
        - Search across all records
        """)

    with f2:
        st.markdown("""
        **📈 Smart Analytics**
        - Interactive Plotly charts (pie, bar, line)
        - Month-over-month comparison
        - Daily spending trends
        - Category breakdown
        """)

    with f3:
        st.markdown("""
        **🔮 AI Predictions**
        - Machine Learning expense forecasts
        - 3-month spending predictions
        - Spending pattern detection
        - Category-level forecasting
        """)

    f4, f5, f6 = st.columns(3)

    with f4:
        st.markdown("""
        **🎯 Budget Management**
        - Set monthly budgets
        - Real-time usage gauge
        - Green alerts when on track
        - Red warnings when over budget
        """)

    with f5:
        st.markdown("""
        **📧 Email Notifications**
        - Monthly summary reports
        - Budget alert emails
        - Login security alerts
        - AI prediction reports
        """)

    with f6:
        st.markdown("""
        **🔐 Secure Authentication**
        - JWT token-based login
        - bcrypt password hashing
        - Login history tracking
        - Session management
        """)

    st.divider()

    # ── Tech Stack ────────────────────────────────────────────
    st.subheader("🛠️ Built With")
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.info("**Streamlit**\nPython UI")
    t2.info("**Supabase**\nCloud DB & Auth")
    t3.info("**Plotly**\nInteractive Charts")
    t4.info("**scikit-learn**\nML Predictions")
    t5.info("**JWT + bcrypt**\nSecurity")


# ═══════════════════════════════════════════════════════════════
#  LOGIN PAGE
# ═══════════════════════════════════════════════════════════════

def render_login():
    """Login form with email + password."""
    st.markdown("<h2 style='text-align:center'>🔑 Login to Your Account</h2>", unsafe_allow_html=True)

    _, form_col, _ = st.columns([1, 2, 1])

    with form_col:
        with st.form("login_form"):
            st.markdown("#### Enter your credentials")
            email    = st.text_input("📧 Email Address", placeholder="you@example.com")
            password = st.text_input("🔒 Password", type="password", placeholder="Your password")

            col1, col2 = st.columns(2)
            submitted = col1.form_submit_button("🚀 Login", use_container_width=True, type="primary")
            go_reg    = col2.form_submit_button("Register Instead", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please fill in both fields.")
            else:
                with st.spinner("Logging in..."):
                    user_agent = "Streamlit Browser Session"
                    success, message, user_data = login_user(email, password, user_agent)

                if success:
                    set_session(user_data)
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        if go_reg:
            st.session_state.current_page = "register"
            st.rerun()

        st.divider()
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()


# ═══════════════════════════════════════════════════════════════
#  REGISTER PAGE
# ═══════════════════════════════════════════════════════════════

def render_register():
    """Registration form for new users."""
    st.markdown("<h2 style='text-align:center'>🎉 Create Your Account</h2>", unsafe_allow_html=True)

    _, form_col, _ = st.columns([1, 2, 1])

    with form_col:
        with st.form("register_form"):
            st.markdown("#### Fill in your details")
            username  = st.text_input("👤 Username", placeholder="e.g. john_doe")
            email     = st.text_input("📧 Email Address", placeholder="you@example.com")
            password  = st.text_input(
                "🔒 Password (min 8 characters)", type="password", placeholder="Strong password"
            )
            password2 = st.text_input(
                "🔒 Confirm Password", type="password", placeholder="Repeat your password"
            )

            col1, col2 = st.columns(2)
            submitted = col1.form_submit_button("✅ Create Account", use_container_width=True, type="primary")
            go_login  = col2.form_submit_button("Login Instead", use_container_width=True)

        if submitted:
            if not all([username, email, password, password2]):
                st.error("Please fill in all fields.")
            elif password != password2:
                st.error("Passwords don't match!")
            else:
                with st.spinner("Creating account..."):
                    success, message = register_user(email, username, password)

                if success:
                    st.success(message)
                    st.info("👇 Click 'Login Instead' to sign in with your new account.")
                else:
                    st.error(message)

        if go_login:
            st.session_state.current_page = "login"
            st.rerun()

        st.divider()
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()


# ═══════════════════════════════════════════════════════════════
#  ROUTER — Decide which page to show
# ═══════════════════════════════════════════════════════════════

def main():
    """
    Main router function.
    Checks authentication state and current_page to decide
    which screen to render.
    """
    # If user is already authenticated, always show dashboard
    if is_authenticated():
        render_dashboard()
        return

    # Otherwise route based on current_page in session state
    page = st.session_state.get("current_page", "home")

    if page == "login":
        render_login()
    elif page == "register":
        render_register()
    else:
        render_home()


# ── Run ────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
else:
    # Streamlit calls the script directly, so we need to call main()
    # at module level too
    main()
