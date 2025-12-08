"use client";

import React, { useState } from 'react';
import { useAuth, PendingRegistration } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { 
  UserPlus, 
  Building2, 
  Check, 
  X, 
  Clock, 
  Mail, 
  Calendar,
  Users,
  Shield,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Filter
} from 'lucide-react';

// ============================================================================
// Registration Card Component
// ============================================================================

function RegistrationCard({ 
  registration, 
  onApprove, 
  onReject,
  isLoading 
}: { 
  registration: PendingRegistration;
  onApprove: () => void;
  onReject: () => void;
  isLoading: boolean;
}) {
  const { isDark } = useTheme();
  const [expanded, setExpanded] = useState(false);

  const isOrg = registration.type === 'organization';
  const timeAgo = getTimeAgo(registration.created_at);

  return (
    <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className={`p-2.5 rounded-xl ${
              isOrg 
                ? isDark ? 'bg-purple-900/30 text-purple-400' : 'bg-purple-100 text-purple-600'
                : isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-600'
            }`}>
              {isOrg ? <Building2 className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className={`font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                  {registration.user.name}
                </h3>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                  isOrg 
                    ? isDark ? 'bg-purple-900/30 text-purple-400' : 'bg-purple-100 text-purple-700'
                    : isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-700'
                }`}>
                  {isOrg ? 'New Organization' : 'Join Request'}
                </span>
              </div>
              <div className={`flex items-center gap-3 mt-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                <span className="flex items-center gap-1">
                  <Mail className="w-3.5 h-3.5" />
                  {registration.user.email}
                </span>
              </div>
            </div>
          </div>
          <div className={`flex items-center gap-1.5 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            <Clock className="w-3.5 h-3.5" />
            {timeAgo}
          </div>
        </div>

        {/* Organization Info */}
        <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
          {isOrg && registration.organization ? (
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-sm font-medium ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>
                  {registration.organization.name}
                </p>
                <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Plan: {registration.organization.plan.charAt(0).toUpperCase() + registration.organization.plan.slice(1)}
                </p>
              </div>
              <div className={`px-2 py-1 rounded text-xs font-medium ${isDark ? 'bg-purple-900/30 text-purple-400' : 'bg-purple-100 text-purple-700'}`}>
                Org Admin
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-sm font-medium ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>
                  Joining: {registration.organization_name}
                </p>
                <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Requested role: {registration.requested_role}
                </p>
              </div>
              <div className={`px-2 py-1 rounded text-xs font-medium ${isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-700'}`}>
                Member
              </div>
            </div>
          )}
        </div>

        {/* Expand/Collapse */}
        <button
          onClick={() => setExpanded(!expanded)}
          className={`flex items-center gap-1 mt-3 text-xs font-medium ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`}
        >
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          {expanded ? 'Less details' : 'More details'}
        </button>

        {/* Expanded Details */}
        {expanded && (
          <div className={`mt-3 pt-3 border-t space-y-2 ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className={`${isDark ? 'text-gray-500' : 'text-gray-400'}`}>User ID:</span>
                <span className={`ml-2 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                  {registration.user.id}
                </span>
              </div>
              <div>
                <span className={`${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Request ID:</span>
                <span className={`ml-2 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                  {registration.id}
                </span>
              </div>
            </div>
            <div className="text-sm">
              <span className={`${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Submitted:</span>
              <span className={`ml-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                {new Date(registration.created_at).toLocaleString()}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className={`flex items-center gap-2 p-3 border-t ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-gray-50 border-gray-200'}`}>
        <button
          onClick={onApprove}
          disabled={isLoading}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50"
        >
          <Check className="w-4 h-4" />
          Approve
        </button>
        <button
          onClick={onReject}
          disabled={isLoading}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 ${
            isDark 
              ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' 
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          <X className="w-4 h-4" />
          Reject
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

function getTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'Yesterday';
  return `${days}d ago`;
}

// ============================================================================
// Approvals Page
// ============================================================================

export default function ApprovalsPage() {
  const { user, pendingRegistrations, approveRegistration, rejectRegistration } = useAuth();
  const { isDark } = useTheme();
  const [filter, setFilter] = useState<'all' | 'organization' | 'member'>('all');
  const [loadingId, setLoadingId] = useState<string | null>(null);

  // Filter registrations based on user role and selected filter
  const filteredRegistrations = pendingRegistrations.filter(reg => {
    // Super admin sees all, org_admin sees only member requests for their org
    if (user?.role === 'org_admin') {
      // Org admins can only approve member requests for their organization
      if (reg.type === 'organization') return false;
      if (reg.organization_id !== user.organization_id) return false;
    }
    
    // Apply type filter
    if (filter !== 'all' && reg.type !== filter) return false;
    
    return reg.status === 'pending';
  });

  const orgRequests = pendingRegistrations.filter(r => r.type === 'organization' && r.status === 'pending');
  const memberRequests = pendingRegistrations.filter(r => r.type === 'member' && r.status === 'pending');

  const handleApprove = async (registrationId: string) => {
    if (!user) return;
    setLoadingId(registrationId);
    try {
      await approveRegistration(registrationId, user.id);
    } catch (error) {
      console.error('Failed to approve:', error);
    } finally {
      setLoadingId(null);
    }
  };

  const handleReject = async (registrationId: string) => {
    if (!user) return;
    setLoadingId(registrationId);
    try {
      await rejectRegistration(registrationId, user.id);
    } catch (error) {
      console.error('Failed to reject:', error);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
            Pending Approvals
          </h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Review and approve registration requests
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isDark ? 'bg-amber-900/30 text-amber-400' : 'bg-amber-100 text-amber-600'}`}>
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                {filteredRegistrations.length}
              </p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Pending Requests
              </p>
            </div>
          </div>
        </div>

        {user?.role === 'super_admin' && (
          <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${isDark ? 'bg-purple-900/30 text-purple-400' : 'bg-purple-100 text-purple-600'}`}>
                <Building2 className="w-5 h-5" />
              </div>
              <div>
                <p className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                  {orgRequests.length}
                </p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  New Organizations
                </p>
              </div>
            </div>
          </div>
        )}

        <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-600'}`}>
              <Users className="w-5 h-5" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                {memberRequests.length}
              </p>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Member Requests
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Tabs (super_admin only) */}
      {user?.role === 'super_admin' && (
        <div className="flex items-center gap-2">
          <Filter className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
          <div className={`flex gap-1 p-1 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
            {[
              { value: 'all', label: 'All' },
              { value: 'organization', label: 'Organizations' },
              { value: 'member', label: 'Members' },
            ].map(f => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value as typeof filter)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  filter === f.value
                    ? isDark ? 'bg-gray-700 text-gray-100' : 'bg-white text-gray-900 shadow-sm'
                    : isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Registrations List */}
      {filteredRegistrations.length > 0 ? (
        <div className="grid gap-4">
          {filteredRegistrations.map(registration => (
            <RegistrationCard
              key={registration.id}
              registration={registration}
              onApprove={() => handleApprove(registration.id)}
              onReject={() => handleReject(registration.id)}
              isLoading={loadingId === registration.id}
            />
          ))}
        </div>
      ) : (
        <div className={`text-center py-16 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-gray-50 border-gray-200'}`}>
          <div className={`w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
            <Check className={`w-8 h-8 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
          </div>
          <h3 className={`text-lg font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            No pending approvals
          </h3>
          <p className={`mt-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            All registration requests have been processed
          </p>
        </div>
      )}

      {/* Info Box */}
      <div className={`p-4 rounded-xl border ${isDark ? 'bg-blue-900/20 border-blue-800' : 'bg-blue-50 border-blue-200'}`}>
        <div className="flex items-start gap-3">
          <AlertCircle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${isDark ? 'text-blue-400' : 'text-blue-600'}`} />
          <div>
            <p className={`font-medium ${isDark ? 'text-blue-300' : 'text-blue-800'}`}>
              Approval Workflow
            </p>
            <p className={`text-sm mt-1 ${isDark ? 'text-blue-400' : 'text-blue-700'}`}>
              {user?.role === 'super_admin' 
                ? 'As a Super Admin, you can approve both new organization registrations and member join requests.'
                : 'As an Organization Admin, you can approve member requests to join your organization. New organization registrations require Super Admin approval.'
              }
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
