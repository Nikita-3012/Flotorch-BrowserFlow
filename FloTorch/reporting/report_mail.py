"""Optional SMTP delivery of the saved scenario report file."""

from __future__ import annotations

import html
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from FloTorch.config.providers import env


def _truthy(key: str, default: bool = False) -> bool:
    raw = env(key)
    if not raw:
        return default
    return raw.lower() in ("1", "true", "yes", "on")


def maybe_send_report_email(
    report_path: str | Path,
    *,
    run_id: str,
    mail_subject: str | None = None,
    html_body: str | None = None,
) -> None:
    """
    If SMTP_HOST and SMTP_TO are set, send `report_path` as text/plain attachment.

    If `html_body` is provided, it is used as the HTML alternative of the email
    (so the body renders as a styled table rather than monospace text). The plain
    text body is still set from the report file for clients that prefer text.

    Environment:
      SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD
      SMTP_FROM (defaults to SMTP_USER if set)
      SMTP_TO — comma-separated recipient addresses
      SMTP_SSL — use implicit TLS (typical for port 465); default true if port is 465
      SMTP_STARTTLS — use STARTTLS after connect (typical for 587); default true unless SMTP_SSL
    """
    host = env("SMTP_HOST")
    to_raw = env("SMTP_TO")
    if not host or not to_raw:
        print("Email: report not mailed (set SMTP_HOST and SMTP_TO to enable).")
        return

    path = Path(report_path)
    if not path.is_file():
        print(f"Email: skipped — report file missing: {path}")
        return

    port_str = env("SMTP_PORT")
    port = int(port_str) if port_str else 587
    user = env("SMTP_USER")
    password = env("SMTP_PASSWORD")
    from_addr = env("SMTP_FROM") or user
    if not from_addr:
        print("Email: skipped — set SMTP_FROM or SMTP_USER.")
        return

    recipients = [a.strip() for a in to_raw.split(",") if a.strip()]
    if not recipients:
        print("Email: skipped — SMTP_TO has no addresses.")
        return

    if env("SMTP_SSL"):
        use_ssl = _truthy("SMTP_SSL")
    else:
        use_ssl = port == 465
    use_starttls = not use_ssl and _truthy("SMTP_STARTTLS", default=True)

    subject = mail_subject or f"Scenario report [{run_id}]"
    report_text = path.read_text(encoding="utf-8")

    intro = f"Automation run {run_id} finished.\n\n"
    intro += f"Full report below (same text as attachment {path.name}).\n\n"
    intro += "─" * 60 + "\n\n"
    plain_body = intro + report_text

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)
    msg.set_content(plain_body, charset="utf-8")

    if html_body:
        html_alt = html_body
    else:
        escaped = html.escape(report_text, quote=True)
        html_alt = (
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body>"
            f"<p>{html.escape(intro.strip(), quote=True).replace(chr(10), '<br/>')}</p>"
            "<hr/><pre style=\"white-space:pre-wrap;font-family:Consolas,Monaco,monospace;"
            "font-size:13px;line-height:1.45;background:#f6f8fa;padding:12px;border-radius:6px;\">"
            f"{escaped}</pre>"
            "</body></html>"
        )
    msg.add_alternative(html_alt, subtype="html")

    data = path.read_bytes()
    msg.add_attachment(
        data,
        maintype="text",
        subtype="plain",
        filename=path.name,
    )

    context = ssl.create_default_context()

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, context=context) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=60) as smtp:
                smtp.ehlo()
                if use_starttls:
                    smtp.starttls(context=context)
                    smtp.ehlo()
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
    except OSError as e:
        print(f"Email: failed ({type(e).__name__}: {e})")
        return
    except smtplib.SMTPException as e:
        print(f"Email: SMTP error ({e})")
        return

    print(f"Email: sent report to {', '.join(recipients)}")
