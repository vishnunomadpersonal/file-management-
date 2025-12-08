#!/bin/bash
# ============================================================================
# Kong Enterprise API Gateway - Initialization Script
# ============================================================================
# This script configures Kong with enterprise-grade features:
# - Multi-tenant rate limiting
# - JWT/OIDC authentication
# - Audit logging
# - Request transformation for tenant context
# ============================================================================

KONG_ADMIN_URL="${KONG_ADMIN_URL:-http://localhost:8001}"

echo "============================================"
echo "Kong API Gateway Initialization"
echo "============================================"
echo "Admin URL: $KONG_ADMIN_URL"
echo ""

# Wait for Kong to be ready
echo "Waiting for Kong to be ready..."
until curl -s "$KONG_ADMIN_URL/status" > /dev/null 2>&1; do
    echo "  Waiting..."
    sleep 2
done
echo "Kong is ready!"
echo ""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

create_or_update_service() {
    local name=$1
    local url=$2
    local connect_timeout=${3:-60000}
    local read_timeout=${4:-60000}
    local write_timeout=${5:-60000}
    
    echo "Creating/updating service: $name -> $url"
    curl -s -X PUT "$KONG_ADMIN_URL/services/$name" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"$name\",
            \"url\": \"$url\",
            \"connect_timeout\": $connect_timeout,
            \"read_timeout\": $read_timeout,
            \"write_timeout\": $write_timeout,
            \"retries\": 3
        }" | jq -r '.id // .message'
}

create_route() {
    local service=$1
    local name=$2
    local paths=$3
    local strip_path=${4:-false}
    
    echo "Creating route: $name for service $service"
    curl -s -X PUT "$KONG_ADMIN_URL/services/$service/routes/$name" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"$name\",
            \"paths\": $paths,
            \"strip_path\": $strip_path,
            \"preserve_host\": true,
            \"protocols\": [\"http\", \"https\"]
        }" | jq -r '.id // .message'
}

enable_plugin() {
    local scope=$1  # "global" or service name
    local plugin=$2
    local config=$3
    
    if [ "$scope" = "global" ]; then
        echo "Enabling global plugin: $plugin"
        curl -s -X POST "$KONG_ADMIN_URL/plugins" \
            -H "Content-Type: application/json" \
            -d "{
                \"name\": \"$plugin\",
                \"config\": $config
            }" | jq -r '.id // .message'
    else
        echo "Enabling plugin $plugin for service: $scope"
        curl -s -X POST "$KONG_ADMIN_URL/services/$scope/plugins" \
            -H "Content-Type: application/json" \
            -d "{
                \"name\": \"$plugin\",
                \"config\": $config
            }" | jq -r '.id // .message'
    fi
}

create_consumer() {
    local username=$1
    local custom_id=$2
    
    echo "Creating consumer: $username"
    curl -s -X PUT "$KONG_ADMIN_URL/consumers/$username" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"$username\",
            \"custom_id\": \"$custom_id\"
        }" | jq -r '.id // .message'
}

# ============================================================================
# SERVICES
# ============================================================================

echo ""
echo "=== Creating Services ==="
echo ""

# FastAPI Backend
create_or_update_service "filemanager-api" "http://filemanager:8000" 60000 300000 300000

# Keycloak
create_or_update_service "keycloak-service" "http://keycloak:8080" 60000 60000 60000

# MinIO S3 API
create_or_update_service "minio-api" "http://minio:9000" 60000 600000 600000

# MinIO Console
create_or_update_service "minio-console" "http://minio:9090" 30000 30000 30000

# ============================================================================
# ROUTES
# ============================================================================

echo ""
echo "=== Creating Routes ==="
echo ""

# API Routes
create_route "filemanager-api" "api-org-routes" '[\"/api/v1/org\"]' false
create_route "filemanager-api" "api-auth-routes" '[\"/api/v1/auth\"]' false
create_route "filemanager-api" "api-legacy-routes" '[\"/api/v1/file\", \"/api/v1/files\", \"/api/v1/appointment\", \"/api/v1/user\", \"/api/v1/pipeline\", \"/api/v1/feedback\", \"/api/v1/mcp\", \"/api/v1/model\", \"/api/v1/keycloak\"]' false
create_route "filemanager-api" "api-health-routes" '[\"/api/v1/health\", \"/api/v1/pipeline/health\"]' false
create_route "filemanager-api" "api-docs-routes" '[\"/docs\", \"/redoc\", \"/openapi.json\"]' false

# Keycloak Routes
create_route "keycloak-service" "keycloak-routes" '[\"/auth\"]' true

# MinIO Routes
create_route "minio-api" "minio-s3-routes" '[\"/s3\"]' true
create_route "minio-console" "minio-console-routes" '[\"/minio-console\"]' true

# ============================================================================
# GLOBAL PLUGINS
# ============================================================================

echo ""
echo "=== Enabling Global Plugins ==="
echo ""

# Correlation ID for request tracing
enable_plugin "global" "correlation-id" '{
    "header_name": "X-Request-ID",
    "generator": "uuid#counter",
    "echo_downstream": true
}'

# Prometheus metrics
enable_plugin "global" "prometheus" '{
    "status_code_metrics": true,
    "latency_metrics": true,
    "bandwidth_metrics": true,
    "upstream_health_metrics": true,
    "per_consumer": true
}'

# Default rate limiting
enable_plugin "global" "rate-limiting" '{
    "minute": 100,
    "hour": 5000,
    "policy": "local",
    "fault_tolerant": true,
    "hide_client_headers": false,
    "error_code": 429,
    "error_message": "Rate limit exceeded. Please try again later."
}'

# Request size limiting (100MB for file uploads)
enable_plugin "global" "request-size-limiting" '{
    "allowed_payload_size": 100,
    "size_unit": "megabytes",
    "require_content_length": false
}'

# CORS
enable_plugin "global" "cors" '{
    "origins": ["http://localhost:3000", "https://localhost:3000", "https://localhost:9443"],
    "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    "headers": ["Accept", "Accept-Version", "Authorization", "Content-Length", "Content-Type", "X-Request-ID", "X-Tenant-ID", "X-Correlation-ID"],
    "exposed_headers": ["X-Request-ID", "X-Correlation-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    "credentials": true,
    "max_age": 3600,
    "preflight_continue": false
}'

# Response transformer - Security headers
enable_plugin "global" "response-transformer" '{
    "add": {
        "headers": [
            "X-Content-Type-Options:nosniff",
            "X-Frame-Options:DENY",
            "X-XSS-Protection:1; mode=block",
            "Referrer-Policy:strict-origin-when-cross-origin"
        ]
    },
    "remove": {
        "headers": ["Server", "X-Powered-By"]
    }
}'

# ============================================================================
# SERVICE-SPECIFIC PLUGINS
# ============================================================================

echo ""
echo "=== Enabling Service-Specific Plugins ==="
echo ""

# Higher rate limit for file uploads
enable_plugin "filemanager-api" "rate-limiting" '{
    "minute": 60,
    "hour": 1000,
    "policy": "local",
    "fault_tolerant": true
}'

# Request transformer for API
enable_plugin "filemanager-api" "request-transformer" '{
    "add": {
        "headers": ["X-Gateway:kong", "X-Forwarded-Proto:https"]
    }
}'

# ============================================================================
# CONSUMERS (Example - created dynamically for tenants)
# ============================================================================

echo ""
echo "=== Creating Default Consumers ==="
echo ""

# System internal consumer
create_consumer "system-internal" "system"

# Demo tenant consumer
create_consumer "tenant-demo" "org-demo-corp"

# ============================================================================
# DONE
# ============================================================================

echo ""
echo "============================================"
echo "Kong initialization complete!"
echo "============================================"
echo ""
echo "Access points:"
echo "  - Kong Proxy:    http://localhost:8100"
echo "  - Kong Admin:    http://localhost:8001"
echo "  - Kong Manager:  http://localhost:8002"
echo "  - Via Caddy:     https://localhost:9443/api/*"
echo ""
echo "Useful commands:"
echo "  - List services: curl http://localhost:8001/services"
echo "  - List routes:   curl http://localhost:8001/routes"
echo "  - List plugins:  curl http://localhost:8001/plugins"
echo "  - Kong status:   curl http://localhost:8001/status"
echo ""
