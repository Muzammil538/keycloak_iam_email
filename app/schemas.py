from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict

class CreateRequest(BaseModel):
    keycloak_user_id: str
    requester_email: Optional[EmailStr]
    requested_role: str
    metadata: Optional[Dict] = {}

class CreateResponse(BaseModel):
    request_id: str
    status: str

class CallbackResponse(BaseModel):
    request_id: str
    status: str
