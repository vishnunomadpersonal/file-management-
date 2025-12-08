import os
from pydantic_core import MultiHostUrl
from dotenv import load_dotenv

load_dotenv()


class Config:
    APP_UPLOAD_DIR = os.getenv("APP_UPLOAD_DIR")
    APP_MAX_CHUNK_SIZE = int(os.getenv("APP_MAX_CHUNK_SIZE"))
    ENV = os.getenv("ENV")
    print("ENV:", ENV)

    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    MINIO_URL = os.getenv("MINIO_URL")
    # Optional: external endpoint used when generating presigned URLs for browser access.
    # Always signed with HTTPS for production use.
    MINIO_EXTERNAL_ENDPOINT = os.getenv("MINIO_EXTERNAL_ENDPOINT")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    MINIO_PUBLIC_BUCKET = os.getenv('MINIO_PUBLIC_BUCKET', 'public')
    MINIO_PRIVATE_BUCKET = os.getenv('MINIO_PRIVATE_BUCKET', 'private')

    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'db-mysql')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "filemanager")
    MYSQL_TEST_DATABASE = os.getenv("MYSQL_TEST_DATABASE", "filemanager_test")

    CLAMAV_REST_URL = os.getenv("CLAMAV_REST_URL", "http://clamav-rest:3000")
    VIRUS_SCAN_ENABLED = os.getenv("VIRUS_SCAN_ENABLED", "true").lower() == "true"
    QUARANTINE_INFECTED_FILES = os.getenv("QUARANTINE_INFECTED_FILES", "true").lower() == "true"
    DELETE_INFECTED_FILES = os.getenv("DELETE_INFECTED_FILES", "false").lower() == "true"
    MAX_SCAN_FILE_SIZE = int(os.getenv("MAX_SCAN_FILE_SIZE", str(100 * 1024 * 1024)))  # 100MB default

    @property
    def MYSQL_DATABASE_URL(self):
        if self.ENV == "testing":
            path = self.MYSQL_TEST_DATABASE
        else:
            path = self.MYSQL_DATABASE
        return MultiHostUrl.build(
            scheme="mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_HOST,
            port=int(self.MYSQL_PORT),
            path=path
        )
    @property
    def CELERY_BACKEND_ENDPOINT(self):
        if self.ENV == "testing":
            path = self.MYSQL_TEST_DATABASE
        else:
            path = self.MYSQL_DATABASE
        return MultiHostUrl.build(
            scheme="db+mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_HOST,
            port=int(self.MYSQL_PORT),
            path=path
        )

    RABBITMQ_DEFAULT_USER = os.getenv('RABBITMQ_DEFAULT_USER', 'root')
    RABBITMQ_DEFAULT_PASS = os.getenv('RABBITMQ_DEFAULT_PASS', 'password')
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = os.getenv('RABBITMQ_PORT', '5672')

    @property
    def RABBITMQ_ENDPOINT(self):
        return MultiHostUrl.build(
            scheme="pyamqp",
            username=self.RABBITMQ_DEFAULT_USER,
            password=self.RABBITMQ_DEFAULT_PASS,
            host=self.RABBITMQ_HOST,
            port=int(self.RABBITMQ_PORT),
        )

    # Keycloak Configuration
    KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "filemanager")
    KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "filemanager-api")
    KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
    KEYCLOAK_ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
    KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    KEYCLOAK_ENABLED = os.getenv("KEYCLOAK_ENABLED", "true").lower() == "true"
    
    # OAuth2 callback URL (used for OAuth2 authorization code flow)
    KEYCLOAK_REDIRECT_URI = os.getenv("KEYCLOAK_REDIRECT_URI", "http://localhost:8000/api/v1/keycloak/login/oauth2/callback")
    
    @property
    def KEYCLOAK_ISSUER_URL(self):
        """Full issuer URL for token validation"""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}"
    
    @property
    def KEYCLOAK_TOKEN_URL(self):
        """Token endpoint URL"""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/token"
    
    @property
    def KEYCLOAK_AUTH_URL(self):
        """Authorization endpoint URL"""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/auth"
    
    @property
    def KEYCLOAK_USERINFO_URL(self):
        """UserInfo endpoint URL"""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
    
    @property
    def KEYCLOAK_LOGOUT_URL(self):
        """Logout endpoint URL"""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/logout"
    
    @property
    def KEYCLOAK_CERTS_URL(self):
        """JWKS endpoint URL for public keys"""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    
    @property
    def KEYCLOAK_ADMIN_URL(self):
        """Admin REST API base URL"""
        return f"{self.KEYCLOAK_URL}/admin/realms/{self.KEYCLOAK_REALM}"

config = Config()
