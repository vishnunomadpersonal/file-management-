from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from infrastructure.db.mysql import mysql
from repositories.user_repository import UserRepo
from services.user_service import UserService
from dto.user_dto import User, UserCreate
from api.responses.response import SuccessResponse, ErrorResponse
from typing import List

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"]
)

def get_user_service(db: Session = Depends(mysql.get_db)) -> UserService:
    repo = UserRepo(db=db)
    return UserService(repo=repo)

@router.post("/", response_model=SuccessResponse[User])
def create_user(user: UserCreate, service: UserService = Depends(get_user_service)):
    new_user = service.create_user(user)
    return SuccessResponse(data=new_user)

@router.get("/", response_model=SuccessResponse[List[User]])
def list_users(service: UserService = Depends(get_user_service)):
    users = service.list_users()
    return SuccessResponse(data=users)

@router.delete("/{user_id}", response_model=SuccessResponse)
def delete_user(user_id: str, service: UserService = Depends(get_user_service)):
    deleted_user = service.delete_user(user_id)
    if not deleted_user:
        return ErrorResponse(message="User not found", status=status.HTTP_404_NOT_FOUND)
    return SuccessResponse(data={"message": "User and all associated data deleted successfully"})