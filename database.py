# ============================================================
# database.py — Supabase Database Operations
# ============================================================
# This module handles ALL interactions with the Supabase database.
# Think of Supabase as a cloud-hosted PostgreSQL database with a
# simple Python SDK. Each function here does ONE thing clearly.
# ============================================================

import os
import inspect
from pathlib import Path
import httpx
from dotenv import load_dotenv
import streamlit as st


# -----------------------------------------------------------------
# Compatibility shim
# -----------------------------------------------------------------
# Some versions of `gotrue` pass `proxy=` into httpx.Client, while the
# installed httpx build expects `proxies=`. Normalize that here so the
# app can connect without a version conflict.
if "proxy" not in inspect.signature(httpx.Client.__init__).parameters:
    _httpx_client_init = httpx.Client.__init__

    def _patched_httpx_client_init(self, *args, proxy=None, proxies=None, **kwargs):
        if proxies is None and proxy is not None:
            proxies = proxy
        return _httpx_client_init(self, *args, proxies=proxies, **kwargs)

    httpx.Client.__init__ = _patched_httpx_client_init

if "proxy" not in inspect.signature(httpx.AsyncClient.__init__).parameters:
    _httpx_async_client_init = httpx.AsyncClient.__init__

    def _patched_httpx_async_client_init(self, *args, proxy=None, proxies=None, **kwargs):
        if proxies is None and proxy is not None:
            proxies = proxy
        return _httpx_async_client_init(self, *args, proxies=proxies, **kwargs)

    httpx.AsyncClient.__init__ = _patched_httpx_async_client_init

from supabase import create_client, Client

# Load environment variables from the .env file next to this module
load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

# ── Helper: get or cache the Supabase client ─────────────────
@st.cache_resource
def get_supabase_client() -> Client:
    """
    Creates and returns a Supabase client.
    @st.cache_resource means it's only created ONCE per session
    (avoids creating a new connection on every page rerender).
    """
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_ANON_KEY") or "").strip()

    if not url or not key:
        st.error(
            "❌ Supabase credentials not found! "
            "Please copy .env.example → .env and fill in your values."
        )
        st.stop()

    try:
        client = create_client(url, key)
        return client
    except Exception as e:
        st.error(f"❌ Failed to connect to Supabase: {e}")
        st.stop()


# ── USER OPERATIONS ──────────────────────────────────────────

def db_create_user(email: str, username: str, hashed_password: str) -> dict | None:
    """
    Insert a new user row into the 'users' table.
    Returns the created user dict or None on failure.
    """
    client = get_supabase_client()
    try:
        response = client.table("users").insert({
            "email": email,
            "username": username,
            "password_hash": hashed_password
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        # Duplicate email raises a unique-constraint error
        raise e


def db_get_user_by_email(email: str) -> dict | None:
    """
    Fetch a single user row by email address.
    Returns user dict or None if not found.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("users")
            .select("*")
            .eq("email", email)
            .single()
            .execute()
        )
        return response.data
    except Exception:
        return None


def db_get_user_by_id(user_id: str) -> dict | None:
    """Fetch a single user row by their UUID."""
    client = get_supabase_client()
    try:
        response = (
            client.table("users")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return response.data
    except Exception:
        return None


def db_update_user_profile(user_id: str, updates: dict) -> bool:
    """Update fields on a user row. Returns True on success."""
    client = get_supabase_client()
    try:
        client.table("users").update(updates).eq("id", user_id).execute()
        return True
    except Exception as e:
        st.error(f"Profile update failed: {e}")
        return False


# ── LOGIN HISTORY OPERATIONS ─────────────────────────────────

def db_log_login(user_id: str, ip_address: str, user_agent: str) -> None:
    """
    Record a login event in the 'login_history' table.
    Stores timestamp, IP, and browser/device info.
    """
    client = get_supabase_client()
    try:
        client.table("login_history").insert({
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent
        }).execute()
    except Exception as e:
        # Non-critical: don't block login if logging fails
        print(f"[WARN] Failed to log login event: {e}")


def db_get_login_history(user_id: str, limit: int = 10) -> list[dict]:
    """
    Retrieve the N most recent login events for a user.
    Returns a list of login history dicts.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("login_history")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[ERROR] Fetching login history: {e}")
        return []


# ── EXPENSE OPERATIONS ────────────────────────────────────────

def db_add_expense(user_id: str, expense: dict) -> dict | None:
    """
    Insert a new expense row.
    expense dict should contain: amount, category, description, date, notes
    Returns the created expense dict.
    """
    client = get_supabase_client()
    try:
        response = client.table("expenses").insert({
            "user_id": user_id,
            "amount": float(expense["amount"]),
            "category": expense["category"],
            "description": expense["description"],
            "expense_date": str(expense["date"]),
            "notes": expense.get("notes", "")
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        raise e


def db_get_expenses(user_id: str, filters: dict = None) -> list[dict]:
    """
    Fetch all expenses for a user, with optional filters.
    filters can include: month (1-12), year, category, search_text
    Returns a list sorted by date descending.
    """
    client = get_supabase_client()
    try:
        query = client.table("expenses").select("*").eq("user_id", user_id)

        # Apply optional filters
        if filters:
            if filters.get("year"):
                # Filter by year using date range
                year = filters["year"]
                query = query.gte("expense_date", f"{year}-01-01")
                query = query.lte("expense_date", f"{year}-12-31")

            if filters.get("month"):
                month = str(filters["month"]).zfill(2)
                year = filters.get("year", 2024)
                # Get last day of month
                import calendar
                last_day = calendar.monthrange(year, int(filters["month"]))[1]
                query = query.gte("expense_date", f"{year}-{month}-01")
                query = query.lte("expense_date", f"{year}-{month}-{last_day}")

            if filters.get("category") and filters["category"] != "All":
                query = query.eq("category", filters["category"])

        response = query.order("expense_date", desc=True).execute()
        return response.data or []
    except Exception as e:
        print(f"[ERROR] Fetching expenses: {e}")
        return []


def db_update_expense(expense_id: str, user_id: str, updates: dict) -> bool:
    """
    Update an expense row by its ID.
    Also checks user_id to prevent editing other users' data (security).
    Returns True on success.
    """
    client = get_supabase_client()
    try:
        if "amount" in updates:
            updates["amount"] = float(updates["amount"])
        if "date" in updates:
            updates["expense_date"] = str(updates.pop("date"))

        client.table("expenses").update(updates)\
            .eq("id", expense_id)\
            .eq("user_id", user_id)\
            .execute()
        return True
    except Exception as e:
        print(f"[ERROR] Updating expense: {e}")
        return False


def db_delete_expense(expense_id: str, user_id: str) -> bool:
    """
    Delete an expense row by ID.
    The user_id check ensures users can only delete their own expenses.
    """
    client = get_supabase_client()
    try:
        client.table("expenses")\
            .delete()\
            .eq("id", expense_id)\
            .eq("user_id", user_id)\
            .execute()
        return True
    except Exception as e:
        print(f"[ERROR] Deleting expense: {e}")
        return False


# ── BUDGET OPERATIONS ─────────────────────────────────────────

def db_get_budget(user_id: str, year: int, month: int) -> dict | None:
    """
    Fetch the budget setting for a specific month/year.
    Returns budget dict or None if not set.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("budgets")
            .select("*")
            .eq("user_id", user_id)
            .eq("year", year)
            .eq("month", month)
            .single()
            .execute()
        )
        return response.data
    except Exception:
        return None


def db_set_budget(user_id: str, year: int, month: int, amount: float) -> bool:
    """
    Upsert (insert or update) a monthly budget.
    If a budget already exists for that month, it gets updated.
    """
    client = get_supabase_client()
    try:
        client.table("budgets").upsert({
            "user_id": user_id,
            "year": year,
            "month": month,
            "budget_amount": float(amount)
        }, on_conflict="user_id,year,month").execute()
        return True
    except Exception as e:
        print(f"[ERROR] Setting budget: {e}")
        return False


def db_get_all_budgets(user_id: str) -> list[dict]:
    """Get all budget records for a user (used for ML predictions)."""
    client = get_supabase_client()
    try:
        response = (
            client.table("budgets")
            .select("*")
            .eq("user_id", user_id)
            .order("year", desc=False)
            .order("month", desc=False)
            .execute()
        )
        return response.data or []
    except Exception:
        return []
