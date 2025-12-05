from pydantic import BaseModel, EmailStr
from typing import Optional, Dict

class CreateRequest(BaseModel):
    keycloak_user_id: str
    requester_email: Optional[EmailStr]
    requested_role: str
    metadata: Optional[Dict] = {}

class CreateResponse(BaseModel):
    request_id: str
    status: str

