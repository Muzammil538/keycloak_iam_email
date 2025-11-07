import smtplib, ssl
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .config import settings
from .db import SessionLocal
from .models import AuditLog
import datetime
import logging
import os

logger = logging.getLogger(__name__)
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=select_autoescape(["html", "xml"])
)

def send_email(to_email: str, subject: str, html_body: str, text_body: str, request_id: str = None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)
        log_audit(request_id, actor=settings.SMTP_USER, action=f"email_sent:{subject}", meta=f"to={to_email}")
        logger.info("Email sent to %s", to_email)
        return True
    except Exception as e:
        logger.exception("Email send failed: %s", e)
        log_audit(request_id, actor=settings.SMTP_USER, action="email_failed", meta=str(e))
        raise

def render_email_template(template_name: str, **ctx):
    tpl = env.get_template(template_name)
    return tpl.render(**ctx)

def log_audit(request_id, actor, action, meta=None, ip=None, user_agent=None):
    db = SessionLocal()
    try:
        rec = AuditLog(request_id=request_id, actor=actor, action=action, ip=ip or "", user_agent=user_agent or "", meta=str(meta))
        db.add(rec)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
