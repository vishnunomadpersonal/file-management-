from repositories.appointment_repository import AppointmentRepo
from services.base_service import BaseService
from dto.appointment_dto import AppointmentCreate, Appointment
from typing import List
from infrastructure.minio import minioStorage
import logging

logger = logging.getLogger(__name__)

# Redis Caching
try:
    from infrastructure.redis_cache import redis_cache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_cache = None

CACHE_TTL_APPOINTMENTS = 180  # 3 minutes for appointment lists


def _serialize_appointment(appointment) -> dict:
    """Serialize appointment entity to dict for caching."""
    return {
        "id": str(appointment.id),
        "name": appointment.name,
        "user_id": appointment.user_id,
        "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
    }


def _invalidate_appointment_caches(user_id: str = None):
    """Invalidate appointment caches."""
    if not REDIS_AVAILABLE or not redis_cache:
        return
    try:
        if user_id:
            redis_cache.delete(f"appointments:user:{user_id}")
        redis_cache.delete_pattern("appointments:user:*")
    except Exception as e:
        logger.warning(f"Failed to invalidate appointment caches: {e}")


class AppointmentService(BaseService[AppointmentRepo]):
    def __init__(self, repo: AppointmentRepo):
        super().__init__(repo)

    def seed_appointments(self): #this code is no longer in use reactivate in main.py for hardcode appt as needed
        hardcoded_appointments = ["subash", "appointment2", "appointment3"]
        for name in hardcoded_appointments:
            existing = self.repo.get_appointment_by_name(name)
            if not existing:
                self.repo.create_appointment(AppointmentCreate(name=name))

    def create_appointment(self, appointment: AppointmentCreate, user_id: str) -> Appointment:
        # In a real app, you'd add more validation here
        result = self.repo.create_appointment(appointment, user_id)
        _invalidate_appointment_caches(user_id)
        return result

    def list_appointments(self, user_id: str) -> List[Appointment]:
        cache_key = f"appointments:user:{user_id}"
        
        # Try cache first
        if REDIS_AVAILABLE and redis_cache:
            try:
                cached = redis_cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return [Appointment(**apt) for apt in cached]
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Cache miss - get from DB
        appointments = self.repo.list_appointments(user_id)
        
        # Store in cache
        if REDIS_AVAILABLE and redis_cache and appointments:
            try:
                cache_data = [_serialize_appointment(apt) for apt in appointments]
                redis_cache.set(cache_key, cache_data, ttl=CACHE_TTL_APPOINTMENTS)
                logger.debug(f"Cache SET: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return appointments

    def delete_appointment(self, appointment_id: str) -> Appointment:
        # First get the appointment to access its files
        appointment = self.repo.get(id=appointment_id)
        if not appointment:
            return None
            
        # Delete all files associated with this appointment
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
        
        # Delete the appointment (cascade will delete associated files from DB)
        deleted = self.repo.delete_appointment(appointment_id)
        if deleted:
            _invalidate_appointment_caches(appointment.user_id)
        return deleted