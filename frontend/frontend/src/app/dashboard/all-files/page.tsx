"use client";

import React, { useState } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import {
  FileStack,
  Search,
  Filter,
  Download,
  Trash2,
  Eye,
  MoreHorizontal,
  File,
  FileText,
  Image,
  Film,
  Music,
  Archive,
  Shield,
  AlertTriangle,
  CheckCircle,
  Clock,
  Building2,
} from 'lucide-react';

// Mock all files data
const allFiles = [
  { id: 1, name: 'Q4_Financial_Report.pdf', type: 'pdf', size: 2.3 * 1024 * 1024, organization: 'Acme Healthcare', user: 'John Smith', status: 'clean', uploadedAt: '2 hours ago' },
  { id: 2, name: 'Product_Roadmap_2025.xlsx', type: 'xlsx', size: 1.2 * 1024 * 1024, organization: 'TechCorp Finance', user: 'Sarah Johnson', status: 'clean', uploadedAt: '4 hours ago' },
  { id: 3, name: 'Team_Photo_2025.jpg', type: 'jpg', size: 8.4 * 1024 * 1024, organization: 'DataFlow Systems', user: 'Mike Wilson', status: 'scanning', uploadedAt: '6 hours ago' },
  { id: 4, name: 'Customer_Database.csv', type: 'csv', size: 5.4 * 1024 * 1024, organization: 'CloudNine Inc', user: 'Emily Davis', status: 'clean', uploadedAt: '1 day ago' },
  { id: 5, name: 'Brand_Guidelines.pdf', type: 'pdf', size: 3.3 * 1024 * 1024, organization: 'StartupX', user: 'Alex Brown', status: 'clean', uploadedAt: '2 days ago' },
  { id: 6, name: 'Suspicious_File.exe', type: 'exe', size: 1.1 * 1024 * 1024, organization: 'Unknown', user: 'Anonymous', status: 'quarantined', uploadedAt: '3 days ago' },
  { id: 7, name: 'Marketing_Video.mp4', type: 'mp4', size: 125 * 1024 * 1024, organization: 'Acme Healthcare', user: 'John Smith', status: 'clean', uploadedAt: '4 days ago' },
  { id: 8, name: 'Employee_Data.zip', type: 'zip', size: 45 * 1024 * 1024, organization: 'TechCorp Finance', user: 'Sarah Johnson', status: 'clean', uploadedAt: '5 days ago' },
];

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const getFileIcon = (type: string) => {
  switch (type) {
    case 'pdf': return <FileText className="w-5 h-5 text-red-400" />;
    case 'xlsx':
    case 'csv': return <FileText className="w-5 h-5 text-green-400" />;
    case 'jpg':
    case 'png': return <Image className="w-5 h-5 text-blue-400" />;
    case 'mp4': return <Film className="w-5 h-5 text-purple-400" />;
    case 'mp3': return <Music className="w-5 h-5 text-pink-400" />;
    case 'zip': return <Archive className="w-5 h-5 text-yellow-400" />;
    default: return <File className="w-5 h-5 text-gray-400" />;
  }
};

const getStatusBadge = (status: string, isDark: boolean) => {
  switch (status) {
    case 'clean':
      return (
        <span className="flex items-center gap-1 text-green-400 text-sm">
          <CheckCircle className="w-4 h-4" /> Clean
        </span>
      );
    case 'scanning':
      return (
        <span className="flex items-center gap-1 text-yellow-400 text-sm">
          <Clock className="w-4 h-4 animate-spin" /> Scanning...
        </span>
      );
    case 'quarantined':
      return (
        <span className="flex items-center gap-1 text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4" /> Quarantined
        </span>
      );
    default:
      return null;
  }
};

export default function AllFilesPage() {
  const { isDark } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const filteredFiles = allFiles.filter(file => {
    const matchesSearch = file.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         file.organization.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === 'all' || file.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const totalSize = allFiles.reduce((acc, f) => acc + f.size, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>All Files</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>View and manage all files across organizations</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <FileStack className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{allFiles.length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Total Files</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{allFiles.filter(f => f.status === 'clean').length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Clean</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{allFiles.filter(f => f.status === 'quarantined').length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Quarantined</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <Shield className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{formatBytes(totalSize)}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Total Size</p>
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
            placeholder="Search files..."
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
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className={`px-4 py-2 rounded-lg border ${
            isDark 
              ? 'bg-gray-700 border-gray-600 text-white' 
              : 'bg-gray-50 border-gray-200 text-gray-900'
          } focus:outline-none focus:ring-2 focus:ring-indigo-500`}
        >
          <option value="all">All Status</option>
          <option value="clean">Clean</option>
          <option value="scanning">Scanning</option>
          <option value="quarantined">Quarantined</option>
        </select>
      </div>

      {/* Files Table */}
      <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <table className="w-full">
          <thead className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
            <tr>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>File</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Organization</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Uploaded By</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Size</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Status</th>
              <th className={`px-6 py-4 text-right text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Actions</th>
            </tr>
          </thead>
          <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
            {filteredFiles.map((file) => (
              <tr key={file.id} className={isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
                      {getFileIcon(file.type)}
                    </div>
                    <div>
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{file.name}</p>
                      <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{file.uploadedAt}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <Building2 className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                    <span className={isDark ? 'text-white' : 'text-gray-900'}>{file.organization}</span>
                  </div>
                </td>
                <td className={`px-6 py-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{file.user}</td>
                <td className={`px-6 py-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{formatBytes(file.size)}</td>
                <td className="px-6 py-4">{getStatusBadge(file.status, isDark)}</td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                      <Eye className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                    </button>
                    <button className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                      <Download className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                    </button>
                    <button className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                      <MoreHorizontal className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
