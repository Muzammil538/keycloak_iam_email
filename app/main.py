from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from .config import settings
from .db import create_tables, SessionLocal
from .schemas import CreateRequest, CreateResponse
from .models import AccessRequest, RequestStatus
from .tasks import start_scheduler, send_initial_email
from .tokens import validate_token_no_mark, mark_token_used
from .mailer_utils import log_audit
from .keycloak_client import KeycloakClient
import uvicorn, logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Keycloak Email Approval")

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

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=False)

