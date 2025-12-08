"use client";

import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

// ============================================================================
// Icons
// ============================================================================

const Icons = {
  Building: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
    </svg>
  ),
  Shield: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  Bell: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
  ),
  Key: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
    </svg>
  ),
  CreditCard: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
    </svg>
  ),
  Database: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  ),
  Globe: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
    </svg>
  ),
  Trash: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  ),
  Copy: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  ),
  RefreshCw: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  Check: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  AlertTriangle: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
};

// ============================================================================
// Types
// ============================================================================

interface SettingsSection {
  id: string;
  label: string;
  icon: React.ReactNode;
}

// ============================================================================
// Settings Sections
// ============================================================================

const settingsSections: SettingsSection[] = [
  { id: 'organization', label: 'Organization', icon: <Icons.Building /> },
  { id: 'security', label: 'Security', icon: <Icons.Shield /> },
  { id: 'notifications', label: 'Notifications', icon: <Icons.Bell /> },
  { id: 'api', label: 'API Keys', icon: <Icons.Key /> },
  { id: 'billing', label: 'Billing', icon: <Icons.CreditCard /> },
  { id: 'storage', label: 'Storage', icon: <Icons.Database /> },
  { id: 'integrations', label: 'Integrations', icon: <Icons.Globe /> },
  { id: 'danger', label: 'Danger Zone', icon: <Icons.Trash /> },
];

// ============================================================================
// Toggle Switch
// ============================================================================

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        enabled ? 'bg-indigo-600' : 'bg-gray-200'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          enabled ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

// ============================================================================
// Organization Settings
// ============================================================================

function OrganizationSettings() {
  const { currentOrg } = useAuth();
  const [name, setName] = useState(currentOrg?.name || '');
  const [slug, setSlug] = useState(currentOrg?.slug || '');

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Organization Details</h3>
        <p className="text-sm text-gray-500 mt-1">Basic information about your organization</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Organization Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Organization Slug
          </label>
          <div className="flex items-center">
            <span className="px-4 py-2.5 bg-gray-100 border border-r-0 border-gray-200 rounded-l-xl text-sm text-gray-500">
              filecloud.io/
            </span>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
              className="flex-1 px-4 py-2.5 rounded-r-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Organization Logo
          </label>
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white text-xl font-bold">
              {name.charAt(0) || 'O'}
            </div>
            <button className="px-4 py-2 border border-gray-200 rounded-xl text-sm text-gray-700 hover:bg-gray-50 transition-colors">
              Change Logo
            </button>
          </div>
        </div>
      </div>

      <button className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors">
        Save Changes
      </button>
    </div>
  );
}

// ============================================================================
// Security Settings
// ============================================================================

function SecuritySettings() {
  const [twoFactor, setTwoFactor] = useState(false);
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [ipRestriction, setIpRestriction] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Security Settings</h3>
        <p className="text-sm text-gray-500 mt-1">Configure security options for your organization</p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div>
            <p className="font-medium text-gray-900">Two-Factor Authentication</p>
            <p className="text-sm text-gray-500">Require 2FA for all team members</p>
          </div>
          <Toggle enabled={twoFactor} onChange={() => setTwoFactor(!twoFactor)} />
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div>
            <p className="font-medium text-gray-900">Single Sign-On (SSO)</p>
            <p className="text-sm text-gray-500">Enable SAML-based SSO with your identity provider</p>
          </div>
          <Toggle enabled={ssoEnabled} onChange={() => setSsoEnabled(!ssoEnabled)} />
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div>
            <p className="font-medium text-gray-900">IP Restriction</p>
            <p className="text-sm text-gray-500">Restrict access to specific IP ranges</p>
          </div>
          <Toggle enabled={ipRestriction} onChange={() => setIpRestriction(!ipRestriction)} />
        </div>
      </div>

      <div className="pt-4 border-t border-gray-200">
        <h4 className="font-medium text-gray-900 mb-4">Session Management</h4>
        <button className="px-4 py-2 text-red-600 border border-red-200 rounded-xl hover:bg-red-50 transition-colors">
          Sign Out All Devices
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Notifications Settings
// ============================================================================

function NotificationsSettings() {
  const [emailNotifs, setEmailNotifs] = useState(true);
  const [uploadNotifs, setUploadNotifs] = useState(true);
  const [securityAlerts, setSecurityAlerts] = useState(true);
  const [weeklyReport, setWeeklyReport] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Notification Preferences</h3>
        <p className="text-sm text-gray-500 mt-1">Control how you receive notifications</p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div>
            <p className="font-medium text-gray-900">Email Notifications</p>
            <p className="text-sm text-gray-500">Receive notifications via email</p>
          </div>
          <Toggle enabled={emailNotifs} onChange={() => setEmailNotifs(!emailNotifs)} />
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div>
            <p className="font-medium text-gray-900">Upload Notifications</p>
            <p className="text-sm text-gray-500">Get notified when files are uploaded</p>
          </div>
          <Toggle enabled={uploadNotifs} onChange={() => setUploadNotifs(!uploadNotifs)} />
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div>
            <p className="font-medium text-gray-900">Security Alerts</p>
            <p className="text-sm text-gray-500">Receive alerts for suspicious activity</p>
          </div>
          <Toggle enabled={securityAlerts} onChange={() => setSecurityAlerts(!securityAlerts)} />
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div>
            <p className="font-medium text-gray-900">Weekly Report</p>
            <p className="text-sm text-gray-500">Receive a weekly usage summary</p>
          </div>
          <Toggle enabled={weeklyReport} onChange={() => setWeeklyReport(!weeklyReport)} />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// API Keys Settings
// ============================================================================

function APISettings() {
  const [copied, setCopied] = useState(false);
  const apiKey = 'your_api_key_here';
  const maskedKey = apiKey.slice(0, 10) + '•'.repeat(28);

  const copyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">API Keys</h3>
        <p className="text-sm text-gray-500 mt-1">Manage your API keys for integrations</p>
      </div>

      <div className="p-4 bg-gray-50 rounded-xl">
        <div className="flex items-center justify-between mb-3">
          <p className="font-medium text-gray-900">Live API Key</p>
          <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">
            Active
          </span>
        </div>
        <div className="flex items-center gap-2">
          <code className="flex-1 px-4 py-2.5 bg-white border border-gray-200 rounded-lg font-mono text-sm text-gray-600">
            {maskedKey}
          </code>
          <button
            onClick={copyKey}
            className="p-2.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {copied ? (
              <Icons.Check className="text-emerald-500" />
            ) : (
              <Icons.Copy className="text-gray-400" />
            )}
          </button>
          <button className="p-2.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
            <Icons.RefreshCw className="text-gray-400" />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">Created Dec 1, 2025 • Last used 2 hours ago</p>
      </div>

      <button className="px-4 py-2.5 border border-gray-200 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors">
        Generate New API Key
      </button>

      <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3">
        <Icons.AlertTriangle className="text-amber-600 mt-0.5" />
        <div>
          <p className="font-medium text-amber-800">Keep your API keys secure</p>
          <p className="text-sm text-amber-700 mt-1">
            Never share your API keys in public repositories or client-side code.
          </p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Billing Settings
// ============================================================================

function BillingSettings() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Billing & Subscription</h3>
        <p className="text-sm text-gray-500 mt-1">Manage your subscription and payment methods</p>
      </div>

      <div className="p-6 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl text-white">
        <div className="flex items-center justify-between mb-4">
          <span className="px-3 py-1 bg-white/20 rounded-full text-sm font-medium">
            Enterprise Plan
          </span>
          <span className="text-sm opacity-80">Renews Jan 1, 2026</span>
        </div>
        <p className="text-3xl font-bold">$499<span className="text-lg font-normal opacity-80">/month</span></p>
        <p className="text-sm opacity-80 mt-1">Billed annually</p>
      </div>

      <div className="p-4 bg-gray-50 rounded-xl">
        <div className="flex items-center justify-between mb-3">
          <p className="font-medium text-gray-900">Payment Method</p>
          <button className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
            Edit
          </button>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-12 h-8 bg-gradient-to-r from-blue-600 to-blue-700 rounded flex items-center justify-center text-white text-xs font-bold">
            VISA
          </div>
          <div>
            <p className="text-sm text-gray-900">•••• •••• •••• 4242</p>
            <p className="text-xs text-gray-500">Expires 12/26</p>
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button className="px-4 py-2.5 border border-gray-200 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors">
          View Invoices
        </button>
        <button className="px-4 py-2.5 border border-gray-200 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors">
          Change Plan
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Storage Settings
// ============================================================================

function StorageSettings() {
  const storageUsed = 245.5;
  const storageTotal = 500;
  const storagePercent = (storageUsed / storageTotal) * 100;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Storage Management</h3>
        <p className="text-sm text-gray-500 mt-1">Monitor and manage your storage usage</p>
      </div>

      <div className="p-6 bg-gray-50 rounded-xl">
        <div className="flex items-center justify-between mb-3">
          <p className="font-medium text-gray-900">Storage Used</p>
          <p className="text-sm text-gray-500">{storageUsed} GB of {storageTotal} GB</p>
        </div>
        <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
            style={{ width: `${storagePercent}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-2">{(storageTotal - storageUsed).toFixed(1)} GB remaining</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Documents', size: '89.2 GB', color: 'bg-blue-500' },
          { label: 'Images', size: '67.8 GB', color: 'bg-emerald-500' },
          { label: 'Videos', size: '54.3 GB', color: 'bg-purple-500' },
          { label: 'Other', size: '34.2 GB', color: 'bg-gray-400' },
        ].map((item, i) => (
          <div key={i} className="p-4 bg-white border border-gray-200 rounded-xl">
            <div className={`w-3 h-3 ${item.color} rounded-full mb-2`} />
            <p className="text-sm text-gray-500">{item.label}</p>
            <p className="text-lg font-semibold text-gray-900">{item.size}</p>
          </div>
        ))}
      </div>

      <button className="px-4 py-2.5 border border-gray-200 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors">
        Upgrade Storage
      </button>
    </div>
  );
}

// ============================================================================
// Integrations Settings
// ============================================================================

function IntegrationsSettings() {
  const integrations = [
    { name: 'Slack', description: 'Get notifications in Slack', connected: true, icon: '💬' },
    { name: 'Google Workspace', description: 'Sync with Google Drive', connected: true, icon: '📁' },
    { name: 'Microsoft 365', description: 'Connect OneDrive and Teams', connected: false, icon: '📎' },
    { name: 'Zapier', description: 'Automate workflows', connected: false, icon: '⚡' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Integrations</h3>
        <p className="text-sm text-gray-500 mt-1">Connect with your favorite tools</p>
      </div>

      <div className="space-y-3">
        {integrations.map((integration, i) => (
          <div key={i} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
            <div className="flex items-center gap-4">
              <span className="text-2xl">{integration.icon}</span>
              <div>
                <p className="font-medium text-gray-900">{integration.name}</p>
                <p className="text-sm text-gray-500">{integration.description}</p>
              </div>
            </div>
            <button
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                integration.connected
                  ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}
            >
              {integration.connected ? 'Disconnect' : 'Connect'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Danger Zone
// ============================================================================

function DangerZone() {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteInput, setDeleteInput] = useState('');
  const { currentOrg } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-red-600">Danger Zone</h3>
        <p className="text-sm text-gray-500 mt-1">Irreversible actions for your organization</p>
      </div>

      <div className="p-6 border-2 border-red-200 rounded-xl space-y-4">
        <div>
          <p className="font-medium text-gray-900">Delete Organization</p>
          <p className="text-sm text-gray-500 mt-1">
            Once you delete an organization, there is no going back. All files, team members, 
            and data will be permanently removed.
          </p>
        </div>

        {!confirmDelete ? (
          <button
            onClick={() => setConfirmDelete(true)}
            className="px-4 py-2.5 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-colors"
          >
            Delete Organization
          </button>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Type <span className="font-mono font-bold text-red-600">{currentOrg?.slug}</span> to confirm
            </p>
            <input
              type="text"
              value={deleteInput}
              onChange={(e) => setDeleteInput(e.target.value)}
              placeholder="Enter organization slug"
              className="w-full px-4 py-2.5 rounded-xl border border-red-200 focus:border-red-500 focus:ring-2 focus:ring-red-100 outline-none transition-all"
            />
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-4 py-2.5 border border-gray-200 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={deleteInput !== currentOrg?.slug}
                className="px-4 py-2.5 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Permanently Delete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Settings Page
// ============================================================================

export default function SettingsPage() {
  const { currentOrg } = useAuth();
  const [activeSection, setActiveSection] = useState('organization');

  const renderSection = () => {
    switch (activeSection) {
      case 'organization': return <OrganizationSettings />;
      case 'security': return <SecuritySettings />;
      case 'notifications': return <NotificationsSettings />;
      case 'api': return <APISettings />;
      case 'billing': return <BillingSettings />;
      case 'storage': return <StorageSettings />;
      case 'integrations': return <IntegrationsSettings />;
      case 'danger': return <DangerZone />;
      default: return <OrganizationSettings />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">
          Configure settings for {currentOrg?.name}
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar Navigation */}
        <nav className="lg:w-64 shrink-0">
          <div className="bg-white rounded-2xl border border-gray-100 p-2">
            {settingsSections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                  activeSection === section.id
                    ? 'bg-indigo-50 text-indigo-700'
                    : section.id === 'danger'
                      ? 'text-red-600 hover:bg-red-50'
                      : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {section.icon}
                {section.label}
              </button>
            ))}
          </div>
        </nav>

        {/* Content */}
        <div className="flex-1">
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            {renderSection()}
          </div>
        </div>
      </div>
    </div>
  );
}
