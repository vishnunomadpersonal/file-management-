from infrastructure.db.mysql import MySQLDB
from .base_repository import BaseRepo
from entities.file import File
from entities.appointment import Appointment
from dto.file_dto import FileBaseDTO
from sqlalchemy.orm import Session


class FileRepo(BaseRepo[File]):
    def __init__(self, db: Session) -> None:
        super().__init__(File, db)

    def get_file(self, id: str) -> File:
        return self.get(id=id)

    def create_file(self, file: FileBaseDTO) -> File:
        db_file = File(
            upload_id=file.upload_id,
            path=file.path,
            credential=file.credential,
            content_type=file.content_type,
            size=file.size,
            detail=file.detail,
            celery_task_id=file.celery_task_id,
            appointment_id=file.appointment_id,
            user_id=file.user_id,
            filename=file.filename,
            virus_scan_status=file.virus_scan_status,
            virus_scan_result=file.virus_scan_result,
            virus_scan_date=file.virus_scan_date,
            is_quarantined=file.is_quarantined,
            quarantine_reason=file.quarantine_reason
        )
        return self.create(db_file)

    def get_files_by_appointment(self, appointment_id: str) -> list[File]:
        return (
            self.db
            .query(self.model)
            .filter(
                self.model.appointment_id == appointment_id,
                self.model.virus_scan_status != 'infected'
            )
            .all()
        )

    def list_all_files(self, user_id: str) -> list[tuple]:
        return (
            self.db
            .query(self.model, Appointment.name)
            .join(Appointment, self.model.appointment_id == Appointment.id)
            .filter(
                self.model.user_id == user_id,
                self.model.virus_scan_status != 'infected'
            )
            .all()
        )

    def delete_file(self, file_id: str):
        file_to_delete = self.get(id=file_id)
        if file_to_delete:
            self.db.delete(file_to_delete)
            self.db.commit()
        return file_to_delete
