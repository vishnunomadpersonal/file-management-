from repositories.appointment_repository import AppointmentRepo
from services.base_service import BaseService
from dto.appointment_dto import AppointmentCreate, Appointment
from typing import List
from infrastructure.minio import minioStorage
import logging

logger = logging.getLogger(__name__)

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
        return self.repo.create_appointment(appointment, user_id)

    def list_appointments(self, user_id: str) -> List[Appointment]:
        return self.repo.list_appointments(user_id)

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
        return self.repo.delete_appointment(appointment_id) 