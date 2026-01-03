from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional


class UserBase(BaseModel):
    name: str


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: str
    email: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    organization_id: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserWithApprover(User):
    """User with approver details for approval history"""
    approver_name: Optional[str] = None
    approver_email: Optional[str] = None
    approver_role: Optional[str] = None
    organization_name: Optional[str] = None