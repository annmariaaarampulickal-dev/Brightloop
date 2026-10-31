import logging
import smtplib
from email.message import EmailMessage

from . import config

log = logging.getLogger("emailer")

# Kept in memory so tests and demos can read what "was sent" without an SMTP server.
OUTBOX: list[dict] = []


def send_email(to: str, subject: str, body: str) -> None:
    OUTBOX.append({"to": to, "subject": subject, "body": body})
    del OUTBOX[:-200]
    if not config.SMTP_HOST:
        log.info("EMAIL to=%s subject=%s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_FROM, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as s:
            s.starttls()
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
    except Exception:  # never let a mail failure break an API call
        log.exception("Failed to send email to %s", to)
