# app/mailers/smtp_adapter.py
import smtplib, ssl
from email.message import EmailMessage
import logging
from ..config import settings

logger = logging.getLogger(__name__)

def _get_sender():
    sender_email = getattr(settings, "SMTP_FROM_EMAIL", None) or settings.SMTP_USER
    sender_name = getattr(settings, "SMTP_FROM_NAME", None) or ""
    return sender_email, sender_name

def _build_message(to_email: str, subject: str, html: str, text: str, request_id=None):
    sender_email, sender_name = _get_sender()
    msg = EmailMessage()
    if sender_name:
        msg['From'] = f"{sender_name} <{sender_email}>"
    else:
        msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    # prefer multipart: html + text
    if html:
        msg.set_content(text or " ")
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(text or "")
    # optional headers for traceability
    if request_id:
        msg['X-Request-ID'] = str(request_id)
    return msg

def send_email(to_email: str, subject: str, html: str, text: str, request_id=None):
    host = settings.SMTP_HOST
    port = int(settings.SMTP_PORT or 465)
    user = settings.SMTP_USER
    password = settings.SMTP_PASS

    if not (host and port and user and password):
        raise ValueError("SMTP settings missing. Check .env")

    msg = _build_message(to_email, subject, html, text, request_id=request_id)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(user, password)
            server.send_message(msg)
        logger.info("SMTP: sent mail to %s subj=%s", to_email, subject)
    except Exception as e:
        logger.exception("SMTP send failed for %s: %s", to_email, e)
        raise
