import datetime
import enum
import uuid
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import relationship
from .db import Base

# small enum for status
class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    error = "error"
    expired = "expired"

class AccessRequest(Base):
    __tablename__ = "access_requests"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    keycloak_user_id = Column(String(36), nullable=False)
    requester_email = Column(String(256))
    requested_role = Column(String(256))
    meta = Column(Text, nullable=True)
    status = Column(Enum(RequestStatus), default=RequestStatus.pending)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_notified_at = Column(DateTime, nullable=True)
    notify_count = Column(Integer, default=0)

class ApprovalToken(Base):
    __tablename__ = "approval_tokens"
    jti = Column(String(64), primary_key=True)
    request_id = Column(String(36), ForeignKey("access_requests.id"), nullable=False)
    action = Column(String(16), nullable=False)  # approve / reject
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    request = relationship("AccessRequest")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String(36), nullable=True)
    actor = Column(String(256), nullable=True)
    action = Column(String(256), nullable=False)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    meta = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
