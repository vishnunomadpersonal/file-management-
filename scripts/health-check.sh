#!/bin/bash
# ==============================================================================
# Multi-Tenant Platform Health Check Script
# ==============================================================================
# This script verifies all services are running and properly connected.
# Run this after `docker-compose up -d` to ensure the platform is healthy.
# ==============================================================================

set -e

echo "=============================================================="
echo " Multi-Tenant File Management Platform - Health Check"
echo "=============================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a service is responding
check_service() {
    local name=$1
    local url=$2
    local expected=${3:-200}
    
    printf "Checking %-25s ... " "$name"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected" ]; then
        echo -e "${GREEN}OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}FAILED${NC} (HTTP $response, expected $expected)"
        return 1
    fi
}

# Function to check container status
check_container() {
    local name=$1
    printf "Checking container %-15s ... " "$name"
    
    status=$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null || echo "no-health")
    running=$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null || echo "false")
    
    if [ "$running" = "true" ]; then
        if [ "$status" = "healthy" ]; then
            echo -e "${GREEN}Running (Healthy)${NC}"
        elif [ "$status" = "no-health" ]; then
            echo -e "${GREEN}Running (No Healthcheck)${NC}"
        else
            echo -e "${YELLOW}Running ($status)${NC}"
        fi
        return 0
    else
        echo -e "${RED}Not Running${NC}"
        return 1
    fi
}

echo "1. Checking Container Status"
echo "------------------------------"
check_container "filemanager"
check_container "kong"
check_container "kong-db"
check_container "mysql"
check_container "minio"
check_container "keycloak"
check_container "keycloak-db"
check_container "caddy"
check_container "clamav"
check_container "clamav-rest"
check_container "rabbitmq"
echo ""

echo "2. Checking Service Endpoints"
echo "------------------------------"

# Direct service checks
check_service "FastAPI Direct" "http://localhost:8000/docs"
check_service "FastAPI Health" "http://localhost:8000/api/v1/pipeline/health"

# Kong checks
check_service "Kong Admin API" "http://localhost:8001/"
check_service "Kong Proxy" "http://localhost:8100/" "404"

# MinIO checks
check_service "MinIO Console" "http://localhost:9090/"

# Keycloak checks
check_service "Keycloak" "http://localhost:8080/health/ready"

# ClamAV REST
check_service "ClamAV REST" "http://localhost:9002/health" || check_service "ClamAV REST" "http://localhost:9002/"

# Caddy (HTTPS)
check_service "Caddy HTTPS" "https://localhost:9443/docs" || echo -e "${YELLOW}(May need to accept self-signed cert)${NC}"

echo ""

echo "3. Checking Kong Routes (via Caddy)"
echo "------------------------------------"
check_service "API via Kong" "http://localhost:8100/api/v1/pipeline/health"
check_service "Docs via Kong" "http://localhost:8100/docs"

echo ""

echo "4. Platform URLs"
echo "------------------------------------"
echo ""
echo "Application:"
echo "  - API Docs:       https://localhost:9443/docs"
echo "  - API Base:       https://localhost:9443/api/v1/"
echo ""
echo "Admin Consoles:"
echo "  - Kong Manager:   https://localhost:9443/kong-admin/"
echo "  - Kong Admin API: https://localhost:9443/kong-api/"
echo "  - Keycloak:       https://localhost:9443/keycloak/"
echo "  - MinIO Console:  https://localhost:9443/minio-console/"
echo ""
echo "Direct Access (dev only):"
echo "  - FastAPI:        http://localhost:8000/docs"
echo "  - Kong Admin:     http://localhost:8001/"
echo "  - Kong Manager:   http://localhost:8002/"
echo "  - MinIO:          http://localhost:9090/"
echo "  - Keycloak:       http://localhost:8080/"
echo ""

echo "=============================================================="
echo " Health Check Complete"
echo "=============================================================="
