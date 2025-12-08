"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useRouter } from 'next/navigation';
import { 
  Shield, 
  Lock, 
  Smartphone, 
  Key, 
  AlertTriangle,
  Check,
  X,
  Eye,
  EyeOff,
  Monitor,
  MapPin,
  Clock,
  Trash2,
  LogOut
} from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

interface Session {
  id: string;
  device: string;
  browser: string;
  location: string;
  ip: string;
  lastActive: string;
  current: boolean;
}

// ============================================================================
// Mock Data
// ============================================================================

const mockSessions: Session[] = [
  {
    id: '1',
    device: 'Windows PC',
    browser: 'Chrome 120',
    location: 'New York, USA',
    ip: '192.168.1.1',
    lastActive: 'Active now',
    current: true,
  },
  {
    id: '2',
    device: 'MacBook Pro',
    browser: 'Safari 17',
    location: 'San Francisco, USA',
    ip: '10.0.0.42',
    lastActive: '2 hours ago',
    current: false,
  },
  {
    id: '3',
    device: 'iPhone 15',
    browser: 'Safari Mobile',
    location: 'Los Angeles, USA',
    ip: '172.16.0.1',
    lastActive: '1 day ago',
    current: false,
  },
];

// ============================================================================
// Security Option Component
// ============================================================================

function SecurityOption({ 
  icon: Icon, 
  title, 
  description, 
  enabled, 
  onToggle,
  recommended = false 
}: { 
  icon: React.ElementType;
  title: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
  recommended?: boolean;
}) {
  const { isDark } = useTheme();

  return (
    <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${enabled ? 'bg-green-500/20 text-green-500' : isDark ? 'bg-gray-700 text-gray-400' : 'bg-gray-100 text-gray-500'}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className={`font-medium ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{title}</h3>
              {recommended && (
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${isDark ? 'bg-indigo-900/30 text-indigo-400' : 'bg-indigo-100 text-indigo-700'}`}>
                  Recommended
                </span>
              )}
            </div>
            <p className={`text-sm mt-0.5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{description}</p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className={`relative w-12 h-6 rounded-full transition-colors ${enabled ? 'bg-green-500' : isDark ? 'bg-gray-600' : 'bg-gray-300'}`}
        >
          <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${enabled ? 'left-7' : 'left-1'}`} />
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Session Row Component
// ============================================================================

function SessionRow({ session, onRevoke }: { session: Session; onRevoke: (id: string) => void }) {
  const { isDark } = useTheme();

  return (
    <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
            <Monitor className={`w-5 h-5 ${isDark ? 'text-gray-300' : 'text-gray-600'}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className={`font-medium ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                {session.device}
              </h3>
              {session.current && (
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${isDark ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-700'}`}>
                  Current
                </span>
              )}
            </div>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{session.browser}</p>
            <div className={`flex flex-wrap items-center gap-4 mt-2 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                {session.location}
              </span>
              <span>{session.ip}</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {session.lastActive}
              </span>
            </div>
          </div>
        </div>
        {!session.current && (
          <button
            onClick={() => onRevoke(session.id)}
            className={`p-2 rounded-lg text-red-500 ${isDark ? 'hover:bg-red-900/30' : 'hover:bg-red-50'}`}
          >
            <LogOut className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Change Password Modal
// ============================================================================

function ChangePasswordModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { isDark } = useTheme();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);

  if (!isOpen) return null;

  const passwordsMatch = newPassword === confirmPassword;
  const isValid = currentPassword && newPassword && confirmPassword && passwordsMatch && newPassword.length >= 8;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className={`relative w-full max-w-md rounded-2xl shadow-2xl p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="flex items-center justify-between mb-6">
            <h2 className={`text-xl font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Change Password</h2>
            <button onClick={onClose} className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700 text-gray-400' : 'hover:bg-gray-100 text-gray-500'}`}>
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className={`block text-sm font-medium mb-1.5 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Current Password</label>
              <div className="relative">
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className={`w-full px-4 py-3 pr-10 rounded-xl border outline-none transition-all ${
                    isDark 
                      ? 'bg-gray-700 border-gray-600 text-gray-100 focus:border-indigo-500' 
                      : 'bg-white border-gray-200 text-gray-900 focus:border-indigo-500'
                  }`}
                />
                <button 
                  type="button"
                  onClick={() => setShowPasswords(!showPasswords)}
                  className={`absolute right-3 top-1/2 -translate-y-1/2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                >
                  {showPasswords ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className={`block text-sm font-medium mb-1.5 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>New Password</label>
              <input
                type={showPasswords ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className={`w-full px-4 py-3 rounded-xl border outline-none transition-all ${
                  isDark 
                    ? 'bg-gray-700 border-gray-600 text-gray-100 focus:border-indigo-500' 
                    : 'bg-white border-gray-200 text-gray-900 focus:border-indigo-500'
                }`}
              />
              {newPassword && newPassword.length < 8 && (
                <p className="text-red-500 text-xs mt-1">Password must be at least 8 characters</p>
              )}
            </div>

            <div>
              <label className={`block text-sm font-medium mb-1.5 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Confirm New Password</label>
              <input
                type={showPasswords ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`w-full px-4 py-3 rounded-xl border outline-none transition-all ${
                  isDark 
                    ? 'bg-gray-700 border-gray-600 text-gray-100 focus:border-indigo-500' 
                    : 'bg-white border-gray-200 text-gray-900 focus:border-indigo-500'
                } ${confirmPassword && !passwordsMatch ? 'border-red-500' : ''}`}
              />
              {confirmPassword && !passwordsMatch && (
                <p className="text-red-500 text-xs mt-1">Passwords do not match</p>
              )}
            </div>

            <button
              onClick={onClose}
              disabled={!isValid}
              className={`w-full py-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2 ${
                isValid 
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700' 
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              <Lock className="w-4 h-4" />
              Update Password
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Security Page
// ============================================================================

export default function SecurityPage() {
  const { user } = useAuth();
  const { isDark } = useTheme();
  const router = useRouter();
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [sessions, setSessions] = useState(mockSessions);
  
  // Security settings state
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [sessionAlerts, setSessionAlerts] = useState(true);
  const [loginNotifications, setLoginNotifications] = useState(true);
  const [ipWhitelisting, setIpWhitelisting] = useState(false);

  // Check if user has access (org_admin, super_admin, or manager can access their own security)
  const hasAccess = user !== null;
  const isAdmin = ['org_admin', 'super_admin'].includes(user?.role || '');

  // Redirect if no access
  useEffect(() => {
    if (!hasAccess) {
      router.push('/dashboard');
    }
  }, [hasAccess, router]);

  if (!hasAccess) {
    return (
      <div className={`flex items-center justify-center min-h-[60vh] ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        <div className="text-center">
          <Shield className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">Access Denied</p>
          <p className="text-sm">Please log in to access security settings.</p>
        </div>
      </div>
    );
  }

  const handleRevokeSession = (id: string) => {
    setSessions(sessions.filter(s => s.id !== id));
  };

  const handleRevokeAllSessions = () => {
    setSessions(sessions.filter(s => s.current));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Security</h1>
        <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          Manage your account security settings
        </p>
      </div>

      {/* Password Section */}
      <div className={`p-6 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <h2 className={`text-lg font-semibold mb-4 ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Password</h2>
        <div className="flex items-center justify-between">
          <div>
            <p className={`${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Last changed 30 days ago</p>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              We recommend changing your password regularly
            </p>
          </div>
          <button
            onClick={() => setShowPasswordModal(true)}
            className="px-4 py-2 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
          >
            Change Password
          </button>
        </div>
      </div>

      {/* Security Options */}
      <div className={`p-6 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <h2 className={`text-lg font-semibold mb-4 ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Security Options</h2>
        <div className="space-y-4">
          <SecurityOption
            icon={Smartphone}
            title="Two-Factor Authentication"
            description="Add an extra layer of security with 2FA"
            enabled={twoFactorEnabled}
            onToggle={() => setTwoFactorEnabled(!twoFactorEnabled)}
            recommended
          />
          <SecurityOption
            icon={AlertTriangle}
            title="Session Alerts"
            description="Get notified when a new device logs into your account"
            enabled={sessionAlerts}
            onToggle={() => setSessionAlerts(!sessionAlerts)}
          />
          <SecurityOption
            icon={Lock}
            title="Login Notifications"
            description="Receive email notifications for successful logins"
            enabled={loginNotifications}
            onToggle={() => setLoginNotifications(!loginNotifications)}
          />
          {isAdmin && (
            <SecurityOption
              icon={Shield}
              title="IP Whitelisting"
              description="Restrict access to specific IP addresses (Admin only)"
              enabled={ipWhitelisting}
              onToggle={() => setIpWhitelisting(!ipWhitelisting)}
            />
          )}
        </div>
      </div>

      {/* Active Sessions */}
      <div className={`p-6 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className={`text-lg font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Active Sessions</h2>
          {sessions.length > 1 && (
            <button
              onClick={handleRevokeAllSessions}
              className={`text-sm font-medium text-red-500 hover:text-red-600`}
            >
              Revoke All Other Sessions
            </button>
          )}
        </div>
        <div className="space-y-4">
          {sessions.map(session => (
            <SessionRow key={session.id} session={session} onRevoke={handleRevokeSession} />
          ))}
        </div>
      </div>

      {/* Danger Zone - Admin Only */}
      {isAdmin && (
        <div className={`p-6 rounded-xl border ${isDark ? 'bg-red-900/20 border-red-800' : 'bg-red-50 border-red-200'}`}>
          <h2 className={`text-lg font-semibold mb-4 ${isDark ? 'text-red-400' : 'text-red-700'}`}>Danger Zone</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className={`font-medium ${isDark ? 'text-red-300' : 'text-red-800'}`}>Delete Account</p>
              <p className={`text-sm ${isDark ? 'text-red-400' : 'text-red-600'}`}>
                Permanently delete your account and all associated data
              </p>
            </div>
            <button className="px-4 py-2 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-colors">
              Delete Account
            </button>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      <ChangePasswordModal isOpen={showPasswordModal} onClose={() => setShowPasswordModal(false)} />
    </div>
  );
}
