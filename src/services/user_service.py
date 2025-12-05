from repositories.user_repository import UserRepo
from services.base_service import BaseService
from dto.user_dto import UserCreate, User
from typing import List
from infrastructure.minio import minioStorage
import logging

logger = logging.getLogger(__name__)


class UserService(BaseService[UserRepo]):
    def __init__(self, repo: UserRepo):
        super().__init__(repo)

    def create_user(self, user: UserCreate) -> User:
        return self.repo.create_user(user.name)

    def list_users(self) -> List[User]:
        return self.repo.list_users()

    def delete_user(self, user_id: str) -> User:
        # First get the user to access its appointments and files
        user = self.repo.get(id=user_id)
        if not user:
            return None
            
        # Delete all files associated with this user from MinIO
        for appointment in user.appointments:
            for file in appointment.files:
                try:
                    # Delete from MinIO
                    bucket_name = file.path.split("/")[0]
                    object_name = "/".join(file.path.split("/")[1:])
                    minioStorage.remove_object(bucket_name, object_name)
                    logger.info(f"Deleted file from MinIO: {bucket_name}/{object_name}")
                except Exception as e:
                    logger.error(f"Failed to delete file from MinIO: {str(e)}")
                    # Continue with deletion even if MinIO deletion fails
        
        # Delete the user (cascade will delete associated appointments and files from DB)
        return self.repo.delete_user(user_id)