import smtplib, ssl
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .config import settings
from .mailer_utils import log_audit
import os, logging

logger = logging.getLogger(__name__)
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=select_autoescape(["html", "xml"])
)

def _render(template_name: str, **ctx):
    tpl = env.get_template(template_name)
    return tpl.render(**ctx)

def send_email(to_email: str, subject: str, html_body: str, text_body: str, request_id: str = None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)
        log_audit(request_id=request_id, actor=settings.SMTP_USER, action=f"email_sent:{subject}", meta=f"to={to_email}")
        logger.info("SMTP email sent to %s", to_email)
        return True
    except Exception as e:
        logger.exception("SMTP send failed: %s", e)
        log_audit(request_id=request_id, actor=settings.SMTP_USER, action="email_failed", meta=str(e))
        raise

