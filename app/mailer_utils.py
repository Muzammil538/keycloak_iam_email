from .db import SessionLocal
from .models import AuditLog
import logging
from .mailer_factory import get_mailer
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .config import settings


logger = logging.getLogger(__name__)

def log_audit(request_id, actor, action, meta=None, ip=None, user_agent=None):
    db = SessionLocal()
    try:
        rec = AuditLog(request_id=request_id, actor=actor, action=action, ip=ip or "", user_agent=user_agent or "", meta=str(meta))
        db.add(rec)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to write audit log")
    finally:
        db.close()

def _render_response_templates(ctx):
    here = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(here), autoescape=select_autoescape(["html"]))
    html = env.get_template("response_email.html").render(**ctx)
    text = env.get_template("response_email.txt").render(**ctx)
    return html, text



def send_response_email(to_email, requested_role, status, request_id=None):
    subject = f"Your access request was {status}"
    text = f"Your request for role '{requested_role}' has been {status}."
    html = f"<p>{text}</p>"

    try:
        if settings.MAILER_BACKEND == "smtp":
            from .mailers.smtp_adapter import send_email as mailer
        else:
            from .mailers.mailersend_adapter import send_email as mailer
        mailer(to_email, subject, html, text, request_id=request_id)
        from .mailer_utils import log_audit
        log_audit(request_id=request_id, actor="system", action=f"response_email_{status}", meta=f"to={to_email}")
    except Exception as e:
        logger.exception("Failed to send response email to %s: %s", to_email, e)
