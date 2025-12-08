"use client";

import React from 'react';
import { useAuth, formatBytes, formatNumber } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';

// ============================================================================
// Icons
// ============================================================================

const Icons = {
  Folder: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  ),
  Users: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
  Cloud: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
  ),
  Shield: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  ArrowUp: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
    </svg>
  ),
  ArrowDown: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
    </svg>
  ),
  Upload: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
    </svg>
  ),
  Download: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
  Eye: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  ),
  File: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  Plus: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
    </svg>
  ),
  MoreHorizontal: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h.01M12 12h.01M19 12h.01M6 12a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0z" />
    </svg>
  ),
};

// ============================================================================
// Stat Card
// ============================================================================

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  color: 'indigo' | 'emerald' | 'amber' | 'rose';
}

function StatCard({ title, value, change, icon, color }: StatCardProps) {
  const { isDark } = useTheme();
  
  const bgColors = {
    indigo: isDark ? 'bg-indigo-900/30' : 'bg-indigo-50',
    emerald: isDark ? 'bg-emerald-900/30' : 'bg-emerald-50',
    amber: isDark ? 'bg-amber-900/30' : 'bg-amber-50',
    rose: isDark ? 'bg-rose-900/30' : 'bg-rose-50',
  };

  const textColors = {
    indigo: isDark ? 'text-indigo-400' : 'text-indigo-600',
    emerald: isDark ? 'text-emerald-400' : 'text-emerald-600',
    amber: isDark ? 'text-amber-400' : 'text-amber-600',
    rose: isDark ? 'text-rose-400' : 'text-rose-600',
  };

  return (
    <div className={`rounded-2xl p-6 border shadow-sm hover:shadow-md transition-shadow ${
      isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'
    }`}>
      <div className="flex items-start justify-between">
        <div className={`p-3 rounded-xl ${bgColors[color]}`}>
          <div className={textColors[color]}>{icon}</div>
        </div>
        {change !== undefined && (
          <div className={`flex items-center gap-1 text-sm ${change >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
            {change >= 0 ? <Icons.ArrowUp /> : <Icons.ArrowDown />}
            <span>{Math.abs(change)}%</span>
          </div>
        )}
      </div>
      <div className="mt-4">
        <h3 className={`text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{title}</h3>
        <p className={`text-3xl font-bold mt-1 ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{value}</p>
      </div>
    </div>
  );
}

// ============================================================================
// Recent Files
// ============================================================================

interface RecentFile {
  id: string;
  name: string;
  type: string;
  size: number;
  uploadedAt: string;
  status: 'clean' | 'scanning' | 'quarantined';
}

const mockRecentFiles: RecentFile[] = [
  { id: '1', name: 'Q4_Financial_Report.pdf', type: 'PDF', size: 2456789, uploadedAt: '2 hours ago', status: 'clean' },
  { id: '2', name: 'Product_Roadmap_2025.xlsx', type: 'Excel', size: 1234567, uploadedAt: '4 hours ago', status: 'clean' },
  { id: '3', name: 'Team_Photo_2025.jpg', type: 'Image', size: 8765432, uploadedAt: '6 hours ago', status: 'scanning' },
  { id: '4', name: 'Customer_Database.csv', type: 'CSV', size: 5678901, uploadedAt: '1 day ago', status: 'clean' },
  { id: '5', name: 'Brand_Guidelines.pdf', type: 'PDF', size: 3456789, uploadedAt: '2 days ago', status: 'clean' },
];

function RecentFiles() {
  const { isDark } = useTheme();
  
  const getFileIcon = (type: string) => {
    const colors: Record<string, string> = {
      'PDF': isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-100 text-red-600',
      'Excel': isDark ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-600',
      'Image': isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-600',
      'CSV': isDark ? 'bg-purple-900/30 text-purple-400' : 'bg-purple-100 text-purple-600',
    };
    return colors[type] || (isDark ? 'bg-gray-700 text-gray-400' : 'bg-gray-100 text-gray-600');
  };

  const getStatusBadge = (status: RecentFile['status']) => {
    switch (status) {
      case 'clean':
        return <span className={`px-2 py-1 text-xs font-medium rounded-full ${isDark ? 'text-emerald-400 bg-emerald-900/30' : 'text-emerald-700 bg-emerald-50'}`}>Clean</span>;
      case 'scanning':
        return <span className={`px-2 py-1 text-xs font-medium rounded-full ${isDark ? 'text-amber-400 bg-amber-900/30' : 'text-amber-700 bg-amber-50'}`}>Scanning...</span>;
      case 'quarantined':
        return <span className={`px-2 py-1 text-xs font-medium rounded-full ${isDark ? 'text-red-400 bg-red-900/30' : 'text-red-700 bg-red-50'}`}>Quarantined</span>;
    }
  };

  return (
    <div className={`rounded-2xl border shadow-sm ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
      <div className={`flex items-center justify-between p-6 border-b ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
        <h2 className={`text-lg font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Recent Files</h2>
        <button className={`text-sm font-medium ${isDark ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-700'}`}>View all</button>
      </div>
      <div className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-50'}`}>
        {mockRecentFiles.map((file) => (
          <div key={file.id} className={`flex items-center gap-4 p-4 transition-colors ${isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}`}>
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${getFileIcon(file.type)}`}>
              <Icons.File />
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium truncate ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{file.name}</p>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{formatBytes(file.size)} • {file.uploadedAt}</p>
            </div>
            <div className="flex items-center gap-3">
              {getStatusBadge(file.status)}
              <button className={`p-1.5 rounded-lg ${isDark ? 'text-gray-500 hover:text-gray-300 hover:bg-gray-700' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}>
                <Icons.MoreHorizontal />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Activity Feed
// ============================================================================

interface Activity {
  id: string;
  action: string;
  user: string;
  target: string;
  time: string;
  type: 'upload' | 'download' | 'view' | 'share';
}

const mockActivity: Activity[] = [
  { id: '1', action: 'uploaded', user: 'John D.', target: 'Q4_Report.pdf', time: '5 min ago', type: 'upload' },
  { id: '2', action: 'downloaded', user: 'Sarah M.', target: 'Product_Specs.docx', time: '15 min ago', type: 'download' },
  { id: '3', action: 'viewed', user: 'Mike R.', target: 'Team_Photo.jpg', time: '1 hour ago', type: 'view' },
  { id: '4', action: 'shared', user: 'Emily K.', target: 'Brand_Guide.pdf', time: '2 hours ago', type: 'share' },
  { id: '5', action: 'uploaded', user: 'Alex T.', target: 'Budget_2025.xlsx', time: '3 hours ago', type: 'upload' },
];

function ActivityFeed() {
  const { isDark } = useTheme();
  
  const getActivityIcon = (type: Activity['type']) => {
    switch (type) {
      case 'upload':
        return <Icons.Upload className={`w-4 h-4 ${isDark ? 'text-indigo-400' : 'text-indigo-600'}`} />;
      case 'download':
        return <Icons.Download className={`w-4 h-4 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`} />;
      case 'view':
        return <Icons.Eye className={`w-4 h-4 ${isDark ? 'text-blue-400' : 'text-blue-600'}`} />;
      case 'share':
        return <Icons.Users className={`w-4 h-4 ${isDark ? 'text-purple-400' : 'text-purple-600'}`} />;
    }
  };

  return (
    <div className={`rounded-2xl border shadow-sm ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
      <div className={`flex items-center justify-between p-6 border-b ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
        <h2 className={`text-lg font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Activity</h2>
        <button className={`text-sm font-medium ${isDark ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-700'}`}>View all</button>
      </div>
      <div className="p-4 space-y-4">
        {mockActivity.map((activity) => (
          <div key={activity.id} className="flex items-start gap-3">
            <div className={`p-2 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
              {getActivityIcon(activity.type)}
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                <span className={`font-medium ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{activity.user}</span>
                {' '}{activity.action}{' '}
                <span className={`font-medium ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{activity.target}</span>
              </p>
              <p className={`text-xs mt-0.5 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Quick Actions (Role-based)
// ============================================================================

function QuickActions() {
  const { isDark } = useTheme();
  const { user } = useAuth();
  
  // Define actions based on role
  const getActionsForRole = () => {
    const baseActions = [
      { icon: <Icons.Eye />, label: 'View Files', color: isDark ? 'bg-gray-700 hover:bg-gray-600 text-gray-200 border border-gray-600' : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200', roles: ['viewer', 'user', 'manager', 'org_admin', 'super_admin'] },
    ];
    
    const uploadActions = [
      { icon: <Icons.Upload />, label: 'Upload Files', color: 'bg-indigo-600 hover:bg-indigo-700 text-white', roles: ['user', 'manager', 'org_admin', 'super_admin'] },
      { icon: <Icons.Folder />, label: 'New Folder', color: isDark ? 'bg-gray-700 hover:bg-gray-600 text-gray-200 border border-gray-600' : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200', roles: ['user', 'manager', 'org_admin', 'super_admin'] },
    ];
    
    const shareActions = [
      { icon: <Icons.Users />, label: 'Share', color: isDark ? 'bg-gray-700 hover:bg-gray-600 text-gray-200 border border-gray-600' : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200', roles: ['manager', 'org_admin', 'super_admin'] },
    ];
    
    const allActions = [...uploadActions, ...baseActions, ...shareActions];
    return allActions.filter(action => action.roles.includes(user?.role || 'viewer'));
  };

  const actions = getActionsForRole();

  return (
    <div className="flex flex-wrap gap-3">
      {actions.map((action, i) => (
        <button
          key={i}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${action.color}`}
        >
          {action.icon}
          {action.label}
        </button>
      ))}
    </div>
  );
}

// ============================================================================
// Storage Chart
// ============================================================================

function StorageChart() {
  const { currentOrg } = useAuth();
  const { isDark } = useTheme();
  
  if (!currentOrg) return null;

  const usagePercent = Math.round((currentOrg.storage_used / currentOrg.storage_limit) * 100);
  const categories = [
    { name: 'Documents', percent: 45, color: 'bg-indigo-500' },
    { name: 'Images', percent: 25, color: 'bg-emerald-500' },
    { name: 'Videos', percent: 20, color: 'bg-amber-500' },
    { name: 'Other', percent: 10, color: 'bg-gray-400' },
  ];

  return (
    <div className={`rounded-2xl border shadow-sm p-6 ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
      <h2 className={`text-lg font-semibold mb-6 ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Storage Breakdown</h2>
      
      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Total Usage</span>
          <span className={`text-sm font-medium ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{usagePercent}%</span>
        </div>
        <div className={`h-3 rounded-full overflow-hidden flex ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
          {categories.map((cat, i) => (
            <div
              key={i}
              className={`${cat.color} transition-all`}
              style={{ width: `${(cat.percent / 100) * usagePercent}%` }}
            />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-4">
        {categories.map((cat) => (
          <div key={cat.name} className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${cat.color}`} />
            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{cat.name}</span>
            <span className={`text-sm font-medium ml-auto ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{cat.percent}%</span>
          </div>
        ))}
      </div>

      {/* Total */}
      <div className={`mt-6 pt-4 border-t ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
        <div className="flex items-center justify-between">
          <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {formatBytes(currentOrg.storage_used)} of {formatBytes(currentOrg.storage_limit)}
          </span>
          {usagePercent > 80 && (
            <span className="text-xs text-amber-500 font-medium">Almost full</span>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Role Badge Component
// ============================================================================

function RoleBadge({ role }: { role: string }) {
  const { isDark } = useTheme();
  
  const roleConfig: Record<string, { label: string; color: string; bgColor: string }> = {
    super_admin: { 
      label: 'Super Admin', 
      color: isDark ? 'text-red-400' : 'text-red-700',
      bgColor: isDark ? 'bg-red-900/30 border-red-800' : 'bg-red-50 border-red-200'
    },
    org_admin: { 
      label: 'Organization Admin', 
      color: isDark ? 'text-purple-400' : 'text-purple-700',
      bgColor: isDark ? 'bg-purple-900/30 border-purple-800' : 'bg-purple-50 border-purple-200'
    },
    manager: { 
      label: 'Manager', 
      color: isDark ? 'text-blue-400' : 'text-blue-700',
      bgColor: isDark ? 'bg-blue-900/30 border-blue-800' : 'bg-blue-50 border-blue-200'
    },
    user: { 
      label: 'User', 
      color: isDark ? 'text-green-400' : 'text-green-700',
      bgColor: isDark ? 'bg-green-900/30 border-green-800' : 'bg-green-50 border-green-200'
    },
    viewer: { 
      label: 'Viewer', 
      color: isDark ? 'text-gray-400' : 'text-gray-700',
      bgColor: isDark ? 'bg-gray-800 border-gray-700' : 'bg-gray-100 border-gray-200'
    },
  };

  const config = roleConfig[role] || roleConfig.viewer;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full border ${config.bgColor} ${config.color}`}>
      {config.label}
    </span>
  );
}

// ============================================================================
// Permissions Card (for viewer role)
// ============================================================================

function PermissionsCard() {
  const { user } = useAuth();
  const { isDark } = useTheme();
  
  const rolePermissions: Record<string, { canDo: string[]; cannotDo: string[] }> = {
    super_admin: {
      canDo: ['Full platform access', 'Manage all organizations', 'Access admin dashboard', 'Manage all users', 'View audit logs'],
      cannotDo: []
    },
    org_admin: {
      canDo: ['Manage organization settings', 'Manage team members', 'Upload & delete files', 'Share files externally', 'View analytics'],
      cannotDo: ['Access admin dashboard', 'Manage other organizations']
    },
    manager: {
      canDo: ['Upload & manage files', 'Share files with team', 'Manage team folder', 'View team activity'],
      cannotDo: ['Delete organization files', 'Manage billing', 'Invite external users']
    },
    user: {
      canDo: ['Upload files', 'Download files', 'Create folders', 'View own files'],
      cannotDo: ['Share externally', 'Manage team members', 'Delete shared files']
    },
    viewer: {
      canDo: ['View files', 'Download files', 'View activity'],
      cannotDo: ['Upload files', 'Delete files', 'Create folders', 'Share files']
    },
  };

  const perms = rolePermissions[user?.role || 'viewer'];

  return (
    <div className={`rounded-2xl border shadow-sm p-6 ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className={`text-lg font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Your Permissions</h2>
        <RoleBadge role={user?.role || 'viewer'} />
      </div>
      
      <div className="space-y-4">
        <div>
          <h3 className={`text-sm font-medium mb-2 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>You can:</h3>
          <ul className="space-y-1">
            {perms.canDo.map((item, i) => (
              <li key={i} className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                <svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {item}
              </li>
            ))}
          </ul>
        </div>
        
        {perms.cannotDo.length > 0 && (
          <div>
            <h3 className={`text-sm font-medium mb-2 ${isDark ? 'text-rose-400' : 'text-rose-600'}`}>Restricted:</h3>
            <ul className="space-y-1">
              {perms.cannotDo.map((item, i) => (
                <li key={i} className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  <svg className="w-4 h-4 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Dashboard Page
// ============================================================================

export default function DashboardPage() {
  const { user, currentOrg } = useAuth();
  const { isDark } = useTheme();

  // Check if user can see team stats (managers and above)
  const canSeeTeamStats = ['manager', 'org_admin', 'super_admin'].includes(user?.role || '');
  // Check if user is viewer (limited access)
  const isViewer = user?.role === 'viewer';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
              Welcome back, {user?.name.split(' ')[0]} 👋
            </h1>
            <RoleBadge role={user?.role || 'viewer'} />
          </div>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Here&apos;s what&apos;s happening with {currentOrg?.name} today.
          </p>
        </div>
        <QuickActions />
      </div>

      {/* Viewer Notice */}
      {isViewer && (
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-amber-900/20 border-amber-800 text-amber-300' : 'bg-amber-50 border-amber-200 text-amber-800'}`}>
          <div className="flex items-center gap-3">
            <Icons.Eye className="w-5 h-5" />
            <div>
              <p className="font-medium">View-Only Access</p>
              <p className={`text-sm ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                You have read-only access to files. Contact your administrator for additional permissions.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Files"
          value={formatNumber(currentOrg?.file_count || 0)}
          change={12}
          icon={<Icons.Folder />}
          color="indigo"
        />
        {canSeeTeamStats && (
          <StatCard
            title="Team Members"
            value={currentOrg?.member_count || 0}
            change={5}
            icon={<Icons.Users />}
            color="emerald"
          />
        )}
        <StatCard
          title="Storage Used"
          value={formatBytes(currentOrg?.storage_used || 0)}
          icon={<Icons.Cloud />}
          color="amber"
        />
        <StatCard
          title="Files Scanned"
          value={formatNumber((currentOrg?.file_count || 0) * 0.98)}
          change={-2}
          icon={<Icons.Shield />}
          color="rose"
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Files - 2 columns */}
        <div className="lg:col-span-2">
          <RecentFiles />
        </div>
        
        {/* Right Sidebar */}
        <div className="space-y-6">
          <PermissionsCard />
          <StorageChart />
          {canSeeTeamStats && <ActivityFeed />}
        </div>
      </div>
    </div>
  );
}
