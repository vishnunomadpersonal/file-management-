"use client";

import React, { useState, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import {
  Users,
  Search,
  Filter,
  Plus,
  MoreVertical,
  Shield,
  Mail,
  Eye,
  Edit,
  Trash2,
  Ban,
  CheckCircle,
  XCircle,
  Download,
  Building2,
  Clock,
  Key,
  UserCog,
  Crown,
  Briefcase,
  UserPlus,
} from 'lucide-react';

// Mock users data
const mockUsers = [
  {
    id: 'usr_001',
    name: 'John Smith',
    email: 'john@acmehealthcare.com',
    role: 'org_admin',
    status: 'active',
    organization: 'Acme Healthcare',
    org_id: 'org_001',
    last_login: '5 minutes ago',
    files_uploaded: 1234,
    created_at: '2024-01-15',
  },
  {
    id: 'usr_002',
    name: 'Sarah Johnson',
    email: 'sarah@techcorp.com',
    role: 'manager',
    status: 'active',
    organization: 'TechCorp Finance',
    org_id: 'org_002',
    last_login: '1 hour ago',
    files_uploaded: 892,
    created_at: '2024-02-20',
  },
  {
    id: 'usr_003',
    name: 'Michael Chen',
    email: 'michael@dataflow.io',
    role: 'user',
    status: 'active',
    organization: 'DataFlow Systems',
    org_id: 'org_003',
    last_login: '2 hours ago',
    files_uploaded: 456,
    created_at: '2024-03-10',
  },
  {
    id: 'usr_004',
    name: 'Emily Davis',
    email: 'emily@cloudnine.com',
    role: 'org_admin',
    status: 'inactive',
    organization: 'CloudNine Inc',
    org_id: 'org_004',
    last_login: '3 days ago',
    files_uploaded: 2341,
    created_at: '2024-04-05',
  },
  {
    id: 'usr_005',
    name: 'Alex Turner',
    email: 'alex@startupx.io',
    role: 'user',
    status: 'active',
    organization: 'StartupX',
    org_id: 'org_005',
    last_login: '30 minutes ago',
    files_uploaded: 89,
    created_at: '2024-05-15',
  },
  {
    id: 'usr_006',
    name: 'Jessica Williams',
    email: 'jessica@megacorp.com',
    role: 'super_admin',
    status: 'active',
    organization: 'MegaCorp Global',
    org_id: 'org_006',
    last_login: '10 minutes ago',
    files_uploaded: 5678,
    created_at: '2023-11-20',
  },
  {
    id: 'usr_007',
    name: 'David Brown',
    email: 'david@innovatetech.dev',
    role: 'viewer',
    status: 'pending',
    organization: 'InnovateTech',
    org_id: 'org_007',
    last_login: 'Never',
    files_uploaded: 0,
    created_at: '2024-06-01',
  },
  {
    id: 'usr_008',
    name: 'Lisa Anderson',
    email: 'lisa@acmehealthcare.com',
    role: 'manager',
    status: 'active',
    organization: 'Acme Healthcare',
    org_id: 'org_001',
    last_login: '4 hours ago',
    files_uploaded: 3421,
    created_at: '2024-01-20',
  },
];

const roleColors: Record<string, string> = {
  super_admin: 'bg-red-500/20 text-red-400 border-red-500/30',
  org_admin: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  manager: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  user: 'bg-green-500/20 text-green-400 border-green-500/30',
  viewer: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

const roleIcons: Record<string, React.ReactNode> = {
  super_admin: <Crown className="w-3 h-3" />,
  org_admin: <Shield className="w-3 h-3" />,
  manager: <Briefcase className="w-3 h-3" />,
  user: <Users className="w-3 h-3" />,
  viewer: <Eye className="w-3 h-3" />,
};

export default function AdminUsers() {
  const { getAllUsers, getApprovedRegistrations, pendingRegistrations } = useAuth();
  const { isDark } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'system' | 'approved'>('system');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);

  // Get users from AuthContext
  const systemUsers = useMemo(() => getAllUsers(), [getAllUsers]);
  const approvedRegistrations = useMemo(() => getApprovedRegistrations(), [getApprovedRegistrations]);

  // Combine system users with approved registrations for display
  const allUsers = useMemo(() => {
    const users = systemUsers.map(({ user, organization_name }) => ({
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role,
      status: user.status === 'approved' ? 'active' : user.status,
      organization: organization_name || 'N/A',
      org_id: user.organization_id || '',
      last_login: '5 minutes ago',
      files_uploaded: Math.floor(Math.random() * 5000),
      created_at: user.created_at,
      source: 'system' as const,
    }));

    const approved = approvedRegistrations.map((reg) => ({
      id: reg.user.id,
      name: reg.user.name,
      email: reg.user.email,
      role: reg.requested_role,
      status: 'active',
      organization: reg.organization?.name || reg.organization_name || 'N/A',
      org_id: reg.organization?.id || reg.organization_id || '',
      last_login: 'Recently approved',
      files_uploaded: 0,
      created_at: reg.reviewed_at || reg.created_at,
      source: 'approved' as const,
      registrationType: reg.type,
    }));

    return [...users, ...approved];
  }, [systemUsers, approvedRegistrations]);

  const filteredUsers = useMemo(() => {
    return allUsers.filter(user => {
      // Filter by source (system vs approved)
      if (viewMode === 'approved' && user.source !== 'approved') return false;
      if (viewMode === 'system' && user.source !== 'system') return false;

      const matchesSearch = user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           user.organization.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesRole = roleFilter === 'all' || user.role === roleFilter;
      const matchesStatus = statusFilter === 'all' || user.status === statusFilter;
      return matchesSearch && matchesRole && matchesStatus;
    });
  }, [allUsers, viewMode, searchQuery, roleFilter, statusFilter]);

  const stats = useMemo(() => ({
    total: allUsers.length,
    active: allUsers.filter(u => u.status === 'active').length,
    admins: allUsers.filter(u => u.role === 'super_admin' || u.role === 'org_admin').length,
    pending: pendingRegistrations.filter(r => r.status === 'pending').length,
    approved: approvedRegistrations.length,
  }), [allUsers, pendingRegistrations, approvedRegistrations]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Users</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Manage all users across all organizations</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add User
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className={`rounded-xl p-4 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isDark ? 'bg-blue-500/20' : 'bg-blue-100'}`}>
              <Users className={`w-5 h-5 ${isDark ? 'text-blue-400' : 'text-blue-600'}`} />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{stats.total}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Users</p>
            </div>
          </div>
        </div>
        <div className={`rounded-xl p-4 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isDark ? 'bg-green-500/20' : 'bg-green-100'}`}>
              <CheckCircle className={`w-5 h-5 ${isDark ? 'text-green-400' : 'text-green-600'}`} />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{stats.active}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Active</p>
            </div>
          </div>
        </div>
        <div className={`rounded-xl p-4 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isDark ? 'bg-purple-500/20' : 'bg-purple-100'}`}>
              <Shield className={`w-5 h-5 ${isDark ? 'text-purple-400' : 'text-purple-600'}`} />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{stats.admins}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Administrators</p>
            </div>
          </div>
        </div>
        <div className={`rounded-xl p-4 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isDark ? 'bg-yellow-500/20' : 'bg-yellow-100'}`}>
              <Clock className={`w-5 h-5 ${isDark ? 'text-yellow-400' : 'text-yellow-600'}`} />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{stats.pending}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Pending</p>
            </div>
          </div>
        </div>
        <div className={`rounded-xl p-4 border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isDark ? 'bg-emerald-500/20' : 'bg-emerald-100'}`}>
              <UserPlus className={`w-5 h-5 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`} />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{stats.approved}</p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Recently Approved</p>
            </div>
          </div>
        </div>
      </div>

      {/* View Mode Toggle */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setViewMode('system')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === 'system'
              ? isDark ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
              : isDark ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          System Users ({systemUsers.length})
        </button>
        <button
          onClick={() => setViewMode('approved')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === 'approved'
              ? isDark ? 'bg-emerald-600 text-white' : 'bg-emerald-500 text-white'
              : isDark ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Recently Approved ({approvedRegistrations.length})
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[300px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Search users, emails, organizations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`w-full pl-10 pr-4 py-2 border rounded-lg placeholder-gray-500 focus:outline-none focus:border-blue-500 ${isDark ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-gray-200 text-gray-900'}`}
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-400" />
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className={`px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500 ${isDark ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-gray-200 text-gray-900'}`}
          >
            <option value="all">All Roles</option>
            <option value="super_admin">Super Admin</option>
            <option value="org_admin">Org Admin</option>
            <option value="manager">Manager</option>
            <option value="user">User</option>
            <option value="viewer">Viewer</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={`px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500 ${isDark ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-gray-200 text-gray-900'}`}
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="pending">Pending</option>
          </select>
        </div>
        <button className={`flex items-center gap-2 px-3 py-2 rounded-lg ${isDark ? 'text-gray-400 hover:text-white hover:bg-gray-800' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}`}>
          <Download className="w-5 h-5" />
          Export
        </button>
      </div>

      {/* Users Table */}
      <div className={`backdrop-blur-sm rounded-2xl border overflow-hidden ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white border-gray-200'}`}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className={`text-left text-sm border-b ${isDark ? 'text-gray-400 border-gray-700 bg-gray-800/50' : 'text-gray-500 border-gray-200 bg-gray-50'}`}>
                <th className="px-6 py-4 font-medium">User</th>
                <th className="px-6 py-4 font-medium">Organization</th>
                <th className="px-6 py-4 font-medium">Role</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Source</th>
                <th className="px-6 py-4 font-medium">Last Login</th>
                <th className="px-6 py-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {filteredUsers.map((user) => (
                <tr key={user.id} className={isDark ? 'hover:bg-gray-700/30' : 'hover:bg-gray-50'}>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${
                        user.role === 'super_admin' ? 'bg-gradient-to-br from-red-500 to-orange-500' :
                        user.role === 'org_admin' ? 'bg-gradient-to-br from-purple-500 to-pink-500' :
                        user.role === 'manager' ? 'bg-gradient-to-br from-blue-500 to-cyan-500' :
                        'bg-gradient-to-br from-green-500 to-emerald-500'
                      }`}>
                        {user.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{user.name}</p>
                        <p className={`text-xs flex items-center gap-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                          <Mail className="w-3 h-3" />
                          {user.email}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Building2 className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                      <span className={`text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{user.organization}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border ${roleColors[user.role]}`}>
                      {roleIcons[user.role]}
                      {user.role.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`flex items-center gap-1 text-xs ${
                      user.status === 'active' ? isDark ? 'text-green-400' : 'text-green-600' :
                      user.status === 'inactive' ? isDark ? 'text-gray-400' : 'text-gray-500' :
                      isDark ? 'text-yellow-400' : 'text-yellow-600'
                    }`}>
                      {user.status === 'active' ? <CheckCircle className="w-3 h-3" /> :
                       user.status === 'inactive' ? <XCircle className="w-3 h-3" /> :
                       <Clock className="w-3 h-3" />}
                      {user.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      user.source === 'approved'
                        ? isDark ? 'bg-emerald-900/30 text-emerald-400' : 'bg-emerald-100 text-emerald-700'
                        : isDark ? 'bg-gray-700 text-gray-400' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {user.source === 'approved' ? 'Recently Approved' : 'System'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{user.last_login}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="relative">
                      <button
                        onClick={() => setSelectedUser(selectedUser === user.id ? null : user.id)}
                        className={`p-2 rounded-lg ${isDark ? 'text-gray-400 hover:text-white hover:bg-gray-700' : 'text-gray-400 hover:text-gray-900 hover:bg-gray-100'}`}
                      >
                        <MoreVertical className="w-5 h-5" />
                      </button>
                      {selectedUser === user.id && (
                        <div className={`absolute right-0 mt-2 w-48 border rounded-xl shadow-2xl overflow-hidden z-10 ${isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}`}>
                          <button className={`w-full flex items-center gap-3 px-4 py-3 text-left ${isDark ? 'text-gray-300 hover:bg-gray-800' : 'text-gray-700 hover:bg-gray-50'}`}>
                            <Eye className="w-4 h-4" />
                            View Profile
                          </button>
                          <button className={`w-full flex items-center gap-3 px-4 py-3 text-left ${isDark ? 'text-gray-300 hover:bg-gray-800' : 'text-gray-700 hover:bg-gray-50'}`}>
                            <Edit className="w-4 h-4" />
                            Edit User
                          </button>
                          <button className={`w-full flex items-center gap-3 px-4 py-3 text-left ${isDark ? 'text-gray-300 hover:bg-gray-800' : 'text-gray-700 hover:bg-gray-50'}`}>
                            <Key className="w-4 h-4" />
                            Reset Password
                          </button>
                          <button className={`w-full flex items-center gap-3 px-4 py-3 text-left ${isDark ? 'text-gray-300 hover:bg-gray-800' : 'text-gray-700 hover:bg-gray-50'}`}>
                            <Mail className="w-4 h-4" />
                            Send Email
                          </button>
                          {user.status === 'active' ? (
                            <button className={`w-full flex items-center gap-3 px-4 py-3 text-left ${isDark ? 'text-yellow-400 hover:bg-gray-800' : 'text-yellow-600 hover:bg-gray-50'}`}>
                              <Ban className="w-4 h-4" />
                              Deactivate
                            </button>
                          ) : (
                            <button className={`w-full flex items-center gap-3 px-4 py-3 text-left ${isDark ? 'text-green-400 hover:bg-gray-800' : 'text-green-600 hover:bg-gray-50'}`}>
                              <CheckCircle className="w-4 h-4" />
                              Activate
                            </button>
                          )}
                          <button className={`w-full flex items-center gap-3 px-4 py-3 text-left ${isDark ? 'text-red-400 hover:bg-gray-800' : 'text-red-600 hover:bg-gray-50'}`}>
                            <Trash2 className="w-4 h-4" />
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        <div className={`px-6 py-4 border-t flex items-center justify-between ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Showing {filteredUsers.length} of {mockUsers.length} users
          </p>
          <div className="flex items-center gap-2">
            <button className={`px-3 py-1 rounded-lg text-sm ${isDark ? 'text-gray-400 hover:text-white hover:bg-gray-700' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}`}>
              Previous
            </button>
            <button className="px-3 py-1 bg-blue-500 text-white rounded-lg text-sm">1</button>
            <button className={`px-3 py-1 rounded-lg text-sm ${isDark ? 'text-gray-400 hover:text-white hover:bg-gray-700' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}`}>2</button>
            <button className={`px-3 py-1 rounded-lg text-sm ${isDark ? 'text-gray-400 hover:text-white hover:bg-gray-700' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}`}>
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Empty State */}
      {filteredUsers.length === 0 && (
        <div className={`text-center py-16 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-gray-50 border-gray-200'}`}>
          <Users className={`w-12 h-12 mx-auto mb-4 ${isDark ? 'text-gray-600' : 'text-gray-300'}`} />
          <h3 className={`text-lg font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            {viewMode === 'approved' ? 'No recently approved users' : 'No users found'}
          </h3>
          <p className={`mt-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            {viewMode === 'approved' 
              ? 'Users will appear here after their registration is approved' 
              : 'Try adjusting your search or filter criteria'}
          </p>
        </div>
      )}

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className={`rounded-2xl w-full max-w-lg border shadow-2xl ${isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}`}>
            <div className={`p-6 border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Create User</h3>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Add a new user to an organization</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm mb-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>First Name</label>
                  <input
                    type="text"
                    placeholder="John"
                    className={`w-full px-4 py-2 border rounded-lg placeholder-gray-500 focus:outline-none focus:border-blue-500 ${isDark ? 'bg-gray-800 border-gray-700 text-white' : 'bg-gray-50 border-gray-200 text-gray-900'}`}
                  />
                </div>
                <div>
                  <label className={`block text-sm mb-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Last Name</label>
                  <input
                    type="text"
                    placeholder="Smith"
                    className={`w-full px-4 py-2 border rounded-lg placeholder-gray-500 focus:outline-none focus:border-blue-500 ${isDark ? 'bg-gray-800 border-gray-700 text-white' : 'bg-gray-50 border-gray-200 text-gray-900'}`}
                  />
                </div>
              </div>
              <div>
                <label className={`block text-sm mb-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Email</label>
                <input
                  type="email"
                  placeholder="user@company.com"
                  className={`w-full px-4 py-2 border rounded-lg placeholder-gray-500 focus:outline-none focus:border-blue-500 ${isDark ? 'bg-gray-800 border-gray-700 text-white' : 'bg-gray-50 border-gray-200 text-gray-900'}`}
                />
              </div>
              <div>
                <label className={`block text-sm mb-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Organization</label>
                <select className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-blue-500 ${isDark ? 'bg-gray-800 border-gray-700 text-white' : 'bg-gray-50 border-gray-200 text-gray-900'}`}>
                  <option value="">Select organization...</option>
                  <option value="org_001">Acme Healthcare</option>
                  <option value="org_002">TechCorp Finance</option>
                  <option value="org_003">DataFlow Systems</option>
                  <option value="org_004">CloudNine Inc</option>
                </select>
              </div>
              <div>
                <label className={`block text-sm mb-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Role</label>
                <select className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-blue-500 ${isDark ? 'bg-gray-800 border-gray-700 text-white' : 'bg-gray-50 border-gray-200 text-gray-900'}`}>
                  <option value="user">User</option>
                  <option value="viewer">Viewer</option>
                  <option value="manager">Manager</option>
                  <option value="org_admin">Organization Admin</option>
                  <option value="super_admin">Super Admin</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="sendInvite" className={`rounded ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-300'}`} />
                <label htmlFor="sendInvite" className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Send invitation email</label>
              </div>
            </div>
            <div className={`p-6 border-t flex justify-end gap-3 ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <button
                onClick={() => setShowCreateModal(false)}
                className={`px-4 py-2 rounded-lg ${isDark ? 'text-gray-400 hover:text-white hover:bg-gray-800' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}`}
              >
                Cancel
              </button>
              <button className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg">
                Create User
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
