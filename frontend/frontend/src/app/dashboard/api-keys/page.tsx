"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useRouter } from 'next/navigation';
import { 
  Key, 
  Plus, 
  Copy, 
  Trash2, 
  Eye, 
  EyeOff, 
  Shield,
  Clock,
  Check,
  X,
  AlertTriangle
} from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

interface ApiKey {
  id: string;
  name: string;
  key: string;
  createdAt: string;
  lastUsed: string;
  expiresAt: string;
  permissions: string[];
  status: 'active' | 'expired' | 'revoked';
}

// ============================================================================
// Mock Data
// ============================================================================

const mockApiKeys: ApiKey[] = [
  {
    id: '1',
    name: 'Production API Key',
    key: 'fv_live_sk_1234567890abcdef1234567890abcdef',
    createdAt: '2024-01-15',
    lastUsed: '2 hours ago',
    expiresAt: '2025-01-15',
    permissions: ['read', 'write', 'delete'],
    status: 'active',
  },
  {
    id: '2',
    name: 'Development Key',
    key: 'fv_test_sk_0987654321fedcba0987654321fedcba',
    createdAt: '2024-03-20',
    lastUsed: '1 day ago',
    expiresAt: '2025-03-20',
    permissions: ['read', 'write'],
    status: 'active',
  },
  {
    id: '3',
    name: 'CI/CD Pipeline',
    key: 'fv_ci_sk_abcdef1234567890abcdef1234567890',
    createdAt: '2024-06-01',
    lastUsed: 'Never',
    expiresAt: '2024-12-01',
    permissions: ['read'],
    status: 'expired',
  },
];

// ============================================================================
// Create Key Modal
// ============================================================================

function CreateKeyModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { isDark } = useTheme();
  const [name, setName] = useState('');
  const [permissions, setPermissions] = useState<string[]>(['read']);
  const [expiresIn, setExpiresIn] = useState('30');

  if (!isOpen) return null;

  const togglePermission = (perm: string) => {
    setPermissions(prev => 
      prev.includes(perm) 
        ? prev.filter(p => p !== perm) 
        : [...prev, perm]
    );
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className={`relative w-full max-w-md rounded-2xl shadow-2xl p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="flex items-center justify-between mb-6">
            <h2 className={`text-xl font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Create API Key</h2>
            <button onClick={onClose} className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700 text-gray-400' : 'hover:bg-gray-100 text-gray-500'}`}>
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className={`block text-sm font-medium mb-1.5 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Key Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Production API Key"
                className={`w-full px-4 py-3 rounded-xl border outline-none transition-all ${
                  isDark 
                    ? 'bg-gray-700 border-gray-600 text-gray-100 focus:border-indigo-500' 
                    : 'bg-white border-gray-200 text-gray-900 focus:border-indigo-500'
                }`}
              />
            </div>

            <div>
              <label className={`block text-sm font-medium mb-1.5 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Permissions</label>
              <div className="flex flex-wrap gap-2">
                {['read', 'write', 'delete'].map(perm => (
                  <button
                    key={perm}
                    onClick={() => togglePermission(perm)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                      permissions.includes(perm)
                        ? 'bg-indigo-600 text-white'
                        : isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {perm.charAt(0).toUpperCase() + perm.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className={`block text-sm font-medium mb-1.5 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Expires In</label>
              <select
                value={expiresIn}
                onChange={(e) => setExpiresIn(e.target.value)}
                className={`w-full px-4 py-3 rounded-xl border outline-none transition-all ${
                  isDark 
                    ? 'bg-gray-700 border-gray-600 text-gray-100' 
                    : 'bg-white border-gray-200 text-gray-900'
                }`}
              >
                <option value="30">30 days</option>
                <option value="90">90 days</option>
                <option value="365">1 year</option>
                <option value="never">Never</option>
              </select>
            </div>

            <button
              onClick={onClose}
              className="w-full py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
            >
              <Key className="w-4 h-4" />
              Generate API Key
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// API Key Row
// ============================================================================

function ApiKeyRow({ apiKey, onDelete }: { apiKey: ApiKey; onDelete: (id: string) => void }) {
  const { isDark } = useTheme();
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(apiKey.key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const maskedKey = apiKey.key.slice(0, 10) + '••••••••••••••••••••••••••';

  return (
    <div className={`p-4 rounded-xl border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <h3 className={`font-medium ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{apiKey.name}</h3>
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
              apiKey.status === 'active' 
                ? isDark ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-700'
                : apiKey.status === 'expired'
                ? isDark ? 'bg-amber-900/30 text-amber-400' : 'bg-amber-100 text-amber-700'
                : isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-100 text-red-700'
            }`}>
              {apiKey.status.charAt(0).toUpperCase() + apiKey.status.slice(1)}
            </span>
          </div>
          
          <div className={`flex items-center gap-2 font-mono text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            <code className="truncate">{showKey ? apiKey.key : maskedKey}</code>
            <button 
              onClick={() => setShowKey(!showKey)}
              className={`p-1 rounded ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
            >
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
            <button 
              onClick={copyToClipboard}
              className={`p-1 rounded ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
            >
              {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>

          <div className={`flex flex-wrap items-center gap-4 mt-3 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Created {apiKey.createdAt}
            </span>
            <span>Last used: {apiKey.lastUsed}</span>
            <span>Expires: {apiKey.expiresAt}</span>
          </div>

          <div className="flex flex-wrap gap-1 mt-2">
            {apiKey.permissions.map(perm => (
              <span 
                key={perm} 
                className={`px-2 py-0.5 text-xs rounded ${isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}`}
              >
                {perm}
              </span>
            ))}
          </div>
        </div>

        <button
          onClick={() => onDelete(apiKey.id)}
          className={`p-2 rounded-lg text-red-500 ${isDark ? 'hover:bg-red-900/30' : 'hover:bg-red-50'}`}
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// API Keys Page
// ============================================================================

export default function ApiKeysPage() {
  const { user, currentOrg } = useAuth();
  const { isDark } = useTheme();
  const router = useRouter();
  const [showCreate, setShowCreate] = useState(false);
  const [keys, setKeys] = useState(mockApiKeys);

  // Check if user has access to this page
  const hasAccess = ['org_admin', 'super_admin'].includes(user?.role || '');
  const hasApiFeature = currentOrg?.features.api_access;

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
          <Shield className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">Access Denied</p>
          <p className="text-sm">You don&apos;t have permission to manage API keys.</p>
        </div>
      </div>
    );
  }

  if (!hasApiFeature) {
    return (
      <div className={`flex items-center justify-center min-h-[60vh] ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-amber-500" />
          <p className="text-lg font-medium">API Access Not Available</p>
          <p className="text-sm">Upgrade your plan to enable API access.</p>
          <button className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700">
            Upgrade Plan
          </button>
        </div>
      </div>
    );
  }

  const handleDelete = (id: string) => {
    setKeys(keys.filter(k => k.id !== id));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>API Keys</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Manage API keys for programmatic access
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create API Key
        </button>
      </div>

      {/* Warning */}
      <div className={`p-4 rounded-xl border ${isDark ? 'bg-amber-900/20 border-amber-800' : 'bg-amber-50 border-amber-200'}`}>
        <div className="flex items-start gap-3">
          <AlertTriangle className={`w-5 h-5 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
          <div>
            <p className={`font-medium ${isDark ? 'text-amber-300' : 'text-amber-800'}`}>Keep your API keys secure</p>
            <p className={`text-sm ${isDark ? 'text-amber-400' : 'text-amber-700'}`}>
              Never share your API keys in public repositories or client-side code.
            </p>
          </div>
        </div>
      </div>

      {/* API Keys List */}
      <div className="space-y-4">
        {keys.map(key => (
          <ApiKeyRow key={key.id} apiKey={key} onDelete={handleDelete} />
        ))}
      </div>

      {keys.length === 0 && (
        <div className={`text-center py-12 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          <Key className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No API keys</p>
          <p className="text-sm">Create your first API key to get started.</p>
        </div>
      )}

      {/* Create Modal */}
      <CreateKeyModal isOpen={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  );
}
