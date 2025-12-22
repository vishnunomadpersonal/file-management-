"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { organizationsApi, filesApi, ApiOrganization, ApiFile } from '@/lib/api';
import {
  Building2,
  FileStack,
  HardDrive,
  ArrowLeft,
  Search,
  Download,
  Eye,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Shield,
  File,
  Image,
  FileText,
  Video,
  Music,
  Archive,
  Calendar,
  ChevronRight,
  FolderOpen,
} from 'lucide-react';

// Format bytes to human readable
const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Format date
const formatDate = (dateStr?: string) => {
  if (!dateStr) return 'Unknown';
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

// Get file type icon
function getFileTypeIcon(contentType: string) {
  if (contentType.startsWith('image/')) return Image;
  if (contentType.startsWith('video/')) return Video;
  if (contentType.startsWith('audio/')) return Music;
  if (contentType.includes('pdf')) return FileText;
  if (contentType.includes('zip') || contentType.includes('archive') || contentType.includes('compressed')) return Archive;
  if (contentType.includes('text') || contentType.includes('document')) return FileText;
  return File;
}

// Get virus status badge
function VirusStatusBadge({ status, isQuarantined }: { status: string; isQuarantined: boolean }) {
  if (isQuarantined) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
        <AlertTriangle className="w-3 h-3" />
        Quarantined
      </span>
    );
  }
  
  switch (status) {
    case 'clean':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
          <CheckCircle className="w-3 h-3" />
          Clean
        </span>
      );
    case 'infected':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
          <Shield className="w-3 h-3" />
          Infected
        </span>
      );
    case 'pending':
    case 'scanning':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
          <RefreshCw className="w-3 h-3 animate-spin" />
          Scanning
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-500/20 text-gray-400 border border-gray-500/30">
          Unknown
        </span>
      );
  }
}

// Plan badge component
function PlanBadge({ plan }: { plan: string }) {
  const colors: Record<string, string> = {
    enterprise: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    pro: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    free: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  };
  
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${colors[plan] || colors.free}`}>
      {plan.charAt(0).toUpperCase() + plan.slice(1)}
    </span>
  );
}

export default function PlatformAdminDashboard() {
  const { isDark } = useTheme();
  const [organizations, setOrganizations] = useState<ApiOrganization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<ApiOrganization | null>(null);
  const [files, setFiles] = useState<ApiFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Fetch organizations
  const fetchOrganizations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await organizationsApi.list(0, 100);
      setOrganizations(result.items || []);
    } catch (err) {
      console.error('Failed to fetch organizations:', err);
      setError('Failed to load organizations');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch files for selected organization
  const fetchFilesForOrg = useCallback(async (orgId: string) => {
    try {
      setLoadingFiles(true);
      setError(null);
      const orgFiles = await filesApi.listByOrganization(orgId);
      setFiles(orgFiles);
    } catch (err) {
      console.error('Failed to fetch files:', err);
      setError('Failed to load files for organization');
      setFiles([]);
    } finally {
      setLoadingFiles(false);
    }
  }, []);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  // When an organization is selected, fetch its files
  const handleSelectOrg = (org: ApiOrganization) => {
    setSelectedOrg(org);
    fetchFilesForOrg(org.id);
  };

  // Go back to organizations list
  const handleBack = () => {
    setSelectedOrg(null);
    setFiles([]);
  };

  // Filter organizations by search
  const filteredOrgs = organizations.filter(org =>
    org.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    org.slug.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter files by search
  const filteredFiles = files.filter(file =>
    file.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Download file
  const handleDownload = async (file: ApiFile) => {
    try {
      await filesApi.download(file.id, file.filename);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  // Delete file
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
        <div className="flex items-center gap-4">
          {selectedOrg && (
            <button
              onClick={handleBack}
              className={`p-2 rounded-lg transition-colors ${
                isDark 
                  ? 'hover:bg-gray-700 text-gray-400 hover:text-white' 
                  : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
              }`}
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          <div>
            <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {selectedOrg ? selectedOrg.name : 'Platform Admin'}
            </h1>
            <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {selectedOrg 
                ? `View and manage files for ${selectedOrg.name}`
                : 'Manage organizations and their files'
              }
            </p>
          </div>
        </div>
        
        {selectedOrg && (
          <div className="flex items-center gap-2">
            <PlanBadge plan={selectedOrg.plan} />
            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {formatBytes(selectedOrg.storage_used_bytes)} / {formatBytes(selectedOrg.storage_quota_bytes)}
            </span>
          </div>
        )}
      </div>

      {/* Breadcrumb */}
      {selectedOrg && (
        <div className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <button onClick={handleBack} className="hover:underline">Organizations</button>
          <ChevronRight className="w-4 h-4" />
          <span className={isDark ? 'text-white' : 'text-gray-900'}>{selectedOrg.name}</span>
          <ChevronRight className="w-4 h-4" />
          <span className={isDark ? 'text-white' : 'text-gray-900'}>Files</span>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
        <input
          type="text"
          placeholder={selectedOrg ? 'Search files...' : 'Search organizations...'}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={`w-full pl-12 pr-4 py-3 rounded-xl border transition-colors ${
            isDark 
              ? 'bg-gray-800/50 border-gray-700 text-white placeholder-gray-500 focus:border-indigo-500' 
              : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-500'
          } focus:outline-none focus:ring-2 focus:ring-indigo-500/20`}
        />
      </div>

      {/* Error message */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/20 border border-red-500/30 text-red-400">
          {error}
        </div>
      )}

      {/* Content */}
      {!selectedOrg ? (
        // Organizations List
        <div className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={`p-6 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500/20 rounded-xl">
                  <Building2 className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {organizations.length}
                  </p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Total Organizations
                  </p>
                </div>
              </div>
            </div>
            <div className={`p-6 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-500/20 rounded-xl">
                  <CheckCircle className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {organizations.filter(o => o.is_active).length}
                  </p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Active Organizations
                  </p>
                </div>
              </div>
            </div>
            <div className={`p-6 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-500/20 rounded-xl">
                  <HardDrive className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {formatBytes(organizations.reduce((sum, o) => sum + o.storage_used_bytes, 0))}
                  </p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Total Storage Used
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Organizations Table */}
          <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
            <div className={`px-6 py-4 border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Organizations
              </h2>
            </div>
            
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className={`w-8 h-8 animate-spin ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
              </div>
            ) : filteredOrgs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Building2 className={`w-12 h-12 mb-4 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
                <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>
                  {searchQuery ? 'No organizations match your search' : 'No organizations found'}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Organization
                      </th>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Plan
                      </th>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Storage
                      </th>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Created
                      </th>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Status
                      </th>
                      <th className={`px-6 py-3 text-right text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
                    {filteredOrgs.map((org) => (
                      <tr 
                        key={org.id} 
                        className={`cursor-pointer transition-colors ${
                          isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'
                        }`}
                        onClick={() => handleSelectOrg(org)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
                              <Building2 className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
                            </div>
                            <div>
                              <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                                {org.name}
                              </p>
                              <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                                {org.slug}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <PlanBadge plan={org.plan} />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <p className={`text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {formatBytes(org.storage_used_bytes)}
                            </p>
                            <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                              of {formatBytes(org.storage_quota_bytes)}
                            </p>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <Calendar className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                              {formatDate(org.created_at)}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {org.is_active ? (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                              <CheckCircle className="w-3 h-3" />
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-500/20 text-gray-400 border border-gray-500/30">
                              Inactive
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectOrg(org);
                            }}
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30 transition-colors"
                          >
                            <FolderOpen className="w-4 h-4" />
                            View Files
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        // Files List for Selected Organization
        <div className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={`p-6 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500/20 rounded-xl">
                  <FileStack className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {files.length}
                  </p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Total Files
                  </p>
                </div>
              </div>
            </div>
            <div className={`p-6 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-500/20 rounded-xl">
                  <CheckCircle className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {files.filter(f => f.virus_scan_status === 'clean').length}
                  </p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Clean Files
                  </p>
                </div>
              </div>
            </div>
            <div className={`p-6 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-500/20 rounded-xl">
                  <HardDrive className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {formatBytes(files.reduce((sum, f) => sum + f.size, 0))}
                  </p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Total Size
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Files Table */}
          <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
            <div className={`px-6 py-4 border-b flex items-center justify-between ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Files
              </h2>
              <button
                onClick={() => fetchFilesForOrg(selectedOrg.id)}
                className={`p-2 rounded-lg transition-colors ${
                  isDark ? 'hover:bg-gray-700 text-gray-400' : 'hover:bg-gray-100 text-gray-600'
                }`}
              >
                <RefreshCw className={`w-5 h-5 ${loadingFiles ? 'animate-spin' : ''}`} />
              </button>
            </div>
            
            {loadingFiles ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className={`w-8 h-8 animate-spin ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
              </div>
            ) : filteredFiles.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <FileStack className={`w-12 h-12 mb-4 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
                <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>
                  {searchQuery ? 'No files match your search' : 'No files found for this organization'}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        File
                      </th>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Size
                      </th>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Type
                      </th>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Status
                      </th>
                      <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Uploaded
                      </th>
                      <th className={`px-6 py-3 text-right text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
                    {filteredFiles.map((file) => {
                      const FileIcon = getFileTypeIcon(file.content_type);
                      return (
                        <tr key={file.id} className={isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center gap-3">
                              <div className={`p-2 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
                                <FileIcon className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
                              </div>
                              <div>
                                <p className={`font-medium truncate max-w-[200px] ${isDark ? 'text-white' : 'text-gray-900'}`}>
                                  {file.filename}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                              {formatBytes(file.size)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                              {file.content_type.split('/')[1]?.toUpperCase() || file.content_type}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <VirusStatusBadge status={file.virus_scan_status} isQuarantined={file.is_quarantined} />
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                              {formatDate(file.created_at)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right">
                            <div className="flex items-center justify-end gap-2">
                              {file.download_url && !file.is_quarantined && (
                                <>
                                  <button
                                    onClick={() => window.open(file.download_url, '_blank')}
                                    className={`p-2 rounded-lg transition-colors ${
                                      isDark ? 'hover:bg-gray-700 text-gray-400 hover:text-white' : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
                                    }`}
                                    title="Preview"
                                  >
                                    <Eye className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => handleDownload(file)}
                                    className={`p-2 rounded-lg transition-colors ${
                                      isDark ? 'hover:bg-gray-700 text-gray-400 hover:text-white' : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
                                    }`}
                                    title="Download"
                                  >
                                    <Download className="w-4 h-4" />
                                  </button>
                                </>
                              )}
                              <button
                                onClick={() => handleDelete(file)}
                                className={`p-2 rounded-lg transition-colors text-red-400 ${
                                  isDark ? 'hover:bg-red-500/20' : 'hover:bg-red-50'
                                }`}
                                title="Delete"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
