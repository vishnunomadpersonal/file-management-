# Keycloak Enterprise IAM Integration

This document describes the Keycloak integration for the File Management System, providing enterprise-grade authentication and authorization.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [API Endpoints](#api-endpoints)
6. [Authentication Flows](#authentication-flows)
7. [Role-Based Access Control](#role-based-access-control)
8. [Social Login](#social-login)
9. [MFA Setup](#mfa-setup)
10. [Admin Operations](#admin-operations)
11. [Frontend Integration](#frontend-integration)
12. [Troubleshooting](#troubleshooting)

---

## Overview

Keycloak is an open-source Identity and Access Management solution that provides:

- **Single Sign-On (SSO)**: Users log in once and access multiple applications
- **Social Login**: Google, GitHub, Microsoft, and other OAuth2/OIDC providers
- **Multi-Factor Authentication (MFA)**: TOTP, WebAuthn, and other methods
- **User Federation**: LDAP, Active Directory integration
- **Fine-grained Authorization**: Role-based and attribute-based access control
- **Enterprise Protocols**: OIDC, OAuth2, SAML 2.0

### Why Keycloak?

| Feature | Keycloak | Basic JWT Auth |
|---------|----------|----------------|
| SSO | ✅ | ❌ |
| Social Login | ✅ | Manual setup |
| MFA | ✅ Built-in | Manual setup |
| LDAP/AD | ✅ | ❌ |
| Admin Console | ✅ | ❌ |
| Session Management | ✅ | Limited |
| Brute Force Protection | ✅ | Manual |
| Password Policies | ✅ | Manual |
| Audit Logging | ✅ | Manual |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Applications                          │
│     (Next.js Frontend, Mobile Apps, Third-party Integrations)       │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Keycloak Server                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Realm:      │  │   Social     │  │   Enterprise Features    │  │
│  │ filemanager  │  │   Logins     │  │                          │  │
│  │              │  │ ┌──────────┐ │  │ • SSO                    │  │
│  │ • Users      │  │ │  Google  │ │  │ • MFA/2FA                │  │
│  │ • Groups     │  │ │  GitHub  │ │  │ • LDAP Federation        │  │
│  │ • Roles      │  │ │Microsoft │ │  │ • Brute Force Protection │  │
│  │ • Clients    │  │ └──────────┘ │  │ • Session Management     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (File Manager)                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Keycloak Integration                        │  │
│  │  /api/v1/auth/keycloak/*  - Auth endpoints                   │  │
│  │  /api/v1/admin/keycloak/* - Admin endpoints                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Protected Resources                              │  │
│  │  /api/v1/files     - File management                         │  │
│  │  /api/v1/pipeline  - ML Pipeline                             │  │
│  │  /api/v1/feedback  - Feedback system                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Keycloak PostgreSQL                             │
│                      (Identity Database)                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Start the Services

```bash
# Copy the example environment file
cp .env.example .env

# Start all services including Keycloak
docker-compose up -d

# Check if Keycloak is running
docker-compose ps keycloak
```

### 2. Access Keycloak Admin Console

- **URL**: http://localhost:8080
- **Username**: admin
- **Password**: admin (change in production!)

### 3. Initial Setup

The realm `filemanager` is auto-imported with:
- Pre-configured roles (super_admin, org_admin, manager, user, viewer)
- API client `filemanager-api`
- Social login placeholders (Google, GitHub, Microsoft)

### 4. Test Authentication

```bash
# Direct password login
curl -X POST http://localhost:8000/api/v1/auth/keycloak/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Response
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 300
}
```

---

## Configuration

### Environment Variables

```bash
# .env file
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=filemanager
KEYCLOAK_CLIENT_ID=filemanager-api
KEYCLOAK_CLIENT_SECRET=your-client-secret
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin
KEYCLOAK_ENABLED=true
KEYCLOAK_REDIRECT_URI=http://localhost:8000/api/v1/keycloak/login/oauth2/callback

# Keycloak Database
KEYCLOAK_DB_USER=keycloak
KEYCLOAK_DB_PASSWORD=keycloak_password
KEYCLOAK_DB_NAME=keycloak
```

### Docker Compose Configuration

The `docker-compose.yml` includes:

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:24.0.1
  environment:
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://keycloak-db:5432/keycloak
    KEYCLOAK_ADMIN: admin
    KEYCLOAK_ADMIN_PASSWORD: admin
  command: start-dev --import-realm
  ports:
    - "8080:8080"
  volumes:
    - ./keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json
```

---

## API Endpoints

### Authentication Endpoints (`/api/v1/auth/keycloak`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Direct login with email/password |
| GET | `/login/oauth2/authorize` | Start OAuth2 authorization flow |
| GET | `/login/oauth2/callback` | OAuth2 callback handler |
| GET | `/social/{provider}` | Social login redirect (google, github, microsoft) |
| POST | `/refresh` | Refresh access token |
| POST | `/logout` | Logout and invalidate session |
| GET | `/userinfo` | Get current user info |
| GET | `/me` | Get current user profile |
| POST | `/password/reset` | Request password reset |

### Admin Endpoints (`/api/v1/admin/keycloak`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List all users (paginated) |
| POST | `/users` | Create new user |
| GET | `/users/{id}` | Get user by ID |
| PUT | `/users/{id}` | Update user |
| DELETE | `/users/{id}` | Delete user |
| POST | `/users/{id}/roles` | Assign roles to user |
| DELETE | `/users/{id}/roles` | Remove roles from user |
| POST | `/users/{id}/groups` | Add user to groups |
| DELETE | `/users/{id}/groups` | Remove user from groups |
| POST | `/users/{id}/mfa/enable` | Enable MFA for user |
| POST | `/users/{id}/mfa/disable` | Disable MFA for user |
| POST | `/users/{id}/password` | Reset user password |
| GET | `/roles` | List all roles |
| POST | `/roles` | Create new role |
| GET | `/groups` | List all groups |
| POST | `/groups` | Create new group |
| GET | `/stats` | Get system statistics |

---

## Authentication Flows

### 1. Direct Login (Password Grant)

Best for: Mobile apps, CLI tools, trusted first-party apps

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/auth/keycloak/login",
    json={
        "email": "user@example.com",
        "password": "secure_password"
    }
)

tokens = response.json()
access_token = tokens["access_token"]

# Use the token
headers = {"Authorization": f"Bearer {access_token}"}
files = requests.get("http://localhost:8000/api/v1/files", headers=headers)
```

### 2. OAuth2 Authorization Code Flow

Best for: Web applications, SPAs

```javascript
// Step 1: Redirect to authorization
window.location.href = '/api/v1/auth/keycloak/login/oauth2/authorize?redirect_uri=/dashboard';

// Step 2: Handle callback (automatic)
// User is redirected back with tokens in cookies/query params

// Step 3: Use the token
const response = await fetch('/api/v1/files', {
    credentials: 'include'  // Sends cookies
});
```

### 3. Social Login

```javascript
// Google login
window.location.href = '/api/v1/auth/keycloak/social/google?redirect_uri=/dashboard';

// GitHub login
window.location.href = '/api/v1/auth/keycloak/social/github?redirect_uri=/dashboard';

// Microsoft login
window.location.href = '/api/v1/auth/keycloak/social/microsoft?redirect_uri=/dashboard';
```

### 4. Token Refresh

```python
# Automatic refresh in frontend with interceptors
# Or manual refresh:
response = requests.post(
    "http://localhost:8000/api/v1/auth/keycloak/refresh",
    json={"refresh_token": refresh_token}
)
new_tokens = response.json()
```

---

## Role-Based Access Control

### Predefined Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `super_admin` | Full system access | All operations |
| `org_admin` | Organization administrator | Manage org users, files |
| `manager` | Team manager | Manage team resources |
| `user` | Standard user | CRUD own files, view shared |
| `viewer` | Read-only access | View files only |

### Protecting Routes

```python
from fastapi import APIRouter, Depends
from core.keycloak import get_current_user_keycloak, require_keycloak_role, KeycloakToken

router = APIRouter()

# Any authenticated user
@router.get("/profile")
async def get_profile(user: KeycloakToken = Depends(get_current_user_keycloak)):
    return {"email": user.email, "roles": user.roles}

# Specific roles required
@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    user: KeycloakToken = Depends(require_keycloak_role("manager", "admin"))
):
    # Only managers and admins can delete
    pass

# Super admin only
@router.post("/system/reset")
async def system_reset(
    user: KeycloakToken = Depends(require_keycloak_role("super_admin"))
):
    # Critical operation
    pass
```

### Role Hierarchy

```
super_admin
    └── org_admin
        └── manager
            └── user
                └── viewer
```

---

## Social Login

### Setting Up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create OAuth 2.0 credentials
3. Set redirect URI: `http://localhost:8080/realms/filemanager/broker/google/endpoint`
4. In Keycloak Admin Console:
   - Navigate to Identity Providers
   - Select Google
   - Enter Client ID and Secret

### Setting Up GitHub OAuth

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create new OAuth App
3. Set callback URL: `http://localhost:8080/realms/filemanager/broker/github/endpoint`
4. In Keycloak Admin Console:
   - Navigate to Identity Providers
   - Select GitHub
   - Enter Client ID and Secret

### Setting Up Microsoft OAuth

1. Go to [Azure Portal](https://portal.azure.com)
2. Register new application in Azure AD
3. Set redirect URI: `http://localhost:8080/realms/filemanager/broker/microsoft/endpoint`
4. In Keycloak Admin Console:
   - Navigate to Identity Providers
   - Select Microsoft
   - Enter Client ID and Secret

---

## MFA Setup

### Enable MFA for User (Admin)

```python
# Admin enables MFA for user
response = requests.post(
    f"http://localhost:8000/api/v1/admin/keycloak/users/{user_id}/mfa/enable",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={"type": "totp"}  # or "webauthn"
)
```

### User Self-Service MFA

1. User logs into Keycloak Account Console
2. Navigate to Security → Authenticator
3. Scan QR code with authenticator app
4. Enter verification code

### Required MFA for Roles

In Keycloak Admin Console:
1. Navigate to Authentication → Flows
2. Create custom flow with OTP requirement
3. Bind to specific clients or roles

---

## Admin Operations

### Creating Users Programmatically

```python
from services.keycloak_admin_service import KeycloakAdminService

admin_service = KeycloakAdminService()

# Create user
user = await admin_service.create_user(
    email="new.user@example.com",
    first_name="John",
    last_name="Doe",
    password="secure_password",
    roles=["user"]
)

# Assign additional role
await admin_service.assign_role(user["id"], "manager")

# Enable MFA
await admin_service.enable_mfa(user["id"])
```

### Bulk Operations

```python
# Import users from CSV
users_data = [
    {"email": "user1@example.com", "firstName": "User", "lastName": "One"},
    {"email": "user2@example.com", "firstName": "User", "lastName": "Two"},
]

for user_data in users_data:
    await admin_service.create_user(**user_data)
```

### User Statistics

```bash
curl http://localhost:8000/api/v1/admin/keycloak/stats \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"

# Response
{
  "total_users": 150,
  "active_sessions": 42,
  "mfa_enabled_users": 89,
  "users_by_role": {
    "user": 120,
    "manager": 20,
    "admin": 8,
    "super_admin": 2
  }
}
```

---

## Frontend Integration

### React/Next.js Example

```typescript
// lib/keycloak.ts
export const keycloakConfig = {
  loginUrl: '/api/v1/auth/keycloak/login/oauth2/authorize',
  logoutUrl: '/api/v1/auth/keycloak/logout',
  refreshUrl: '/api/v1/auth/keycloak/refresh',
  userInfoUrl: '/api/v1/auth/keycloak/userinfo',
};

// hooks/useAuth.ts
import { useState, useEffect, createContext } from 'react';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(keycloakConfig.userInfoUrl, { credentials: 'include' })
      .then(res => res.ok ? res.json() : null)
      .then(setUser)
      .finally(() => setLoading(false));
  }, []);

  const login = () => {
    window.location.href = `${keycloakConfig.loginUrl}?redirect_uri=${window.location.pathname}`;
  };

  const logout = async () => {
    await fetch(keycloakConfig.logoutUrl, { method: 'POST', credentials: 'include' });
    setUser(null);
    window.location.href = '/';
  };

  return { user, loading, login, logout };
}

// components/ProtectedRoute.tsx
export function ProtectedRoute({ children, requiredRoles = [] }) {
  const { user, loading, login } = useAuth();

  if (loading) return <LoadingSpinner />;
  if (!user) {
    login();
    return null;
  }

  if (requiredRoles.length > 0) {
    const hasRole = requiredRoles.some(role => user.roles?.includes(role));
    if (!hasRole) return <AccessDenied />;
  }

  return children;
}
```

### Axios Interceptor for Token Refresh

```typescript
// lib/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  withCredentials: true,
});

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        await api.post('/auth/keycloak/refresh');
        return api(originalRequest);
      } catch (refreshError) {
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
```

---

## Troubleshooting

### Common Issues

#### 1. "Invalid token" errors

```bash
# Check if Keycloak is running
docker-compose logs keycloak

# Verify realm exists
curl http://localhost:8080/realms/filemanager/.well-known/openid-configuration

# Check token with introspection
curl -X POST http://localhost:8080/realms/filemanager/protocol/openid-connect/token/introspect \
  -d "client_id=filemanager-api" \
  -d "client_secret=your-secret" \
  -d "token=YOUR_TOKEN"
```

#### 2. Social login not working

- Verify redirect URIs match exactly
- Check client credentials in Keycloak
- Ensure Identity Provider is enabled

#### 3. CORS issues

```python
# Ensure CORS is configured in main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 4. Token expiration

```bash
# In Keycloak Admin Console:
# Realm Settings → Tokens
# Adjust:
# - Access Token Lifespan
# - Refresh Token Lifespan
```

### Logging

Enable debug logging:

```python
# In main.py or config
import logging
logging.getLogger("core.keycloak").setLevel(logging.DEBUG)
```

### Health Check

```bash
# Check Keycloak health
curl http://localhost:8080/health

# Check integration
curl http://localhost:8000/api/v1/auth/keycloak/health
```

---

## Production Checklist

- [ ] Change default admin password
- [ ] Enable HTTPS for Keycloak
- [ ] Configure proper SSL certificates
- [ ] Set up database backups
- [ ] Configure email for password reset
- [ ] Enable brute force detection
- [ ] Set up audit logging
- [ ] Configure session timeouts
- [ ] Review password policies
- [ ] Set up monitoring and alerts
- [ ] Configure proper CORS origins
- [ ] Enable MFA for admin accounts
- [ ] Set up LDAP/AD federation if needed
- [ ] Configure rate limiting

---

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Keycloak Admin REST API](https://www.keycloak.org/docs-api/24.0.1/rest-api/index.html)
- [OIDC Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
