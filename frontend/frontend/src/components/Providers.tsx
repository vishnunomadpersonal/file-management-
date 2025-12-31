"use client";

import { ReactNode } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import ChatWidget from '@/components/ChatWidget';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <AuthProvider>
        {children}
        {/* Global Chat Widget - handles its own state and navigation */}
        <ChatWidget />
      </AuthProvider>
    </ThemeProvider>
  );
}
