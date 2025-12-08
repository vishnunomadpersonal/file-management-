"use client";

import React from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import {
  Building2,
  Users,
  FileStack,
  HardDrive,
  AlertTriangle,
  Shield,
  TrendingUp,
  Activity,
  Server,
  Database,
  Globe,
  Clock,
  CheckCircle,
  XCircle,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';

// Format bytes to human readable
const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Mock platform data
const platformStats = {
  organizations: { total: 156, active: 142, new_this_month: 12 },
  users: { total: 4823, active: 3912, new_this_month: 287 },
  files: { total: 892341, uploaded_today: 12847, scanned_today: 12847 },
  storage: { used: 4.2 * 1024 * 1024 * 1024 * 1024, limit: 10 * 1024 * 1024 * 1024 * 1024 },
  threats: { quarantined: 23, blocked_today: 5, total_scanned: 892341 },
  api: { requests_today: 1284723, avg_response_ms: 45, uptime: 99.99 },
};

const recentActivities = [
  { type: 'org_created', message: 'New organization "MedTech Solutions" created', user: 'john@medtech.com', time: '5m ago', icon: Building2 },
  { type: 'threat', message: 'Virus detected and quarantined in org_healthcare', user: 'System', time: '12m ago', icon: Shield },
  { type: 'user', message: 'New admin user added to "FinCorp Inc"', user: 'admin@fincorp.com', time: '23m ago', icon: Users },
  { type: 'api', message: 'API rate limit exceeded for org_startup', user: 'System', time: '45m ago', icon: Globe },
  { type: 'file', message: '10,000 files uploaded by "DataCorp"', user: 'batch@datacorp.com', time: '1h ago', icon: FileStack },
  { type: 'system', message: 'Scheduled backup completed successfully', user: 'System', time: '2h ago', icon: Database },
];

const topOrganizations = [
  { name: 'Acme Healthcare', files: 128473, storage: 32 * 1024 * 1024 * 1024, plan: 'enterprise', trend: 12.5 },
  { name: 'TechCorp Finance', files: 89234, storage: 24 * 1024 * 1024 * 1024, plan: 'enterprise', trend: 8.3 },
  { name: 'DataFlow Systems', files: 67891, storage: 18 * 1024 * 1024 * 1024, plan: 'pro', trend: -2.1 },
  { name: 'CloudNine Inc', files: 45672, storage: 12 * 1024 * 1024 * 1024, plan: 'pro', trend: 15.7 },
  { name: 'StartupX', files: 23456, storage: 6 * 1024 * 1024 * 1024, plan: 'free', trend: 45.2 },
];

const services = [
  { name: 'Kong API Gateway', status: 'healthy', port: 8100, latency: '12ms' },
  { name: 'FastAPI Backend', status: 'healthy', port: 8000, latency: '8ms' },
  { name: 'MySQL Database', status: 'healthy', port: 3306, latency: '3ms' },
  { name: 'MinIO Storage', status: 'healthy', port: 9000, latency: '15ms' },
  { name: 'ClamAV Scanner', status: 'healthy', port: 3000, latency: '45ms' },
  { name: 'Keycloak Auth', status: 'healthy', port: 8080, latency: '22ms' },
  { name: 'RabbitMQ', status: 'healthy', port: 5672, latency: '5ms' },
  { name: 'Celery Workers', status: 'healthy', port: null, latency: null },
];

export default function PlatformAdminDashboard() {
  const { isDark } = useTheme();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Platform Overview</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Monitor and manage all organizations, users, and system health</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-4 py-2 bg-green-500/20 border border-green-500/30 rounded-lg">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-green-400 text-sm font-medium">All Systems Operational</span>
          </div>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Organizations */}
        <div className={`backdrop-blur-sm rounded-2xl p-6 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-blue-500/20 rounded-xl">
              <Building2 className="w-6 h-6 text-blue-400" />
            </div>
            <span className="flex items-center gap-1 text-green-400 text-sm">
              <ArrowUpRight className="w-4 h-4" />
              +{platformStats.organizations.new_this_month}
            </span>
          </div>
          <h3 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{platformStats.organizations.total.toLocaleString()}</h3>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Total Organizations</p>
          <div className="mt-4 flex items-center gap-2">
            <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
              {platformStats.organizations.active} active
            </span>
          </div>
        </div>

        {/* Users */}
        <div className={`backdrop-blur-sm rounded-2xl p-6 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-purple-500/20 rounded-xl">
              <Users className="w-6 h-6 text-purple-400" />
            </div>
            <span className="flex items-center gap-1 text-green-400 text-sm">
              <ArrowUpRight className="w-4 h-4" />
              +{platformStats.users.new_this_month}
            </span>
          </div>
          <h3 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{platformStats.users.total.toLocaleString()}</h3>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Total Users</p>
          <div className="mt-4 flex items-center gap-2">
            <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
              {platformStats.users.active.toLocaleString()} active
            </span>
          </div>
        </div>

        {/* Files */}
        <div className={`backdrop-blur-sm rounded-2xl p-6 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-cyan-500/20 rounded-xl">
              <FileStack className="w-6 h-6 text-cyan-400" />
            </div>
            <span className="flex items-center gap-1 text-green-400 text-sm">
              <TrendingUp className="w-4 h-4" />
              +{platformStats.files.uploaded_today.toLocaleString()}
            </span>
          </div>
          <h3 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{platformStats.files.total.toLocaleString()}</h3>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Total Files</p>
          <div className="mt-4 flex items-center gap-2">
            <span className="text-xs px-2 py-1 bg-cyan-500/20 text-cyan-400 rounded-full">
              {platformStats.files.scanned_today.toLocaleString()} scanned today
            </span>
          </div>
        </div>

        {/* Threats */}
        <div className={`backdrop-blur-sm rounded-2xl p-6 border border-red-500/30 ${isDark ? 'bg-gray-800/50' : 'bg-white'}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-red-500/20 rounded-xl">
              <AlertTriangle className="w-6 h-6 text-red-400" />
            </div>
            <span className="flex items-center gap-1 text-red-400 text-sm">
              <Shield className="w-4 h-4" />
              {platformStats.threats.blocked_today} today
            </span>
          </div>
          <h3 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{platformStats.threats.quarantined}</h3>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Threats Quarantined</p>
          <div className="mt-4 flex items-center gap-2">
            <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
              100% detected
            </span>
          </div>
        </div>
      </div>

      {/* Storage & API Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Platform Storage */}
        <div className={`backdrop-blur-sm rounded-2xl p-6 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center justify-between mb-6">
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Platform Storage</h3>
            <HardDrive className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
          </div>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className={isDark ? 'text-gray-400' : 'text-gray-600'}>Total Used</span>
                <span className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {formatBytes(platformStats.storage.used)} / {formatBytes(platformStats.storage.limit)}
                </span>
              </div>
              <div className={`h-4 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                  style={{ width: `${(platformStats.storage.used / platformStats.storage.limit) * 100}%` }}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-6">
              <div className={`text-center p-3 rounded-lg ${isDark ? 'bg-gray-700/50' : 'bg-gray-100'}`}>
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>4.2</p>
                <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>TB Used</p>
              </div>
              <div className={`text-center p-3 rounded-lg ${isDark ? 'bg-gray-700/50' : 'bg-gray-100'}`}>
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>5.8</p>
                <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>TB Available</p>
              </div>
              <div className={`text-center p-3 rounded-lg ${isDark ? 'bg-gray-700/50' : 'bg-gray-100'}`}>
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>42%</p>
                <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Utilized</p>
              </div>
            </div>
          </div>
        </div>

        {/* API Performance */}
        <div className={`backdrop-blur-sm rounded-2xl p-6 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center justify-between mb-6">
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>API Performance</h3>
            <Globe className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className={`text-center p-4 rounded-xl ${isDark ? 'bg-gray-700/50' : 'bg-gray-100'}`}>
              <p className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>1.28M</p>
              <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Requests Today</p>
            </div>
            <div className={`text-center p-4 rounded-xl ${isDark ? 'bg-gray-700/50' : 'bg-gray-100'}`}>
              <p className="text-3xl font-bold text-green-400">{platformStats.api.avg_response_ms}ms</p>
              <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Avg Response</p>
            </div>
            <div className={`text-center p-4 rounded-xl ${isDark ? 'bg-gray-700/50' : 'bg-gray-100'}`}>
              <p className="text-3xl font-bold text-green-400">{platformStats.api.uptime}%</p>
              <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Uptime</p>
            </div>
          </div>
          <div className="mt-6 h-24 flex items-end justify-between gap-1">
            {/* Mini bar chart for API requests */}
            {[65, 72, 58, 80, 45, 90, 78, 85, 92, 70, 88, 95].map((height, i) => (
              <div
                key={i}
                className="flex-1 bg-gradient-to-t from-blue-500 to-cyan-400 rounded-t opacity-70"
                style={{ height: `${height}%` }}
              />
            ))}
          </div>
          <p className={`text-xs text-center mt-2 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Last 12 hours</p>
        </div>
      </div>

      {/* Services & Activity Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Service Health */}
        <div className={`backdrop-blur-sm rounded-2xl p-6 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center justify-between mb-6">
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Service Health</h3>
            <Server className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
          </div>
          <div className="space-y-3">
            {services.map((service, i) => (
              <div key={i} className={`flex items-center justify-between p-3 rounded-lg ${isDark ? 'bg-gray-700/30' : 'bg-gray-100'}`}>
                <div className="flex items-center gap-3">
                  {service.status === 'healthy' ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-400" />
                  )}
                  <span className={`text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{service.name}</span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  {service.port && (
                    <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>:{service.port}</span>
                  )}
                  {service.latency && (
                    <span className="text-green-400">{service.latency}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className={`backdrop-blur-sm rounded-2xl p-6 border lg:col-span-2 ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center justify-between mb-6">
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Recent Activity</h3>
            <Activity className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
          </div>
          <div className="space-y-4">
            {recentActivities.map((activity, i) => {
              const Icon = activity.icon;
              return (
                <div key={i} className={`flex items-start gap-4 p-3 rounded-lg ${isDark ? 'bg-gray-700/30' : 'bg-gray-100'}`}>
                  <div className={`p-2 rounded-lg ${
                    activity.type === 'threat' ? 'bg-red-500/20' :
                    activity.type === 'org_created' ? 'bg-blue-500/20' :
                    activity.type === 'user' ? 'bg-purple-500/20' :
                    activity.type === 'api' ? 'bg-yellow-500/20' :
                    'bg-gray-500/20'
                  }`}>
                    <Icon className={`w-4 h-4 ${
                      activity.type === 'threat' ? 'text-red-400' :
                      activity.type === 'org_created' ? 'text-blue-400' :
                      activity.type === 'user' ? 'text-purple-400' :
                      activity.type === 'api' ? 'text-yellow-400' :
                      'text-gray-400'
                    }`} />
                  </div>
                  <div className="flex-1">
                    <p className={`text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{activity.message}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{activity.user}</span>
                      <span className={`text-xs ${isDark ? 'text-gray-600' : 'text-gray-300'}`}>•</span>
                      <span className={`text-xs flex items-center gap-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                        <Clock className="w-3 h-3" />
                        {activity.time}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Top Organizations */}
      <div className={`backdrop-blur-sm rounded-2xl p-6 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
        <div className="flex items-center justify-between mb-6">
          <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Top Organizations by Usage</h3>
          <button className="text-sm text-blue-400 hover:text-blue-300">View All</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className={`text-left text-sm border-b ${isDark ? 'text-gray-400 border-gray-700' : 'text-gray-500 border-gray-200'}`}>
                <th className="pb-4 font-medium">Organization</th>
                <th className="pb-4 font-medium">Plan</th>
                <th className="pb-4 font-medium">Files</th>
                <th className="pb-4 font-medium">Storage</th>
                <th className="pb-4 font-medium">Growth</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-200'}`}>
              {topOrganizations.map((org, i) => (
                <tr key={i} className={`${isDark ? 'hover:bg-gray-700/30' : 'hover:bg-gray-50'}`}>
                  <td className="py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center text-white font-bold">
                        {org.name.charAt(0)}
                      </div>
                      <span className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{org.name}</span>
                    </div>
                  </td>
                  <td className="py-4">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      org.plan === 'enterprise' ? 'bg-purple-500/20 text-purple-400' :
                      org.plan === 'pro' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {org.plan}
                    </span>
                  </td>
                  <td className={`py-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{org.files.toLocaleString()}</td>
                  <td className={`py-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{formatBytes(org.storage)}</td>
                  <td className="py-4">
                    <span className={`flex items-center gap-1 ${
                      org.trend >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {org.trend >= 0 ? (
                        <ArrowUpRight className="w-4 h-4" />
                      ) : (
                        <ArrowDownRight className="w-4 h-4" />
                      )}
                      {Math.abs(org.trend)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
