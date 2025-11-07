from apscheduler.schedulers.background import BackgroundScheduler
from .db import SessionLocal
from .models import AccessRequest, ApprovalToken, RequestStatus
from .tokens import create_token_jti
from .mailer import render_email_template, send_email, log_audit
from .config import settings
import datetime
import urllib.parse

scheduler = BackgroundScheduler()

def send_initial_email(request_id: str, approver_email: str, approver_name: str = None):
    db = SessionLocal()
    try:
        req = db.query(AccessRequest).filter_by(id=request_id).first()
        if not req:
            return
        approve_token = create_token_jti(request_id, "approve")
        reject_token = create_token_jti(request_id, "reject")
        approve_url = f"{settings.APP_BASE}/callback?token={urllib.parse.quote_plus(approve_token)}"
        reject_url = f"{settings.APP_BASE}/callback?token={urllib.parse.quote_plus(reject_token)}"
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.TOKEN_EXPIRY_SECONDS)).isoformat()
        html = render_email_template("approve_email.html",
                                    approver_name=approver_name,
                                    requester_email=req.requester_email,
                                    requested_role=req.requested_role,
                                    approve_url=approve_url,
                                    reject_url=reject_url,
                                    expiry_date=expiry)
        text = render_email_template("approve_email.txt",
                                    approver_name=approver_name,
                                    requester_email=req.requester_email,
                                    requested_role=req.requested_role,
                                    approve_url=approve_url,
                                    reject_url=reject_url,
                                    expiry_date=expiry)
        send_email(approver_email, f"[Action Required] Access request for {req.requester_email}", html, text, request_id=req.id)
        req.last_notified_at = datetime.datetime.utcnow()
        req.notify_count = (req.notify_count or 0) + 1
        db.commit()
    except Exception as e:
        db.rollback()
        log_audit(request_id, actor="system", action="send_email_failed", meta=str(e))
        raise
    finally:
        db.close()

def reminder_check():
    db = SessionLocal()
    try:
        threshold = datetime.datetime.utcnow() - datetime.timedelta(hours=settings.REMINDER_HOURS)
        pendings = db.query(AccessRequest).filter(AccessRequest.status == RequestStatus.pending, AccessRequest.created_at <= threshold).all()
        for r in pendings:
            # simplistic: send to same approver email (in prod, store approver list)
            # avoid spamming: only if last_notified_at is None or older than reminder interval
            if not r.last_notified_at or (datetime.datetime.utcnow() - r.last_notified_at).total_seconds() > settings.REMINDER_CHECK_INTERVAL_MINUTES*60:
                # pick approver - placeholder
                approver_email = "approver@example.com"
                send_initial_email(r.id, approver_email)
    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(reminder_check, 'interval', minutes=settings.REMINDER_CHECK_INTERVAL_MINUTES, id="reminder_check")
    scheduler.start()
