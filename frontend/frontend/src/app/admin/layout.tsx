"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import {
  Shield,
  LayoutDashboard,
  Building2,
  Users,
  Server,
  Activity,
  Settings,
  Bell,
  Search,
  LogOut,
  ChevronDown,
  Menu,
  X,
  FileStack,
  AlertTriangle,
  Database,
  Globe,
  Sun,
  Moon,
  UserCheck,
} from 'lucide-react';

const adminNavItems = [
  { icon: LayoutDashboard, label: 'Overview', href: '/admin' },
  { icon: UserCheck, label: 'Approvals', href: '/admin/approvals', badge: true },
  { icon: Building2, label: 'Organizations', href: '/admin/organizations' },
  { icon: Users, label: 'Users', href: '/admin/users' },
  { icon: FileStack, label: 'All Files', href: '/admin/files' },
  { icon: AlertTriangle, label: 'Quarantine', href: '/admin/quarantine' },
  { icon: Server, label: 'Infrastructure', href: '/admin/infrastructure' },
  { icon: Activity, label: 'System Logs', href: '/admin/logs' },
  { icon: Database, label: 'Database', href: '/admin/database' },
  { icon: Globe, label: 'API Gateway', href: '/admin/api-gateway' },
  { icon: Settings, label: 'Settings', href: '/admin/settings' },
];

// Nav Items Component with pending count
function NavItems({ sidebarOpen }: { sidebarOpen: boolean }) {
  const { pendingRegistrations } = useAuth();
  const pendingCount = pendingRegistrations.filter(r => r.status === 'pending').length;

  return (
    <>
      {adminNavItems.map((item) => {
        const Icon = item.icon;
        const isActive = typeof window !== 'undefined' && window.location.pathname === item.href;
        const showBadge = item.badge && pendingCount > 0;
        
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
              isActive
                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            }`}
          >
            <div className="relative">
              <Icon className="w-5 h-5 flex-shrink-0" />
              {showBadge && !sidebarOpen && (
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />
              )}
            </div>
            {sidebarOpen && (
              <div className="flex items-center justify-between flex-1">
                <span className="font-medium">{item.label}</span>
                {showBadge && (
                  <span className="px-2 py-0.5 text-xs font-bold bg-red-500 text-white rounded-full">
                    {pendingCount}
                  </span>
                )}
              </div>
            )}
          </Link>
        );
      })}
    </>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  // Redirect non-super_admin users
  useEffect(() => {
    if (!isLoading && (!isAuthenticated || user?.role !== 'super_admin')) {
      router.push('/');
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-red-500 border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated || user?.role !== 'super_admin') {
    return null;
  }

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  return (
    <div className="min-h-screen bg-gray-900 flex">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 bg-gray-950 border-r border-red-900/30 transition-all duration-300 ${
          sidebarOpen ? 'w-64' : 'w-20'
        }`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-red-900/30">
          <Link href="/admin" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-orange-600 rounded-xl flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            {sidebarOpen && (
              <div>
                <span className="text-xl font-bold text-white">Platform Admin</span>
                <p className="text-xs text-red-400">Super Admin Panel</p>
              </div>
            )}
          </Link>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-gray-400 hover:text-white p-1"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          <NavItems sidebarOpen={sidebarOpen} />
        </nav>

        {/* System Status */}
        {sidebarOpen && (
          <div className="absolute bottom-20 left-4 right-4">
            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              <h4 className="text-sm font-medium text-white mb-3">System Status</h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400">API Gateway</span>
                  <span className="flex items-center gap-1 text-green-400">
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                    Online
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400">Database</span>
                  <span className="flex items-center gap-1 text-green-400">
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                    Online
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400">Virus Scanner</span>
                  <span className="flex items-center gap-1 text-green-400">
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                    Online
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Back to Dashboard */}
        <div className="absolute bottom-4 left-4 right-4">
          <Link
            href="/dashboard"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white transition-all ${
              !sidebarOpen && 'justify-center'
            }`}
          >
            <LayoutDashboard className="w-5 h-5" />
            {sidebarOpen && <span className="font-medium">User Dashboard</span>}
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <div className={`flex-1 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
        {/* Top Bar */}
        <header className="h-16 bg-gray-950/50 backdrop-blur-xl border-b border-red-900/30 flex items-center justify-between px-6 sticky top-0 z-40">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                type="text"
                placeholder="Search organizations, users, files..."
                className="w-96 pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>

            {/* Notifications */}
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg"
              >
                <Bell className="w-5 h-5" />
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs text-white flex items-center justify-center">
                  5
                </span>
              </button>
              
              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
                  <div className="p-4 border-b border-gray-700">
                    <h3 className="font-semibold text-white">System Alerts</h3>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {[
                      { type: 'warning', message: 'High CPU usage detected on file-scanner-01', time: '2m ago' },
                      { type: 'danger', message: '3 virus threats quarantined', time: '15m ago' },
                      { type: 'info', message: 'New organization "MegaCorp" registered', time: '1h ago' },
                      { type: 'success', message: 'Database backup completed', time: '2h ago' },
                      { type: 'info', message: 'API rate limit reached for org_xyz', time: '3h ago' },
                    ].map((alert, i) => (
                      <div key={i} className="px-4 py-3 hover:bg-gray-800 cursor-pointer border-b border-gray-800">
                        <div className="flex items-start gap-3">
                          <div className={`w-2 h-2 rounded-full mt-2 ${
                            alert.type === 'danger' ? 'bg-red-500' :
                            alert.type === 'warning' ? 'bg-yellow-500' :
                            alert.type === 'success' ? 'bg-green-500' :
                            'bg-blue-500'
                          }`} />
                          <div className="flex-1">
                            <p className="text-sm text-white">{alert.message}</p>
                            <span className="text-xs text-gray-500">{alert.time}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-3 p-2 hover:bg-gray-800 rounded-lg"
              >
                <div className="w-8 h-8 bg-gradient-to-br from-red-500 to-orange-600 rounded-full flex items-center justify-center">
                  <Shield className="w-4 h-4 text-white" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-white">{user?.name}</p>
                  <p className="text-xs text-red-400">Super Admin</p>
                </div>
                <ChevronDown className="w-4 h-4 text-gray-400" />
              </button>
              
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
                  <div className="p-4 border-b border-gray-700">
                    <p className="text-sm text-white font-medium">{user?.email}</p>
                    <p className="text-xs text-gray-500">Platform Administrator</p>
                  </div>
                  <div className="p-2">
                    <Link
                      href="/admin/settings"
                      className="flex items-center gap-3 px-3 py-2 text-gray-300 hover:bg-gray-800 rounded-lg"
                    >
                      <Settings className="w-4 h-4" />
                      System Settings
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-3 py-2 text-red-400 hover:bg-gray-800 rounded-lg"
                    >
                      <LogOut className="w-4 h-4" />
                      Logout
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
