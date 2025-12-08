"use client";

import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';

// Service status types
interface Service {
  name: string;
  type: 'api' | 'database' | 'cache' | 'queue' | 'storage' | 'scanner' | 'auth';
  status: 'healthy' | 'degraded' | 'down';
  port: number;
  host: string;
  uptime: string;
  cpu: number;
  memory: number;
  latency: number;
  requests_per_min?: number;
  connections?: number;
  queue_size?: number;
}

const services: Service[] = [
  {
    name: 'Kong API Gateway',
    type: 'api',
    status: 'healthy',
    port: 8100,
    host: 'kong',
    uptime: '15d 4h 23m',
    cpu: 12,
    memory: 34,
    latency: 8,
    requests_per_min: 4521,
  },
  {
    name: 'FastAPI Backend',
    type: 'api',
    status: 'healthy',
    port: 8000,
    host: 'api',
    uptime: '15d 4h 23m',
    cpu: 28,
    memory: 45,
    latency: 12,
    requests_per_min: 3892,
  },
  {
    name: 'MySQL Database',
    type: 'database',
    status: 'healthy',
    port: 3306,
    host: 'mysql',
    uptime: '15d 4h 23m',
    cpu: 15,
    memory: 62,
    latency: 3,
    connections: 45,
  },
  {
    name: 'MinIO Storage',
    type: 'storage',
    status: 'healthy',
    port: 9000,
    host: 'minio',
    uptime: '15d 4h 23m',
    cpu: 8,
    memory: 28,
    latency: 15,
  },
  {
    name: 'ClamAV Scanner',
    type: 'scanner',
    status: 'healthy',
    port: 3310,
    host: 'clamav',
    uptime: '15d 4h 22m',
    cpu: 45,
    memory: 78,
    latency: 120,
  },
  {
    name: 'Keycloak Auth',
    type: 'auth',
    status: 'healthy',
    port: 8080,
    host: 'keycloak',
    uptime: '15d 4h 23m',
    cpu: 18,
    memory: 56,
    latency: 25,
  },
  {
    name: 'RabbitMQ',
    type: 'queue',
    status: 'healthy',
    port: 5672,
    host: 'rabbitmq',
    uptime: '15d 4h 23m',
    cpu: 5,
    memory: 22,
    latency: 2,
    queue_size: 128,
  },
  {
    name: 'Caddy Server',
    type: 'api',
    status: 'healthy',
    port: 9443,
    host: 'caddy',
    uptime: '15d 4h 23m',
    cpu: 3,
    memory: 12,
    latency: 5,
  },
];

const serviceIcons: Record<Service['type'], React.ElementType> = {
  api: Globe,
  database: Database,
  cache: Zap,
  queue: Network,
  storage: HardDrive,
  scanner: Activity,
  auth: Settings,
};

export default function AdminInfrastructure() {
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const refreshData = () => {
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
      setLastUpdated(new Date());
    }, 1500);
  };

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdated(new Date());
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const healthyServices = services.filter(s => s.status === 'healthy').length;
  const totalServices = services.length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Infrastructure</h1>
          <p className="text-gray-400 mt-1">Monitor all services and system health</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-400 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Last updated: {lastUpdated.toLocaleTimeString()}
          </div>
          <button
            onClick={refreshData}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Overall Health */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50 md:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">System Health</h3>
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
              healthyServices === totalServices 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-yellow-500/20 text-yellow-400'
            }`}>
              {healthyServices === totalServices ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <AlertTriangle className="w-4 h-4" />
              )}
              <span className="text-sm font-medium">
                {healthyServices === totalServices ? 'All Systems Operational' : 'Partial Degradation'}
              </span>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-gray-700/30 rounded-xl">
              <p className="text-3xl font-bold text-green-400">{healthyServices}</p>
              <p className="text-sm text-gray-400">Healthy</p>
            </div>
            <div className="text-center p-4 bg-gray-700/30 rounded-xl">
              <p className="text-3xl font-bold text-yellow-400">0</p>
              <p className="text-sm text-gray-400">Degraded</p>
            </div>
            <div className="text-center p-4 bg-gray-700/30 rounded-xl">
              <p className="text-3xl font-bold text-red-400">0</p>
              <p className="text-sm text-gray-400">Down</p>
            </div>
          </div>
        </div>

        {/* Cluster Resources */}
        <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">CPU Usage</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Total</span>
              <span className="text-white">18%</span>
            </div>
            <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full" style={{ width: '18%' }} />
            </div>
            <p className="text-xs text-gray-500">8 cores available</p>
          </div>
        </div>

        <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50">
          <div className="flex items-center gap-2 mb-4">
            <MemoryStick className="w-5 h-5 text-purple-400" />
            <h3 className="text-lg font-semibold text-white">Memory</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Used</span>
              <span className="text-white">12.4 / 32 GB</span>
            </div>
            <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full" style={{ width: '39%' }} />
            </div>
            <p className="text-xs text-gray-500">39% utilization</p>
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
              className={`bg-gray-800/50 rounded-xl p-5 border transition-all hover:border-gray-600 ${
                service.status === 'healthy' ? 'border-gray-700/50' :
                service.status === 'degraded' ? 'border-yellow-500/50' :
                'border-red-500/50'
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
                    <h4 className="text-white font-medium text-sm">{service.name}</h4>
                    <p className="text-xs text-gray-500">{service.host}:{service.port}</p>
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
                  <span className="text-gray-400">CPU</span>
                  <span className="text-white">{service.cpu}%</span>
                </div>
                <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
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
                  <span className="text-gray-400">Memory</span>
                  <span className="text-white">{service.memory}%</span>
                </div>
                <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${
                      service.memory > 80 ? 'bg-red-500' :
                      service.memory > 60 ? 'bg-yellow-500' :
                      'bg-blue-500'
                    }`}
                    style={{ width: `${service.memory}%` }}
                  />
                </div>

                <div className="pt-2 border-t border-gray-700 flex justify-between text-xs">
                  <span className="text-gray-400">Latency</span>
                  <span className={`${
                    service.latency > 100 ? 'text-yellow-400' : 'text-green-400'
                  }`}>{service.latency}ms</span>
                </div>

                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Uptime</span>
                  <span className="text-gray-300">{service.uptime}</span>
                </div>

                {service.requests_per_min && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Requests/min</span>
                    <span className="text-cyan-400">{service.requests_per_min.toLocaleString()}</span>
                  </div>
                )}

                {service.connections !== undefined && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Connections</span>
                    <span className="text-purple-400">{service.connections}</span>
                  </div>
                )}

                {service.queue_size !== undefined && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Queue Size</span>
                    <span className="text-orange-400">{service.queue_size}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Docker Containers */}
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Container className="w-5 h-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">Docker Containers</h3>
          </div>
          <span className="text-sm text-green-400">8 running</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-gray-400 border-b border-gray-700">
                <th className="pb-3 font-medium">Container</th>
                <th className="pb-3 font-medium">Image</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Ports</th>
                <th className="pb-3 font-medium">CPU</th>
                <th className="pb-3 font-medium">Memory</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {[
                { name: 'file-management-api', image: 'filemanagement:latest', status: 'running', ports: '8000', cpu: '2.4%', memory: '256MB' },
                { name: 'file-management-kong', image: 'kong:latest', status: 'running', ports: '8100, 8001', cpu: '0.8%', memory: '128MB' },
                { name: 'file-management-mysql', image: 'mysql:8.0', status: 'running', ports: '3306', cpu: '1.2%', memory: '512MB' },
                { name: 'file-management-minio', image: 'minio/minio:latest', status: 'running', ports: '9000, 9001', cpu: '0.5%', memory: '192MB' },
                { name: 'file-management-clamav', image: 'clamav/clamav:latest', status: 'running', ports: '3310', cpu: '3.8%', memory: '1.2GB' },
                { name: 'file-management-keycloak', image: 'keycloak/keycloak:latest', status: 'running', ports: '8080', cpu: '1.5%', memory: '768MB' },
                { name: 'file-management-rabbitmq', image: 'rabbitmq:3-management', status: 'running', ports: '5672, 15672', cpu: '0.3%', memory: '128MB' },
                { name: 'file-management-caddy', image: 'caddy:latest', status: 'running', ports: '9443', cpu: '0.1%', memory: '32MB' },
              ].map((container, i) => (
                <tr key={i} className="hover:bg-gray-700/30">
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-400 rounded-full" />
                      <span className="text-white text-sm">{container.name}</span>
                    </div>
                  </td>
                  <td className="py-3 text-gray-400 text-sm">{container.image}</td>
                  <td className="py-3">
                    <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
                      {container.status}
                    </span>
                  </td>
                  <td className="py-3 text-gray-400 text-sm">{container.ports}</td>
                  <td className="py-3 text-white text-sm">{container.cpu}</td>
                  <td className="py-3 text-white text-sm">{container.memory}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Network Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50">
          <div className="flex items-center gap-2 mb-6">
            <Wifi className="w-5 h-5 text-cyan-400" />
            <h3 className="text-lg font-semibold text-white">Network I/O</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-700/30 rounded-lg">
              <div>
                <p className="text-sm text-gray-400">Inbound</p>
                <p className="text-xl font-bold text-white">2.4 GB/s</p>
              </div>
              <div className="h-12 w-32 flex items-end gap-1">
                {[40, 55, 45, 60, 50, 70, 65, 80, 75, 85, 90, 78].map((h, i) => (
                  <div key={i} className="flex-1 bg-cyan-500/50 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-gray-700/30 rounded-lg">
              <div>
                <p className="text-sm text-gray-400">Outbound</p>
                <p className="text-xl font-bold text-white">1.8 GB/s</p>
              </div>
              <div className="h-12 w-32 flex items-end gap-1">
                {[35, 45, 40, 50, 45, 55, 50, 60, 55, 65, 70, 58].map((h, i) => (
                  <div key={i} className="flex-1 bg-purple-500/50 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50">
          <div className="flex items-center gap-2 mb-6">
            <HardDrive className="w-5 h-5 text-orange-400" />
            <h3 className="text-lg font-semibold text-white">Disk I/O</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-700/30 rounded-lg">
              <div>
                <p className="text-sm text-gray-400">Read</p>
                <p className="text-xl font-bold text-white">450 MB/s</p>
              </div>
              <div className="h-12 w-32 flex items-end gap-1">
                {[50, 45, 60, 55, 70, 65, 75, 70, 80, 75, 85, 82].map((h, i) => (
                  <div key={i} className="flex-1 bg-orange-500/50 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-gray-700/30 rounded-lg">
              <div>
                <p className="text-sm text-gray-400">Write</p>
                <p className="text-xl font-bold text-white">320 MB/s</p>
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
