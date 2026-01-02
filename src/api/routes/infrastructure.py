"""
Infrastructure API Routes
=========================
Real-time Docker container metrics and system statistics.

Endpoints:
- GET /containers - List all containers with stats
- GET /containers/{id}/stats - Get single container stats
- GET /containers/{id}/logs - Get container logs
- GET /system - Get system-wide metrics
- POST /containers/{id}/action - Perform container action (start/stop/restart)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime
import logging

from src.infrastructure.docker_monitor import docker_monitor, DockerMonitor
from src.core.security import get_current_user
from src.entities.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/infrastructure", tags=["Infrastructure"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin or super_admin role."""
    if current_user.role not in ['admin', 'super_admin']:
        raise HTTPException(
            status_code=403,
            detail="Admin access required for infrastructure monitoring"
        )
    return current_user


@router.get("/health")
async def check_docker_health():
    """Check if Docker daemon is accessible."""
    try:
        is_connected = docker_monitor.is_connected
        return {
            "status": "connected" if is_connected else "disconnected",
            "docker_available": is_connected
        }
    except Exception as e:
        logger.error(f"Docker health check failed: {e}")
        return {
            "status": "error",
            "docker_available": False,
            "error": str(e)
        }


@router.get("/containers", response_model=List[Dict])
async def list_containers(
    project: Optional[str] = Query(None, description="Filter by docker-compose project name"),
    current_user: User = Depends(require_admin)
):
    """
    Get all containers with real-time statistics.
    
    Returns CPU, memory, network I/O, and status for each container.
    """
    try:
        containers = await docker_monitor.get_all_containers_stats(project_filter=project)
        return containers
    except Exception as e:
        logger.error(f"Failed to get containers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve container stats: {str(e)}"
        )


@router.get("/containers/{container_id}/stats")
async def get_container_stats(
    container_id: str,
    current_user: User = Depends(require_admin)
):
    """Get detailed stats for a specific container."""
    try:
        stats = await docker_monitor.get_container_stats(container_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Container not found")
        return stats.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get container stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers/{container_id}/logs")
async def get_container_logs(
    container_id: str,
    tail: int = Query(100, ge=1, le=1000, description="Number of log lines"),
    since_minutes: Optional[int] = Query(None, ge=1, le=1440, description="Logs from last N minutes"),
    current_user: User = Depends(require_admin)
):
    """
    Get logs from a specific container.
    
    Args:
        container_id: Container ID or name
        tail: Number of recent log lines (default 100, max 1000)
        since_minutes: Only logs from last N minutes
    """
    try:
        since = None
        if since_minutes:
            since = datetime.now() - timedelta(minutes=since_minutes)
        
        logs = await docker_monitor.get_container_logs(
            container_id, 
            tail=tail,
            since=since
        )
        
        return {
            "container_id": container_id,
            "log_count": len(logs),
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Failed to get container logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system")
async def get_system_stats(
    current_user: User = Depends(require_admin)
):
    """
    Get system-wide statistics.
    
    Includes:
    - Container counts (total, running, stopped, healthy, unhealthy)
    - CPU usage
    - Memory usage
    - Disk usage
    """
    try:
        stats = await docker_monitor.get_system_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/io")
async def get_io_stats(
    current_user: User = Depends(require_admin)
):
    """
    Get real-time I/O statistics.
    
    Returns network and disk I/O rates.
    Note: This endpoint takes ~2 seconds to calculate rates.
    """
    try:
        network_io = await docker_monitor.get_network_io_rate()
        disk_io = await docker_monitor.get_disk_io_rate()
        
        return {
            "network": network_io,
            "disk": disk_io
        }
    except Exception as e:
        logger.error(f"Failed to get I/O stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/containers/{container_id}/action")
async def container_action(
    container_id: str,
    action: str = Query(..., regex="^(start|stop|restart)$"),
    current_user: User = Depends(require_admin)
):
    """
    Perform an action on a container.
    
    Actions: start, stop, restart
    
    **WARNING**: This affects running services!
    """
    try:
        container = docker_monitor.client.containers.get(container_id)
        
        if action == "start":
            container.start()
            message = f"Container {container.name} started"
        elif action == "stop":
            container.stop(timeout=30)
            message = f"Container {container.name} stopped"
        elif action == "restart":
            container.restart(timeout=30)
            message = f"Container {container.name} restarted"
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        logger.info(f"User {current_user.email} performed {action} on container {container.name}")
        
        return {
            "success": True,
            "action": action,
            "container_id": container_id,
            "container_name": container.name,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to {action} container: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_infrastructure_summary(
    current_user: User = Depends(require_admin)
):
    """
    Get a complete infrastructure summary in one call.
    
    Combines containers, system stats, and I/O metrics.
    Use this for the dashboard overview.
    """
    try:
        containers = await docker_monitor.get_all_containers_stats()
        system = await docker_monitor.get_system_stats()
        
        # Group containers by status
        running = [c for c in containers if c['status'] == 'running']
        stopped = [c for c in containers if c['status'] != 'running']
        
        # Calculate aggregate stats
        total_cpu = sum(c['cpu_percent'] for c in running)
        total_memory = sum(c['memory_used_mb'] for c in running)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": system,
            "containers": {
                "total": len(containers),
                "running": len(running),
                "stopped": len(stopped),
                "list": containers
            },
            "aggregate": {
                "total_container_cpu_percent": round(total_cpu, 1),
                "total_container_memory_mb": round(total_memory, 1)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get infrastructure summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import datetime timedelta for since_minutes
from datetime import timedelta
