'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { chatApi, ChatMessage, ChatAction, SuggestionsResponse, ChatHealthResponse } from '@/lib/chatApi';

// ============================================================================
// Types
// ============================================================================

interface ChatContextType {
  // State
  isOpen: boolean;
  isEnabled: boolean;
  isLoading: boolean;
  isConnected: boolean;
  messages: ChatMessage[];
  suggestions: string[];
  sessionId: string | null;
  health: ChatHealthResponse | null;

  // Actions
  toggleChat: () => void;
  openChat: () => void;
  closeChat: () => void;
  sendMessage: (content: string) => Promise<void>;
  handleAction: (action: ChatAction) => void;
  clearMessages: () => void;
  endSession: () => Promise<void>;
  refresh: () => Promise<void>;
}

const ChatContext = createContext<ChatContextType | null>(null);

// ============================================================================
// Hook
// ============================================================================

export function useChatbot() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatbot must be used within a ChatProvider');
  }
  return context;
}

// ============================================================================
// Provider
// ============================================================================

interface ChatProviderProps {
  children: ReactNode;
  onNavigate?: (path: string) => void;
}

export function ChatProvider({ children, onNavigate }: ChatProviderProps) {
  // State
  const [isOpen, setIsOpen] = useState(false);
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [health, setHealth] = useState<ChatHealthResponse | null>(null);

  // Refs
  const initRef = useRef(false);

  // Check chatbot health on mount
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    const checkHealth = async () => {
      try {
        const healthData = await chatApi.health();
        setHealth(healthData);
        setIsEnabled(healthData.enabled);
        setIsConnected(healthData.provider.status === 'healthy');
      } catch (error) {
        console.error('Chatbot health check failed:', error);
        setIsEnabled(false);
      }
    };

    checkHealth();
  }, []);

  // Load suggestions when chat is opened
  useEffect(() => {
    if (isOpen && isEnabled && suggestions.length === 0) {
      loadSuggestions();
    }
  }, [isOpen, isEnabled]);

  // Load initial suggestions
  const loadSuggestions = useCallback(async () => {
    try {
      const data = await chatApi.getSuggestions();
      setSuggestions(data.suggestions);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  }, []);

  // Toggle chat panel
  const toggleChat = useCallback(() => {
    setIsOpen(prev => !prev);
  }, []);

  const openChat = useCallback(() => {
    setIsOpen(true);
  }, []);

  const closeChat = useCallback(() => {
    setIsOpen(false);
  }, []);

  // Send a message
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Add loading message
    const loadingMessage: ChatMessage = {
      id: `loading-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isLoading: true,
    };
    setMessages(prev => [...prev, loadingMessage]);
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage(content, sessionId || undefined);
      
      // Update session ID
      setSessionId(response.session_id);

      // Remove loading message and add real response
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.response.message,
        timestamp: response.timestamp,
        actions: response.response.actions,
        suggestions: response.response.suggestions,
      };

      setMessages(prev => 
        prev.filter(m => !m.isLoading).concat(assistantMessage)
      );

      // Update suggestions
      if (response.response.suggestions.length > 0) {
        setSuggestions(response.response.suggestions);
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Remove loading and add error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: error instanceof Error 
          ? error.message 
          : 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => 
        prev.filter(m => !m.isLoading).concat(errorMessage)
      );
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading]);

  // Handle chatbot actions
  const handleAction = useCallback((action: ChatAction) => {
    switch (action.type) {
      case 'navigate':
        const path = action.payload.path as string;
        if (onNavigate) {
          onNavigate(path);
        } else {
          window.location.href = path;
        }
        // Optionally close chat after navigation
        // closeChat();
        break;

      case 'execute':
        // Handle execute actions - could dispatch to a handler
        console.log('Execute action:', action.payload);
        break;

      case 'confirm':
        // Handle confirmation dialogs
        const confirmed = window.confirm(action.payload.message as string);
        if (confirmed) {
          // Send confirmation to backend or execute action
          sendMessage(`Yes, ${action.payload.action}`);
        }
        break;

      case 'info':
      case 'error':
        // These are just informational, no action needed
        break;
    }
  }, [onNavigate, sendMessage]);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    setSuggestions([]);
    loadSuggestions();
  }, [loadSuggestions]);

  // End session
  const endSession = useCallback(async () => {
    if (sessionId) {
      try {
        await chatApi.endSession(sessionId);
      } catch (error) {
        console.error('Failed to end session:', error);
      }
    }
    setSessionId(null);
    clearMessages();
  }, [sessionId, clearMessages]);

  // Refresh health
  const refresh = useCallback(async () => {
    try {
      const healthData = await chatApi.health();
      setHealth(healthData);
      setIsEnabled(healthData.enabled);
      setIsConnected(healthData.provider.status === 'healthy');
    } catch (error) {
      console.error('Chatbot refresh failed:', error);
    }
  }, []);

  const value: ChatContextType = {
    isOpen,
    isEnabled,
    isLoading,
    isConnected,
    messages,
    suggestions,
    sessionId,
    health,
    toggleChat,
    openChat,
    closeChat,
    sendMessage,
    handleAction,
    clearMessages,
    endSession,
    refresh,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}
