"""
Docker Infrastructure Monitor
==============================
Real-time metrics from Docker containers using Docker SDK.

Provides:
- Container stats (CPU, Memory, Network I/O, Disk I/O)
- Container status (running, stopped, health)
- Container logs
- System-wide metrics
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import docker
from docker.errors import DockerException, NotFound
from dataclasses import dataclass, asdict
import psutil

logger = logging.getLogger(__name__)


@dataclass
class ContainerStats:
    """Container statistics."""
    container_id: str
    container_name: str
    image: str
    status: str
    health: str
    cpu_percent: float
    memory_used_mb: float
    memory_limit_mb: float
    memory_percent: float
    network_rx_mb: float
    network_tx_mb: float
    block_read_mb: float
    block_write_mb: float
    uptime: str
    ports: List[str]
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemStats:
    """System-wide statistics."""
    total_containers: int
    running_containers: int
    stopped_containers: int
    healthy_containers: int
    unhealthy_containers: int
    total_cpu_percent: float
    total_memory_used_gb: float
    total_memory_gb: float
    memory_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DockerMonitor:
    """
    Docker container monitoring using Docker SDK.
    
    Provides real-time metrics for infrastructure dashboard.
    """
    
    # Service name mapping for display
    SERVICE_NAMES = {
        'filemanager': {'display': 'FastAPI Backend', 'icon': '🚀', 'color': 'green'},
        'mysql': {'display': 'MySQL Database', 'icon': '🗄️', 'color': 'blue'},
        'minio': {'display': 'MinIO Storage', 'icon': '📦', 'color': 'yellow'},
        'rabbitmq': {'display': 'RabbitMQ', 'icon': '🐰', 'color': 'orange'},
        'kong': {'display': 'Kong API Gateway', 'icon': '🦍', 'color': 'cyan'},
        'keycloak': {'display': 'Keycloak Auth', 'icon': '🔐', 'color': 'red'},
        'caddy': {'display': 'Caddy Server', 'icon': '🌐', 'color': 'purple'},
        'clamav': {'display': 'ClamAV Scanner', 'icon': '🛡️', 'color': 'teal'},
        'clamav-rest': {'display': 'ClamAV REST', 'icon': '🔬', 'color': 'teal'},
        'ollama': {'display': 'Ollama LLM', 'icon': '🤖', 'color': 'indigo'},
    }
    
    def __init__(self):
        """Initialize Docker client."""
        self._client = None
        self._connected = False
        
    @property
    def client(self) -> docker.DockerClient:
        """Get or create Docker client."""
        if self._client is None:
            try:
                # Try Unix socket first (Linux/Mac), then named pipe (Windows)
                self._client = docker.from_env()
                self._connected = True
                logger.info("Connected to Docker daemon")
            except DockerException as e:
                logger.error(f"Failed to connect to Docker: {e}")
                self._connected = False
                raise
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Docker."""
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def _calculate_cpu_percent(self, stats: Dict) -> float:
        """Calculate CPU percentage from Docker stats."""
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            if system_delta > 0 and cpu_delta > 0:
                cpu_count = stats['cpu_stats'].get('online_cpus', 1) or len(stats['cpu_stats']['cpu_usage'].get('percpu_usage', [1]))
                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
                return round(min(cpu_percent, 100.0), 1)
        except (KeyError, TypeError, ZeroDivisionError):
            pass
        return 0.0
    
    def _calculate_memory(self, stats: Dict) -> tuple:
        """Calculate memory usage from Docker stats."""
        try:
            memory_usage = stats['memory_stats'].get('usage', 0)
            memory_limit = stats['memory_stats'].get('limit', 1)
            
            # Subtract cache if available
            cache = stats['memory_stats'].get('stats', {}).get('cache', 0)
            memory_used = memory_usage - cache
            
            memory_used_mb = round(memory_used / (1024 * 1024), 1)
            memory_limit_mb = round(memory_limit / (1024 * 1024), 1)
            memory_percent = round((memory_used / memory_limit) * 100, 1) if memory_limit > 0 else 0
            
            return memory_used_mb, memory_limit_mb, memory_percent
        except (KeyError, TypeError, ZeroDivisionError):
            return 0.0, 0.0, 0.0
    
    def _calculate_network(self, stats: Dict) -> tuple:
        """Calculate network I/O from Docker stats."""
        try:
            networks = stats.get('networks', {})
            rx_bytes = sum(net.get('rx_bytes', 0) for net in networks.values())
            tx_bytes = sum(net.get('tx_bytes', 0) for net in networks.values())
            return round(rx_bytes / (1024 * 1024), 2), round(tx_bytes / (1024 * 1024), 2)
        except (KeyError, TypeError):
            return 0.0, 0.0
    
    def _calculate_block_io(self, stats: Dict) -> tuple:
        """Calculate block I/O from Docker stats."""
        try:
            blkio = stats.get('blkio_stats', {}).get('io_service_bytes_recursive', []) or []
            read_bytes = sum(item.get('value', 0) for item in blkio if item.get('op') == 'read')
            write_bytes = sum(item.get('value', 0) for item in blkio if item.get('op') == 'write')
            return round(read_bytes / (1024 * 1024), 2), round(write_bytes / (1024 * 1024), 2)
        except (KeyError, TypeError):
            return 0.0, 0.0
    
    def _calculate_uptime(self, started_at: str) -> str:
        """Calculate human-readable uptime."""
        try:
            # Parse Docker timestamp
            started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            now = datetime.now(started.tzinfo)
            delta = now - started
            
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "Unknown"
    
    def _get_ports(self, container) -> List[str]:
        """Get exposed ports for container."""
        try:
            ports = []
            port_bindings = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            for container_port, host_bindings in port_bindings.items():
                if host_bindings:
                    for binding in host_bindings:
                        ports.append(binding.get('HostPort', ''))
                else:
                    # Port exposed but not published
                    ports.append(container_port.split('/')[0])
            return [p for p in ports if p]
        except:
            return []
    
    def _get_health_status(self, container) -> str:
        """Get container health status."""
        try:
            state = container.attrs.get('State', {})
            health = state.get('Health', {})
            
            if health:
                return health.get('Status', 'unknown')
            elif state.get('Running'):
                return 'healthy'  # No health check, but running
            else:
                return 'unhealthy'
        except:
            return 'unknown'
    
    def _get_service_info(self, container_name: str) -> Dict:
        """Get display info for a service."""
        # Match by partial name
        for key, info in self.SERVICE_NAMES.items():
            if key in container_name.lower():
                return info
        return {'display': container_name, 'icon': '📦', 'color': 'gray'}
    
    async def get_container_stats(self, container_id: str) -> Optional[ContainerStats]:
        """Get stats for a single container."""
        try:
            container = self.client.containers.get(container_id)
            
            # Get real-time stats (non-streaming)
            stats = container.stats(stream=False)
            
            # Calculate metrics
            cpu_percent = self._calculate_cpu_percent(stats)
            mem_used, mem_limit, mem_percent = self._calculate_memory(stats)
            net_rx, net_tx = self._calculate_network(stats)
            blk_read, blk_write = self._calculate_block_io(stats)
            
            # Get container info
            state = container.attrs.get('State', {})
            started_at = state.get('StartedAt', '')
            created_at = container.attrs.get('Created', '')
            
            return ContainerStats(
                container_id=container.short_id,
                container_name=container.name,
                image=container.image.tags[0] if container.image.tags else 'unknown',
                status=container.status,
                health=self._get_health_status(container),
                cpu_percent=cpu_percent,
                memory_used_mb=mem_used,
                memory_limit_mb=mem_limit,
                memory_percent=mem_percent,
                network_rx_mb=net_rx,
                network_tx_mb=net_tx,
                block_read_mb=blk_read,
                block_write_mb=blk_write,
                uptime=self._calculate_uptime(started_at),
                ports=self._get_ports(container),
                created_at=created_at
            )
        except NotFound:
            logger.warning(f"Container {container_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting stats for {container_id}: {e}")
            return None
    
    async def get_all_containers_stats(self, project_filter: str = None) -> List[Dict]:
        """Get stats for all containers, optionally filtered by project name."""
        containers_stats = []
        
        try:
            containers = self.client.containers.list(all=True)
            
            for container in containers:
                # Filter by project name if specified (docker-compose labels)
                if project_filter:
                    labels = container.labels
                    project = labels.get('com.docker.compose.project', '')
                    if project_filter.lower() not in project.lower():
                        continue
                
                # Skip system containers
                if container.name.startswith('k8s_') or container.name.startswith('vsc-'):
                    continue
                
                # Get stats
                stats = await self.get_container_stats(container.id)
                if stats:
                    stats_dict = stats.to_dict()
                    # Add service display info
                    service_info = self._get_service_info(container.name)
                    stats_dict['display_name'] = service_info['display']
                    stats_dict['icon'] = service_info['icon']
                    stats_dict['color'] = service_info['color']
                    containers_stats.append(stats_dict)
            
            # Sort by name
            containers_stats.sort(key=lambda x: x['container_name'])
            
        except DockerException as e:
            logger.error(f"Docker error: {e}")
        
        return containers_stats
    
    async def get_system_stats(self) -> Dict:
        """Get system-wide statistics."""
        try:
            containers = self.client.containers.list(all=True)
            
            running = sum(1 for c in containers if c.status == 'running')
            stopped = len(containers) - running
            healthy = sum(1 for c in containers if self._get_health_status(c) == 'healthy')
            unhealthy = len(containers) - healthy
            
            # System metrics using psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return SystemStats(
                total_containers=len(containers),
                running_containers=running,
                stopped_containers=stopped,
                healthy_containers=healthy,
                unhealthy_containers=unhealthy,
                total_cpu_percent=round(cpu_percent, 1),
                total_memory_used_gb=round(memory.used / (1024**3), 2),
                total_memory_gb=round(memory.total / (1024**3), 2),
                memory_percent=round(memory.percent, 1),
                disk_used_gb=round(disk.used / (1024**3), 2),
                disk_total_gb=round(disk.total / (1024**3), 2),
                disk_percent=round(disk.percent, 1)
            ).to_dict()
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    async def get_container_logs(
        self, 
        container_id: str, 
        tail: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """Get logs from a container."""
        try:
            container = self.client.containers.get(container_id)
            
            kwargs = {
                'tail': tail,
                'timestamps': True,
                'stream': False
            }
            if since:
                kwargs['since'] = since
            
            logs = container.logs(**kwargs).decode('utf-8', errors='replace')
            
            # Parse logs into structured format
            log_entries = []
            for line in logs.strip().split('\n'):
                if not line:
                    continue
                
                # Try to parse timestamp
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    timestamp, message = parts
                else:
                    timestamp = datetime.now().isoformat()
                    message = line
                
                # Detect log level
                level = 'INFO'
                message_upper = message.upper()
                if 'ERROR' in message_upper or 'EXCEPTION' in message_upper:
                    level = 'ERROR'
                elif 'WARN' in message_upper:
                    level = 'WARN'
                elif 'DEBUG' in message_upper:
                    level = 'DEBUG'
                
                log_entries.append({
                    'timestamp': timestamp,
                    'level': level,
                    'message': message
                })
            
            return log_entries
            
        except NotFound:
            logger.warning(f"Container {container_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error getting logs for {container_id}: {e}")
            return []
    
    async def get_network_io_rate(self) -> Dict:
        """Get network I/O rate using psutil."""
        try:
            # Get initial reading
            net1 = psutil.net_io_counters()
            await asyncio.sleep(1)
            net2 = psutil.net_io_counters()
            
            # Calculate rate (bytes per second)
            rx_rate = (net2.bytes_recv - net1.bytes_recv) / 1  # per second
            tx_rate = (net2.bytes_sent - net1.bytes_sent) / 1
            
            return {
                'rx_bytes_per_sec': round(rx_rate, 0),
                'tx_bytes_per_sec': round(tx_rate, 0),
                'rx_mb_per_sec': round(rx_rate / (1024 * 1024), 2),
                'tx_mb_per_sec': round(tx_rate / (1024 * 1024), 2)
            }
        except:
            return {'rx_mb_per_sec': 0, 'tx_mb_per_sec': 0}
    
    async def get_disk_io_rate(self) -> Dict:
        """Get disk I/O rate using psutil."""
        try:
            # Get initial reading
            disk1 = psutil.disk_io_counters()
            await asyncio.sleep(1)
            disk2 = psutil.disk_io_counters()
            
            # Calculate rate (bytes per second)
            read_rate = (disk2.read_bytes - disk1.read_bytes) / 1
            write_rate = (disk2.write_bytes - disk1.write_bytes) / 1
            
            return {
                'read_bytes_per_sec': round(read_rate, 0),
                'write_bytes_per_sec': round(write_rate, 0),
                'read_mb_per_sec': round(read_rate / (1024 * 1024), 2),
                'write_mb_per_sec': round(write_rate / (1024 * 1024), 2)
            }
        except:
            return {'read_mb_per_sec': 0, 'write_mb_per_sec': 0}


# Singleton instance
docker_monitor = DockerMonitor()
