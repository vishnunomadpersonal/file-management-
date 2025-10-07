from fastapi import APIRouter, UploadFile, Form, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from infrastructure.db.mysql import mysql as db
from repositories.file_repository import FileRepo
from services.file_service import FileService
from handlers.file_handler import FileHandler
from api.responses.file_response import FileResponse, UploadInitResponse, UploadChunkResponse, UploadStatusResponse
from typing import Optional
from api.responses.response import SuccessResponse, ErrorResponse
from core.config import config
from constants.file_extensions import FileExtension
from infrastructure.db.mysql import mysql
from dto.file_dto import FileResponseDTO
from api.responses.quarantine_response import VirusScanHealthResponse


router = APIRouter(
    prefix="/api/v1/file",
    tags=["file"]
)


def get_file_handler(db: Session = Depends(mysql.get_db)) -> FileHandler:
    repo = FileRepo(db=db)
    service = FileService(repo=repo)
    handler = FileHandler(service=service)
    return handler


@router.post("/upload/init/", response_model=SuccessResponse[UploadInitResponse])
async def endpoint(file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.upload_initialize()


@router.post("/upload/chunk/", response_model=SuccessResponse[UploadChunkResponse], responses={
    422: {"model": ErrorResponse},
})
async def endpoint(chunk_size: int = Form(..., le=config.APP_MAX_CHUNK_SIZE),
                   upload_id: str = Form(...), chunk_index: int = Form(...), file: UploadFile = Form(...),
                   file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.upload_chunk(chunk_size=chunk_size, upload_id=upload_id, chunk_index=chunk_index, file=file)


@router.post("/upload/complete/", response_model=SuccessResponse[FileResponse], responses={
    422: {"model": ErrorResponse},
})
async def endpoint(upload_id: str = Form(...), total_chunks: int = Form(...),
                   total_size: int = Form(...), credential: Optional[str] = Form(None),
                   file_extension: FileExtension = Form(...), content_type: str = Form(...),
                   appointment_id: str = Form(...), user_id: str = Form(...),
                   filename: str = Form(...),
                   detail: Optional[str] = Form(None), file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.upload_complete(upload_id=upload_id, total_chunks=total_chunks, total_size=total_size,
                                              file_extension=file_extension, content_type=content_type,
                                              credential=credential, detail=detail, appointment_id=appointment_id,
                                              user_id=user_id, filename=filename)


@router.get('/get/{file_id}', response_model=SuccessResponse[FileResponse], responses={
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    403: {"model": ErrorResponse}
})
async def endpoint(file_id: str, request: Request, file_handler: FileHandler = Depends(get_file_handler)) -> JSONResponse:
    credential = dict(request.query_params)
    return await file_handler.get_file(file_id=file_id, credential=credential)


@router.get("/appointment/{appointment_id}", response_model=SuccessResponse[list[FileResponseDTO]])
async def get_files_by_appointment(appointment_id: str, file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.get_files_by_appointment(appointment_id)


@router.get("/all", response_model=SuccessResponse[list[FileResponseDTO]])
async def list_all_files(user_id: str, file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.list_all_files(user_id)


@router.delete("/{file_id}", response_model=SuccessResponse)
async def delete_file(file_id: str, file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.delete_file(file_id)


@router.get('/status/{file_id}', response_model=SuccessResponse[UploadStatusResponse], responses={
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    403: {"model": ErrorResponse}
})
async def endpoint(file_id: str, request: Request, file_handler: FileHandler = Depends(get_file_handler)) -> JSONResponse:
    credential = dict(request.query_params)
    return await file_handler.get_upload_status(file_id=file_id, credential=credential)


@router.post('/upload/retry', response_model=SuccessResponse[FileResponse], responses={
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    403: {"model": ErrorResponse}
})
async def endpoint(file_id: str = Form(...), credential: Optional[str] = Form(None), file_handler: FileHandler = Depends(get_file_handler)) -> JSONResponse:
    return await file_handler.retry_upload(file_id=file_id, credential=credential)


@router.get('/virus-scanner/health', response_model=SuccessResponse[VirusScanHealthResponse], responses={
    503: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def virus_scanner_health(file_handler: FileHandler = Depends(get_file_handler)) -> JSONResponse:
    """Check the health status of the virus scanner service"""
    return await file_handler.virus_scanner_health()
