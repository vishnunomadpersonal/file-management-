"use client";

import React, { useState, useEffect } from 'react';
import { useAuth, formatBytes, formatNumber } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useRouter } from 'next/navigation';

// ============================================================================
// Icons
// ============================================================================

const Icons = {
  TrendingUp: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
    </svg>
  ),
  TrendingDown: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6" />
    </svg>
  ),
  Calendar: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  Download: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
  Upload: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
    </svg>
  ),
  Users: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
  File: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  Shield: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  Zap: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  Globe: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
    </svg>
  ),
};

// ============================================================================
// Types
// ============================================================================

type TimeRange = '7d' | '30d' | '90d' | '12m';

// ============================================================================
// Mock Data
// ============================================================================

const mockStats = {
  totalFiles: 12847,
  filesChange: 12.5,
  storageUsed: 245.5 * 1024 * 1024 * 1024, // 245.5 GB
  storageChange: 8.3,
  activeUsers: 47,
  usersChange: 15.2,
  apiCalls: 1284567,
  apiChange: 23.1,
  uploadsToday: 234,
  downloadsToday: 567,
  threatsBlocked: 12,
  avgUploadSpeed: 45.2, // MB/s
};

const mockChartData = {
  '7d': {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    uploads: [45, 62, 38, 71, 55, 23, 34],
    downloads: [89, 124, 76, 145, 112, 45, 67],
    storage: [240, 241, 242, 243, 244, 245, 245.5],
  },
  '30d': {
    labels: Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`),
    uploads: Array.from({ length: 30 }, () => Math.floor(Math.random() * 100) + 20),
    downloads: Array.from({ length: 30 }, () => Math.floor(Math.random() * 200) + 50),
    storage: Array.from({ length: 30 }, (_, i) => 220 + i * 0.85),
  },
  '90d': {
    labels: Array.from({ length: 12 }, (_, i) => `Week ${i + 1}`),
    uploads: Array.from({ length: 12 }, () => Math.floor(Math.random() * 500) + 200),
    downloads: Array.from({ length: 12 }, () => Math.floor(Math.random() * 1000) + 400),
    storage: Array.from({ length: 12 }, (_, i) => 180 + i * 5.5),
  },
  '12m': {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    uploads: [1200, 1450, 1380, 1620, 1780, 1950, 2100, 2340, 2560, 2780, 2980, 3200],
    downloads: [2400, 2890, 2760, 3240, 3560, 3900, 4200, 4680, 5120, 5560, 5960, 6400],
    storage: [50, 70, 95, 115, 135, 155, 175, 195, 210, 225, 238, 245.5],
  },
};

const mockTopFiles = [
  { name: 'Q4_Financial_Report.pdf', downloads: 1234, size: 2456789 },
  { name: 'Product_Roadmap_2025.xlsx', downloads: 987, size: 1234567 },
  { name: 'Brand_Guidelines.pdf', downloads: 856, size: 3456789 },
  { name: 'Team_Presentation.pptx', downloads: 743, size: 5678901 },
  { name: 'Customer_Data_Export.csv', downloads: 621, size: 1234567 },
];

const mockTopUsers = [
  { name: 'Sarah Chen', uploads: 245, downloads: 567 },
  { name: 'Michael Rodriguez', uploads: 189, downloads: 432 },
  { name: 'Emily Thompson', uploads: 156, downloads: 387 },
  { name: 'David Park', uploads: 134, downloads: 298 },
  { name: 'Jennifer Martinez', uploads: 112, downloads: 256 },
];

// ============================================================================
// Stat Card
// ============================================================================

function StatCard({ 
  title, 
  value, 
  change, 
  icon,
  format = 'number',
}: { 
  title: string; 
  value: number; 
  change: number; 
  icon: React.ReactNode;
  format?: 'number' | 'bytes' | 'speed';
}) {
  const isPositive = change >= 0;
  
  const formatValue = () => {
    switch (format) {
      case 'bytes':
        return formatBytes(value);
      case 'speed':
        return `${value.toFixed(1)} MB/s`;
      default:
        return formatNumber(value);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="p-2 bg-gray-100 rounded-xl text-gray-600">{icon}</span>
        <span className={`flex items-center gap-1 text-sm font-medium ${
          isPositive ? 'text-emerald-600' : 'text-red-600'
        }`}>
          {isPositive ? <Icons.TrendingUp className="w-4 h-4" /> : <Icons.TrendingDown className="w-4 h-4" />}
          {Math.abs(change)}%
        </span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{formatValue()}</p>
      <p className="text-sm text-gray-500 mt-1">{title}</p>
    </div>
  );
}

// ============================================================================
// Simple Bar Chart
// ============================================================================

function BarChart({ 
  data, 
  labels, 
  color = 'indigo',
  height = 200,
}: { 
  data: number[]; 
  labels: string[]; 
  color?: string;
  height?: number;
}) {
  const max = Math.max(...data);
  const colorMap: Record<string, string> = {
    indigo: 'bg-indigo-500',
    emerald: 'bg-emerald-500',
    purple: 'bg-purple-500',
    amber: 'bg-amber-500',
  };

  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {data.map((value, i) => (
        <div key={i} className="flex-1 flex flex-col items-center group">
          <div className="w-full flex flex-col items-center">
            <span className="text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity mb-1">
              {value}
            </span>
            <div 
              className={`w-full ${colorMap[color]} rounded-t transition-all hover:opacity-80`}
              style={{ height: `${(value / max) * (height - 30)}px` }}
            />
          </div>
          <span className="text-xs text-gray-400 mt-2 truncate w-full text-center">
            {labels[i]}
          </span>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Simple Line Chart (Simplified visualization)
// ============================================================================

function LineChart({ 
  data, 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  labels,
  height = 200,
}: { 
  data: number[]; 
  labels: string[];
  height?: number;
}) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min;

  return (
    <div className="relative" style={{ height }}>
      {/* Y-axis labels */}
      <div className="absolute left-0 top-0 bottom-6 w-12 flex flex-col justify-between text-xs text-gray-400">
        <span>{max.toFixed(0)} GB</span>
        <span>{((max + min) / 2).toFixed(0)} GB</span>
        <span>{min.toFixed(0)} GB</span>
      </div>
      
      {/* Chart area */}
      <div className="ml-14 h-full flex items-end">
        <svg className="w-full h-full" viewBox={`0 0 ${data.length * 40} ${height - 24}`} preserveAspectRatio="none">
          {/* Gradient fill */}
          <defs>
            <linearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
            </linearGradient>
          </defs>
          
          {/* Area fill */}
          <path
            d={`M 0 ${height - 24} ${data.map((v, i) => {
              const x = i * 40 + 20;
              const y = height - 24 - ((v - min) / range) * (height - 48);
              return `L ${x} ${y}`;
            }).join(' ')} L ${data.length * 40} ${height - 24} Z`}
            fill="url(#lineGradient)"
          />
          
          {/* Line */}
          <path
            d={`M ${data.map((v, i) => {
              const x = i * 40 + 20;
              const y = height - 24 - ((v - min) / range) * (height - 48);
              return `${i === 0 ? '' : 'L'} ${x} ${y}`;
            }).join(' ')}`}
            fill="none"
            stroke="#6366f1"
            strokeWidth="2"
          />
          
          {/* Data points */}
          {data.map((v, i) => {
            const x = i * 40 + 20;
            const y = height - 24 - ((v - min) / range) * (height - 48);
            return (
              <circle key={i} cx={x} cy={y} r="4" fill="#6366f1" className="hover:r-6 cursor-pointer" />
            );
          })}
        </svg>
      </div>
    </div>
  );
}

// ============================================================================
// Analytics Page
// ============================================================================

export default function AnalyticsPage() {
  const { currentOrg, user } = useAuth();
  const { isDark } = useTheme();
  const router = useRouter();
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const chartData = mockChartData[timeRange];

  // Check if user has access to this page
  const hasAccess = ['manager', 'org_admin', 'super_admin'].includes(user?.role || '');

  // Redirect if no access
  useEffect(() => {
    if (user && !hasAccess) {
      router.push('/dashboard');
    }
  }, [user, hasAccess, router]);

  if (!hasAccess) {
    return (
      <div className={`flex items-center justify-center min-h-[60vh] ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        <div className="text-center">
          <Icons.Shield className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">Access Denied</p>
          <p className="text-sm">You don&apos;t have permission to view analytics.</p>
        </div>
      </div>
    );
  }

  const timeRangeLabels: Record<TimeRange, string> = {
    '7d': 'Last 7 days',
    '30d': 'Last 30 days',
    '90d': 'Last 90 days',
    '12m': 'Last 12 months',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Analytics</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Usage statistics for {currentOrg?.name}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Icons.Calendar className={isDark ? 'text-gray-500' : 'text-gray-400'} />
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as TimeRange)}
            className={`px-4 py-2 border rounded-xl text-sm outline-none appearance-none cursor-pointer ${
              isDark ? 'bg-gray-800 border-gray-700 text-gray-200' : 'bg-white border-gray-200 text-gray-600'
            }`}
          >
            {Object.entries(timeRangeLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Files"
          value={mockStats.totalFiles}
          change={mockStats.filesChange}
          icon={<Icons.File />}
        />
        <StatCard
          title="Storage Used"
          value={mockStats.storageUsed}
          change={mockStats.storageChange}
          icon={<Icons.Upload />}
          format="bytes"
        />
        <StatCard
          title="Active Users"
          value={mockStats.activeUsers}
          change={mockStats.usersChange}
          icon={<Icons.Users />}
        />
        <StatCard
          title="API Calls"
          value={mockStats.apiCalls}
          change={mockStats.apiChange}
          icon={<Icons.Zap />}
        />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-emerald-50 rounded-xl">
          <div className="flex items-center gap-2 text-emerald-700 mb-1">
            <Icons.Upload className="w-4 h-4" />
            <span className="text-sm font-medium">Uploads Today</span>
          </div>
          <p className="text-2xl font-bold text-emerald-900">{mockStats.uploadsToday}</p>
        </div>
        <div className="p-4 bg-blue-50 rounded-xl">
          <div className="flex items-center gap-2 text-blue-700 mb-1">
            <Icons.Download className="w-4 h-4" />
            <span className="text-sm font-medium">Downloads Today</span>
          </div>
          <p className="text-2xl font-bold text-blue-900">{mockStats.downloadsToday}</p>
        </div>
        <div className="p-4 bg-red-50 rounded-xl">
          <div className="flex items-center gap-2 text-red-700 mb-1">
            <Icons.Shield className="w-4 h-4" />
            <span className="text-sm font-medium">Threats Blocked</span>
          </div>
          <p className="text-2xl font-bold text-red-900">{mockStats.threatsBlocked}</p>
        </div>
        <div className="p-4 bg-purple-50 rounded-xl">
          <div className="flex items-center gap-2 text-purple-700 mb-1">
            <Icons.Zap className="w-4 h-4" />
            <span className="text-sm font-medium">Avg Upload Speed</span>
          </div>
          <p className="text-2xl font-bold text-purple-900">{mockStats.avgUploadSpeed} MB/s</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Uploads Chart */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">File Uploads</h3>
          <BarChart 
            data={chartData.uploads.slice(0, 12)} 
            labels={chartData.labels.slice(0, 12)}
            color="indigo"
          />
        </div>

        {/* Downloads Chart */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">File Downloads</h3>
          <BarChart 
            data={chartData.downloads.slice(0, 12)} 
            labels={chartData.labels.slice(0, 12)}
            color="emerald"
          />
        </div>
      </div>

      {/* Storage Growth */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">Storage Growth</h3>
        <LineChart 
          data={chartData.storage.slice(0, 12)} 
          labels={chartData.labels.slice(0, 12)}
          height={250}
        />
      </div>

      {/* Tables */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Files */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Files by Downloads</h3>
          <div className="space-y-3">
            {mockTopFiles.map((file, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <span className="w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-xs font-bold">
                    {i + 1}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-gray-900 truncate max-w-48">{file.name}</p>
                    <p className="text-xs text-gray-500">{formatBytes(file.size)}</p>
                  </div>
                </div>
                <span className="text-sm font-medium text-gray-600">
                  {file.downloads.toLocaleString()} downloads
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Top Users */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Most Active Users</h3>
          <div className="space-y-3">
            {mockTopUsers.map((user, i) => {
              const colors = [
                'from-indigo-500 to-purple-500',
                'from-emerald-500 to-teal-500',
                'from-amber-500 to-orange-500',
                'from-rose-500 to-pink-500',
                'from-cyan-500 to-blue-500',
              ];
              const initials = user.name.split(' ').map(n => n[0]).join('');
              
              return (
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${colors[i]} flex items-center justify-center text-white text-xs font-medium`}>
                      {initials}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{user.name}</p>
                      <p className="text-xs text-gray-500">{user.uploads} uploads • {user.downloads} downloads</p>
                    </div>
                  </div>
                  <span className="text-sm font-medium text-gray-600">
                    {user.uploads + user.downloads} total
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Geographic Distribution */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Icons.Globe />
          Access by Region
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { region: 'North America', percent: 45, color: 'bg-indigo-500' },
            { region: 'Europe', percent: 28, color: 'bg-emerald-500' },
            { region: 'Asia Pacific', percent: 18, color: 'bg-purple-500' },
            { region: 'South America', percent: 6, color: 'bg-amber-500' },
            { region: 'Other', percent: 3, color: 'bg-gray-400' },
          ].map((item, i) => (
            <div key={i} className="text-center">
              <div className="w-full h-2 bg-gray-100 rounded-full mb-2">
                <div 
                  className={`h-full ${item.color} rounded-full`}
                  style={{ width: `${item.percent}%` }}
                />
              </div>
              <p className="text-sm font-medium text-gray-900">{item.percent}%</p>
              <p className="text-xs text-gray-500">{item.region}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
