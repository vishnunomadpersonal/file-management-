"use client";

import React, { useState } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import {
  Globe,
  Activity,
  Shield,
  Clock,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Settings,
  BarChart3,
} from 'lucide-react';

// Mock API Gateway stats
const gatewayStats = {
  totalRequests: 1284723,
  avgLatency: 45,
  successRate: 99.2,
  activeRoutes: 24,
  rateLimitHits: 156,
  blockedRequests: 23,
};

const routes = [
  { path: '/api/v1/files', method: 'GET', requests: 450000, avgLatency: 35, status: 'healthy' },
  { path: '/api/v1/files', method: 'POST', requests: 125000, avgLatency: 120, status: 'healthy' },
  { path: '/api/v1/auth/login', method: 'POST', requests: 89000, avgLatency: 45, status: 'healthy' },
  { path: '/api/v1/users', method: 'GET', requests: 67000, avgLatency: 28, status: 'healthy' },
  { path: '/api/v1/organizations', method: 'GET', requests: 45000, avgLatency: 32, status: 'healthy' },
  { path: '/api/v1/scan', method: 'POST', requests: 125000, avgLatency: 250, status: 'warning' },
  { path: '/api/v1/quarantine', method: 'GET', requests: 12000, avgLatency: 22, status: 'healthy' },
  { path: '/api/v1/analytics', method: 'GET', requests: 34000, avgLatency: 180, status: 'healthy' },
];

const recentErrors = [
  { code: 429, message: 'Rate limit exceeded', count: 156, lastOccurred: '2 min ago' },
  { code: 500, message: 'Internal server error', count: 12, lastOccurred: '15 min ago' },
  { code: 503, message: 'Service unavailable', count: 5, lastOccurred: '1 hour ago' },
  { code: 401, message: 'Unauthorized', count: 89, lastOccurred: '30 sec ago' },
];

export default function ApiGatewayPage() {
  const { isDark } = useTheme();
  const [selectedTab, setSelectedTab] = useState<'routes' | 'errors'>('routes');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>API Gateway</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Monitor API traffic and performance</p>
        </div>
        <div className="flex items-center gap-3">
          <button className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
            isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'
          } transition-colors`}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors">
            <Settings className="w-4 h-4" />
            Configure
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-2 mb-2">
            <Globe className="w-4 h-4 text-blue-400" />
            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Requests Today</span>
          </div>
          <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>1.28M</p>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-purple-400" />
            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Avg Latency</span>
          </div>
          <p className={`text-2xl font-bold text-green-400`}>{gatewayStats.avgLatency}ms</p>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Success Rate</span>
          </div>
          <p className={`text-2xl font-bold text-green-400`}>{gatewayStats.successRate}%</p>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Active Routes</span>
          </div>
          <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{gatewayStats.activeRoutes}</p>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-4 h-4 text-yellow-400" />
            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Rate Limited</span>
          </div>
          <p className={`text-2xl font-bold text-yellow-400`}>{gatewayStats.rateLimitHits}</p>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-2 mb-2">
            <XCircle className="w-4 h-4 text-red-400" />
            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Blocked</span>
          </div>
          <p className={`text-2xl font-bold text-red-400`}>{gatewayStats.blockedRequests}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className={`flex gap-2 p-1 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
        <button
          onClick={() => setSelectedTab('routes')}
          className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            selectedTab === 'routes'
              ? 'bg-indigo-600 text-white'
              : isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Routes
        </button>
        <button
          onClick={() => setSelectedTab('errors')}
          className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            selectedTab === 'errors'
              ? 'bg-indigo-600 text-white'
              : isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Errors
        </button>
      </div>

      {/* Content */}
      {selectedTab === 'routes' && (
        <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <table className="w-full">
            <thead className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
              <tr>
                <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Route</th>
                <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Method</th>
                <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Requests</th>
                <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Avg Latency</th>
                <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Status</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {routes.map((route, i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}>
                  <td className="px-6 py-4">
                    <code className={`px-2 py-1 rounded ${isDark ? 'bg-gray-700 text-cyan-400' : 'bg-gray-100 text-cyan-600'}`}>
                      {route.path}
                    </code>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                      route.method === 'GET' ? 'bg-green-500/20 text-green-400' :
                      route.method === 'POST' ? 'bg-blue-500/20 text-blue-400' :
                      route.method === 'PUT' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      {route.method}
                    </span>
                  </td>
                  <td className={`px-6 py-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {route.requests.toLocaleString()}
                  </td>
                  <td className={`px-6 py-4 ${route.avgLatency > 100 ? 'text-yellow-400' : 'text-green-400'}`}>
                    {route.avgLatency}ms
                  </td>
                  <td className="px-6 py-4">
                    <span className={`flex items-center gap-1 ${
                      route.status === 'healthy' ? 'text-green-400' : 'text-yellow-400'
                    }`}>
                      {route.status === 'healthy' ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                      {route.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedTab === 'errors' && (
        <div className={`rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="p-4 space-y-4">
            {recentErrors.map((error, i) => (
              <div key={i} className={`flex items-center justify-between p-4 rounded-lg ${isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                <div className="flex items-center gap-4">
                  <div className={`px-3 py-2 rounded-lg font-mono font-bold ${
                    error.code >= 500 ? 'bg-red-500/20 text-red-400' :
                    error.code >= 400 ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-blue-500/20 text-blue-400'
                  }`}>
                    {error.code}
                  </div>
                  <div>
                    <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{error.message}</p>
                    <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Last: {error.lastOccurred}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{error.count}</p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>occurrences</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
