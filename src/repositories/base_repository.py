from typing import Type, Generic, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
import traceback

logger = logging.getLogger(__name__)

T = TypeVar("T")

class BaseRepo(Generic[T]):
    def __init__(self, model: Type[T], db: Session) -> None:
        self.model = model
        self.db = db
        
    def create(self, entity: T) -> T:
        try:
            logger.info(f"Creating entity: {entity}")
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            logger.info(f"Entity created successfully with ID: {getattr(entity, 'id', 'N/A')}")
            return entity
        except SQLAlchemyError as e:
            logger.error(f"Database error in create: {str(e)}\n{traceback.format_exc()}")
            self.db.rollback()
            raise e
        except Exception as e:
            logger.error(f"Unexpected error in create: {str(e)}\n{traceback.format_exc()}")
            self.db.rollback()
            raise e
    
    def get(self, id: str) -> T:
        try:
            result = self.db.query(self.model).filter(self.model.id == id).first()
            logger.info(f"Retrieved entity with ID {id}: {'Found' if result else 'Not found'}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Database error in get: {str(e)}\n{traceback.format_exc()}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error in get: {str(e)}\n{traceback.format_exc()}")
            raise e