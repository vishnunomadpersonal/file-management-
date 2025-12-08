"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useRouter } from 'next/navigation';
import { usersApi } from '@/lib/api';

// ============================================================================
// Icons
// ============================================================================

const Icons = {
  Plus: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
    </svg>
  ),
  Search: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  MoreVertical: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
    </svg>
  ),
  Mail: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  Edit: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  ),
  Trash: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  ),
  X: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  Users: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
  Shield: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  Clock: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  Check: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
};

// ============================================================================
// Types
// ============================================================================

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'owner' | 'admin' | 'member' | 'viewer' | 'org_admin' | 'super_admin' | 'manager' | 'user';
  status: 'active' | 'pending' | 'suspended' | 'approved' | 'rejected';
  avatar?: string;
  lastActive?: string;
  filesUploaded: number;
  storageUsed: number;
}

// Map API roles to display roles
const mapRole = (apiRole: string): TeamMember['role'] => {
  const roleMap: Record<string, TeamMember['role']> = {
    'org_admin': 'admin',
    'super_admin': 'owner',
    'manager': 'admin',
    'user': 'member',
    'viewer': 'viewer',
  };
  return roleMap[apiRole] || 'member';
};

// Map API status to display status
const mapStatus = (apiStatus: string): TeamMember['status'] => {
  if (apiStatus === 'approved') return 'active';
  if (apiStatus === 'pending') return 'pending';
  if (apiStatus === 'rejected') return 'suspended';
  return 'active';
};

// ============================================================================
// Role Badge
// ============================================================================

function RoleBadge({ role }: { role: TeamMember['role'] }) {
  const { isDark } = useTheme();
  
  const styles: Record<TeamMember['role'], string> = {
    owner: isDark ? 'bg-purple-900/50 text-purple-300 border-purple-700' : 'bg-purple-50 text-purple-700 border-purple-100',
    admin: isDark ? 'bg-indigo-900/50 text-indigo-300 border-indigo-700' : 'bg-indigo-50 text-indigo-700 border-indigo-100',
    member: isDark ? 'bg-gray-700 text-gray-300 border-gray-600' : 'bg-gray-50 text-gray-700 border-gray-100',
    viewer: isDark ? 'bg-gray-700 text-gray-400 border-gray-600' : 'bg-gray-50 text-gray-500 border-gray-100',
    org_admin: isDark ? 'bg-indigo-900/50 text-indigo-300 border-indigo-700' : 'bg-indigo-50 text-indigo-700 border-indigo-100',
    super_admin: isDark ? 'bg-purple-900/50 text-purple-300 border-purple-700' : 'bg-purple-50 text-purple-700 border-purple-100',
    manager: isDark ? 'bg-blue-900/50 text-blue-300 border-blue-700' : 'bg-blue-50 text-blue-700 border-blue-100',
    user: isDark ? 'bg-gray-700 text-gray-300 border-gray-600' : 'bg-gray-50 text-gray-700 border-gray-100',
  };

  const labels: Record<TeamMember['role'], string> = {
    owner: 'Owner',
    admin: 'Admin',
    member: 'Member',
    viewer: 'Viewer',
    org_admin: 'Admin',
    super_admin: 'Owner',
    manager: 'Manager',
    user: 'Member',
  };

  return (
    <span className={`px-2.5 py-1 text-xs font-medium rounded-full border ${styles[role]}`}>
      {labels[role]}
    </span>
  );
}

// ============================================================================
// Status Badge
// ============================================================================

function StatusBadge({ status }: { status: TeamMember['status'] }) {
  const { isDark } = useTheme();
  
  const styles: Record<TeamMember['status'], string> = {
    active: isDark ? 'bg-emerald-900/50 text-emerald-300' : 'bg-emerald-50 text-emerald-700',
    approved: isDark ? 'bg-emerald-900/50 text-emerald-300' : 'bg-emerald-50 text-emerald-700',
    pending: isDark ? 'bg-amber-900/50 text-amber-300' : 'bg-amber-50 text-amber-700',
    suspended: isDark ? 'bg-red-900/50 text-red-300' : 'bg-red-50 text-red-700',
    rejected: isDark ? 'bg-red-900/50 text-red-300' : 'bg-red-50 text-red-700',
  };

  const icons: Record<TeamMember['status'], React.ReactNode> = {
    active: <Icons.Check className="w-3 h-3" />,
    approved: <Icons.Check className="w-3 h-3" />,
    pending: <Icons.Clock className="w-3 h-3" />,
    suspended: <Icons.X className="w-3 h-3" />,
    rejected: <Icons.X className="w-3 h-3" />,
  };

  const labels: Record<TeamMember['status'], string> = {
    active: 'Active',
    approved: 'Active',
    pending: 'Pending',
    suspended: 'Suspended',
    rejected: 'Rejected',
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}>
      {icons[status]}
      {labels[status]}
    </span>
  );
}

// ============================================================================
// Member Avatar
// ============================================================================

function MemberAvatar({ member, size = 'md' }: { member: TeamMember; size?: 'sm' | 'md' | 'lg' }) {
  const sizes = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
  };

  const initials = member.name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase();

  const colors = [
    'from-indigo-500 to-purple-500',
    'from-emerald-500 to-teal-500',
    'from-amber-500 to-orange-500',
    'from-rose-500 to-pink-500',
    'from-cyan-500 to-blue-500',
  ];
  
  const colorIndex = member.id.charCodeAt(0) % colors.length;

  return (
    <div className={`${sizes[size]} rounded-full bg-gradient-to-br ${colors[colorIndex]} flex items-center justify-center text-white font-medium`}>
      {initials}
    </div>
  );
}

// ============================================================================
// Invite Modal
// ============================================================================

function InviteModal({ 
  isOpen, 
  onClose 
}: { 
  isOpen: boolean; 
  onClose: () => void;
}) {
  const { isDark } = useTheme();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<TeamMember['role']>('member');
  const [sending, setSending] = useState(false);

  const handleInvite = async () => {
    setSending(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSending(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className={`relative w-full max-w-md rounded-2xl shadow-2xl p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
          <button 
            onClick={onClose}
            className={`absolute top-4 right-4 p-2 rounded-lg ${isDark ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
          >
            <Icons.X />
          </button>

          <h2 className={`text-xl font-bold mb-1 ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Invite Team Member</h2>
          <p className={`text-sm mb-6 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Send an invitation to join your organization
          </p>

          <div className="space-y-4">
            <div>
              <label className={`block text-sm font-medium mb-1.5 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@company.com"
                className={`w-full px-4 py-2.5 rounded-xl border outline-none transition-all ${isDark ? 'bg-gray-700 border-gray-600 text-gray-100 placeholder-gray-500 focus:border-indigo-500' : 'border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100'}`}
              />
            </div>

            <div>
              <label className={`block text-sm font-medium mb-1.5 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as TeamMember['role'])}
                className={`w-full px-4 py-2.5 rounded-xl border outline-none transition-all appearance-none ${isDark ? 'bg-gray-700 border-gray-600 text-gray-100' : 'bg-white border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100'}`}
              >
                <option value="admin">Admin - Full access to all features</option>
                <option value="member">Member - Can upload and manage files</option>
                <option value="viewer">Viewer - Read-only access</option>
              </select>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
              <h4 className={`text-sm font-medium mb-2 flex items-center gap-2 ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>
                <Icons.Shield className="w-4 h-4 text-indigo-500" />
                Role Permissions
              </h4>
              <div className={`space-y-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {role === 'admin' && (
                  <>
                    <p>• Manage team members and roles</p>
                    <p>• Access all files and folders</p>
                    <p>• Manage organization settings</p>
                    <p>• View analytics and reports</p>
                  </>
                )}
                {role === 'member' && (
                  <>
                    <p>• Upload and manage own files</p>
                    <p>• Access shared files</p>
                    <p>• Create and manage folders</p>
                  </>
                )}
                {role === 'viewer' && (
                  <>
                    <p>• View shared files only</p>
                    <p>• Download files</p>
                    <p>• No upload permissions</p>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={onClose}
              className={`flex-1 px-4 py-2.5 border rounded-xl font-medium transition-colors ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-200 text-gray-700 hover:bg-gray-50'}`}
            >
              Cancel
            </button>
            <button
              onClick={handleInvite}
              disabled={!email || sending}
              className="flex-1 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending ? 'Sending...' : 'Send Invitation'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Team Member Row
// ============================================================================

function TeamMemberRow({ member }: { member: TeamMember }) {
  const { isDark } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  const formatStorage = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <tr className={`group ${isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}`}>
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <MemberAvatar member={member} />
          <div>
            <p className={`text-sm font-medium ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{member.name}</p>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{member.email}</p>
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <RoleBadge role={member.role} />
      </td>
      <td className="px-6 py-4">
        <StatusBadge status={member.status} />
      </td>
      <td className={`px-6 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        {member.lastActive || '—'}
      </td>
      <td className={`px-6 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        {member.filesUploaded.toLocaleString()}
      </td>
      <td className={`px-6 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        {formatStorage(member.storageUsed)}
      </td>
      <td className="px-6 py-4">
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className={`p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity ${isDark ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
          >
            <Icons.MoreVertical />
          </button>
          
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className={`absolute right-0 top-full mt-1 w-48 rounded-xl shadow-xl border py-2 z-20 ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
                <button className={`w-full flex items-center gap-3 px-4 py-2 text-sm ${isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-50'}`}>
                  <Icons.Edit />
                  Edit Role
                </button>
                <button className={`w-full flex items-center gap-3 px-4 py-2 text-sm ${isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-50'}`}>
                  <Icons.Mail />
                  Send Message
                </button>
                {member.role !== 'owner' && (
                  <button className={`w-full flex items-center gap-3 px-4 py-2 text-sm ${isDark ? 'text-red-400 hover:bg-red-900/30' : 'text-red-600 hover:bg-red-50'}`}>
                    <Icons.Trash />
                    Remove
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

// ============================================================================
// Team Page
// ============================================================================

export default function TeamPage() {
  const { currentOrg, user } = useAuth();
  const { isDark } = useTheme();
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [showInvite, setShowInvite] = useState(false);
  const [filterRole, setFilterRole] = useState<string>('all');
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);

  // Check if user has access to this page
  const hasAccess = ['manager', 'org_admin', 'super_admin'].includes(user?.role || '');
  const canManageTeam = ['org_admin', 'super_admin'].includes(user?.role || '');

  // Fetch team members when organization changes
  useEffect(() => {
    const fetchTeamMembers = async () => {
      if (!user?.organization_id) {
        setTeamMembers([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const users = await usersApi.listByOrganization(user.organization_id);
        const members: TeamMember[] = users.map(u => ({
          id: u.id,
          name: u.name,
          email: u.email || '',
          role: mapRole(u.role || 'user'),
          status: mapStatus(u.status || 'approved'),
          lastActive: 'Recently',
          filesUploaded: 0, // TODO: Get from file stats
          storageUsed: 0, // TODO: Get from storage stats
        }));
        setTeamMembers(members);
      } catch (error) {
        console.error('Failed to fetch team members:', error);
        setTeamMembers([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTeamMembers();
  }, [user?.organization_id]);

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
          <p className="text-lg font-medium">Access Denied</p>
          <p className="text-sm">You don&apos;t have permission to view this page.</p>
        </div>
      </div>
    );
  }

  const filteredMembers = teamMembers.filter(member => {
    const matchesSearch = member.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         member.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = filterRole === 'all' || member.role === filterRole;
    return matchesSearch && matchesRole;
  });

  const roleStats = {
    owner: teamMembers.filter(m => m.role === 'owner' || m.role === 'org_admin').length,
    admin: teamMembers.filter(m => m.role === 'admin' || m.role === 'manager').length,
    member: teamMembers.filter(m => m.role === 'member' || m.role === 'user').length,
    viewer: teamMembers.filter(m => m.role === 'viewer').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Team</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Manage team members for {currentOrg?.name}
          </p>
        </div>
        {canManageTeam && (
          <button
            onClick={() => setShowInvite(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
          >
            <Icons.Plus />
            Invite Member
          </button>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(roleStats).map(([role, count]) => (
          <div 
            key={role}
            onClick={() => setFilterRole(filterRole === role ? 'all' : role)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              isDark ? 'bg-gray-800' : 'bg-white'
            } ${
              filterRole === role 
                ? (isDark ? 'border-indigo-500 ring-2 ring-indigo-500/30' : 'border-indigo-500 ring-2 ring-indigo-100')
                : isDark ? 'border-gray-700 hover:border-gray-600' : 'border-gray-100 hover:border-gray-200'
            }`}
          >
            <p className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{count}</p>
            <p className={`text-sm capitalize ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{role}s</p>
          </div>
        ))}
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className={`flex-1 flex items-center gap-2 px-4 py-2.5 border rounded-xl ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
          <svg className={`w-5 h-5 flex-shrink-0 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search team members..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`flex-1 bg-transparent border-none outline-none text-sm ${isDark ? 'text-gray-200 placeholder-gray-500' : 'text-gray-600 placeholder-gray-400'}`}
          />
        </div>
        
        <select
          value={filterRole}
          onChange={(e) => setFilterRole(e.target.value)}
          className={`px-4 py-2.5 border rounded-xl text-sm outline-none appearance-none ${isDark ? 'bg-gray-800 border-gray-700 text-gray-200' : 'bg-white border-gray-200 text-gray-600'}`}
        >
          <option value="all">All Roles</option>
          <option value="owner">Owner</option>
          <option value="admin">Admin</option>
          <option value="member">Member</option>
          <option value="viewer">Viewer</option>
        </select>
      </div>

      {/* Team Table */}
      <div className={`rounded-2xl border shadow-sm overflow-hidden ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          </div>
        ) : filteredMembers.length === 0 ? (
          <div className="text-center py-16">
            <p className={`text-lg font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              {teamMembers.length === 0 ? 'No team members yet' : 'No members match your filters'}
            </p>
            <p className={`mt-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              {teamMembers.length === 0 
                ? 'Invite team members to collaborate on files' 
                : 'Try adjusting your search or filter criteria'}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className={`border-b ${isDark ? 'border-gray-700 bg-gray-700/50' : 'border-gray-100 bg-gray-50'}`}>
                <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Member</th>
                <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Role</th>
                <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Status</th>
                <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Last Active</th>
                <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Files</th>
                <th className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Storage</th>
                <th className="px-6 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-50'}`}>
              {filteredMembers.map((member) => (
                <TeamMemberRow key={member.id} member={member} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Invite Modal */}
      <InviteModal
        isOpen={showInvite}
        onClose={() => setShowInvite(false)}
      />
    </div>
  );
}
