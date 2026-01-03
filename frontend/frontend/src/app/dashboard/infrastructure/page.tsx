"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import {
  Server,
  Database,
  HardDrive,
  Cpu,
  MemoryStick,
  Network,
  Activity,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Wifi,
  Clock,
  Zap,
  Globe,
  Container,
  Settings,
  Loader2,
} from 'lucide-react';

// Service status types
interface Service {
  name: string;
  type: 'api' | 'database' | 'cache' | 'queue' | 'storage' | 'scanner' | 'auth';
  status: 'healthy' | 'degraded' | 'down';
  port: string;
  host: string;
  uptime: string;
  cpu: number;
  memory: number;
  latency: number | null;
  requests_per_min?: number | null;
  connections?: number | null;
  queue_size?: number | null;
}

interface ContainerData {
  container_id: string;
  container_name: string;
  display_name: string;
  image: string;
  status: string;
  health: string;
  cpu_percent: number;
  memory_used_mb: number;
  memory_limit_mb: number;
  memory_percent: number;
  network_rx_mb: number;
  network_tx_mb: number;
  block_read_mb: number;
  block_write_mb: number;
  uptime: string;
  ports: string[];
  latency_ms: number | null;
  requests_per_min: number | null;
  connections: number | null;
  queue_size: number | null;
  icon: string;
  color: string;
}

interface SystemStats {
  total_containers: number;
  running_containers: number;
  stopped_containers: number;
  healthy_containers: number;
  unhealthy_containers: number;
  total_cpu_percent: number;
  total_memory_used_gb: number;
  total_memory_gb: number;
  memory_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  disk_percent: number;
}

interface InfrastructureSummary {
  timestamp: string;
  system: SystemStats;
  containers: {
    total: number;
    running: number;
    stopped: number;
    list: ContainerData[];
  };
  aggregate: {
    total_container_cpu_percent: number;
    total_container_memory_mb: number;
  };
}

const serviceIcons: Record<Service['type'], React.ElementType> = {
  api: Globe,
  database: Database,
  cache: Zap,
  queue: Network,
  storage: HardDrive,
  scanner: Activity,
  auth: Settings,
};

// Map container names to service types
const getServiceType = (containerName: string): Service['type'] => {
  const name = containerName.toLowerCase();
  if (name.includes('mysql') || name.includes('postgres') || name.includes('kong-db') || name.includes('keycloak-db')) return 'database';
  if (name.includes('rabbitmq')) return 'queue';
  if (name.includes('minio')) return 'storage';
  if (name.includes('clamav')) return 'scanner';
  if (name.includes('keycloak')) return 'auth';
  return 'api';
};

// Main services to show in the grid (filter out helper containers)
const MAIN_SERVICES = ['filemanager', 'kong', 'mysql', 'minio', 'clamav', 'keycloak', 'rabbitmq', 'caddy'];

export default function InfrastructurePage() {
  const { isDark } = useTheme();
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [data, setData] = useState<InfrastructureSummary | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const token = localStorage.getItem('filevault_access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/infrastructure/summary`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result: InfrastructureSummary = await response.json();
      setData(result);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch infrastructure data:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const refreshData = () => {
    setRefreshing(true);
    fetchData();
  };

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchData();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Convert container data to services for the grid
  const services: Service[] = data?.containers.list
    .filter(c => MAIN_SERVICES.some(s => c.container_name.toLowerCase().includes(s)))
    .filter((c, i, arr) => {
      // Remove duplicates - keep the one with actual stats (running)
      const isDupe = arr.findIndex(x => 
        getServiceType(x.container_name) === getServiceType(c.container_name) &&
        x.display_name === c.display_name
      ) !== i;
      return !isDupe || c.status === 'running';
    })
    .map(c => ({
      name: c.display_name,
      type: getServiceType(c.container_name),
      status: c.status === 'running' ? (c.health === 'healthy' ? 'healthy' : 'degraded') : 'down',
      port: c.ports.join(', ') || '-',
      host: c.container_name,
      uptime: c.uptime,
      cpu: Math.round(c.cpu_percent),
      memory: Math.round(c.memory_percent),
      latency: c.latency_ms,
      requests_per_min: c.requests_per_min,
      connections: c.connections,
      queue_size: c.queue_size,
    })) || [];

  // System stats
  const healthyServices = services.filter(s => s.status === 'healthy').length;
  const degradedServices = services.filter(s => s.status === 'degraded').length;
  const downServices = services.filter(s => s.status === 'down').length;
  const totalServices = services.length;

  // System resource stats
  const systemCpu = data?.system.total_cpu_percent || 0;
  const memoryUsedGb = data?.system.total_memory_used_gb || 0;
  const memoryTotalGb = data?.system.total_memory_gb || 32;
  const memoryPercent = data?.system.memory_percent || 0;

  // All containers for the table
  const containers = data?.containers.list || [];
  const runningContainers = containers.filter(c => c.status === 'running').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <span className={`ml-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Loading infrastructure data...</span>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <XCircle className="w-12 h-12 text-red-500 mb-4" />
        <h2 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Failed to Load Infrastructure Data</h2>
        <p className={`mt-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{error}</p>
        <button
          onClick={refreshData}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Infrastructure</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Monitor all services and system health</p>
        </div>
        <div className="flex items-center gap-4">
          <div className={`text-sm flex items-center gap-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            <Clock className="w-4 h-4" />
            Last updated: {lastUpdated.toLocaleTimeString()}
          </div>
          <button
            onClick={refreshData}
            disabled={refreshing}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors disabled:opacity-50 ${
              isDark ? 'bg-gray-800 hover:bg-gray-700 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
            }`}
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Overall Health */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className={`rounded-2xl p-6 border md:col-span-2 ${
          isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'
        }`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>System Health</h3>
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
              healthyServices === totalServices && totalServices > 0
                ? 'bg-green-500/20 text-green-400' 
                : downServices > 0
                ? 'bg-red-500/20 text-red-400'
                : 'bg-yellow-500/20 text-yellow-400'
            }`}>
              {healthyServices === totalServices && totalServices > 0 ? (
                <CheckCircle className="w-4 h-4" />
              ) : downServices > 0 ? (
                <XCircle className="w-4 h-4" />
              ) : (
                <AlertTriangle className="w-4 h-4" />
              )}
              <span className="text-sm font-medium">
                {healthyServices === totalServices && totalServices > 0 ? 'All Systems Operational' : 
                 downServices > 0 ? 'Systems Down' : 'Partial Degradation'}
              </span>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className={`text-center p-4 rounded-xl ${isDark ? 'bg-gray-700/30' : 'bg-gray-50'}`}>
              <p className="text-3xl font-bold text-green-400">{healthyServices}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Healthy</p>
            </div>
            <div className={`text-center p-4 rounded-xl ${isDark ? 'bg-gray-700/30' : 'bg-gray-50'}`}>
              <p className="text-3xl font-bold text-yellow-400">{degradedServices}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Degraded</p>
            </div>
            <div className={`text-center p-4 rounded-xl ${isDark ? 'bg-gray-700/30' : 'bg-gray-50'}`}>
              <p className="text-3xl font-bold text-red-400">{downServices}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Down</p>
            </div>
          </div>
        </div>

        {/* Cluster Resources */}
        <div className={`rounded-2xl p-6 border ${
          isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'
        }`}>
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-blue-400" />
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>CPU Usage</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Total</span>
              <span className={isDark ? 'text-white' : 'text-gray-900'}>{systemCpu.toFixed(1)}%</span>
            </div>
            <div className={`h-3 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
              <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full" style={{ width: `${Math.min(systemCpu, 100)}%` }} />
            </div>
            <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>8 cores available</p>
          </div>
        </div>

        <div className={`rounded-2xl p-6 border ${
          isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'
        }`}>
          <div className="flex items-center gap-2 mb-4">
            <MemoryStick className="w-5 h-5 text-purple-400" />
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Memory</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Used</span>
              <span className={isDark ? 'text-white' : 'text-gray-900'}>{memoryUsedGb.toFixed(1)} / {memoryTotalGb.toFixed(0)} GB</span>
            </div>
            <div className={`h-3 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
              <div className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full" style={{ width: `${Math.min(memoryPercent, 100)}%` }} />
            </div>
            <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{memoryPercent.toFixed(0)}% utilization</p>
          </div>
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {services.map((service, i) => {
          const Icon = serviceIcons[service.type];
          return (
            <div
              key={i}
              className={`rounded-xl p-5 border transition-all ${
                isDark 
                  ? `bg-gray-800/50 hover:border-gray-600 ${
                      service.status === 'healthy' ? 'border-gray-700/50' :
                      service.status === 'degraded' ? 'border-yellow-500/50' :
                      'border-red-500/50'
                    }`
                  : `bg-white hover:border-gray-300 ${
                      service.status === 'healthy' ? 'border-gray-200' :
                      service.status === 'degraded' ? 'border-yellow-400' :
                      'border-red-400'
                    }`
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    service.status === 'healthy' ? 'bg-green-500/20' :
                    service.status === 'degraded' ? 'bg-yellow-500/20' :
                    'bg-red-500/20'
                  }`}>
                    <Icon className={`w-5 h-5 ${
                      service.status === 'healthy' ? 'text-green-400' :
                      service.status === 'degraded' ? 'text-yellow-400' :
                      'text-red-400'
                    }`} />
                  </div>
                  <div>
                    <h4 className={`font-medium text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{service.name}</h4>
                    <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{service.host}:{service.port}</p>
                  </div>
                </div>
                <span className={`flex items-center gap-1 text-xs ${
                  service.status === 'healthy' ? 'text-green-400' :
                  service.status === 'degraded' ? 'text-yellow-400' :
                  'text-red-400'
                }`}>
                  {service.status === 'healthy' ? <CheckCircle className="w-3 h-3" /> :
                   service.status === 'degraded' ? <AlertTriangle className="w-3 h-3" /> :
                   <XCircle className="w-3 h-3" />}
                  {service.status}
                </span>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between text-xs">
                  <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>CPU</span>
                  <span className={isDark ? 'text-white' : 'text-gray-900'}>{service.cpu}%</span>
                </div>
                <div className={`h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
                  <div 
                    className={`h-full rounded-full ${
                      service.cpu > 80 ? 'bg-red-500' :
                      service.cpu > 60 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${service.cpu}%` }}
                  />
                </div>

                <div className="flex justify-between text-xs">
                  <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Memory</span>
                  <span className={isDark ? 'text-white' : 'text-gray-900'}>{service.memory}%</span>
                </div>
                <div className={`h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
                  <div 
                    className={`h-full rounded-full ${
                      service.memory > 80 ? 'bg-red-500' :
                      service.memory > 60 ? 'bg-yellow-500' :
                      'bg-blue-500'
                    }`}
                    style={{ width: `${service.memory}%` }}
                  />
                </div>

                <div className={`pt-2 border-t flex justify-between text-xs ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                  <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Latency</span>
                  <span className={`${
                    service.latency === null ? (isDark ? 'text-gray-500' : 'text-gray-400') :
                    service.latency > 100 ? 'text-yellow-400' : 'text-green-400'
                  }`}>{service.latency !== null ? `${service.latency.toFixed(0)}ms` : 'N/A'}</span>
                </div>

                <div className="flex justify-between text-xs">
                  <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Uptime</span>
                  <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>{service.uptime}</span>
                </div>

                {service.requests_per_min !== null && service.requests_per_min !== undefined && (
                  <div className="flex justify-between text-xs">
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Requests/min</span>
                    <span className="text-cyan-400">{service.requests_per_min.toLocaleString()}</span>
                  </div>
                )}

                {service.connections !== null && service.connections !== undefined && (
                  <div className="flex justify-between text-xs">
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Connections</span>
                    <span className="text-purple-400">{service.connections}</span>
                  </div>
                )}

                {service.queue_size !== null && service.queue_size !== undefined && (
                  <div className="flex justify-between text-xs">
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Queue Size</span>
                    <span className="text-orange-400">{service.queue_size}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Docker Containers */}
      <div className={`rounded-2xl p-6 border ${
        isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'
      }`}>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Container className="w-5 h-5 text-blue-400" />
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Docker Containers</h3>
          </div>
          <span className="text-sm text-green-400">{runningContainers} running</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className={`text-left text-sm border-b ${isDark ? 'text-gray-400 border-gray-700' : 'text-gray-500 border-gray-200'}`}>
                <th className="pb-3 font-medium">Container</th>
                <th className="pb-3 font-medium">Image</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Ports</th>
                <th className="pb-3 font-medium">CPU</th>
                <th className="pb-3 font-medium">Memory</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {containers.map((container, i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-700/30' : 'hover:bg-gray-50'}>
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${
                        container.status === 'running' ? 'bg-green-400' : 'bg-red-400'
                      }`} />
                      <span className={`text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{container.container_name}</span>
                    </div>
                  </td>
                  <td className={`py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{container.image}</td>
                  <td className="py-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      container.status === 'running' 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {container.status}
                    </span>
                  </td>
                  <td className={`py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    {container.ports.length > 0 ? container.ports.join(', ') : '-'}
                  </td>
                  <td className={`py-3 text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {container.cpu_percent.toFixed(1)}%
                  </td>
                  <td className={`py-3 text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {container.memory_used_mb >= 1024 
                      ? `${(container.memory_used_mb / 1024).toFixed(1)}GB`
                      : `${container.memory_used_mb.toFixed(0)}MB`
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Network Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className={`rounded-2xl p-6 border ${
          isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'
        }`}>
          <div className="flex items-center gap-2 mb-6">
            <Wifi className="w-5 h-5 text-cyan-400" />
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Network I/O</h3>
          </div>
          <div className="space-y-4">
            <div className={`flex items-center justify-between p-4 rounded-lg ${isDark ? 'bg-gray-700/30' : 'bg-gray-50'}`}>
              <div>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Received</p>
                <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {((data?.containers.list || []).reduce((sum, c) => sum + c.network_rx_mb, 0) / 1024).toFixed(2)} GB
                </p>
              </div>
              <div className="h-12 w-32 flex items-end gap-1">
                {[40, 55, 45, 60, 50, 70, 65, 80, 75, 85, 90, 78].map((h, i) => (
                  <div key={i} className="flex-1 bg-cyan-500/50 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
            <div className={`flex items-center justify-between p-4 rounded-lg ${isDark ? 'bg-gray-700/30' : 'bg-gray-50'}`}>
              <div>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Sent</p>
                <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {((data?.containers.list || []).reduce((sum, c) => sum + c.network_tx_mb, 0) / 1024).toFixed(2)} GB
                </p>
              </div>
              <div className="h-12 w-32 flex items-end gap-1">
                {[35, 45, 40, 50, 45, 55, 50, 60, 55, 65, 70, 58].map((h, i) => (
                  <div key={i} className="flex-1 bg-purple-500/50 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className={`rounded-2xl p-6 border ${
          isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'
        }`}>
          <div className="flex items-center gap-2 mb-6">
            <HardDrive className="w-5 h-5 text-orange-400" />
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Disk I/O</h3>
          </div>
          <div className="space-y-4">
            <div className={`flex items-center justify-between p-4 rounded-lg ${isDark ? 'bg-gray-700/30' : 'bg-gray-50'}`}>
              <div>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Read</p>
                <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {((data?.containers.list || []).reduce((sum, c) => sum + c.block_read_mb, 0) / 1024).toFixed(2)} GB
                </p>
              </div>
              <div className="h-12 w-32 flex items-end gap-1">
                {[50, 45, 60, 55, 70, 65, 75, 70, 80, 75, 85, 82].map((h, i) => (
                  <div key={i} className="flex-1 bg-orange-500/50 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
            <div className={`flex items-center justify-between p-4 rounded-lg ${isDark ? 'bg-gray-700/30' : 'bg-gray-50'}`}>
              <div>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Write</p>
                <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {((data?.containers.list || []).reduce((sum, c) => sum + c.block_write_mb, 0) / 1024).toFixed(2)} GB
                </p>
              </div>
              <div className="h-12 w-32 flex items-end gap-1">
                {[30, 35, 40, 45, 50, 55, 45, 50, 55, 60, 65, 58].map((h, i) => (
                  <div key={i} className="flex-1 bg-yellow-500/50 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
