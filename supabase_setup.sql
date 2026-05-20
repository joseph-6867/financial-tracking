-- ============================================================
-- supabase_setup.sql — Database Schema for Expense Tracker
-- ============================================================
-- Run this entire file in:
--   Supabase Dashboard → SQL Editor → New Query → Paste → Run
--
-- Tables created:
--   1. users          — stores registered user accounts
--   2. login_history  — records every login event
--   3. expenses       — stores individual expense records
--   4. budgets        — stores monthly budget settings
-- ============================================================


-- ── 1. USERS TABLE ────────────────────────────────────────────
-- Stores registered accounts (separate from Supabase Auth)
-- We manage auth ourselves with JWT + bcrypt for learning purposes

CREATE TABLE IF NOT EXISTS public.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    username        TEXT NOT NULL,
    password_hash   TEXT NOT NULL,           -- bcrypt hash, NEVER plain text!
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast email lookups during login
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at ON public.users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── 2. LOGIN HISTORY TABLE ────────────────────────────────────
-- Records every successful login for security audit trail

CREATE TABLE IF NOT EXISTS public.login_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    ip_address  TEXT,
    user_agent  TEXT,                        -- browser/device info
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_history_user ON public.login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_time ON public.login_history(created_at DESC);


-- ── 3. EXPENSES TABLE ─────────────────────────────────────────
-- Stores individual expense records

CREATE TABLE IF NOT EXISTS public.expenses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    amount          DECIMAL(12, 2) NOT NULL CHECK (amount > 0),
    category        TEXT NOT NULL DEFAULT 'Other',
    description     TEXT NOT NULL,
    expense_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    notes           TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast filtering
CREATE INDEX IF NOT EXISTS idx_expenses_user       ON public.expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date       ON public.expenses(expense_date DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_category   ON public.expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_user_date  ON public.expenses(user_id, expense_date DESC);

DROP TRIGGER IF EXISTS expenses_updated_at ON public.expenses;
CREATE TRIGGER expenses_updated_at
    BEFORE UPDATE ON public.expenses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── 4. BUDGETS TABLE ──────────────────────────────────────────
-- Stores monthly budget limits per user

CREATE TABLE IF NOT EXISTS public.budgets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    budget_amount   DECIMAL(12, 2) NOT NULL DEFAULT 0 CHECK (budget_amount >= 0),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    -- One budget per user per month
    UNIQUE (user_id, year, month)
);

CREATE INDEX IF NOT EXISTS idx_budgets_user ON public.budgets(user_id);

DROP TRIGGER IF EXISTS budgets_updated_at ON public.budgets;
CREATE TRIGGER budgets_updated_at
    BEFORE UPDATE ON public.budgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── ROW LEVEL SECURITY (RLS) ──────────────────────────────────
-- RLS ensures users can ONLY read/write THEIR OWN data.
-- This is a critical security feature — without it, any user
-- could read everyone's expenses!
--
-- IMPORTANT: Since we use our own JWT (not Supabase Auth),
-- we use the service role key for operations, so RLS policies
-- should allow service role unrestricted access.
-- The application enforces user_id checks at the code level.

-- Enable RLS on all tables
ALTER TABLE public.users          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.login_history  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.expenses       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.budgets        ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (used by our Python app)
CREATE POLICY "service_role_users"         ON public.users         FOR ALL USING (true);
CREATE POLICY "service_role_login_history" ON public.login_history FOR ALL USING (true);
CREATE POLICY "service_role_expenses"      ON public.expenses       FOR ALL USING (true);
CREATE POLICY "service_role_budgets"       ON public.budgets        FOR ALL USING (true);


-- ── SAMPLE DATA (optional, for testing) ───────────────────────
-- Uncomment and run to insert demo data after creating a user account.
-- Replace 'YOUR-USER-UUID-HERE' with an actual user ID from your users table.

/*
INSERT INTO public.expenses (user_id, amount, category, description, expense_date, notes)
VALUES
  ('YOUR-USER-UUID-HERE', 450.00, 'Food',          'Grocery shopping',      '2024-12-01', 'Monthly groceries'),
  ('YOUR-USER-UUID-HERE', 1200.00, 'Bills',         'Electricity bill',      '2024-12-03', 'December electricity'),
  ('YOUR-USER-UUID-HERE', 350.00, 'Travel',         'Metro card recharge',   '2024-12-05', ''),
  ('YOUR-USER-UUID-HERE', 2500.00, 'Shopping',      'New headphones',        '2024-12-08', 'Sony WH-1000XM4'),
  ('YOUR-USER-UUID-HERE', 180.00, 'Entertainment',  'Movie tickets',         '2024-12-10', 'Weekend movie'),
  ('YOUR-USER-UUID-HERE', 650.00, 'Healthcare',     'Doctor consultation',   '2024-12-12', 'Annual checkup'),
  ('YOUR-USER-UUID-HERE', 320.00, 'Food',           'Restaurant dinner',     '2024-12-15', 'Birthday dinner'),
  ('YOUR-USER-UUID-HERE', 900.00, 'Bills',          'Internet bill',         '2024-12-18', 'Fibre broadband'),
  ('YOUR-USER-UUID-HERE', 1500.00, 'Shopping',      'Winter jacket',         '2024-12-20', 'H&M sale'),
  ('YOUR-USER-UUID-HERE', 280.00, 'Food',           'Coffee & snacks',       '2024-12-22', '');

INSERT INTO public.budgets (user_id, year, month, budget_amount)
VALUES ('YOUR-USER-UUID-HERE', 2024, 12, 10000.00);
*/


-- ── VERIFICATION QUERIES ──────────────────────────────────────
-- Run these to verify tables were created:

SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('users', 'login_history', 'expenses', 'budgets')
ORDER BY table_name, ordinal_position;
