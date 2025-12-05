import time, logging, requests
from typing import Optional
from ..config import settings
from ..mailer_utils import log_audit

logger = logging.getLogger(__name__)
MAILERSEND_API_URL = "https://api.mailersend.com/v1/email"
MAILERSEND_API_KEY = settings.MAILERSEND_API_KEY
MAILERSEND_FROM_EMAIL = settings.MAILERSEND_FROM_EMAIL
MAILERSEND_FROM_NAME = settings.MAILERSEND_FROM_NAME
MAILERSEND_MAX_RETRIES = settings.MAILERSEND_MAX_RETRIES
MAILERSEND_RETRY_BACKOFF = settings.MAILERSEND_RETRY_BACKOFF

if not MAILERSEND_API_KEY or not MAILERSEND_FROM_EMAIL:
    logger.warning("MailerSend not configured. Please set MAILERSEND_API_KEY and MAILERSEND_FROM_EMAIL")

def _build_payload(to_email: str, subject: str, html_body: str, text_body: str):
    return {
        "from": {"email": MAILERSEND_FROM_EMAIL, "name": MAILERSEND_FROM_NAME},
        "to": [{"email": to_email}],
        "subject": subject,
        "html": html_body,
        "text": text_body
    }

def send_email(to_email: str, subject: str, html_body: str, text_body: str, request_id: Optional[str] = None) -> bool:
    if not MAILERSEND_API_KEY:
        raise RuntimeError("MailerSend API key not configured")

    headers = {
        "Authorization": f"Bearer {MAILERSEND_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = _build_payload(to_email, subject, html_body, text_body)
    backoff = MAILERSEND_RETRY_BACKOFF

    for attempt in range(1, MAILERSEND_MAX_RETRIES + 1):
        try:
            resp = requests.post(MAILERSEND_API_URL, json=payload, headers=headers, timeout=10)
        except requests.RequestException as e:
            logger.warning("MailerSend exception (attempt %d): %s", attempt, e)
            if attempt == MAILERSEND_MAX_RETRIES:
                logger.exception("MailerSend failed permanently for %s", to_email)
                raise
            time.sleep(backoff ** attempt)
            continue

        if resp.status_code in (200, 202):
            log_audit(request_id=request_id, actor="mailersend", action=f"email_sent:{subject}", meta=f"to={to_email}")
            logger.info("MailerSend delivered email to %s", to_email)
            return True

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            sleep_for = float(retry_after) if retry_after else backoff ** attempt
            logger.warning("MailerSend rate limited (429). Sleeping %s secs", sleep_for)
            time.sleep(sleep_for)
            if attempt == MAILERSEND_MAX_RETRIES:
                logger.error("MailerSend rate-limit exhausted for %s", to_email)
                resp.raise_for_status()
            continue

        if 500 <= resp.status_code < 600:
            logger.warning("MailerSend server error %d (attempt %d)", resp.status_code, attempt)
            if attempt == MAILERSEND_MAX_RETRIES:
                logger.error("MailerSend permanent 5xx for %s", to_email)
                resp.raise_for_status()
            time.sleep(backoff ** attempt)
            continue

        logger.error("MailerSend permanent failure %d: %s", resp.status_code, resp.text)
        resp.raise_for_status()

    raise RuntimeError("MailerSend failed after retries")

