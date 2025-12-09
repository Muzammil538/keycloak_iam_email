from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from .config import settings
from .db import create_tables, SessionLocal
from .schemas import CreateRequest, CreateResponse
from .models import AccessRequest, RequestStatus
from .tasks import start_scheduler, send_initial_email
from .tokens import validate_token_no_mark, mark_token_used
from .mailer_utils import log_audit
from .keyclock_client import KeycloakClient
import uvicorn, logging
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import datetime
import hmac, hashlib, base64
from fastapi import Header, Request
from .models import InboundEmail
from .config import settings
import json

logger = logging.getLogger(__name__)

app = FastAPI(title="Keycloak Email Approval")

# helper to load templates directory
_templates_dir = os.path.join(os.path.dirname(__file__), "templates")
_jinja_env = Environment(loader=FileSystemLoader(_templates_dir), autoescape=select_autoescape(["html", "xml"]))

def _verify_mailersend_signature(secret: str, raw_body: bytes, signature_header: str) -> bool:
    """
    MailerSend includes a Signature header when calling webhooks.
    The header contains an HMAC (sha256) of the raw body using the webhook signing secret.
    We'll compute HMAC-SHA256 and compare. Accepts hex or base64 encodings for safety.
    """
    if not secret:
        return False

    # compute HMAC-SHA256 (raw bytes)
    computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    # header might be hex or base64. Try both.
    try:
        # common: hex string
        if signature_header.lower() == computed.hex():
            return True
    except Exception:
        pass

    try:
        # header could be base64
        if signature_header == base64.b64encode(computed).decode("utf-8"):
            return True
    except Exception:
        pass

    # fallback: constant-time compare against hex representation too
    try:
        return hmac.compare_digest(signature_header, computed.hex())
    except Exception:
        return False

@app.on_event("startup")
def startup():
    create_tables()
    start_scheduler()
    logger.info("App started and scheduler launched")

@app.post("/api/v1/requests", response_model=CreateResponse)
def create_request(payload: CreateRequest):
    db = SessionLocal()
    try:
        req = AccessRequest(
            keycloak_user_id=payload.keycloak_user_id,
            requester_email=payload.requester_email,
            requested_role=payload.requested_role,
            meta=str(payload.metadata),
            status=RequestStatus.pending
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        approver_email = "approver@example.com"
        send_initial_email(req.id, approver_email)
        log_audit(req.id, actor="system", action="request_created", meta=str(payload.dict()))
        return CreateResponse(request_id=req.id, status=req.status.value)
    finally:
        db.close()

@app.get("/callback", response_class=HTMLResponse)
def callback(token: str = None, request: Request = None):
    if not token:
        raise HTTPException(400, "missing token")
    payload, err = validate_token_no_mark(token)
    if err:
        raise HTTPException(400, f"token error: {err}")
    request_id = payload.get("request_id")
    jti = payload.get("jti")
    action = payload.get("action")
    db = SessionLocal()
    try:
        req = db.query(AccessRequest).filter_by(id=request_id).first()
        if not req:
            raise HTTPException(404, "request not found")
        if req.status != RequestStatus.pending:
            return HTMLResponse(f"<h3>Request already {req.status.value}</h3>")

        # perform Keycloak operation, then mark token used
        if action == "approve":
            kc = KeycloakClient()
            kc.assign_realm_role(req.keycloak_user_id, req.requested_role)
            req.status = RequestStatus.approved
            log_audit(request_id, actor="approver", action="approved", ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
            status_str = "approved"
        else:
            req.status = RequestStatus.rejected
            log_audit(request_id, actor="approver", action="rejected", ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
            status_str = "rejected"

        db.commit()
        # mark token used after success
        from .tokens import mark_token_used
        mark_token_used(jti)

        # Send confirmation email to requester
        try:
            from .mailer_utils import send_response_email
            if req.requester_email:
                send_response_email(to_email=req.requester_email, requested_role=req.requested_role, status=status_str, request_id=req.id)
        except Exception:
            # we already logged inside send_response_email; do not fail the callback
            pass

        return HTMLResponse(f"<h3>Request {req.status.value}</h3>")
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"error processing request: {e}")
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/admin/requests", response_class=HTMLResponse)
def admin_list():
    """Render inbox of requests"""
    db = SessionLocal()
    try:
        reqs = db.query(AccessRequest).order_by(AccessRequest.created_at.desc()).all()
        # convert to simple dicts or pass objects; Jinja can access attributes
        html = _jinja_env.get_template("admin_list.html").render(requests=reqs)
        return HTMLResponse(html)
    finally:
        db.close()

@app.get("/admin/requests/{request_id}", response_class=HTMLResponse)
def admin_view(request_id: str):
    """Render a single request with full email HTML embedded"""
    db = SessionLocal()
    try:
        req = db.query(AccessRequest).filter_by(id=request_id).first()
        if not req:
            raise HTTPException(404, "request not found")
        # Build email HTML as the same as send_initial_email would produce (fresh tokens not needed)
        # We can re-create the original email content with approve/reject links (new tokens)
        from .tokens import create_token_jti
        approve_token = create_token_jti(req.id, "approve")
        reject_token = create_token_jti(req.id, "reject")
        approve_url = f"{settings.APP_BASE}/callback?token={approve_token}"
        reject_url = f"{settings.APP_BASE}/callback?token={reject_token}"
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.TOKEN_EXPIRY_SECONDS)).isoformat()
        ctx = {"approver_name": None, "requester_email": req.requester_email, "requested_role": req.requested_role, "approve_url": approve_url, "reject_url": reject_url, "expiry_date": expiry}
        email_html = _jinja_env.get_template("approve_email.html").render(**ctx)
        html = _jinja_env.get_template("admin_view.html").render(req=req, email_html=email_html)
        return HTMLResponse(html)
    finally:
        db.close()

@app.post("/admin/requests/{request_id}/action")
async def admin_action(request_id: str, payload: dict = None, request: Request = None):
    """
    Perform approve/reject action from admin UI.
    payload = {"action": "approve" or "reject"}
    """
    db = SessionLocal()
    try:
        req = db.query(AccessRequest).filter_by(id=request_id).first()
        if not req:
            return HTMLResponse("not found", status_code=404)
        if req.status != RequestStatus.pending:
            return {"ok": False, "message": "already acted", "status": req.status.value}

        body = None
        if payload is None:
            try:
                body = await request.json()
            except Exception:
                body = {}
        else:
            body = payload

        action = body.get("action")
        if action not in ("approve", "reject"):
            return HTMLResponse("invalid action", status_code=400)

        # perform Keycloak action if approve
        if action == "approve":
            try:
                kc = KeycloakClient()
                kc.assign_realm_role(req.keycloak_user_id, req.requested_role)
                req.status = RequestStatus.approved
                log_audit(req.id, actor="admin", action="approved", ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
            except Exception as e:
                db.rollback()
                return HTMLResponse(f"Keycloak error: {e}", status_code=500)
        else:
            req.status = RequestStatus.rejected
            log_audit(req.id, actor="admin", action="rejected", ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))

        db.commit()

        # mark any existing tokens for this request as used (optional safety)
        try:
            from .db import SessionLocal as _SL
            s2 = _SL()
            from .models import ApprovalToken
            toks = s2.query(ApprovalToken).filter(ApprovalToken.request_id == req.id, ApprovalToken.used_at == None).all()
            for t in toks:
                t.used_at = datetime.datetime.utcnow()
            s2.commit()
            s2.close()
        except Exception:
            # non-fatal
            pass

        # send response email to requester
        try:
            from .mailer_utils import send_response_email
            if req.requester_email:
                send_response_email(req.requester_email, req.requested_role, "approved" if action == "approve" else "rejected", request_id=req.id)
        except Exception:
            # ignore send failures, already logged inside send_response_email
            pass

        return {"ok": True, "status": req.status.value}
    finally:
        db.close()
        
        
        
@app.get("/", response_class=HTMLResponse)
def root():
    """
    Simple landing page with links to health, admin inbox and API docs.
    Useful for local demos so visiting '/' shows something friendly.
    """
    # Basic inline HTML — uses Tailwind CDN for quick nice look
    page = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <script src="https://cdn.tailwindcss.com"></script>
        <title>Keycloak Email Approval</title>
      </head>
      <body class="bg-gray-50 font-sans text-gray-800">
        <div class="max-w-3xl mx-auto py-16 px-6">
          <div class="bg-white p-8 rounded-lg shadow">
            <h1 class="text-2xl font-bold mb-2">Keycloak Email Approval System</h1>
            <p class="text-sm text-gray-600 mb-6">Simple demo page — use links below to navigate.</p>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <a href="/health" class="block p-4 bg-indigo-50 border rounded hover:bg-indigo-100 text-center">Health</a>
              <a href="/admin/requests" class="block p-4 bg-green-50 border rounded hover:bg-green-100 text-center">Admin Inbox</a>
              <a href="/docs" class="block p-4 bg-blue-50 border rounded hover:bg-blue-100 text-center">API Docs</a>
            </div>

            <div class="mt-6 text-xs text-gray-500">
              <p>Note: Admin pages are not protected by auth in this demo. For production, enable Keycloak auth.</p>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    # Escape nothing necessary here as content is static, but be safe
    return HTMLResponse(content=page)


@app.post("/webhook/mailersend/inbound")
async def mailersend_inbound(request: Request, signature: str = Header(None, convert_underscores=False)):
    """
    Endpoint to receive inbound emails forwarded by MailerSend inbound routing.
    MailerSend sends a JSON payload and sets a Signature header — validate it using
    MAILERSEND_INBOUND_SECRET (optional for dev/testing).
    """
    raw_body = await request.body()
    secret = settings.MAILERSEND_INBOUND_SECRET

    # verify signature only if secret is configured
    if secret:
        sig_header = signature or request.headers.get("Signature") or request.headers.get("signature")
        if not sig_header or not _verify_mailersend_signature(secret, raw_body, sig_header):
            return {"ok": False, "error": "invalid signature"}, 400

    try:
        payload = await request.json()
    except Exception:
        # if JSON parse fails, still save raw payload
        payload = None

    # Payload shape: MailerSend inbound JSON uses keys like "from", "to", "subject", "text", "html", "message_id".
    # Be defensive when extracting fields.
    mail_data = {}
    if isinstance(payload, dict):
        # Some payloads include top-level 'mail' object (depends on webhook type). Try common patterns.
        if "mail" in payload and isinstance(payload["mail"], dict):
            m = payload["mail"]
        else:
            m = payload

        # Try several likely keys
        mail_data["message_id"] = m.get("message_id") or m.get("Message-Id") or m.get("headers", {}).get("message-id")
        # 'from' may be dict or string
        frm = m.get("from") or {}
        if isinstance(frm, dict):
            mail_data["from_email"] = frm.get("email") or frm.get("address")
            mail_data["from_name"] = frm.get("name")
        else:
            # parse "Name <email@example.com>"
            mail_data["from_email"] = frm
            mail_data["from_name"] = None

        # recipients
        to_field = m.get("to") or m.get("recipients") or m.get("envelope", {}).get("to")
        if isinstance(to_field, list):
            mail_data["to_email"] = ",".join([ (t.get("email") if isinstance(t, dict) else t) for t in to_field ])
        else:
            mail_data["to_email"] = to_field

        mail_data["subject"] = m.get("subject") or m.get("headers", {}).get("subject")
        mail_data["text"] = m.get("text") or m.get("plain") or ""
        mail_data["html"] = m.get("html") or ""
    else:
        mail_data = {"message_id": None, "from_email": None, "from_name": None, "to_email": None, "subject": None, "text": None, "html": None}

    # Save into DB
    db = SessionLocal()
    try:
        rec = InboundEmail(
            message_id = mail_data.get("message_id"),
            from_email  = mail_data.get("from_email"),
            from_name   = mail_data.get("from_name"),
            to_email    = mail_data.get("to_email"),
            subject     = mail_data.get("subject"),
            text        = mail_data.get("text"),
            html        = mail_data.get("html"),
            raw_payload = json.dumps(payload) if payload is not None else raw_body.decode("utf-8", errors="ignore")
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

        # Optional: create an AccessRequest automatically when inbound email matches some pattern
        # e.g., if subject contains "Request access" or sender is a known user — implement here if desired.

        # Log audit
        from .mailer_utils import log_audit
        log_audit(request_id=None, actor="mailersend_inbound", action="inbound_received", meta=f"msg_id={rec.message_id}, from={rec.from_email}")

        return {"ok": True, "id": rec.id}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}, 500
    finally:
        db.close()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=False)

