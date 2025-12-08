from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from infrastructure.db.mysql import mysql
from repositories.user_repository import UserRepo
from services.user_service import UserService
from dto.user_dto import User, UserCreate
from api.responses.response import SuccessResponse, ErrorResponse
from core.security import get_current_user, AuthenticatedUser, Role

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"]
)

def get_user_service(db: Session = Depends(mysql.get_db)) -> UserService:
    repo = UserRepo(db=db)
    return UserService(repo=repo)


class StatusUpdateRequest(BaseModel):
    status: str  # 'approved' or 'rejected'


@router.post("/", response_model=SuccessResponse[User])
def create_user(user: UserCreate, service: UserService = Depends(get_user_service)):
    new_user = service.create_user(user)
    return SuccessResponse(data=new_user)

@router.get("/", response_model=SuccessResponse[List[User]])
def list_users(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    service: UserService = Depends(get_user_service),
    db: Session = Depends(mysql.get_db)
):
    """List all users, optionally filtered by organization."""
    from entities.user import User as UserEntity
    
    query = db.query(UserEntity)
    if organization_id:
        query = query.filter(UserEntity.organization_id == organization_id)
    
    users = query.all()
    return SuccessResponse(data=[User.model_validate(u) for u in users])

@router.patch("/{user_id}/status", response_model=SuccessResponse[User])
def update_user_status(
    user_id: str,
    data: StatusUpdateRequest,
    service: UserService = Depends(get_user_service),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(mysql.get_db)
):
    """Update user status (approve/reject). Requires super_admin or org_admin role."""
    # Only super_admin and org_admin can approve/reject
    if current_user.role not in [Role.SUPER_ADMIN, Role.ORG_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can approve or reject users"
        )
    
    # Validate status value
    if data.status not in ['approved', 'rejected', 'pending']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'approved', 'rejected', or 'pending'"
        )
    
    # Get and update the user
    from entities.user import User as UserEntity
    user = db.query(UserEntity).filter(UserEntity.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Org admins can only approve users in their own organization
    if current_user.role == Role.ORG_ADMIN:
        if user.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only approve users in your organization"
            )
    
    user.status = data.status
    db.commit()
    db.refresh(user)
    
    return SuccessResponse(data=User.model_validate(user))


@router.delete("/{user_id}", response_model=SuccessResponse)
def delete_user(user_id: str, service: UserService = Depends(get_user_service)):
    deleted_user = service.delete_user(user_id)
    if not deleted_user:
        return ErrorResponse(message="User not found", status=status.HTTP_404_NOT_FOUND)
    return SuccessResponse(data={"message": "User and all associated data deleted successfully"})