"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';

// ============================================================================
// Types
// ============================================================================

export type UserStatus = 'pending' | 'approved' | 'rejected';
export type RegistrationType = 'organization' | 'member';

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role: 'super_admin' | 'org_admin' | 'manager' | 'user' | 'viewer';
  status: UserStatus;
  organization_id?: string;
  created_at: string;
}

export interface PendingRegistration {
  id: string;
  type: RegistrationType;
  user: {
    id: string;
    name: string;
    email: string;
    password: string;
  };
  organization?: {
    id: string;
    name: string;
    plan: 'free' | 'pro' | 'enterprise';
  };
  organization_id?: string; // For member registrations
  organization_name?: string; // For display
  requested_role: User['role'];
  status: UserStatus;
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url?: string;
  plan: 'free' | 'pro' | 'enterprise';
  storage_used: number;
  storage_limit: number;
  member_count: number;
  file_count: number;
  features: {
    virus_scan: boolean;
    ml_pipeline: boolean;
    api_access: boolean;
    audit_logs: boolean;
    sso: boolean;
    custom_domains: boolean;
    priority_support: boolean;
  };
  created_at: string;
}

export interface AuthState {
  user: User | null;
  currentOrg: Organization | null;
  organizations: Organization[];
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface RegisteredUser {
  user: User;
  organization?: Organization;
  organization_name?: string;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<{ status: UserStatus }>;
  signup: (name: string, email: string, password: string, orgName?: string, joinOrgId?: string) => Promise<{ status: UserStatus; message: string }>;
  logout: () => void;
  switchOrganization: (orgId: string) => void;
  refreshUser: () => Promise<void>;
  createOrganization: (name: string, plan: Organization['plan']) => Promise<Organization>;
  // Approval system
  pendingRegistrations: PendingRegistration[];
  approveRegistration: (registrationId: string, reviewerId: string) => Promise<void>;
  rejectRegistration: (registrationId: string, reviewerId: string) => Promise<void>;
  getAvailableOrganizations: () => Organization[];
  // User management
  getAllUsers: () => RegisteredUser[];
  getApprovedRegistrations: () => PendingRegistration[];
}

// ============================================================================
// Mock Data
// ============================================================================

// Store for pending registrations (would be in DB in real app)
let PENDING_REGISTRATIONS: PendingRegistration[] = [
  // Sample pending org registration
  {
    id: 'reg_001',
    type: 'organization',
    user: {
      id: 'usr_pending_001',
      name: 'John Startup',
      email: 'john@newstartup.com',
      password: 'startup123',
    },
    organization: {
      id: 'org_pending_001',
      name: 'New Startup Inc',
      plan: 'pro',
    },
    requested_role: 'org_admin',
    status: 'pending',
    created_at: '2024-12-05T10:00:00Z',
  },
  // Sample pending member registration
  {
    id: 'reg_002',
    type: 'member',
    user: {
      id: 'usr_pending_002',
      name: 'Jane Employee',
      email: 'jane@company.com',
      password: 'employee123',
    },
    organization_id: 'org_innovate',
    organization_name: 'Innovate Solutions',
    requested_role: 'user',
    status: 'pending',
    created_at: '2024-12-05T14:30:00Z',
  },
];

// Available organizations for joining
const AVAILABLE_ORGANIZATIONS: Organization[] = [
  {
    id: 'org_innovate',
    name: 'Innovate Solutions',
    slug: 'innovate-solutions',
    plan: 'enterprise',
    storage_used: 45097156608,
    storage_limit: 107374182400,
    member_count: 85,
    file_count: 23456,
    features: {
      virus_scan: true,
      ml_pipeline: true,
      api_access: true,
      audit_logs: true,
      sso: true,
      custom_domains: true,
      priority_support: true,
    },
    created_at: '2024-01-15T00:00:00Z',
  },
  {
    id: 'org_acme',
    name: 'Acme Healthcare',
    slug: 'acme-healthcare',
    plan: 'enterprise',
    storage_used: 32212254720,
    storage_limit: 107374182400,
    member_count: 47,
    file_count: 12847,
    features: {
      virus_scan: true,
      ml_pipeline: true,
      api_access: true,
      audit_logs: true,
      sso: true,
      custom_domains: true,
      priority_support: true,
    },
    created_at: '2024-01-15T00:00:00Z',
  },
];

const MOCK_USERS: Record<string, { user: User; password: string; organizations: Organization[] }> = {
  // Super Admin - Platform Administrator
  'admin@gmail.com': {
    password: 'admin',
    user: {
      id: 'usr_admin_001',
      email: 'admin@gmail.com',
      name: 'Platform Admin',
      avatar_url: '/avatars/admin.png',
      role: 'super_admin',
      status: 'approved',
      created_at: '2023-01-01T00:00:00Z',
    },
    organizations: [
      {
        id: 'org_platform',
        name: 'FileVault Platform',
        slug: 'filevault-platform',
        plan: 'enterprise',
        storage_used: 0,
        storage_limit: 1099511627776, // 1TB
        member_count: 1,
        file_count: 0,
        features: {
          virus_scan: true,
          ml_pipeline: true,
          api_access: true,
          audit_logs: true,
          sso: true,
          custom_domains: true,
          priority_support: true,
        },
        created_at: '2023-01-01T00:00:00Z',
      },
    ],
  },
  
  // Organization Admin - Full org management
  'orgadmin@company.com': {
    password: 'orgadmin',
    user: {
      id: 'usr_orgadmin_001',
      email: 'orgadmin@company.com',
      name: 'Sarah Johnson',
      avatar_url: '/avatars/sarah.png',
      role: 'org_admin',
      status: 'approved',
      organization_id: 'org_innovate',
      created_at: '2024-01-15T00:00:00Z',
    },
    organizations: [
      {
        id: 'org_innovate',
        name: 'Innovate Solutions',
        slug: 'innovate-solutions',
        plan: 'enterprise',
        storage_used: 45097156608, // ~42GB
        storage_limit: 107374182400, // 100GB
        member_count: 85,
        file_count: 23456,
        features: {
          virus_scan: true,
          ml_pipeline: true,
          api_access: true,
          audit_logs: true,
          sso: true,
          custom_domains: true,
          priority_support: true,
        },
        created_at: '2024-01-15T00:00:00Z',
      },
    ],
  },

  // Manager - Department/Team Manager
  'manager@company.com': {
    password: 'manager',
    user: {
      id: 'usr_manager_001',
      email: 'manager@company.com',
      name: 'Michael Chen',
      avatar_url: '/avatars/michael.png',
      role: 'manager',
      status: 'approved',
      organization_id: 'org_innovate',
      created_at: '2024-03-10T00:00:00Z',
    },
    organizations: [
      {
        id: 'org_innovate',
        name: 'Innovate Solutions',
        slug: 'innovate-solutions',
        plan: 'enterprise',
        storage_used: 45097156608,
        storage_limit: 107374182400,
        member_count: 85,
        file_count: 23456,
        features: {
          virus_scan: true,
          ml_pipeline: true,
          api_access: true,
          audit_logs: true,
          sso: true,
          custom_domains: true,
          priority_support: true,
        },
        created_at: '2024-01-15T00:00:00Z',
      },
    ],
  },

  // Regular User - Standard file access
  'user@company.com': {
    password: 'user',
    user: {
      id: 'usr_user_001',
      email: 'user@company.com',
      name: 'Emily Davis',
      avatar_url: '/avatars/emily.png',
      role: 'user',
      status: 'approved',
      organization_id: 'org_innovate',
      created_at: '2024-05-20T00:00:00Z',
    },
    organizations: [
      {
        id: 'org_innovate',
        name: 'Innovate Solutions',
        slug: 'innovate-solutions',
        plan: 'enterprise',
        storage_used: 45097156608,
        storage_limit: 107374182400,
        member_count: 85,
        file_count: 23456,
        features: {
          virus_scan: true,
          ml_pipeline: true,
          api_access: true,
          audit_logs: true,
          sso: true,
          custom_domains: true,
          priority_support: true,
        },
        created_at: '2024-01-15T00:00:00Z',
      },
    ],
  },

  // Viewer - Read-only access
  'viewer@company.com': {
    password: 'viewer',
    user: {
      id: 'usr_viewer_001',
      email: 'viewer@company.com',
      name: 'Alex Thompson',
      avatar_url: '/avatars/alex.png',
      role: 'viewer',
      status: 'approved',
      organization_id: 'org_innovate',
      created_at: '2024-08-01T00:00:00Z',
    },
    organizations: [
      {
        id: 'org_innovate',
        name: 'Innovate Solutions',
        slug: 'innovate-solutions',
        plan: 'enterprise',
        storage_used: 45097156608,
        storage_limit: 107374182400,
        member_count: 85,
        file_count: 23456,
        features: {
          virus_scan: true,
          ml_pipeline: true,
          api_access: true,
          audit_logs: true,
          sso: true,
          custom_domains: true,
          priority_support: true,
        },
        created_at: '2024-01-15T00:00:00Z',
      },
    ],
  },

  // Demo User - Organization Admin (existing)
  'demo@filevault.io': {
    password: 'demo123',
    user: {
      id: 'usr_demo123',
      email: 'demo@filevault.io',
      name: 'Demo User',
      role: 'org_admin',
      status: 'approved',
      organization_id: 'org_acme',
      created_at: '2024-01-15T00:00:00Z',
    },
    organizations: [
      {
        id: 'org_acme',
        name: 'Acme Healthcare',
        slug: 'acme-healthcare',
        plan: 'enterprise',
        storage_used: 32212254720,
        storage_limit: 107374182400,
        member_count: 47,
        file_count: 12847,
        features: {
          virus_scan: true,
          ml_pipeline: true,
          api_access: true,
          audit_logs: true,
          sso: true,
          custom_domains: true,
          priority_support: true,
        },
        created_at: '2024-01-15T00:00:00Z',
      },
      {
        id: 'org_techcorp',
        name: 'TechCorp Finance',
        slug: 'techcorp-finance',
        plan: 'pro',
        storage_used: 10737418240,
        storage_limit: 53687091200,
        member_count: 12,
        file_count: 2341,
        features: {
          virus_scan: true,
          ml_pipeline: false,
          api_access: true,
          audit_logs: true,
          sso: false,
          custom_domains: false,
          priority_support: false,
        },
        created_at: '2024-06-01T00:00:00Z',
      },
    ],
  },
};

// ============================================================================
// Context
// ============================================================================

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    currentOrg: null,
    organizations: [],
    isAuthenticated: false,
    isLoading: true,
  });
  
  const [pendingRegistrations, setPendingRegistrations] = useState<PendingRegistration[]>(PENDING_REGISTRATIONS);

  // Check for existing session on mount
  useEffect(() => {
    const savedSession = localStorage.getItem('filevault_session');
    if (savedSession) {
      try {
        const session = JSON.parse(savedSession);
        // Check if user is still approved
        if (session.user?.status === 'approved') {
          setState({
            user: session.user,
            currentOrg: session.currentOrg,
            organizations: session.organizations,
            isAuthenticated: true,
            isLoading: false,
          });
        } else {
          localStorage.removeItem('filevault_session');
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } catch {
        localStorage.removeItem('filevault_session');
        setState(prev => ({ ...prev, isLoading: false }));
      }
    } else {
      setState(prev => ({ ...prev, isLoading: false }));
    }
    
    // Load pending registrations from localStorage
    const savedPending = localStorage.getItem('filevault_pending_registrations');
    if (savedPending) {
      try {
        const parsed = JSON.parse(savedPending);
        setPendingRegistrations(parsed);
        PENDING_REGISTRATIONS = parsed;
      } catch {
        // Use default
      }
    }
  }, []);

  const saveSession = useCallback((user: User, orgs: Organization[], currentOrg: Organization) => {
    localStorage.setItem('filevault_session', JSON.stringify({
      user,
      organizations: orgs,
      currentOrg,
    }));
  }, []);
  
  const savePendingRegistrations = useCallback((regs: PendingRegistration[]) => {
    localStorage.setItem('filevault_pending_registrations', JSON.stringify(regs));
    PENDING_REGISTRATIONS = regs;
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<{ status: UserStatus }> => {
    setState(prev => ({ ...prev, isLoading: true }));
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 800));
    
    const userData = MOCK_USERS[email.toLowerCase()];
    if (!userData || userData.password !== password) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw new Error('Invalid email or password');
    }
    
    // Check if user is approved
    if (userData.user.status === 'pending') {
      setState(prev => ({ ...prev, isLoading: false }));
      return { status: 'pending' };
    }
    
    if (userData.user.status === 'rejected') {
      setState(prev => ({ ...prev, isLoading: false }));
      throw new Error('Your account has been rejected. Please contact support.');
    }
    
    const currentOrg = userData.organizations[0];
    setState({
      user: userData.user,
      currentOrg,
      organizations: userData.organizations,
      isAuthenticated: true,
      isLoading: false,
    });
    
    saveSession(userData.user, userData.organizations, currentOrg);
    return { status: 'approved' };
  }, [saveSession]);

  const signup = useCallback(async (
    name: string, 
    email: string, 
    password: string, 
    orgName?: string,
    joinOrgId?: string
  ): Promise<{ status: UserStatus; message: string }> => {
    setState(prev => ({ ...prev, isLoading: true }));
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    if (MOCK_USERS[email.toLowerCase()]) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw new Error('Email already registered');
    }
    
    // Check if already pending
    const existingPending = pendingRegistrations.find(r => r.user.email.toLowerCase() === email.toLowerCase());
    if (existingPending) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw new Error('Registration already pending approval');
    }
    
    const registrationId = `reg_${Date.now()}`;
    const userId = `usr_${Date.now()}`;
    
    if (joinOrgId) {
      // Member joining existing organization - needs org_admin + super_admin approval
      const org = AVAILABLE_ORGANIZATIONS.find(o => o.id === joinOrgId);
      const newRegistration: PendingRegistration = {
        id: registrationId,
        type: 'member',
        user: {
          id: userId,
          name,
          email,
          password,
        },
        organization_id: joinOrgId,
        organization_name: org?.name || 'Unknown Organization',
        requested_role: 'user',
        status: 'pending',
        created_at: new Date().toISOString(),
      };
      
      const updatedPending = [...pendingRegistrations, newRegistration];
      setPendingRegistrations(updatedPending);
      savePendingRegistrations(updatedPending);
      
      setState(prev => ({ ...prev, isLoading: false }));
      return { 
        status: 'pending', 
        message: `Your request to join ${org?.name || 'the organization'} has been submitted. Please wait for admin approval.`
      };
    } else {
      // New organization registration - needs super_admin approval
      const orgId = `org_${Date.now()}`;
      const newRegistration: PendingRegistration = {
        id: registrationId,
        type: 'organization',
        user: {
          id: userId,
          name,
          email,
          password,
        },
        organization: {
          id: orgId,
          name: orgName || `${name}'s Workspace`,
          plan: 'free',
        },
        requested_role: 'org_admin',
        status: 'pending',
        created_at: new Date().toISOString(),
      };
      
      const updatedPending = [...pendingRegistrations, newRegistration];
      setPendingRegistrations(updatedPending);
      savePendingRegistrations(updatedPending);
      
      setState(prev => ({ ...prev, isLoading: false }));
      return { 
        status: 'pending', 
        message: `Your organization "${orgName || `${name}'s Workspace`}" registration has been submitted. Please wait for platform admin approval.`
      };
    }
  }, [pendingRegistrations, savePendingRegistrations]);

  const approveRegistration = useCallback(async (registrationId: string, reviewerId: string) => {
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const registration = pendingRegistrations.find(r => r.id === registrationId);
    if (!registration) throw new Error('Registration not found');
    
    if (registration.type === 'organization' && registration.organization) {
      // Create new organization and user
      const newOrg: Organization = {
        id: registration.organization.id,
        name: registration.organization.name,
        slug: registration.organization.name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        plan: registration.organization.plan,
        storage_used: 0,
        storage_limit: 1073741824, // 1GB for free
        member_count: 1,
        file_count: 0,
        features: {
          virus_scan: true,
          ml_pipeline: false,
          api_access: false,
          audit_logs: false,
          sso: false,
          custom_domains: false,
          priority_support: false,
        },
        created_at: new Date().toISOString(),
      };
      
      const newUser: User = {
        id: registration.user.id,
        email: registration.user.email,
        name: registration.user.name,
        role: 'org_admin',
        status: 'approved',
        organization_id: newOrg.id,
        created_at: new Date().toISOString(),
      };
      
      // Add to mock users
      MOCK_USERS[registration.user.email.toLowerCase()] = {
        password: registration.user.password,
        user: newUser,
        organizations: [newOrg],
      };
      
      // Add org to available orgs
      AVAILABLE_ORGANIZATIONS.push(newOrg);
    } else if (registration.type === 'member' && registration.organization_id) {
      // Create new member for existing organization
      const org = AVAILABLE_ORGANIZATIONS.find(o => o.id === registration.organization_id);
      if (!org) throw new Error('Organization not found');
      
      const newUser: User = {
        id: registration.user.id,
        email: registration.user.email,
        name: registration.user.name,
        role: registration.requested_role,
        status: 'approved',
        organization_id: registration.organization_id,
        created_at: new Date().toISOString(),
      };
      
      // Add to mock users
      MOCK_USERS[registration.user.email.toLowerCase()] = {
        password: registration.user.password,
        user: newUser,
        organizations: [org],
      };
      
      // Update org member count
      org.member_count += 1;
    }
    
    // Remove from pending
    const updatedPending = pendingRegistrations.filter(r => r.id !== registrationId);
    setPendingRegistrations(updatedPending);
    savePendingRegistrations(updatedPending);
  }, [pendingRegistrations, savePendingRegistrations]);

  const rejectRegistration = useCallback(async (registrationId: string, reviewerId: string) => {
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Remove from pending
    const updatedPending = pendingRegistrations.filter(r => r.id !== registrationId);
    setPendingRegistrations(updatedPending);
    savePendingRegistrations(updatedPending);
  }, [pendingRegistrations, savePendingRegistrations]);

  const getAvailableOrganizations = useCallback(() => {
    return AVAILABLE_ORGANIZATIONS;
  }, []);

  const getAllUsers = useCallback((): RegisteredUser[] => {
    // Get all users from MOCK_USERS
    const users: RegisteredUser[] = Object.values(MOCK_USERS).map(({ user, organizations }) => ({
      user,
      organization: organizations[0],
      organization_name: organizations[0]?.name,
    }));
    return users;
  }, []);

  const getApprovedRegistrations = useCallback(() => {
    return pendingRegistrations.filter(reg => reg.status === 'approved');
  }, [pendingRegistrations]);

  const logout = useCallback(() => {
    localStorage.removeItem('filevault_session');
    setState({
      user: null,
      currentOrg: null,
      organizations: [],
      isAuthenticated: false,
      isLoading: false,
    });
  }, []);

  const switchOrganization = useCallback((orgId: string) => {
    const org = state.organizations.find(o => o.id === orgId);
    if (org) {
      setState(prev => ({ ...prev, currentOrg: org }));
      if (state.user) {
        saveSession(state.user, state.organizations, org);
      }
    }
  }, [state.organizations, state.user, saveSession]);

  const refreshUser = useCallback(async () => {
    // In real app, fetch from API
    await new Promise(resolve => setTimeout(resolve, 500));
  }, []);

  const createOrganization = useCallback(async (name: string, plan: Organization['plan']) => {
    await new Promise(resolve => setTimeout(resolve, 800));
    
    const planLimits = {
      free: { storage: 1073741824, features: { virus_scan: true, ml_pipeline: false, api_access: false, audit_logs: false, sso: false, custom_domains: false, priority_support: false } },
      pro: { storage: 53687091200, features: { virus_scan: true, ml_pipeline: false, api_access: true, audit_logs: true, sso: false, custom_domains: false, priority_support: false } },
      enterprise: { storage: 107374182400, features: { virus_scan: true, ml_pipeline: true, api_access: true, audit_logs: true, sso: true, custom_domains: true, priority_support: true } },
    };
    
    const newOrg: Organization = {
      id: `org_${Date.now()}`,
      name,
      slug: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      plan,
      storage_used: 0,
      storage_limit: planLimits[plan].storage,
      member_count: 1,
      file_count: 0,
      features: planLimits[plan].features,
      created_at: new Date().toISOString(),
    };
    
    const newOrgs = [...state.organizations, newOrg];
    setState(prev => ({ ...prev, organizations: newOrgs, currentOrg: newOrg }));
    
    if (state.user) {
      saveSession(state.user, newOrgs, newOrg);
    }
    
    return newOrg;
  }, [state.organizations, state.user, saveSession]);

  return (
    <AuthContext.Provider value={{
      ...state,
      login,
      signup,
      logout,
      switchOrganization,
      refreshUser,
      createOrganization,
      pendingRegistrations,
      approveRegistration,
      rejectRegistration,
      getAvailableOrganizations,
      getAllUsers,
      getApprovedRegistrations,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// ============================================================================
// Utility Functions
// ============================================================================

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

export function getPlanColor(plan: Organization['plan']): string {
  switch (plan) {
    case 'enterprise': return 'purple';
    case 'pro': return 'blue';
    default: return 'gray';
  }
}
