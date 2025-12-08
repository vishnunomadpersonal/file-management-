"use client";

import React, { useState } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import {
  AlertTriangle,
  Search,
  Trash2,
  RefreshCw,
  Shield,
  File,
  FileText,
  Eye,
  MoreHorizontal,
  Clock,
  Building2,
  XCircle,
} from 'lucide-react';

// Mock quarantined files
const quarantinedFiles = [
  { id: 1, name: 'malware.exe', type: 'exe', size: 1.1 * 1024 * 1024, organization: 'Unknown', user: 'Anonymous', threat: 'Trojan.Generic', detectedAt: '3 hours ago', severity: 'high' },
  { id: 2, name: 'suspicious_script.js', type: 'js', size: 45 * 1024, organization: 'TechCorp Finance', user: 'External', threat: 'Script.Suspicious', detectedAt: '6 hours ago', severity: 'medium' },
  { id: 3, name: 'infected_doc.docx', type: 'docx', size: 2.3 * 1024 * 1024, organization: 'DataFlow Systems', user: 'Mike Wilson', threat: 'Macro.Malware', detectedAt: '1 day ago', severity: 'high' },
  { id: 4, name: 'phishing_pdf.pdf', type: 'pdf', size: 890 * 1024, organization: 'CloudNine Inc', user: 'Emily Davis', threat: 'Phishing.PDF', detectedAt: '2 days ago', severity: 'medium' },
  { id: 5, name: 'ransomware_sample.zip', type: 'zip', size: 5.6 * 1024 * 1024, organization: 'Acme Healthcare', user: 'John Smith', threat: 'Ransom.WannaCry', detectedAt: '3 days ago', severity: 'critical' },
];

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const getSeverityBadge = (severity: string) => {
  switch (severity) {
    case 'critical':
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-500/20 text-red-400">Critical</span>;
    case 'high':
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-500/20 text-orange-400">High</span>;
    case 'medium':
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-500/20 text-yellow-400">Medium</span>;
    case 'low':
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-500/20 text-blue-400">Low</span>;
    default:
      return null;
  }
};

export default function QuarantinePage() {
  const { isDark } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<number[]>([]);

  const filteredFiles = quarantinedFiles.filter(file =>
    file.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    file.threat.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleSelectAll = () => {
    if (selectedFiles.length === filteredFiles.length) {
      setSelectedFiles([]);
    } else {
      setSelectedFiles(filteredFiles.map(f => f.id));
    }
  };

  const toggleSelect = (id: number) => {
    if (selectedFiles.includes(id)) {
      setSelectedFiles(selectedFiles.filter(f => f !== id));
    } else {
      setSelectedFiles([...selectedFiles, id]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Quarantine</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Manage files flagged by virus scanner</p>
        </div>
        <div className="flex items-center gap-3">
          <button className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
            isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'
          } transition-colors`}>
            <RefreshCw className="w-4 h-4" />
            Rescan All
          </button>
          {selectedFiles.length > 0 && (
            <button className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors">
              <Trash2 className="w-4 h-4" />
              Delete Selected ({selectedFiles.length})
            </button>
          )}
        </div>
      </div>

      {/* Alert Banner */}
      <div className={`flex items-center gap-4 p-4 rounded-xl border ${
        isDark ? 'bg-red-500/10 border-red-500/30' : 'bg-red-50 border-red-200'
      }`}>
        <div className="p-2 bg-red-500/20 rounded-lg">
          <AlertTriangle className="w-6 h-6 text-red-400" />
        </div>
        <div className="flex-1">
          <h3 className={`font-semibold ${isDark ? 'text-red-400' : 'text-red-700'}`}>
            {quarantinedFiles.length} Threats Detected
          </h3>
          <p className={`text-sm ${isDark ? 'text-red-400/70' : 'text-red-600'}`}>
            These files have been isolated to protect your systems. Review and take action.
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{quarantinedFiles.length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Total Quarantined</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <XCircle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{quarantinedFiles.filter(f => f.severity === 'critical').length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Critical</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-500/20 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-orange-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{quarantinedFiles.filter(f => f.severity === 'high').length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>High Risk</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <Shield className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>100%</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Detection Rate</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className={`flex items-center gap-4 p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className="flex-1 relative">
          <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
          <input
            type="text"
            placeholder="Search quarantined files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`w-full pl-10 pr-4 py-2 rounded-lg border ${
              isDark 
                ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' 
                : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-500'
            } focus:outline-none focus:ring-2 focus:ring-red-500`}
          />
        </div>
      </div>

      {/* Table */}
      <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <table className="w-full">
          <thead className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
            <tr>
              <th className="px-6 py-4 text-left">
                <input
                  type="checkbox"
                  checked={selectedFiles.length === filteredFiles.length && filteredFiles.length > 0}
                  onChange={toggleSelectAll}
                  className="rounded border-gray-400"
                />
              </th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>File</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Threat</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Severity</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Organization</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Detected</th>
              <th className={`px-6 py-4 text-right text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Actions</th>
            </tr>
          </thead>
          <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
            {filteredFiles.map((file) => (
              <tr key={file.id} className={`${isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'} ${selectedFiles.includes(file.id) ? (isDark ? 'bg-red-500/10' : 'bg-red-50') : ''}`}>
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedFiles.includes(file.id)}
                    onChange={() => toggleSelect(file.id)}
                    className="rounded border-gray-400"
                  />
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-red-500/20 rounded-lg">
                      <FileText className="w-5 h-5 text-red-400" />
                    </div>
                    <div>
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{file.name}</p>
                      <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{formatBytes(file.size)}</p>
                    </div>
                  </div>
                </td>
                <td className={`px-6 py-4 ${isDark ? 'text-red-400' : 'text-red-600'} font-mono text-sm`}>{file.threat}</td>
                <td className="px-6 py-4">{getSeverityBadge(file.severity)}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <Building2 className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                    <span className={isDark ? 'text-white' : 'text-gray-900'}>{file.organization}</span>
                  </div>
                </td>
                <td className={`px-6 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {file.detectedAt}
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                      <Eye className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                    </button>
                    <button className={`p-2 rounded-lg hover:bg-red-500/20`}>
                      <Trash2 className="w-4 h-4 text-red-400" />
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
