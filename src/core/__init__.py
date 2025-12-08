"""
Core Package.

Exports core configuration and security modules.
"""

from .config import config, Config
from .security import (
    Role,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_role
)
from .keycloak import (
    KeycloakSettings,
    KeycloakToken,
    TokenResponse,
    UserInfo,
    KeycloakClient,
    KeycloakOIDC,
    KeycloakUser,
    get_keycloak_settings,
    get_keycloak_client,
    get_keycloak_oidc,
    get_current_user_keycloak,
    require_keycloak_role,
    require_keycloak_permission
)

__all__ = [
    # Config
    "config",
    "Config",
    # Security
    "Role",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "require_role",
    # Keycloak
    "KeycloakSettings",
    "KeycloakToken",
    "TokenResponse",
    "UserInfo",
    "KeycloakClient",
    "KeycloakOIDC",
    "KeycloakUser",
    "get_keycloak_settings",
    "get_keycloak_client",
    "get_keycloak_oidc",
    "get_current_user_keycloak",
    "require_keycloak_role",
    "require_keycloak_permission"
]