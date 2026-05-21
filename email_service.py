# ============================================================
# email_service.py — SMTP Email Notification Service
# ============================================================
# Sends automated emails for:
#   • Login alerts (security notification)
#   • Monthly expense summaries
#   • Budget exceeded warnings
#   • ML prediction reports
#
# Uses Python's built-in smtplib — no extra library needed!
# ============================================================

import os
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

load_dotenv(dotenv_path=Path(__file__).with_name('.env'))


def _get_setting(name: str, default: str = "") -> str:
  """Read a setting from Streamlit secrets first, then environment variables."""
  try:
    if hasattr(st, "secrets") and name in st.secrets:
      value = st.secrets[name]
      return str(value).strip()
  except Exception:
    pass

  return str(os.getenv(name, default)).strip()

# ── SMTP Configuration ─────────────────────────────────────────
SMTP_SERVER = _get_setting("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(_get_setting("SMTP_PORT", "587"))
SMTP_EMAIL = _get_setting("SMTP_EMAIL")
SMTP_PASS = _get_setting("SMTP_PASSWORD")


# ── Core Send Function ─────────────────────────────────────────

def send_email(to_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    """
    Send an HTML email via SMTP (TLS).
    Returns (success: bool, message: str).

    HOW SMTP WORKS:
    1. Connect to mail server (e.g. smtp.gmail.com:587)
    2. Start TLS encryption (STARTTLS)
    3. Login with credentials
    4. Send the MIME message
    5. Disconnect

    For Gmail, you MUST use an App Password (not your real password).
    """
    if not SMTP_EMAIL or not SMTP_PASS:
      return False, "SMTP credentials not configured in .env file or Streamlit secrets."

    try:
        # Build the email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Expense Tracker <{SMTP_EMAIL}>"
        msg["To"]      = to_email

        # Attach the HTML part (email clients will display the HTML version)
        msg.attach(MIMEText(html_body, "html"))

        # Connect and send
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()          # Upgrade to encrypted connection
            server.login(SMTP_EMAIL, SMTP_PASS)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        return True, "Email sent successfully!"

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Authentication failed. For Gmail, ensure you're using an App Password. "
            "Go to: Google Account → Security → 2-Step Verification → App Passwords."
        )
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"


# ── Email Templates ────────────────────────────────────────────

def _base_html(title: str, content: str) -> str:
    """Wrap content in a clean, responsive HTML email template."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 30px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header p {{ margin: 8px 0 0; opacity: 0.85; font-size: 14px; }}
        .body {{ padding: 30px; color: #333; line-height: 1.6; }}
        .card {{ background: #f8f9fe; border-radius: 8px; padding: 16px 20px; margin: 12px 0; border-left: 4px solid #667eea; }}
        .stat {{ display: inline-block; text-align: center; padding: 12px 20px; background: #fff; border-radius: 8px; margin: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .stat .value {{ font-size: 22px; font-weight: bold; color: #667eea; }}
        .stat .label {{ font-size: 12px; color: #888; margin-top: 4px; }}
        .alert-success {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 12px 16px; border-radius: 8px; margin: 12px 0; }}
        .alert-warning {{ background: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 12px 16px; border-radius: 8px; margin: 12px 0; }}
        .alert-danger  {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 12px 16px; border-radius: 8px; margin: 12px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }}
        th {{ background: #667eea; color: #fff; padding: 10px 12px; text-align: left; }}
        td {{ padding: 9px 12px; border-bottom: 1px solid #eee; }}
        tr:last-child td {{ border-bottom: none; }}
        .footer {{ text-align: center; padding: 20px; color: #aaa; font-size: 12px; background: #f8f9fe; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>💰 Expense Tracker</h1>
          <p>{title}</p>
        </div>
        <div class="body">
          {content}
        </div>
        <div class="footer">
          This email was sent by your Expense Tracker app.<br>
          {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
        </div>
      </div>
    </body>
    </html>
    """


def send_login_alert(to_email: str, username: str, user_agent: str) -> tuple[bool, str]:
    """
    Send a security email when a new login is detected.
    Helps users spot unauthorised access.
    """
    content = f"""
    <p>Hi <strong>{username}</strong>,</p>
    <p>A new login to your Expense Tracker account was detected.</p>
    <div class="card">
      <strong>🕐 Time:</strong> {datetime.now().strftime("%B %d, %Y at %I:%M %p")}<br>
      <strong>🖥️ Device:</strong> {user_agent[:100]}
    </div>
    <p>If this was you, no action needed. If you didn't log in, please change your password immediately.</p>
    """
    html = _base_html("New Login Alert", content)
    return send_email(to_email, "🔐 New Login Detected — Expense Tracker", html)


def send_monthly_summary(
    to_email: str,
    username: str,
    month_name: str,
    year: int,
    total_spent: float,
    budget: float,
    category_breakdown: dict,
    top_expense: dict | None = None
) -> tuple[bool, str]:
    """
    Send a monthly expense summary email.
    category_breakdown: {category: amount}
    """
    budget_used_pct = (total_spent / budget * 100) if budget > 0 else 0
    remaining = budget - total_spent if budget > 0 else 0

    # Budget status box
    if budget <= 0:
        budget_box = '<div class="alert-warning">ℹ️ No budget was set for this month.</div>'
    elif total_spent <= budget:
        budget_box = f'<div class="alert-success">✅ You stayed within budget! Saved ₹{remaining:,.2f} ({100-budget_used_pct:.0f}% remaining)</div>'
    else:
        budget_box = f'<div class="alert-danger">🚨 You exceeded your budget by ₹{abs(remaining):,.2f} ({budget_used_pct-100:.0f}% over)</div>'

    # Category table
    cat_rows = "".join(
        f"<tr><td>{cat}</td><td>₹{amt:,.2f}</td><td>{(amt/total_spent*100):.1f}%</td></tr>"
        for cat, amt in sorted(category_breakdown.items(), key=lambda x: -x[1])
    ) if category_breakdown else "<tr><td colspan='3'>No categories</td></tr>"

    top_exp_html = ""
    if top_expense:
        top_exp_html = f"""
        <div class="card">
          <strong>🏆 Biggest Expense:</strong> {top_expense.get('description', 'N/A')}<br>
          <strong>Amount:</strong> ₹{top_expense.get('amount', 0):,.2f}<br>
          <strong>Category:</strong> {top_expense.get('category', 'N/A')}
        </div>
        """

    content = f"""
    <p>Hi <strong>{username}</strong>,</p>
    <p>Here's your expense summary for <strong>{month_name} {year}</strong>:</p>

    <div style="text-align:center; margin: 20px 0;">
      <div class="stat"><div class="value">₹{total_spent:,.2f}</div><div class="label">Total Spent</div></div>
      <div class="stat"><div class="value">₹{budget:,.2f}</div><div class="label">Budget</div></div>
      <div class="stat"><div class="value">{budget_used_pct:.0f}%</div><div class="label">Budget Used</div></div>
    </div>

    {budget_box}

    <h3 style="margin-top:24px">📊 Category Breakdown</h3>
    <table>
      <tr><th>Category</th><th>Amount</th><th>% of Total</th></tr>
      {cat_rows}
    </table>

    {top_exp_html}

    <p style="color:#888;font-size:13px;margin-top:20px">
      Log in to your Expense Tracker app for detailed charts and predictions.
    </p>
    """
    html = _base_html(f"Monthly Summary — {month_name} {year}", content)
    return send_email(
        to_email,
        f"📊 Monthly Summary: {month_name} {year} — ₹{total_spent:,.2f} spent",
        html
    )


def send_budget_alert(
    to_email: str,
    username: str,
    total_spent: float,
    budget: float,
    percentage: float
) -> tuple[bool, str]:
    """
    Send a warning email when spending exceeds 80% or 100% of budget.
    """
    if percentage >= 100:
        status = "exceeded"
        alert_class = "alert-danger"
        icon = "🚨"
        message = f"You've exceeded your monthly budget by ₹{total_spent - budget:,.2f}!"
    else:
        status = "near limit"
        alert_class = "alert-warning"
        icon = "⚠️"
        message = f"You've used {percentage:.0f}% of your monthly budget. Only ₹{budget - total_spent:,.2f} remaining!"

    content = f"""
    <p>Hi <strong>{username}</strong>,</p>
    <div class="{alert_class}">
      <strong>{icon} Budget Alert:</strong> {message}
    </div>
    <div class="card">
      <strong>💸 Amount Spent:</strong> ₹{total_spent:,.2f}<br>
      <strong>🎯 Monthly Budget:</strong> ₹{budget:,.2f}<br>
      <strong>📊 Usage:</strong> {percentage:.1f}%
    </div>
    <p>Log in to review your expenses and make adjustments.</p>
    """
    html = _base_html(f"Budget {status.title()} Alert", content)
    return send_email(
        to_email,
        f"{icon} Budget Alert — {percentage:.0f}% used",
        html
    )


def send_prediction_report(
    to_email: str,
    username: str,
    predictions: list[dict],
    trend: str,
    avg_monthly: float,
    insights: list[str]
) -> tuple[bool, str]:
    """
    Send an ML prediction report with next 3 months forecast.
    predictions: list of {month_label, predicted_amount}
    """
    pred_rows = "".join(
        f"<tr><td>{p['month_label']}</td><td>₹{p['predicted_amount']:,.2f}</td></tr>"
        for p in predictions
    )

    insights_html = "".join(f"<li>{i}</li>" for i in insights) if insights else "<li>No insights available.</li>"

    content = f"""
    <p>Hi <strong>{username}</strong>,</p>
    <p>Here is your personalized expense forecast based on your spending history:</p>

    <div class="card">
      <strong>📈 Spending Trend:</strong> {trend}<br>
      <strong>📊 Average Monthly Spend:</strong> ₹{avg_monthly:,.2f}
    </div>

    <h3>🔮 Next 3 Months Forecast</h3>
    <table>
      <tr><th>Month</th><th>Predicted Expense</th></tr>
      {pred_rows}
    </table>

    <h3>💡 Spending Insights</h3>
    <ul style="line-height:2">
      {insights_html}
    </ul>

    <p style="color:#888;font-size:13px;margin-top:20px">
      <em>⚠️ These are AI-powered predictions based on your past data. Actual spending may vary.</em>
    </p>
    """
    html = _base_html("Your Expense Forecast Report", content)
    return send_email(
        to_email,
        "🔮 Your Expense Prediction Report — Expense Tracker",
        html
    )
