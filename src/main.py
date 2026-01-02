from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from api.routes import (
    file, appointment, user, pipeline, auth, mcp, 
    model_versioning, feedback, keycloak_auth, keycloak_users
)
from api.routes.organizations import router as organizations_router
from api.routes.folder import folder_router
from api.routes.chatbot import router as chatbot_router
from api.routes.infrastructure import router as infrastructure_router
from exceptions.handler import ExceptionHandler
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from contextlib import asynccontextmanager
from infrastructure.minio import minioStorage
from api.responses.response import ErrorResponse
from core.tenant import TenantMiddleware
import logging
import traceback
import sys
import time
from infrastructure.db.mysql import mysql
from services.appointment_service import AppointmentService
from repositories.appointment_repository import AppointmentRepo

# Configure logging to ensure it outputs to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test logging to verify configuration
logger.info("=== FASTAPI APPLICATION STARTING ===")
logger.info("Logging configuration initialized")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup, run the bucket setup logic and seed the database.
    try:
        minioStorage.setup_buckets()
        logger.info("MinIO buckets and policies configured.")
        
        # Seed the database with initial appointments
        db_session = next(mysql.get_db())
        appointment_repo = AppointmentRepo(db=db_session)
        appointment_service = AppointmentService(repo=appointment_repo)
        #appointment_service.seed_appointments() no longer in use - for hardcoded appts
        logger.info("Database seeded with initial appointments.")

    except Exception as e:
        logger.error(f"Failed during application startup: {str(e)}")
        raise
    finally:
        db_session.close()
        
    yield
    # Code to run on shutdown could go here if needed.


def create_application() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title="File Management API",
        description="Enterprise-grade multi-tenant file management system",
        version="2.0.0"
    )

    # Honor X-Forwarded-Proto/For from Caddy so generated redirects use https
    app.add_middleware(ProxyHeadersMiddleware)
    
    # Add Tenant Context Middleware (extracts tenant from path/headers)
    app.add_middleware(TenantMiddleware)

    # Add CORS middleware FIRST
    app.add_middleware(
        CORSMiddleware,
        # Allow both http and https localhost (Next.js dev often runs on http)
        allow_origins=[
            "http://localhost:3000",
            "https://localhost:3000",
            "http://localhost:3001",
            "https://localhost:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Global exception handler to ensure CORS headers are always present
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception handler caught: {str(exc)}\n{traceback.format_exc()}")
        
        # Create a JSONResponse with CORS headers
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error", "detail": str(exc)}
        )
        
        # Manually add CORS headers to ensure they're present
        # Mirror the primary dev origins; browsers require exact match when credentials=true
        origin = request.headers.get("origin")
        if origin in {"http://localhost:3000", "https://localhost:3000", "http://localhost:3001", "https://localhost:3001"}:
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:3001"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response
    
    app.include_router(file.router)
    app.include_router(appointment.router)
    app.include_router(user.router)
    app.include_router(pipeline.router)  # Incremental ML Pipeline routes
    app.include_router(auth.router)      # Authentication routes
    app.include_router(keycloak_auth.router)  # Keycloak OAuth2/OIDC authentication
    app.include_router(keycloak_users.router)  # Keycloak user management (admin)
    app.include_router(organizations_router)  # Multi-tenant organization management
    app.include_router(folder_router)     # Folder management routes
    app.include_router(mcp.router)       # MCP Server routes (Document Chat)
    app.include_router(model_versioning.router)  # Model versioning routes
    app.include_router(feedback.router)  # Feedback & continuous learning routes
    app.include_router(chatbot_router)   # AI Chatbot routes (REST + WebSocket)
    app.include_router(infrastructure_router)  # Infrastructure monitoring routes (Docker)
    ExceptionHandler(app)
    
    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    return app


app = create_application()
