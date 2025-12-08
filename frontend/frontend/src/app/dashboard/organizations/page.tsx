"use client";

import React, { useState, useMemo } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import {
  Building2,
  Search,
  Plus,
  MoreHorizontal,
  Users,
  FileStack,
  HardDrive,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react';

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

export default function OrganizationsPage() {
  const { isDark } = useTheme();
  const { getAvailableOrganizations, getApprovedRegistrations } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [filterPlan, setFilterPlan] = useState<string>('all');

  // Get organizations from AuthContext - includes newly created ones from approvals
  const organizations = useMemo(() => {
    const availableOrgs = getAvailableOrganizations();
    const approvedRegistrations = getApprovedRegistrations();

    // Get organizations from available list
    const orgs = availableOrgs.map((org) => ({
      id: org.id,
      name: org.name,
      slug: org.slug,
      plan: org.plan,
      status: 'active' as const,
      users: org.member_count || 0,
      files: org.file_count || 0,
      storage: org.storage_used || 0,
      storageLimit: org.storage_limit || 10 * 1024 * 1024 * 1024,
      created: org.created_at,
      trend: Math.random() > 0.3 ? (Math.random() * 50) : -(Math.random() * 10), // Mock trend
    }));

    // Add organizations from approved registrations that created new orgs
    const newOrgsFromApprovals = approvedRegistrations
      .filter(reg => reg.type === 'organization' && reg.organization)
      .map(reg => ({
        id: reg.organization!.id,
        name: reg.organization!.name,
        slug: reg.organization!.name.toLowerCase().replace(/\s+/g, '-'),
        plan: reg.organization!.plan || 'free',
        status: 'active' as const,
        users: 1,
        files: 0,
        storage: 0,
        storageLimit: 10 * 1024 * 1024 * 1024,
        created: reg.reviewed_at || reg.created_at,
        trend: 100, // New org, high growth
      }));

    // Combine and deduplicate
    const combined = [...orgs, ...newOrgsFromApprovals];
    const uniqueOrgs = combined.reduce((acc, org) => {
      if (!acc.find(o => o.id === org.id)) {
        acc.push(org);
      }
      return acc;
    }, [] as typeof combined);

    return uniqueOrgs;
  }, [getAvailableOrganizations, getApprovedRegistrations]);

  const filteredOrgs = organizations.filter(org => {
    const matchesSearch = org.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPlan = filterPlan === 'all' || org.plan === filterPlan;
    return matchesSearch && matchesPlan;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Organizations</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Manage all organizations on the platform</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors">
          <Plus className="w-4 h-4" />
          Add Organization
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <Building2 className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{organizations.length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Total Organizations</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{organizations.filter(o => o.status === 'active').length}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Active</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <Users className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{organizations.reduce((acc, o) => acc + o.users, 0)}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Total Users</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/20 rounded-lg">
              <HardDrive className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{formatBytes(organizations.reduce((acc, o) => acc + o.storage, 0))}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Storage Used</p>
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
            placeholder="Search organizations..."
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
          value={filterPlan}
          onChange={(e) => setFilterPlan(e.target.value)}
          className={`px-4 py-2 rounded-lg border ${
            isDark 
              ? 'bg-gray-700 border-gray-600 text-white' 
              : 'bg-gray-50 border-gray-200 text-gray-900'
          } focus:outline-none focus:ring-2 focus:ring-indigo-500`}
        >
          <option value="all">All Plans</option>
          <option value="enterprise">Enterprise</option>
          <option value="pro">Pro</option>
          <option value="free">Free</option>
        </select>
      </div>

      {/* Organizations Table */}
      <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <table className="w-full">
          <thead className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
            <tr>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Organization</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Plan</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Status</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Users</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Storage</th>
              <th className={`px-6 py-4 text-left text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Growth</th>
              <th className={`px-6 py-4 text-right text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Actions</th>
            </tr>
          </thead>
          <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
            {filteredOrgs.map((org) => (
              <tr key={org.id} className={isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold">
                      {org.name.charAt(0)}
                    </div>
                    <div>
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{org.name}</p>
                      <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{org.slug}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    org.plan === 'enterprise' ? 'bg-purple-500/20 text-purple-400' :
                    org.plan === 'pro' ? 'bg-blue-500/20 text-blue-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {org.plan}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`flex items-center gap-1 text-sm ${
                    org.status === 'active' ? 'text-green-400' : 'text-yellow-400'
                  }`}>
                    {org.status === 'active' ? <CheckCircle className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
                    {org.status}
                  </span>
                </td>
                <td className={`px-6 py-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{org.users}</td>
                <td className="px-6 py-4">
                  <div>
                    <p className={`text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{formatBytes(org.storage)}</p>
                    <div className={`w-24 h-1.5 rounded-full mt-1 ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
                      <div 
                        className="h-full bg-indigo-500 rounded-full" 
                        style={{ width: `${(org.storage / org.storageLimit) * 100}%` }}
                      />
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`flex items-center gap-1 text-sm ${org.trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {org.trend >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                    {Math.abs(org.trend)}%
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                    <MoreHorizontal className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
