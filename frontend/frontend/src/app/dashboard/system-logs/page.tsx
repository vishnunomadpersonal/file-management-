"use client";

import React, { useState } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import {
  Activity,
  Search,
  Filter,
  Download,
  AlertTriangle,
  Info,
  CheckCircle,
  XCircle,
  Clock,
  Server,
  User,
  Shield,
} from 'lucide-react';

// Mock logs data
const systemLogs = [
  { id: 1, level: 'info', message: 'User john@acme.com logged in successfully', source: 'Auth Service', timestamp: '2025-12-06 17:45:23', ip: '192.168.1.100' },
  { id: 2, level: 'warning', message: 'High memory usage detected on MinIO service (85%)', source: 'Monitoring', timestamp: '2025-12-06 17:44:12', ip: null },
  { id: 3, level: 'error', message: 'Failed to connect to external API endpoint', source: 'API Gateway', timestamp: '2025-12-06 17:43:55', ip: null },
  { id: 4, level: 'info', message: 'File uploaded: quarterly_report.pdf (2.3MB)', source: 'File Service', timestamp: '2025-12-06 17:42:30', ip: '192.168.1.105' },
  { id: 5, level: 'success', message: 'Virus scan completed: 0 threats detected', source: 'ClamAV', timestamp: '2025-12-06 17:41:15', ip: null },
  { id: 6, level: 'warning', message: 'Rate limit exceeded for API key: sk_live_xxx', source: 'API Gateway', timestamp: '2025-12-06 17:40:00', ip: '203.0.113.50' },
  { id: 7, level: 'info', message: 'Database backup completed successfully', source: 'MySQL', timestamp: '2025-12-06 17:35:00', ip: null },
  { id: 8, level: 'error', message: 'Malware detected in uploaded file: suspicious.exe', source: 'ClamAV', timestamp: '2025-12-06 17:30:22', ip: '192.168.1.110' },
  { id: 9, level: 'info', message: 'New organization created: TechCorp Finance', source: 'Platform', timestamp: '2025-12-06 17:25:00', ip: '192.168.1.1' },
  { id: 10, level: 'success', message: 'SSL certificate renewed for api.filevault.com', source: 'Certificates', timestamp: '2025-12-06 17:20:00', ip: null },
];

const getLevelIcon = (level: string) => {
  switch (level) {
    case 'info': return <Info className="w-4 h-4 text-blue-400" />;
    case 'warning': return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
    case 'error': return <XCircle className="w-4 h-4 text-red-400" />;
    case 'success': return <CheckCircle className="w-4 h-4 text-green-400" />;
    default: return <Activity className="w-4 h-4 text-gray-400" />;
  }
};

const getLevelBadge = (level: string) => {
  const colors: Record<string, string> = {
    info: 'bg-blue-500/20 text-blue-400',
    warning: 'bg-yellow-500/20 text-yellow-400',
    error: 'bg-red-500/20 text-red-400',
    success: 'bg-green-500/20 text-green-400',
  };
  return `px-2 py-1 text-xs font-medium rounded-full ${colors[level] || 'bg-gray-500/20 text-gray-400'}`;
};

export default function SystemLogsPage() {
  const { isDark } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [filterLevel, setFilterLevel] = useState<string>('all');

  const filteredLogs = systemLogs.filter(log => {
    const matchesSearch = log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         log.source.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesLevel = filterLevel === 'all' || log.level === filterLevel;
    return matchesSearch && matchesLevel;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>System Logs</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Monitor system events and activities</p>
        </div>
        <button className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
          isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'
        } transition-colors`}>
          <Download className="w-4 h-4" />
          Export Logs
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <Info className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{systemLogs.filter(l => l.level === 'info').length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Info</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{systemLogs.filter(l => l.level === 'warning').length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Warnings</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <XCircle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{systemLogs.filter(l => l.level === 'error').length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Errors</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{systemLogs.filter(l => l.level === 'success').length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Success</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className={`flex items-center gap-4 p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className="flex-1 relative">
          <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
          <input
            type="text"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`w-full pl-10 pr-4 py-2 rounded-lg border ${
              isDark 
                ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' 
                : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-500'
            } focus:outline-none focus:ring-2 focus:ring-indigo-500`}
          />
        </div>
        <select
          value={filterLevel}
          onChange={(e) => setFilterLevel(e.target.value)}
          className={`px-4 py-2 rounded-lg border ${
            isDark 
              ? 'bg-gray-700 border-gray-600 text-white' 
              : 'bg-gray-50 border-gray-200 text-gray-900'
          } focus:outline-none focus:ring-2 focus:ring-indigo-500`}
        >
          <option value="all">All Levels</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
          <option value="success">Success</option>
        </select>
      </div>

      {/* Logs List */}
      <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className="divide-y divide-gray-700">
          {filteredLogs.map((log) => (
            <div key={log.id} className={`p-4 ${isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}`}>
              <div className="flex items-start gap-4">
                <div className={`p-2 rounded-lg ${
                  log.level === 'error' ? 'bg-red-500/20' :
                  log.level === 'warning' ? 'bg-yellow-500/20' :
                  log.level === 'success' ? 'bg-green-500/20' :
                  'bg-blue-500/20'
                }`}>
                  {getLevelIcon(log.level)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className={getLevelBadge(log.level)}>{log.level.toUpperCase()}</span>
                    <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{log.source}</span>
                  </div>
                  <p className={`${isDark ? 'text-white' : 'text-gray-900'}`}>{log.message}</p>
                  <div className="flex items-center gap-4 mt-2">
                    <span className={`flex items-center gap-1 text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      <Clock className="w-3 h-3" />
                      {log.timestamp}
                    </span>
                    {log.ip && (
                      <span className={`flex items-center gap-1 text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                        <Server className="w-3 h-3" />
                        {log.ip}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
