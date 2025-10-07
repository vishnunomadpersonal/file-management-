from sqlalchemy.orm import Session
from .base_repository import BaseRepo
from entities.appointment import Appointment
from dto.appointment_dto import AppointmentCreate
from typing import List

class AppointmentRepo(BaseRepo[Appointment]):
    def __init__(self, db: Session):
        super().__init__(Appointment, db)

    def create_appointment(self, appointment: AppointmentCreate, user_id: str) -> Appointment:
        db_appointment = Appointment(name=appointment.name, user_id=user_id)
        return self.create(db_appointment)

    def get_appointment_by_name(self, name: str) -> Appointment:
        return self.db.query(self.model).filter(self.model.name == name).first()

    def list_appointments(self, user_id: str) -> List[Appointment]:
        return self.db.query(self.model).filter(self.model.user_id == user_id).all()

    def delete_appointment(self, appointment_id: str) -> Appointment:
        appointment = self.get(id=appointment_id)
        if appointment:
            self.db.delete(appointment)
            self.db.commit()
        return appointment 