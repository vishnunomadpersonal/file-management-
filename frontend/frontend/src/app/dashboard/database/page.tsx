"use client";

import React from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import {
  Database,
  HardDrive,
  Clock,
  Activity,
  RefreshCw,
  Download,
  Play,
  Table,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';

// Mock database stats
const databaseStats = {
  size: '2.4 GB',
  tables: 24,
  connections: 45,
  maxConnections: 100,
  uptime: '45 days',
  queries: '1.2M/day',
  avgQueryTime: '12ms',
  slowQueries: 3,
};

const tables = [
  { name: 'files', rows: 892341, size: '1.2 GB', lastUpdated: '2 min ago' },
  { name: 'users', rows: 4823, size: '45 MB', lastUpdated: '5 min ago' },
  { name: 'organizations', rows: 156, size: '12 MB', lastUpdated: '1 hour ago' },
  { name: 'audit_logs', rows: 2456789, size: '890 MB', lastUpdated: '1 min ago' },
  { name: 'api_keys', rows: 1234, size: '8 MB', lastUpdated: '3 hours ago' },
  { name: 'sessions', rows: 12456, size: '56 MB', lastUpdated: '30 sec ago' },
  { name: 'virus_scans', rows: 892341, size: '120 MB', lastUpdated: '2 min ago' },
  { name: 'quarantine', rows: 23, size: '2 MB', lastUpdated: '6 hours ago' },
];

const recentBackups = [
  { id: 1, type: 'Full', size: '2.4 GB', status: 'completed', timestamp: '2025-12-06 03:00:00' },
  { id: 2, type: 'Incremental', size: '120 MB', status: 'completed', timestamp: '2025-12-06 09:00:00' },
  { id: 3, type: 'Incremental', size: '85 MB', status: 'completed', timestamp: '2025-12-06 15:00:00' },
  { id: 4, type: 'Incremental', size: '45 MB', status: 'in_progress', timestamp: '2025-12-06 17:00:00' },
];

export default function DatabasePage() {
  const { isDark } = useTheme();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Database</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Monitor and manage database performance</p>
        </div>
        <div className="flex items-center gap-3">
          <button className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
            isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'
          } transition-colors`}>
            <Download className="w-4 h-4" />
            Backup Now
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors">
            <Play className="w-4 h-4" />
            Run Query
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <Database className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{databaseStats.size}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Database Size</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <Activity className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{databaseStats.connections}/{databaseStats.maxConnections}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Connections</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <Clock className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{databaseStats.avgQueryTime}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Avg Query Time</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/20 rounded-lg">
              <Table className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{databaseStats.tables}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Tables</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tables List */}
      <div className={`rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className="p-4 border-b border-gray-700">
          <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Database Tables</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
              <tr>
                <th className={`px-6 py-3 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Table Name</th>
                <th className={`px-6 py-3 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Rows</th>
                <th className={`px-6 py-3 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Size</th>
                <th className={`px-6 py-3 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Last Updated</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {tables.map((table, i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Table className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                      <span className={`font-mono ${isDark ? 'text-white' : 'text-gray-900'}`}>{table.name}</span>
                    </div>
                  </td>
                  <td className={`px-6 py-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{table.rows.toLocaleString()}</td>
                  <td className={`px-6 py-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{table.size}</td>
                  <td className={`px-6 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{table.lastUpdated}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Backups */}
      <div className={`rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className="p-4 border-b border-gray-700">
          <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Recent Backups</h2>
        </div>
        <div className="p-4 space-y-3">
          {recentBackups.map((backup) => (
            <div key={backup.id} className={`flex items-center justify-between p-4 rounded-lg ${isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
              <div className="flex items-center gap-4">
                <div className={`p-2 rounded-lg ${backup.status === 'completed' ? 'bg-green-500/20' : 'bg-yellow-500/20'}`}>
                  {backup.status === 'completed' ? (
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  ) : (
                    <RefreshCw className="w-5 h-5 text-yellow-400 animate-spin" />
                  )}
                </div>
                <div>
                  <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{backup.type} Backup</p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{backup.timestamp}</p>
                </div>
              </div>
              <div className="text-right">
                <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{backup.size}</p>
                <p className={`text-sm ${backup.status === 'completed' ? 'text-green-400' : 'text-yellow-400'}`}>
                  {backup.status === 'completed' ? 'Completed' : 'In Progress...'}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
