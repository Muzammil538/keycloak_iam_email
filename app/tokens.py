import jwt, datetime, uuid
from .config import settings
from .db import SessionLocal
from .models import ApprovalToken
from sqlalchemy.exc import SQLAlchemyError

def create_token_jti(request_id: str, action: str, expiry_seconds: int=None):
    expiry_seconds = expiry_seconds or settings.TOKEN_EXPIRY_SECONDS
    jti = str(uuid.uuid4())
    now = datetime.datetime.utcnow()
    exp = now + datetime.timedelta(seconds=expiry_seconds)
    payload = {
        "jti": jti,
        "request_id": request_id,
        "action": action,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": "iam-email-service"
    }
    token = jwt.encode(payload, settings.TOKEN_SECRET, algorithm="HS256")
    # persist jti
    db = SessionLocal()
    try:
        db_token = ApprovalToken(jti=jti, request_id=request_id, action=action, created_at=now, expires_at=exp)
        db.add(db_token)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()
    return token

def validate_and_mark_token(token_str: str):
    try:
        payload = jwt.decode(token_str, settings.TOKEN_SECRET, algorithms=["HS256"], options={"require": ["exp","iat","jti"]})
    except jwt.ExpiredSignatureError:
        return None, "expired"
    except Exception as e:
        return None, f"invalid: {e}"
    jti = payload.get("jti")
    db = SessionLocal()
    try:
        db_token = db.query(ApprovalToken).filter_by(jti=jti).first()
        if not db_token:
            return None, "unknown token"
        if db_token.used_at is not None:
            return None, "already used"
        if db_token.expires_at < datetime.datetime.utcnow():
            return None, "expired (DB)"
        # mark used atomically
        db_token.used_at = datetime.datetime.utcnow()
        db.commit()
        return payload, None
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()
