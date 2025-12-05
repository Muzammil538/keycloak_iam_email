from .db import SessionLocal
from .models import AuditLog
import logging
from .mailer_factory import get_mailer
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

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

def send_response_email(to_email: str, requested_role: str, status: str, request_id: str=None, approver_note: str=None):
    """
    Send a confirmation email to the requester notifying approve/reject.
    Uses the configured mailer backend via get_mailer().
    """
    mailer = get_mailer()
    subject = f"Your access request for {requested_role} has been {status}"
    ctx = {"requested_role": requested_role, "status": status, "approver_note": approver_note}
    html, text = _render_response_templates(ctx)
    try:
        mailer(to_email, subject, html, text, request_id=request_id)
        log_audit(request_id, actor="system", action=f"response_email_sent:{status}", meta=f"to={to_email}")
        logger.info("Response email (%s) sent to %s", status, to_email)
    except Exception as e:
        logger.exception("Failed to send response email to %s: %s", to_email, e)
        log_audit(request_id, actor="system", action=f"response_email_failed:{status}", meta=str(e))
