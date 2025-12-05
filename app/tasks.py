from apscheduler.schedulers.background import BackgroundScheduler
from .db import SessionLocal
from .models import AccessRequest, RequestStatus
from .tokens import create_token_jti
from .mailer_factory import get_mailer
from .config import settings
import datetime, urllib.parse, logging, os
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

def _render_templates(ctx):
    here = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(here), autoescape=select_autoescape(["html"]))
    html = env.get_template("approve_email.html").render(**ctx)
    text = env.get_template("approve_email.txt").render(**ctx)
    return html, text

def send_initial_email(request_id: str, approver_email: str, approver_name: str = None):
    db = SessionLocal()
    try:
        req = db.query(AccessRequest).filter_by(id=request_id).first()
        if not req:
            return
        mailer = get_mailer()
        approve_token = create_token_jti(request_id, "approve")
        reject_token = create_token_jti(request_id, "reject")
        approve_url = f"{settings.APP_BASE}/callback?token={urllib.parse.quote_plus(approve_token)}"
        reject_url = f"{settings.APP_BASE}/callback?token={urllib.parse.quote_plus(reject_token)}"
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.TOKEN_EXPIRY_SECONDS)).isoformat()
        ctx = {"approver_name": approver_name, "requester_email": req.requester_email, "requested_role": req.requested_role, "approve_url": approve_url, "reject_url": reject_url, "expiry_date": expiry}
        html, text = _render_templates(ctx)
        mailer(approver_email, f"[Action Required] Access request for {req.requester_email}", html, text, request_id=req.id)
        req.last_notified_at = datetime.datetime.utcnow()
        req.notify_count = (req.notify_count or 0) + 1
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Failed to send initial email: %s", e)
    finally:
        db.close()

def reminder_check():
    db = SessionLocal()
    try:
        threshold = datetime.datetime.utcnow() - datetime.timedelta(hours=settings.REMINDER_HOURS)
        pendings = db.query(AccessRequest).filter(AccessRequest.status == RequestStatus.pending, AccessRequest.created_at <= threshold).all()
        for r in pendings:
            if not r.last_notified_at or (datetime.datetime.utcnow() - r.last_notified_at).total_seconds() > settings.REMINDER_CHECK_INTERVAL_MINUTES*60:
                approver_email = "approver@example.com"
                send_initial_email(r.id, approver_email)
    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(reminder_check, 'interval', minutes=settings.REMINDER_CHECK_INTERVAL_MINUTES, id="reminder_check")
    scheduler.start()

