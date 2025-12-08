"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth, formatBytes, Organization } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import {
  Home,
  Folder,
  Users,
  Settings,
  BarChart3,
  Key,
  Shield,
  Bell,
  Plus,
  Search,
  ChevronDown,
  LogOut,
  Menu,
  X,
  Check,
  Sun,
  Moon,
  UserCheck,
  Crown,
  Building2,
  FileStack,
  AlertTriangle,
  Server,
  Activity,
  Database,
  Globe,
} from 'lucide-react';

// ============================================================================
// Logo Icon
// ============================================================================

const LogoIcon = ({ className = "w-8 h-8" }: { className?: string }) => (
  <svg className={className} viewBox="0 0 48 48" fill="none">
    <rect width="48" height="48" rx="12" className="fill-indigo-600" />
    <path d="M14 16h20v4H14v-4zm0 6h20v4H14v-4zm0 6h12v4H14v-4z" fill="white" fillOpacity="0.9" />
    <circle cx="36" cy="34" r="6" className="fill-emerald-400" />
    <path d="M33.5 34l2 2 3-3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// ============================================================================
// Navigation Items (with role-based access)
// ============================================================================

type UserRole = 'super_admin' | 'org_admin' | 'manager' | 'user' | 'viewer';

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: UserRole[];
  badge?: boolean; // For pending approvals count
}

const navItems: NavItem[] = [
  { href: '/dashboard', label: 'Overview', icon: Home, roles: ['super_admin', 'org_admin', 'manager', 'user', 'viewer'] },
  { href: '/dashboard/approvals', label: 'Approvals', icon: UserCheck, roles: ['super_admin', 'org_admin'], badge: true },
  { href: '/dashboard/organizations', label: 'Organizations', icon: Building2, roles: ['super_admin'] },
  { href: '/dashboard/users', label: 'Users', icon: Users, roles: ['super_admin'] },
  { href: '/dashboard/files', label: 'Files', icon: Folder, roles: ['super_admin', 'org_admin', 'manager', 'user', 'viewer'] },
  { href: '/dashboard/all-files', label: 'All Files', icon: FileStack, roles: ['super_admin'] },
  { href: '/dashboard/quarantine', label: 'Quarantine', icon: AlertTriangle, roles: ['super_admin'] },
  { href: '/dashboard/team', label: 'Team', icon: Users, roles: ['org_admin', 'manager'] },
  { href: '/dashboard/analytics', label: 'Analytics', icon: BarChart3, roles: ['super_admin', 'org_admin', 'manager'] },
  { href: '/dashboard/api-keys', label: 'API Keys', icon: Key, roles: ['super_admin', 'org_admin'] },
  { href: '/dashboard/infrastructure', label: 'Infrastructure', icon: Server, roles: ['super_admin'] },
  { href: '/dashboard/system-logs', label: 'System Logs', icon: Activity, roles: ['super_admin'] },
  { href: '/dashboard/database', label: 'Database', icon: Database, roles: ['super_admin'] },
  { href: '/dashboard/api-gateway', label: 'API Gateway', icon: Globe, roles: ['super_admin'] },
  { href: '/dashboard/security', label: 'Security', icon: Shield, roles: ['super_admin', 'org_admin'] },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings, roles: ['super_admin', 'org_admin', 'manager', 'user', 'viewer'] },
];

// ============================================================================
// Nav Items with Badge (for pending approvals)
// ============================================================================

function NavItemsWithBadge({ 
  pathname, 
  userRole, 
  currentOrg, 
  onClose 
}: { 
  pathname: string; 
  userRole: string; 
  currentOrg: Organization | null; 
  onClose: () => void;
}) {
  const { pendingRegistrations, user } = useAuth();
  const { isDark } = useTheme();
  
  // Calculate pending count based on role
  const pendingCount = pendingRegistrations.filter(r => {
    if (r.status !== 'pending') return false;
    // Org admins only see member requests for their org
    if (userRole === 'org_admin') {
      return r.type === 'member' && r.organization_id === user?.organization_id;
    }
    // Super admins see all
    return true;
  }).length;

  return (
    <>
      {navItems.map((item) => {
        const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
        const Icon = item.icon;
        const showBadge = item.badge && pendingCount > 0;

        // Hide items based on user role
        if (!item.roles.includes(userRole as UserRole)) return null;

        // Hide some items based on plan
        if (item.href === '/dashboard/api-keys' && !currentOrg?.features.api_access) return null;

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onClose}
            className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
              isActive
                ? (isDark ? 'bg-indigo-900/50 text-indigo-400' : 'bg-indigo-50 text-indigo-600')
                : (isDark ? 'text-gray-400 hover:bg-gray-800 hover:text-gray-200' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900')
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Icon className={`w-4 h-4 ${isActive ? (isDark ? 'text-indigo-400' : 'text-indigo-600') : (isDark ? 'text-gray-500' : 'text-gray-400')}`} />
              <span>{item.label}</span>
            </div>
            {showBadge && (
              <span className="px-1.5 py-0.5 text-xs font-bold bg-red-500 text-white rounded-full min-w-[20px] text-center">
                {pendingCount}
              </span>
            )}
          </Link>
        );
      })}
    </>
  );
}

// ============================================================================
// Organization Switcher
// ============================================================================

function OrgSwitcher() {
  const { currentOrg, organizations, switchOrganization } = useAuth();
  const { isDark } = useTheme();
  const [isOpen, setIsOpen] = useState(false);

  if (!currentOrg) return null;

  const planColors: Record<Organization['plan'], string> = {
    free: isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600',
    pro: isDark ? 'bg-blue-900/50 text-blue-300' : 'bg-blue-100 text-blue-600',
    enterprise: isDark ? 'bg-purple-900/50 text-purple-300' : 'bg-purple-100 text-purple-600',
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center gap-3 p-2 rounded-lg transition-colors ${
          isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-50'
        }`}
      >
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
          {currentOrg.name.charAt(0)}
        </div>
        <div className="flex-1 text-left min-w-0">
          <p className={`text-sm font-medium truncate ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{currentOrg.name}</p>
          <p className={`text-xs truncate ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{formatBytes(currentOrg.storage_used)} used</p>
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''} ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className={`absolute top-full left-0 right-0 mt-2 rounded-xl shadow-xl border py-2 z-20 max-h-80 overflow-auto ${
            isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'
          }`}>
            {organizations.map((org) => (
              <button
                key={org.id}
                onClick={() => {
                  switchOrganization(org.id);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 transition-colors ${
                  org.id === currentOrg.id 
                    ? (isDark ? 'bg-indigo-900/30' : 'bg-indigo-50')
                    : (isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-50')
                }`}
              >
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold text-xs">
                  {org.name.charAt(0)}
                </div>
                <div className="flex-1 text-left min-w-0">
                  <p className={`text-sm font-medium truncate ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{org.name}</p>
                  <span className={`inline-block text-xs px-2 py-0.5 rounded-full capitalize ${planColors[org.plan]}`}>
                    {org.plan}
                  </span>
                </div>
                {org.id === currentOrg.id && (
                  <Check className="w-4 h-4 text-indigo-500" />
                )}
              </button>
            ))}
            <div className={`border-t mt-2 pt-2 ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
              <Link
                href="/dashboard/new-org"
                className={`flex items-center gap-2 px-4 py-3 text-sm transition-colors ${
                  isDark ? 'text-indigo-400 hover:bg-indigo-900/30' : 'text-indigo-600 hover:bg-indigo-50'
                }`}
                onClick={() => setIsOpen(false)}
              >
                <Plus className="w-4 h-4" />
                Create new organization
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ============================================================================
// User Menu
// ============================================================================

function UserMenu() {
  const { user, logout } = useAuth();
  const { isDark } = useTheme();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);

  if (!user) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 p-1.5 rounded-lg transition-colors ${
          isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-50'
        }`}
      >
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-medium text-sm">
          {user.name.charAt(0)}
        </div>
        <div className="hidden md:block text-left">
          <p className={`text-sm font-medium ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{user.name}</p>
          <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{user.email}</p>
        </div>
        <ChevronDown className={`w-4 h-4 hidden md:block ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className={`absolute right-0 top-full mt-2 w-56 rounded-xl shadow-xl border py-2 z-20 ${
            isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'
          }`}>
            <div className={`px-4 py-3 border-b md:hidden ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
              <p className={`text-sm font-medium ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{user.name}</p>
              <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{user.email}</p>
            </div>
            <Link
              href="/dashboard/settings"
              className={`flex items-center gap-3 px-4 py-2.5 text-sm ${
                isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => setIsOpen(false)}
            >
              <Settings className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
              Settings
            </Link>
            <button
              onClick={() => {
                logout();
                router.push('/');
                setIsOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm ${
                isDark ? 'text-red-400 hover:bg-red-900/30' : 'text-red-600 hover:bg-red-50'
              }`}
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ============================================================================
// Sidebar
// ============================================================================

function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const { currentOrg, user } = useAuth();
  const { isDark } = useTheme();

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={onClose} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed top-0 left-0 bottom-0 w-60 border-r z-50
        transform transition-transform duration-200 ease-in-out
        lg:translate-x-0 lg:static lg:z-auto
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        ${isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}
      `}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className={`flex items-center justify-between px-4 h-14 border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
            <Link href="/dashboard" className="flex items-center gap-2">
              <LogoIcon className="w-7 h-7" />
              <span className={`text-base font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>FileVault</span>
            </Link>
            <button className={`lg:hidden p-1.5 rounded ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-400 hover:text-gray-600'}`} onClick={onClose}>
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Org Switcher */}
          <div className={`px-3 py-3 border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
            <OrgSwitcher />
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-auto">
            <NavItemsWithBadge pathname={pathname} userRole={user?.role || 'viewer'} currentOrg={currentOrg} onClose={onClose} />
          </nav>

          {/* Storage Usage */}
          {currentOrg && (
            <div className={`px-3 py-3 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <div className={`p-3 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xs font-medium ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Storage</span>
                  <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                    {Math.round((currentOrg.storage_used / currentOrg.storage_limit) * 100)}%
                  </span>
                </div>
                <div className={`h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
                  <div
                    className="h-full bg-indigo-500 rounded-full transition-all"
                    style={{ width: `${Math.min((currentOrg.storage_used / currentOrg.storage_limit) * 100, 100)}%` }}
                  />
                </div>
                <p className={`text-xs mt-2 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                  {formatBytes(currentOrg.storage_used)} of {formatBytes(currentOrg.storage_limit)} used
                </p>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

// ============================================================================
// Header
// ============================================================================

function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const { isDark, toggleTheme } = useTheme();
  
  return (
    <header className={`sticky top-0 z-30 backdrop-blur-lg border-b ${
      isDark ? 'bg-gray-900/80 border-gray-700' : 'bg-white/80 border-gray-100'
    }`}>
      <div className="flex items-center justify-between px-4 lg:px-6 h-14">
        <div className="flex items-center gap-3">
          <button className={`lg:hidden p-1.5 rounded ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-400 hover:text-gray-600'}`} onClick={onMenuClick}>
            <Menu className="w-5 h-5" />
          </button>
          
          {/* Search */}
          <div className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg w-64 lg:w-80 ${
            isDark ? 'bg-gray-800 border border-gray-700' : 'bg-gray-50 border border-gray-100'
          }`}>
            <Search className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
            <input
              type="text"
              placeholder="Search files, folders..."
              className={`bg-transparent border-none outline-none text-sm w-full ${
                isDark ? 'text-gray-200 placeholder-gray-500' : 'text-gray-600 placeholder-gray-400'
              }`}
            />
            <kbd className={`hidden lg:block px-1.5 py-0.5 text-xs rounded ${
              isDark ? 'text-gray-500 bg-gray-700 border border-gray-600' : 'text-gray-400 bg-white border border-gray-200'
            }`}>⌘K</kbd>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {/* Dark Mode Toggle */}
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-lg transition-colors ${
              isDark ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-800' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-50'
            }`}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
          
          {/* Notifications */}
          <button className={`p-2 rounded-lg transition-colors relative ${
            isDark ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-800' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-50'
          }`}>
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
          </button>
          
          <UserMenu />
        </div>
      </div>
    </header>
  );
}

// ============================================================================
// Dashboard Layout
// ============================================================================

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const { isDark } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Redirect if not authenticated
  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${isDark ? 'bg-gray-900' : 'bg-gray-50'}`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className={`min-h-screen flex ${isDark ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <div className="flex-1 flex flex-col min-w-0">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
