# Expense Tracker — Short Setup

What it is
| `app.py` | Entry point, page routing, home/login/register UI |
| `auth.py` | Password hashing, JWT create/verify, login/register logic |
| `database.py` | All Supabase CRUD operations (create, read, update, delete) |
| `dashboard.py` | Post-login UI: tabs, forms, tables, alerts |
| `ml_model.py` | scikit-learn regression, pattern detection |
| `charts.py` | Plotly figures: pie, bar, line, gauge, forecast |
| `email_service.py` | SMTP email sending with HTML templates |
| `utils.py` | Constants, formatters, DataFrame helpers |


## 🐛 Troubleshooting

**"Supabase credentials not found"**
→ Make sure `.env` file exists (not just `.env.example`) and has the correct values.

**"Authentication failed" for email**
→ You must use a Gmail App Password, not your regular password. Enable 2FA first.

**"relation 'users' does not exist"**
→ Run `supabase_setup.sql` in the Supabase SQL editor first.

**Charts not showing**
→ Add at least one expense. Charts need data to display.

**Predictions need more data**
→ Add expenses across at least 2-3 different months for ML to work.


## 📝 License

MIT License — Free to use for educational purposes.


## 👨‍💻 Built With ❤️ for Final Year Project

This project demonstrates:

# Expense Tracker

Simple app to track expenses, view charts, set budgets, and send email summaries.

Quick start
1. Install Python 3.10+.
2. Create & activate venv:
   - `python -m venv .venv`
   - PowerShell: `.\\.venv\\Scripts\\Activate.ps1`
3. Install deps: `python -m pip install -r requirements.txt` (or fallback: `python -m pip install streamlit supabase pandas`).
4. Copy `.env.example` → `.env` and fill `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `JWT_SECRET_KEY`, `SMTP_EMAIL`, `SMTP_PASSWORD` (Gmail App Password).
5. Run `supabase_setup.sql` in Supabase (SQL Editor).
6. Start: `python -m streamlit run app.py` → open `http://localhost:8501`.

Key files: `app.py`, `auth.py`, `database.py`, `dashboard.py`, `email_service.py`.

Need anything else? (sample data script, troubleshooting notes, or keep this as-is)
