from sqlalchemy.orm import Session
from .base_repository import BaseRepo
from entities.user import User
from typing import List


class UserRepo(BaseRepo[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def create_user(self, name: str) -> User:
        db_user = User(name=name)
        return self.create(db_user)

    def get_user_by_name(self, name: str) -> User:
        return self.db.query(self.model).filter(self.model.name == name).first()

    def list_users(self) -> List[User]:
        return self.db.query(self.model).all()

    def delete_user(self, user_id: str) -> User:
        user = self.get(id=user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
        return user