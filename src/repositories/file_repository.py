from infrastructure.db.mysql import MySQLDB
from .base_repository import BaseRepo
from entities.file import File
from entities.appointment import Appointment
from dto.file_dto import FileBaseDTO
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List, Optional


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
            quarantine_reason=file.quarantine_reason,
            organization_id=getattr(file, 'organization_id', None),
            folder_id=getattr(file, 'folder_id', None)
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
            .options(joinedload(self.model.organization), joinedload(self.model.user))
            .outerjoin(Appointment, self.model.appointment_id == Appointment.id)
            .filter(
                self.model.user_id == user_id,
                self.model.virus_scan_status != 'infected'
            )
            .all()
        )

    def list_all_platform_files(self, skip: int = 0, limit: int = 100) -> List[File]:
        """List all files across all organizations (for platform admin)."""
        return (
            self.db
            .query(self.model)
            .options(joinedload(self.model.organization), joinedload(self.model.user))
            .order_by(self.model.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_by_folder(self, folder_id: str) -> List[File]:
        """List all files in a specific folder."""
        return (
            self.db
            .query(self.model)
            .filter(
                self.model.folder_id == folder_id,
                self.model.virus_scan_status != 'infected'
            )
            .all()
        )

    def list_by_organization_root(self, organization_id: str) -> List[File]:
        """List all files at root level (no folder) for an organization."""
        return (
            self.db
            .query(self.model)
            .filter(
                and_(
                    self.model.organization_id == organization_id,
                    self.model.folder_id.is_(None),
                    self.model.virus_scan_status != 'infected'
                )
            )
            .all()
        )

    def list_by_organization_and_folder(
        self, 
        organization_id: str, 
        folder_id: Optional[str] = None
    ) -> List[File]:
        """List files by organization and optional folder."""
        query = self.db.query(self.model).filter(
            self.model.organization_id == organization_id,
            self.model.virus_scan_status != 'infected'
        )
        
        if folder_id is None:
            query = query.filter(self.model.folder_id.is_(None))
        else:
            query = query.filter(self.model.folder_id == folder_id)
        
        return query.all()

    def move_files_to_folder(self, file_ids: List[str], folder_id: Optional[str]) -> int:
        """Move multiple files to a folder (or root if folder_id is None)."""
        updated = (
            self.db
            .query(self.model)
            .filter(self.model.id.in_(file_ids))
            .update({self.model.folder_id: folder_id}, synchronize_session=False)
        )
        self.db.commit()
        return updated

    def delete_file(self, file_id: str):
        file_to_delete = self.get(id=file_id)
        if file_to_delete:
            self.db.delete(file_to_delete)
            self.db.commit()
        return file_to_delete
