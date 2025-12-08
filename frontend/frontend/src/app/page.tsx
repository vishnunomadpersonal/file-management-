"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';

// ============================================================================
// Icons
// ============================================================================

const Icons = {
  Logo: ({ className = "w-10 h-10" }: { className?: string }) => (
    <svg className={className} viewBox="0 0 48 48" fill="none">
      <rect width="48" height="48" rx="12" className="fill-indigo-600" />
      <path d="M14 16h20v4H14zM14 24h16v4H14zM14 32h12v4H14z" fill="white" fillOpacity="0.9" />
      <circle cx="36" cy="34" r="6" className="fill-emerald-400" />
      <path d="M33.5 34l2 2 3-3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Shield: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  Users: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
  Folder: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  ),
  Zap: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  Check: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  X: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  ArrowRight: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
    </svg>
  ),
  Star: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  ),
  Play: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M8 5v14l11-7z" />
    </svg>
  ),
  Spinner: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={`${className} animate-spin`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  ),
  Eye: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  ),
  EyeOff: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
    </svg>
  ),
  Clock: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="10" strokeWidth="2" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6l4 2" />
    </svg>
  ),
  Sun: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  ),
  Moon: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
    </svg>
  ),
};

// ============================================================================
// Feature Card
// ============================================================================

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  gradient: string;
}

function FeatureCard({ icon, title, description, gradient }: FeatureCardProps) {
  return (
    <div className="group relative bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-xl hover:border-gray-200 dark:hover:border-gray-600 transition-all duration-300">
      <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-white mb-6 group-hover:scale-110 transition-transform duration-300`}>
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400 leading-relaxed">{description}</p>
    </div>
  );
}

// ============================================================================
// Pricing Card
// ============================================================================

interface PricingCardProps {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  highlighted?: boolean;
  onSelect: () => void;
}

function PricingCard({ name, price, period, description, features, highlighted, onSelect }: PricingCardProps) {
  return (
    <div className={`relative rounded-2xl p-8 ${
      highlighted 
        ? 'bg-gradient-to-br from-indigo-600 to-purple-700 text-white shadow-2xl scale-105' 
        : 'bg-white border border-gray-200 shadow-sm'
    }`}>
      {highlighted && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-amber-400 to-orange-500 text-white text-sm font-medium rounded-full">
          Most Popular
        </div>
      )}
      <div className="mb-6">
        <h3 className={`text-xl font-semibold mb-2 ${highlighted ? 'text-white' : 'text-gray-900'}`}>{name}</h3>
        <p className={`text-sm ${highlighted ? 'text-indigo-100' : 'text-gray-500'}`}>{description}</p>
      </div>
      <div className="mb-6">
        <span className={`text-4xl font-bold ${highlighted ? 'text-white' : 'text-gray-900'}`}>{price}</span>
        <span className={`text-sm ${highlighted ? 'text-indigo-100' : 'text-gray-500'}`}>/{period}</span>
      </div>
      <ul className="space-y-3 mb-8">
        {features.map((feature, i) => (
          <li key={i} className="flex items-center gap-3">
            <Icons.Check className={`w-5 h-5 ${highlighted ? 'text-emerald-300' : 'text-emerald-500'}`} />
            <span className={`text-sm ${highlighted ? 'text-indigo-100' : 'text-gray-600'}`}>{feature}</span>
          </li>
        ))}
      </ul>
      <button
        onClick={onSelect}
        className={`w-full py-3 rounded-xl font-medium transition-all ${
          highlighted
            ? 'bg-white text-indigo-600 hover:bg-gray-100'
            : 'bg-gray-900 text-white hover:bg-gray-800'
        }`}
      >
        Get Started
      </button>
    </div>
  );
}

// ============================================================================
// Auth Modal
// ============================================================================

function AuthModal({ 
  isOpen, 
  onClose, 
  mode,
  onSwitchMode,
}: { 
  isOpen: boolean; 
  onClose: () => void;
  mode: 'login' | 'signup';
  onSwitchMode: () => void;
}) {
  const router = useRouter();
  const { login, signup } = useAuth();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [pendingMessage, setPendingMessage] = useState('');
  
  // Form state
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [orgName, setOrgName] = useState('');
  const [plan, setPlan] = useState<'starter' | 'pro' | 'enterprise'>('pro');
  const [signupType, setSignupType] = useState<'new_org' | 'join_org'>('new_org');
  const [selectedOrgId, setSelectedOrgId] = useState('');
  const [availableOrgs, setAvailableOrgs] = useState<{ id: string; name: string }[]>([]);

  // Fetch organizations when modal opens for signup
  useEffect(() => {
    if (isOpen && mode === 'signup') {
      import('@/lib/api').then(({ organizationsApi }) => {
        organizationsApi.listPublic().then(orgs => {
          setAvailableOrgs(orgs);
        }).catch(err => {
          console.error('Failed to load organizations:', err);
        });
      });
    }
  }, [isOpen, mode]);

  const resetForm = () => {
    setStep(1);
    setName('');
    setEmail('');
    setPassword('');
    setOrgName('');
    setPlan('pro');
    setError('');
    setPendingMessage('');
    setSignupType('new_org');
    setSelectedOrgId('');
  };

  const handleLogin = async () => {
    setLoading(true);
    setError('');
    setPendingMessage('');
    try {
      const result = await login(email, password);
      if (result.status === 'pending') {
        setPendingMessage('Your account is pending approval. Please wait for an admin to approve your registration.');
        return;
      }
      onClose();
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async () => {
    if (step === 1) {
      if (!name || !email || !password) {
        setError('Please fill in all fields');
        return;
      }
      if (password.length < 8) {
        setError('Password must be at least 8 characters');
        return;
      }
      setError('');
      setStep(2);
    } else if (step === 2) {
      if (signupType === 'new_org' && !orgName) {
        setError('Please enter your organization name');
        return;
      }
      if (signupType === 'join_org' && !selectedOrgId) {
        setError('Please select an organization to join');
        return;
      }
      setError('');
      // Skip plan selection for join_org
      if (signupType === 'join_org') {
        // Submit directly
        setLoading(true);
        try {
          const result = await signup(name, email, password, undefined, selectedOrgId);
          if (result.status === 'pending') {
            setPendingMessage(result.message);
            setStep(4); // Show pending message
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Failed to submit registration');
        } finally {
          setLoading(false);
        }
      } else {
        setStep(3);
      }
    } else if (step === 3) {
      setLoading(true);
      setError('');
      try {
        const result = await signup(name, email, password, orgName, undefined);
        if (result.status === 'pending') {
          setPendingMessage(result.message);
          setStep(4); // Show pending message
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to submit registration');
      } finally {
        setLoading(false);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => { onClose(); resetForm(); }} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
          {/* Close button */}
          <button 
            onClick={() => { onClose(); resetForm(); }}
            className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 z-10"
          >
            <Icons.X />
          </button>

          {/* Header gradient */}
          <div className="h-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />

          <div className="p-8">
            {/* Logo */}
            <div className="flex justify-center mb-6">
              <Icons.Logo className="w-12 h-12" />
            </div>

            {mode === 'login' ? (
              <>
                <h2 className="text-2xl font-bold text-center text-gray-900 mb-2">Welcome back</h2>
                <p className="text-center text-gray-500 mb-8">Sign in to your account</p>

                {error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
                    {error}
                  </div>
                )}
                
                {pendingMessage && (
                  <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-xl">
                    <div className="flex items-start gap-3">
                      <Icons.Clock className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-amber-800 font-medium text-sm">Account Pending Approval</p>
                        <p className="text-amber-700 text-sm mt-1">{pendingMessage}</p>
                      </div>
                    </div>
                  </div>
                )}

                {!pendingMessage && (
                  <>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="you@company.com"
                          className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
                        <div className="relative">
                          <input
                            type={showPassword ? 'text' : 'password'}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all pr-12"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                          >
                            {showPassword ? <Icons.EyeOff /> : <Icons.Eye />}
                          </button>
                        </div>
                      </div>
                      <button
                        onClick={handleLogin}
                        disabled={loading}
                        className="w-full py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        {loading ? <Icons.Spinner /> : 'Sign In'}
                      </button>
                    </div>

                    {/* Demo Accounts Section */}
                    <div className="mt-6 pt-6 border-t border-gray-100">
                      <p className="text-xs text-gray-500 text-center mb-3">Quick login with demo accounts:</p>
                      <div className="grid grid-cols-2 gap-2">
                    {[
                      { email: 'admin@filemanager.com', pass: 'Admin1234', role: 'Super Admin', color: 'bg-red-500' },
                      { email: 'orgadmin@company.com', pass: 'OrgAdmin1234', role: 'Org Admin', color: 'bg-purple-500' },
                      { email: 'manager@company.com', pass: 'Manager1234', role: 'Manager', color: 'bg-blue-500' },
                      { email: 'user@company.com', pass: 'User1234', role: 'User', color: 'bg-green-500' },
                      { email: 'viewer@company.com', pass: 'Viewer1234', role: 'Viewer', color: 'bg-gray-500' },
                    ].map((demo) => (
                      <button
                        key={demo.email}
                        onClick={() => {
                          setEmail(demo.email);
                          setPassword(demo.pass);
                        }}
                        className="flex items-center gap-2 px-3 py-2 text-xs rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all"
                      >
                        <span className={`w-2 h-2 rounded-full ${demo.color}`} />
                        <span className="text-gray-700 font-medium">{demo.role}</span>
                      </button>
                    ))}
                      </div>
                    </div>

                    <p className="text-center text-gray-500 mt-6">
                      Don&apos;t have an account?{' '}
                      <button onClick={onSwitchMode} className="text-indigo-600 font-medium hover:text-indigo-700">
                        Sign up
                      </button>
                    </p>
                  </>
                )}
              </>
            ) : (
              <>
                {/* Step 4: Pending Approval Message */}
                {step === 4 ? (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 mx-auto mb-6 bg-amber-100 rounded-full flex items-center justify-center">
                      <Icons.Clock className="w-8 h-8 text-amber-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-3">Registration Submitted</h2>
                    <p className="text-gray-600 mb-6">{pendingMessage}</p>
                    <div className="p-4 bg-gray-50 rounded-xl text-left">
                      <p className="text-sm text-gray-500 mb-2">What happens next?</p>
                      <ul className="text-sm text-gray-700 space-y-2">
                        <li className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full" />
                          An admin will review your request
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full" />
                          You&apos;ll receive an email when approved
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full" />
                          Then you can sign in with your credentials
                        </li>
                      </ul>
                    </div>
                    <button
                      onClick={() => { onClose(); resetForm(); }}
                      className="w-full mt-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
                    >
                      Got it
                    </button>
                  </div>
                ) : (
                  <>
                    {/* Progress indicator */}
                    <div className="flex items-center justify-center gap-2 mb-6">
                      {[1, 2, 3].map((s) => (
                        <div
                          key={s}
                          className={`w-2.5 h-2.5 rounded-full transition-all ${
                            s === step ? 'w-8 bg-indigo-600' : s < step ? 'bg-indigo-600' : 'bg-gray-200'
                          }`}
                        />
                      ))}
                    </div>

                    <h2 className="text-2xl font-bold text-center text-gray-900 mb-2">
                      {step === 1 && 'Create your account'}
                      {step === 2 && 'Join or Create Organization'}
                      {step === 3 && 'Choose your plan'}
                    </h2>
                    <p className="text-center text-gray-500 mb-8">
                      {step === 1 && 'Start your 14-day free trial'}
                      {step === 2 && 'Create a new organization or join an existing one'}
                      {step === 3 && 'Select the plan that fits your needs'}
                    </p>

                    {error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
                    {error}
                  </div>
                )}

                    {step === 1 && (
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1.5">Full Name</label>
                          <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="John Smith"
                            className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1.5">Work Email</label>
                          <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@company.com"
                            className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
                          <div className="relative">
                            <input
                              type={showPassword ? 'text' : 'password'}
                              value={password}
                              onChange={(e) => setPassword(e.target.value)}
                              placeholder="Min. 8 characters"
                              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all pr-12"
                            />
                            <button
                              type="button"
                              onClick={() => setShowPassword(!showPassword)}
                              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                            >
                              {showPassword ? <Icons.EyeOff /> : <Icons.Eye />}
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {step === 2 && (
                      <div className="space-y-4">
                        {/* Toggle between create/join */}
                        <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
                          <button
                            onClick={() => setSignupType('new_org')}
                            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                              signupType === 'new_org' 
                                ? 'bg-white text-gray-900 shadow-sm' 
                                : 'text-gray-500 hover:text-gray-700'
                            }`}
                          >
                            Create Organization
                          </button>
                          <button
                            onClick={() => setSignupType('join_org')}
                            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                              signupType === 'join_org' 
                                ? 'bg-white text-gray-900 shadow-sm' 
                                : 'text-gray-500 hover:text-gray-700'
                            }`}
                          >
                            Join Organization
                          </button>
                        </div>

                        {signupType === 'new_org' ? (
                          <>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1.5">Organization Name</label>
                              <input
                                type="text"
                                value={orgName}
                                onChange={(e) => setOrgName(e.target.value)}
                                placeholder="Acme Inc."
                                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                              />
                            </div>
                            <div className="p-4 bg-gray-50 rounded-xl">
                              <p className="text-sm text-gray-600">
                                Your organization URL will be:<br />
                                <span className="font-mono text-indigo-600">
                                  filevault.io/{orgName.toLowerCase().replace(/[^a-z0-9]/g, '-') || 'your-org'}
                                </span>
                              </p>
                            </div>
                            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl">
                              <p className="text-xs text-amber-700">
                                <strong>Note:</strong> New organization registrations require approval from a platform administrator.
                              </p>
                            </div>
                          </>
                        ) : (
                          <>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1.5">Select Organization</label>
                              <select
                                value={selectedOrgId}
                                onChange={(e) => setSelectedOrgId(e.target.value)}
                                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                              >
                                <option value="">Choose an organization...</option>
                                {availableOrgs.map(org => (
                                  <option key={org.id} value={org.id}>
                                    {org.name}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl">
                              <p className="text-xs text-blue-700">
                                <strong>Note:</strong> Joining an organization requires approval from both the organization admin and platform admin.
                              </p>
                            </div>
                          </>
                        )}
                      </div>
                    )}

                    {step === 3 && (
                      <div className="space-y-3">
                    {[
                      { id: 'starter', name: 'Starter', price: '$19', desc: 'For small teams' },
                      { id: 'pro', name: 'Pro', price: '$49', desc: 'For growing companies', popular: true },
                      { id: 'enterprise', name: 'Enterprise', price: '$199', desc: 'For large organizations' },
                    ].map((p) => (
                      <button
                        key={p.id}
                        onClick={() => setPlan(p.id as 'starter' | 'pro' | 'enterprise')}
                        className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                          plan === p.id
                            ? 'border-indigo-500 bg-indigo-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-gray-900">{p.name}</span>
                              {p.popular && (
                                <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-medium rounded-full">
                                  Popular
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-gray-500">{p.desc}</p>
                          </div>
                          <span className="text-lg font-bold text-gray-900">{p.price}<span className="text-sm font-normal text-gray-500">/mo</span></span>
                        </div>
                      </button>
                    ))}
                      </div>
                    )}

                    <button
                      onClick={handleSignup}
                      disabled={loading}
                      className="w-full mt-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      {loading ? <Icons.Spinner /> : step === 3 ? 'Submit Registration' : 'Continue'}
                      {!loading && <Icons.ArrowRight className="w-4 h-4" />}
                    </button>

                    {step > 1 && (
                      <button
                        onClick={() => setStep(step - 1)}
                        className="w-full mt-3 py-3 text-gray-600 font-medium hover:text-gray-900 transition-colors"
                      >
                        Back
                      </button>
                    )}

                    {step === 1 && (
                      <p className="text-center text-gray-500 mt-6">
                        Already have an account?{' '}
                        <button onClick={onSwitchMode} className="text-indigo-600 font-medium hover:text-indigo-700">
                          Sign in
                        </button>
                      </p>
                    )}
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Testimonial
// ============================================================================

function Testimonial({ quote, author, role, company }: { quote: string; author: string; role: string; company: string }) {
  return (
    <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
      <div className="flex gap-1 mb-4">
        {[...Array(5)].map((_, i) => (
          <Icons.Star key={i} className="w-5 h-5 text-amber-400" />
        ))}
      </div>
      <p className="text-gray-700 mb-6 leading-relaxed">&ldquo;{quote}&rdquo;</p>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600" />
        <div>
          <p className="font-semibold text-gray-900">{author}</p>
          <p className="text-sm text-gray-500">{role}, {company}</p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Landing Page
// ============================================================================

export default function LandingPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const [authModal, setAuthModal] = useState<'login' | 'signup' | null>(null);

  // Redirect if already authenticated
  React.useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, router]);

  const features = [
    {
      icon: <Icons.Shield className="w-7 h-7" />,
      title: 'Enterprise Security',
      description: 'Bank-grade encryption with automatic virus scanning. Your files are protected by ClamAV and stored securely in isolated containers.',
      gradient: 'from-indigo-500 to-indigo-600',
    },
    {
      icon: <Icons.Users className="w-7 h-7" />,
      title: 'Team Collaboration',
      description: 'Invite unlimited team members, set granular permissions, and collaborate in real-time with version history and comments.',
      gradient: 'from-emerald-500 to-emerald-600',
    },
    {
      icon: <Icons.Folder className="w-7 h-7" />,
      title: 'Smart Organization',
      description: 'AI-powered file categorization, advanced search, and intelligent tagging. Find any file in seconds, not minutes.',
      gradient: 'from-amber-500 to-orange-500',
    },
    {
      icon: <Icons.Zap className="w-7 h-7" />,
      title: 'API-First Platform',
      description: 'RESTful APIs and webhooks for seamless integration with your existing tools. SDKs available for all major languages.',
      gradient: 'from-purple-500 to-pink-500',
    },
  ];

  const pricingPlans = [
    {
      name: 'Starter',
      price: '$19',
      period: 'month',
      description: 'Perfect for small teams getting started',
      features: ['5 team members', '50 GB storage', 'Basic virus scanning', 'Email support', 'API access'],
    },
    {
      name: 'Pro',
      price: '$49',
      period: 'month',
      description: 'For growing companies that need more',
      features: ['25 team members', '500 GB storage', 'Advanced security', 'Priority support', 'Unlimited API calls', 'Custom integrations'],
      highlighted: true,
    },
    {
      name: 'Enterprise',
      price: '$199',
      period: 'month',
      description: 'For large organizations with advanced needs',
      features: ['Unlimited members', '5 TB storage', 'SSO & SAML', 'Dedicated support', 'SLA guarantee', 'Custom deployment'],
    },
  ];

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-gradient-to-b from-gray-50 to-white'}`}>
      {/* Navigation */}
      <nav className={`sticky top-0 z-40 backdrop-blur-xl border-b ${isDark ? 'bg-gray-900/80 border-gray-800' : 'bg-white/80 border-gray-100'}`}>
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Icons.Logo />
              <span className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>FileVault</span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className={`transition-colors ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}>Features</a>
              <a href="#pricing" className={`transition-colors ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}>Pricing</a>
              <a href="#testimonials" className={`transition-colors ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}>Testimonials</a>
            </div>
            <div className="flex items-center gap-3">
              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className={`p-2 rounded-lg transition-colors ${isDark ? 'text-gray-400 hover:text-white hover:bg-gray-800' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}
                title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {isDark ? <Icons.Sun className="w-5 h-5" /> : <Icons.Moon className="w-5 h-5" />}
              </button>
              <button 
                onClick={() => setAuthModal('login')}
                className={`font-medium transition-colors ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}
              >
                Sign In
              </button>
              <button 
                onClick={() => setAuthModal('signup')}
                className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
              >
                Start Free Trial
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-20 pb-32 overflow-hidden">
        <div className={`absolute inset-0 ${isDark ? 'bg-gray-900' : 'bg-gradient-to-br from-indigo-50 via-white to-purple-50'}`} />
        <div className={`absolute top-0 right-0 w-1/2 h-full ${isDark ? 'bg-gradient-to-l from-indigo-900/20 to-transparent' : 'bg-gradient-to-l from-indigo-100/50 to-transparent'}`} />
        
        <div className="relative max-w-7xl mx-auto px-6">
          <div className="max-w-3xl">
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium mb-8 ${isDark ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'}`}>
              <Icons.Zap className="w-4 h-4" />
              Now with ML-powered file classification
            </div>
            
            <h1 className={`text-5xl md:text-6xl font-bold leading-tight mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Enterprise file management,{' '}
              <span className="bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
                simplified
              </span>
            </h1>
            
            <p className={`text-xl mb-10 leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              Secure, multi-tenant file storage with automatic virus scanning, 
              team collaboration, and powerful APIs. Built for modern enterprises.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4">
              <button 
                onClick={() => setAuthModal('signup')}
                className="px-8 py-4 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2"
              >
                Start Free Trial
                <Icons.ArrowRight />
              </button>
              <button className={`px-8 py-4 rounded-xl font-semibold border transition-all flex items-center justify-center gap-2 ${isDark ? 'bg-gray-800 text-white border-gray-700 hover:border-gray-600' : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'}`}>
                <Icons.Play className="w-5 h-5 text-indigo-500" />
                Watch Demo
              </button>
            </div>

            <div className="flex items-center gap-8 mt-12">
              <div className="flex -space-x-3">
                {[...Array(4)].map((_, i) => (
                  <div 
                    key={i} 
                    className={`w-10 h-10 rounded-full border-2 bg-gradient-to-br from-indigo-400 to-purple-500 ${isDark ? 'border-gray-900' : 'border-white'}`}
                  />
                ))}
              </div>
              <div>
                <div className="flex items-center gap-1">
                  {[...Array(5)].map((_, i) => (
                    <Icons.Star key={i} className="w-4 h-4 text-amber-400" />
                  ))}
                </div>
                <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Trusted by 10,000+ companies</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className={`py-24 ${isDark ? 'bg-gray-800/50' : 'bg-white'}`}>
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className={`text-3xl md:text-4xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Everything you need to manage files at scale
            </h2>
            <p className={`text-xl max-w-2xl mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              Built for security-conscious teams who need enterprise features without enterprise complexity.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, i) => (
              <FeatureCard key={i} {...feature} />
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Start free for 14 days. No credit card required.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {pricingPlans.map((plan, i) => (
              <PricingCard 
                key={i} 
                {...plan} 
                onSelect={() => setAuthModal('signup')}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section id="testimonials" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Loved by teams worldwide
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <Testimonial
              quote="FileVault transformed how our team handles sensitive documents. The virus scanning alone has blocked dozens of threats."
              author="Sarah Chen"
              role="CTO"
              company="TechFlow"
            />
            <Testimonial
              quote="We migrated from Dropbox and never looked back. The API integration with our existing tools was seamless."
              author="Michael Rodriguez"
              role="Engineering Lead"
              company="DataSync"
            />
            <Testimonial
              quote="Finally, an enterprise solution that does not require a dedicated team to manage. Setup took less than an hour."
              author="Emily Thompson"
              role="Operations Director"
              company="HealthFirst"
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-br from-indigo-600 to-purple-700">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
            Ready to secure your files?
          </h2>
          <p className="text-xl text-indigo-100 mb-10">
            Join thousands of companies that trust FileVault for their file management needs.
          </p>
          <button 
            onClick={() => setAuthModal('signup')}
            className="px-8 py-4 bg-white text-indigo-600 rounded-xl font-semibold hover:bg-gray-100 transition-all shadow-xl"
          >
            Start Your Free Trial
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-gray-900 text-gray-400">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <Icons.Logo className="w-8 h-8" />
              <span className="text-white font-semibold">FileVault</span>
            </div>
            <p className="text-sm">© 2025 FileVault. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModal !== null}
        onClose={() => setAuthModal(null)}
        mode={authModal || 'login'}
        onSwitchMode={() => setAuthModal(authModal === 'login' ? 'signup' : 'login')}
      />
    </div>
  );
}
