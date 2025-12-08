"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';
import { authApi, usersApi, organizationsApi, ApiUser, ApiOrganization } from '@/lib/api';

// ============================================================================
// Types
// ============================================================================

export type UserStatus = 'pending' | 'approved' | 'rejected' | 'active';
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
  organization_id?: string;
  organization_name?: string;
  requested_role: User['role'];
  status: UserStatus;
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

export interface RegisteredUser {
  user: User;
  organization?: Organization;
  organization_name?: string;
}

export interface AuthState {
  user: User | null;
  currentOrg: Organization | null;
  organizations: Organization[];
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<{ status: UserStatus }>;
  signup: (name: string, email: string, password: string, orgName?: string, joinOrgId?: string) => Promise<{ status: UserStatus; message: string }>;
  logout: () => void;
  switchOrganization: (orgId: string) => void;
  refreshUser: () => Promise<void>;
  createOrganization: (name: string, plan: Organization['plan']) => Promise<Organization>;
  pendingRegistrations: PendingRegistration[];
  approveRegistration: (registrationId: string, reviewerId: string) => Promise<void>;
  rejectRegistration: (registrationId: string, reviewerId: string) => Promise<void>;
  getAvailableOrganizations: () => Organization[];
  getAllUsers: () => RegisteredUser[];
  getApprovedRegistrations: () => PendingRegistration[];
}

// ============================================================================
// Helper: Convert API types to local types
// ============================================================================

function apiUserToUser(apiUser: ApiUser): User {
  return {
    id: apiUser.id,
    email: apiUser.email,
    name: apiUser.name,
    role: apiUser.role as User['role'],
    status: (apiUser.status === 'active' ? 'approved' : apiUser.status) as UserStatus,
    organization_id: apiUser.organization_id,
    created_at: apiUser.created_at,
  };
}

function apiOrgToOrg(apiOrg: ApiOrganization): Organization {
  return {
    id: apiOrg.id,
    name: apiOrg.name,
    slug: apiOrg.slug,
    plan: apiOrg.plan as Organization['plan'],
    storage_used: apiOrg.storage_used_bytes,
    storage_limit: apiOrg.storage_quota_bytes,
    member_count: apiOrg.max_users,
    file_count: apiOrg.max_files,
    features: {
      virus_scan: apiOrg.features?.virus_scan ?? true,
      ml_pipeline: apiOrg.features?.ml_pipeline ?? false,
      api_access: apiOrg.features?.api_access ?? false,
      audit_logs: apiOrg.features?.audit_logs ?? false,
      sso: apiOrg.features?.sso ?? false,
      custom_domains: apiOrg.features?.custom_domains ?? false,
      priority_support: apiOrg.features?.priority_support ?? false,
    },
    created_at: apiOrg.created_at,
  };
}

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

  const [allUsers, setAllUsers] = useState<RegisteredUser[]>([]);
  const [allOrganizations, setAllOrganizations] = useState<Organization[]>([]);
  const [pendingRegistrations, setPendingRegistrations] = useState<PendingRegistration[]>([]);

  // Load session on mount
  useEffect(() => {
    const loadSession = async () => {
      const token = localStorage.getItem('filevault_access_token');
      const savedSession = localStorage.getItem('filevault_session');

      if (token && savedSession) {
        try {
          const session = JSON.parse(savedSession);
          setState({
            user: session.user,
            currentOrg: session.currentOrg,
            organizations: session.organizations || [],
            isAuthenticated: true,
            isLoading: false,
          });

          // Fetch fresh user data from API
          try {
            const currentUser = await authApi.getCurrentUser();
            setState(prev => ({
              ...prev,
              user: apiUserToUser(currentUser),
            }));
          } catch {
            // Token might be expired, clear session
            localStorage.removeItem('filevault_access_token');
            localStorage.removeItem('filevault_session');
            setState({
              user: null,
              currentOrg: null,
              organizations: [],
              isAuthenticated: false,
              isLoading: false,
            });
          }
        } catch {
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } else {
        setState(prev => ({ ...prev, isLoading: false }));
        return; // Not authenticated, don't try to load users/orgs
      }

      // Load users and organizations only if authenticated
      await loadUsersAndOrgs();
    };

    loadSession();
  }, []);

  const loadUsersAndOrgs = async () => {
    let usersData: ReturnType<typeof apiUserToUser>[] = [];
    let orgsData: Organization[] = [];
    let rawUsers: Awaited<ReturnType<typeof usersApi.list>> = [];
    
    try {
      // Load users
      rawUsers = await usersApi.list();
      usersData = rawUsers.map(u => apiUserToUser(u));
    } catch (error) {
      console.error('Failed to load users:', error);
    }

    try {
      // Load organizations
      const orgsResponse = await organizationsApi.list();
      orgsData = orgsResponse.items.map(apiOrgToOrg);
      setAllOrganizations(orgsData);
    } catch (error) {
      console.error('Failed to load organizations:', error);
    }

    // Now set users with proper organization names
    setAllUsers(rawUsers.map(u => {
      const org = orgsData.find(o => o.id === u.organization_id);
      return { 
        user: apiUserToUser(u), 
        organization_name: org?.name || 'N/A' 
      };
    }));
    
    // Build pending registrations from users with status === 'pending'
    const pendingUsers = usersData.filter(u => u.status === 'pending');
    const pendingRegs: PendingRegistration[] = pendingUsers.map(u => {
      const userOrg = orgsData.find(o => o.id === u.organization_id);
      // If user has an org and they're org_admin, they're creating a new org
      // If user has an org and they're a regular user, they're joining an existing org
      const isNewOrgRequest = u.role === 'org_admin' && userOrg;
      const isMemberRequest = u.role !== 'org_admin' && userOrg;
      
      return {
        id: u.id,
        type: isNewOrgRequest ? 'organization' : 'member' as RegistrationType,
        user: {
          id: u.id,
          name: u.name,
          email: u.email,
          password: '', // Not available from API
        },
        organization: userOrg ? {
          id: userOrg.id,
          name: userOrg.name,
          plan: userOrg.plan as 'free' | 'pro' | 'enterprise',
        } : undefined,
        organization_id: u.organization_id,
        organization_name: userOrg?.name,
        requested_role: u.role as User['role'],
        status: u.status as UserStatus,
        created_at: u.created_at,
      };
    });
    setPendingRegistrations(pendingRegs);
  };

  const saveSession = useCallback((user: User, orgs: Organization[], currentOrg: Organization | null) => {
    localStorage.setItem('filevault_session', JSON.stringify({
      user,
      organizations: orgs,
      currentOrg,
    }));
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<{ status: UserStatus }> => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      const response = await authApi.login({ email, password });
      
      // Backend returns user_id, role, and status in the token response
      const authData = response.data;
      
      // If account is pending, don't allow login
      if (authData.status === 'pending') {
        // Clear any tokens
        localStorage.removeItem('filevault_access_token');
        localStorage.removeItem('filevault_refresh_token');
        setState(prev => ({ ...prev, isLoading: false }));
        return { status: 'pending' };
      }
      
      // If account is rejected, don't allow login
      if (authData.status === 'rejected') {
        localStorage.removeItem('filevault_access_token');
        localStorage.removeItem('filevault_refresh_token');
        setState(prev => ({ ...prev, isLoading: false }));
        throw new Error('Your account has been rejected. Please contact support.');
      }
      
      // Create user object from auth response
      const user: User = {
        id: authData.user_id,
        email: email,
        name: email.split('@')[0], // Will be updated when we fetch full user
        role: authData.role as User['role'],
        status: authData.status as UserStatus,
        organization_id: authData.organization_id || undefined,
        created_at: new Date().toISOString(),
      };
      
      // Fetch user's organizations
      let orgs: Organization[] = [];
      let currentOrg: Organization | null = null;
      
      // If user has an organization, fetch it
      if (authData.organization_id) {
        try {
          const org = await organizationsApi.get(authData.organization_id);
          currentOrg = apiOrgToOrg(org);
          orgs = [currentOrg];
        } catch (err) {
          console.error('Failed to fetch organization:', err);
        }
      }

      setState({
        user,
        currentOrg,
        organizations: orgs,
        isAuthenticated: true,
        isLoading: false,
      });

      saveSession(user, orgs, currentOrg);
      await loadUsersAndOrgs();

      return { status: authData.status as UserStatus };
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, [saveSession]);

  const signup = useCallback(async (
    name: string,
    email: string,
    password: string,
    orgName?: string,
    joinOrgId?: string
  ): Promise<{ status: UserStatus; message: string }> => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      const response = await authApi.register({
        name,
        email,
        password,
        organization_name: orgName,
        organization_id: joinOrgId,
      });

      // Backend returns user_id, role, and status in the token response
      const authData = response.data;
      
      // If status is pending, don't log the user in - show pending message
      if (authData.status === 'pending') {
        // Clear any tokens since they shouldn't be logged in yet
        localStorage.removeItem('filevault_access_token');
        localStorage.removeItem('filevault_refresh_token');
        
        setState(prev => ({ ...prev, isLoading: false }));
        
        return { 
          status: 'pending', 
          message: 'Your account has been submitted for approval. A platform administrator will review your registration.' 
        };
      }
      
      // Create user object from auth response
      const user: User = {
        id: authData.user_id,
        email: email,
        name: name,
        role: authData.role as User['role'],
        status: authData.status as UserStatus,
        created_at: new Date().toISOString(),
      };

      // Fetch organization if user has one
      let orgs: Organization[] = [];
      let currentOrg: Organization | null = null;

      setState({
        user,
        currentOrg,
        organizations: orgs,
        isAuthenticated: true,
        isLoading: false,
      });

      saveSession(user, orgs, currentOrg);
      await loadUsersAndOrgs();

      return { 
        status: authData.status as UserStatus, 
        message: 'Account created successfully!' 
      };
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, [saveSession]);

  const logout = useCallback(() => {
    authApi.logout();
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
    try {
      const currentUser = await authApi.getCurrentUser();
      setState(prev => ({
        ...prev,
        user: apiUserToUser(currentUser),
      }));
      await loadUsersAndOrgs();
    } catch (error) {
      console.error('Failed to refresh user:', error);
    }
  }, []);

  const createOrganization = useCallback(async (name: string, plan: Organization['plan']): Promise<Organization> => {
    const response = await organizationsApi.create({ name, plan });
    const org = apiOrgToOrg(response);

    setState(prev => ({
      ...prev,
      organizations: [...prev.organizations, org],
      currentOrg: org,
    }));

    if (state.user) {
      saveSession(state.user, [...state.organizations, org], org);
    }

    await loadUsersAndOrgs();
    return org;
  }, [state.user, state.organizations, saveSession]);

  const approveRegistration = useCallback(async (registrationId: string, reviewerId: string) => {
    // Call backend API to approve user
    await usersApi.updateStatus(registrationId, 'approved');
    
    // Update local state
    setPendingRegistrations(prev => 
      prev.map(r => r.id === registrationId 
        ? { ...r, status: 'approved' as UserStatus, reviewed_by: reviewerId, reviewed_at: new Date().toISOString() }
        : r
      )
    );
    await loadUsersAndOrgs();
  }, []);

  const rejectRegistration = useCallback(async (registrationId: string, reviewerId: string) => {
    // Call backend API to reject user
    await usersApi.updateStatus(registrationId, 'rejected');
    
    // Update local state
    setPendingRegistrations(prev => 
      prev.map(r => r.id === registrationId 
        ? { ...r, status: 'rejected' as UserStatus, reviewed_by: reviewerId, reviewed_at: new Date().toISOString() }
        : r
      )
    );
    await loadUsersAndOrgs();
  }, []);
  const getAvailableOrganizations = useCallback(() => {
    return allOrganizations;
  }, [allOrganizations]);

  const getAllUsers = useCallback((): RegisteredUser[] => {
    return allUsers;
  }, [allUsers]);

  const getApprovedRegistrations = useCallback(() => {
    return pendingRegistrations.filter(r => r.status === 'approved');
  }, [pendingRegistrations]);

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
