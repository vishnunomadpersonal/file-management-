"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { filesApi, ApiFile } from '@/lib/api';
import {
  FileStack,
  Search,
  Download,
  Trash2,
  Eye,
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
  RefreshCw,
} from 'lucide-react';

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const formatDate = (dateStr?: string) => {
  if (!dateStr) return 'Unknown';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const getFileIcon = (contentType: string) => {
  if (contentType.includes('pdf')) return <FileText className="w-5 h-5 text-red-400" />;
  if (contentType.includes('spreadsheet') || contentType.includes('excel') || contentType.includes('csv')) 
    return <FileText className="w-5 h-5 text-green-400" />;
  if (contentType.startsWith('image/')) return <Image className="w-5 h-5 text-blue-400" />;
  if (contentType.startsWith('video/')) return <Film className="w-5 h-5 text-purple-400" />;
  if (contentType.startsWith('audio/')) return <Music className="w-5 h-5 text-pink-400" />;
  if (contentType.includes('zip') || contentType.includes('archive')) return <Archive className="w-5 h-5 text-yellow-400" />;
  return <File className="w-5 h-5 text-gray-400" />;
};

const getStatusBadge = (file: ApiFile, isDark: boolean) => {
  if (file.is_quarantined) {
    return (
      <span className="flex items-center gap-1 text-red-400 text-sm">
        <AlertTriangle className="w-4 h-4" /> Quarantined
      </span>
    );
  }
  
  switch (file.virus_scan_status) {
    case 'clean':
      return (
        <span className="flex items-center gap-1 text-green-400 text-sm">
          <CheckCircle className="w-4 h-4" /> Clean
        </span>
      );
    case 'scanning':
    case 'pending':
      return (
        <span className="flex items-center gap-1 text-yellow-400 text-sm">
          <Clock className="w-4 h-4 animate-spin" /> Scanning...
        </span>
      );
    case 'infected':
      return (
        <span className="flex items-center gap-1 text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4" /> Infected
        </span>
      );
    default:
      return (
        <span className="flex items-center gap-1 text-gray-400 text-sm">
          <Clock className="w-4 h-4" /> Unknown
        </span>
      );
  }
};

export default function AllFilesPage() {
  const { isDark } = useTheme();
  const [files, setFiles] = useState<ApiFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const filesData = await filesApi.listAllPlatform(0, 100);
      setFiles(filesData);
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setError('Failed to load files');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredFiles = files.filter(file => {
    const matchesSearch = file.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         (file.organization_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                         (file.user_name || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === 'all' || 
                         (filterStatus === 'quarantined' && file.is_quarantined) ||
                         (filterStatus !== 'quarantined' && file.virus_scan_status === filterStatus);
    return matchesSearch && matchesStatus;
  });

  const totalSize = files.reduce((acc, f) => acc + f.size, 0);
  const cleanFiles = files.filter(f => f.virus_scan_status === 'clean' && !f.is_quarantined).length;
  const quarantinedFiles = files.filter(f => f.is_quarantined).length;

  const handleDownload = async (file: ApiFile) => {
    try {
      await filesApi.download(file.id, file.filename);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const handleDelete = async (file: ApiFile) => {
    if (!confirm(`Are you sure you want to delete "${file.filename}"?`)) return;
    
    try {
      await filesApi.delete(file.id);
      setFiles(prev => prev.filter(f => f.id !== file.id));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>All Files</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>View and manage all files across organizations</p>
        </div>
        <button
          onClick={fetchData}
          className={`p-2 rounded-lg transition-colors ${
            isDark ? 'hover:bg-gray-700 text-gray-400' : 'hover:bg-gray-100 text-gray-600'
          }`}
        >
          <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Error message */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/20 border border-red-500/30 text-red-400">
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <FileStack className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{files.length}</p>
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
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{cleanFiles}</p>
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
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{quarantinedFiles}</p>
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
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className={`w-8 h-8 animate-spin ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
          </div>
        ) : filteredFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <FileStack className={`w-12 h-12 mb-4 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
            <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>
              {searchQuery || filterStatus !== 'all' ? 'No files match your filters' : 'No files found'}
            </p>
          </div>
        ) : (
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
                      {getFileIcon(file.content_type)}
                    </div>
                    <div>
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{file.filename}</p>
                      <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{formatDate(file.created_at)}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <Building2 className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                    <span className={isDark ? 'text-white' : 'text-gray-900'}>
                      {file.organization_name || 'No Organization'}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div>
                    <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {file.user_name || 'Unknown User'}
                    </p>
                    {file.user_email && (
                      <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {file.user_email}
                      </p>
                    )}
                  </div>
                </td>
                <td className={`px-6 py-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{formatBytes(file.size)}</td>
                <td className="px-6 py-4">{getStatusBadge(file, isDark)}</td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {file.download_url && !file.is_quarantined && (
                      <>
                        <button 
                          onClick={() => window.open(file.download_url, '_blank')}
                          className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
                          title="Preview"
                        >
                          <Eye className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                        </button>
                        <button 
                          onClick={() => handleDownload(file)}
                          className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
                          title="Download"
                        >
                          <Download className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                        </button>
                      </>
                    )}
                    <button 
                      onClick={() => handleDelete(file)}
                      className={`p-2 rounded-lg text-red-400 ${isDark ? 'hover:bg-red-500/20' : 'hover:bg-red-50'}`}
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        )}
      </div>
    </div>
  );
}
