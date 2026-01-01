'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import { chatApi, ChatMessage, ChatAction, ChatHealthResponse } from '@/lib/chatApi';
import { filesApi } from '@/lib/api';
import {
  MessageCircle,
  X,
  Send,
  RotateCcw,
  ArrowRight,
  Bot,
  User,
  Sparkles,
  ChevronRight,
  ExternalLink,
  CheckCircle,
  AlertCircle,
  Loader2,
  Minimize2,
  Maximize2,
  Paperclip,
  Upload
} from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  actions?: ChatAction[];
  suggestions?: string[];
  isLoading?: boolean;
  isError?: boolean;
}

// ============================================================================
// Loading Animation Component
// ============================================================================

const TypingIndicator = () => (
  <div className="flex items-center gap-1 py-2">
    <div className="flex gap-1">
      <span className="w-2 h-2 rounded-full bg-current animate-bounce [animation-delay:-0.3s]" />
      <span className="w-2 h-2 rounded-full bg-current animate-bounce [animation-delay:-0.15s]" />
      <span className="w-2 h-2 rounded-full bg-current animate-bounce" />
    </div>
    <span className="text-xs ml-2 opacity-70">Thinking...</span>
  </div>
);

// ============================================================================
// Message Bubble Component
// ============================================================================

interface MessageBubbleProps {
  message: Message;
  isDark: boolean;
  onAction: (action: ChatAction) => void;
  onSuggestionClick: (suggestion: string) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isDark,
  onAction,
  onSuggestionClick
}) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <span className={`text-xs px-3 py-1 rounded-full ${
          isDark ? 'bg-gray-800 text-gray-400' : 'bg-gray-100 text-gray-500'
        }`}>
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 mb-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser
          ? isDark ? 'bg-blue-600' : 'bg-blue-500'
          : isDark ? 'bg-purple-600' : 'bg-purple-500'
      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`rounded-2xl px-4 py-3 ${
          isUser
            ? isDark ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
            : isDark ? 'bg-gray-800 text-gray-100' : 'bg-gray-100 text-gray-900'
        } ${isUser ? 'rounded-br-md' : 'rounded-bl-md'}`}>
          {message.isLoading ? (
            <TypingIndicator />
          ) : (
            <div className="text-sm whitespace-pre-wrap leading-relaxed">
              {message.content}
            </div>
          )}
        </div>

        {/* Actions */}
        {message.actions && message.actions.length > 0 && !message.isLoading && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.actions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => onAction(action)}
                className={`inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-all ${
                  action.type === 'navigate'
                    ? isDark
                      ? 'bg-blue-900/50 text-blue-300 hover:bg-blue-900/70 border border-blue-800'
                      : 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200'
                    : action.type === 'execute'
                    ? isDark
                      ? 'bg-green-900/50 text-green-300 hover:bg-green-900/70 border border-green-800'
                      : 'bg-green-50 text-green-700 hover:bg-green-100 border border-green-200'
                    : action.type === 'error'
                    ? isDark
                      ? 'bg-red-900/50 text-red-300 border border-red-800'
                      : 'bg-red-50 text-red-700 border border-red-200'
                    : isDark
                      ? 'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300'
                }`}
              >
                {action.type === 'navigate' && <ArrowRight className="w-3.5 h-3.5" />}
                {action.type === 'execute' && <CheckCircle className="w-3.5 h-3.5" />}
                {action.type === 'error' && <AlertCircle className="w-3.5 h-3.5" />}
                {action.type === 'info' && <Sparkles className="w-3.5 h-3.5" />}
                {action.description || action.type}
                {action.type === 'navigate' && <ExternalLink className="w-3 h-3" />}
              </button>
            ))}
          </div>
        )}

        {/* Inline Suggestions */}
        {message.suggestions && message.suggestions.length > 0 && !message.isLoading && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.suggestions.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => onSuggestionClick(suggestion)}
                className={`inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-full transition-all ${
                  isDark
                    ? 'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700'
                    : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200 shadow-sm'
                }`}
              >
                <ChevronRight className="w-3 h-3" />
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className={`text-[10px] mt-1 ${
          isDark ? 'text-gray-500' : 'text-gray-400'
        }`}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
};

// ============================================================================
// Quick Actions Bar
// ============================================================================

interface QuickActionsProps {
  onAction: (action: string) => void;
  isDark: boolean;
  disabled: boolean;
}

const QuickActions: React.FC<QuickActionsProps> = ({ onAction, isDark, disabled }) => {
  const actions = [
    { label: 'Upload file', action: 'How do I upload a file?' },
    { label: 'My files', action: 'Show my files' },
    { label: 'Help', action: 'What can you help me with?' },
  ];

  return (
    <div className="flex gap-2 overflow-x-auto py-2 px-1">
      {actions.map((item, idx) => (
        <button
          key={idx}
          onClick={() => onAction(item.action)}
          disabled={disabled}
          className={`flex-shrink-0 text-xs font-medium px-3 py-1.5 rounded-full transition-all ${
            isDark
              ? 'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700 disabled:opacity-50'
              : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200 shadow-sm disabled:opacity-50'
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
};

// ============================================================================
// Main Chat Widget Component
// ============================================================================

export default function ChatWidget() {
  const router = useRouter();
  const { isDark } = useTheme();
  const { user } = useAuth();
  const currentUserId = user?.id || '';
  
  // State
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [health, setHealth] = useState<ChatHealthResponse | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const initRef = useRef(false);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen && !isMinimized) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, isMinimized]);

  // Check health on mount
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

  // Load suggestions when chat opens
  useEffect(() => {
    if (isOpen && isEnabled && suggestions.length === 0) {
      loadSuggestions();
    }
  }, [isOpen, isEnabled, suggestions.length]);

  const loadSuggestions = async () => {
    try {
      const data = await chatApi.getSuggestions();
      setSuggestions(data.suggestions);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  // Handle action execution
  const handleAction = useCallback((action: ChatAction) => {
    switch (action.type) {
      case 'navigate':
        const path = action.payload?.path as string;
        if (path) {
          // Add system message about navigation
          setMessages(prev => [...prev, {
            id: `system-${Date.now()}`,
            role: 'system',
            content: `Navigating to ${path}...`,
            timestamp: new Date(),
          }]);
          
          // Perform navigation
          setTimeout(() => {
            router.push(path);
            // Optionally minimize chat after navigation
            setIsMinimized(true);
          }, 300);
        }
        break;

      case 'execute':
        // Execute the action
        const actionName = action.payload?.action as string;
        console.log('Executing action:', actionName, action.payload);
        
        // Add system message
        setMessages(prev => [...prev, {
          id: `system-${Date.now()}`,
          role: 'system',
          content: `Executing: ${action.description || actionName}`,
          timestamp: new Date(),
        }]);
        
        // Handle specific execute actions
        if (actionName === 'upload') {
          router.push('/dashboard/files?action=upload');
        } else if (actionName === 'search') {
          router.push(`/dashboard/files?search=${action.payload?.query || ''}`);
        }
        break;

      case 'confirm':
        const confirmed = window.confirm(action.payload?.message as string || 'Are you sure?');
        if (confirmed && action.payload?.action) {
          sendMessage(`Yes, proceed with ${action.payload.action}`);
        }
        break;

      case 'upload':
        // Trigger file upload
        const fileInput = document.getElementById('chat-file-upload') as HTMLInputElement;
        if (fileInput) {
          fileInput.click();
        }
        break;

      case 'info':
      case 'error':
        // These are informational only
        break;
    }
  }, [router]);

  // Upload state
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  // Handle file upload from chat - using the same API as Files page
  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    // Check if user is logged in
    if (!currentUserId) {
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: '❌ **Upload Failed**\n\nYou must be logged in to upload files.',
        timestamp: new Date(),
        isError: true,
      }]);
      event.target.value = '';
      return;
    }

    const file = files[0];
    const uploadMsgId = `upload-${Date.now()}`;
    
    // Add user message showing file selection
    setMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      role: 'user',
      content: `📎 ${file.name}`,
      timestamp: new Date(),
    }]);

    setIsUploading(true);
    setUploadProgress(0);

    // Add upload status message
    setMessages(prev => [...prev, {
      id: uploadMsgId,
      role: 'system' as const,
      content: '⏳ Uploading...',
      timestamp: new Date(),
    }]);

    try {
      // Use the same uploadFile method as the Files page
      const uploadedFile = await filesApi.uploadFile(
        file,
        currentUserId,
        undefined, // appointmentId
        user?.organization_id || undefined, // organizationId
        undefined, // folderId
        (progress) => {
          setUploadProgress(progress);
          setMessages(prev => prev.map(m => 
            m.id === uploadMsgId 
              ? { ...m, content: `📤 Uploading... ${progress}%` }
              : m
          ));
        }
      );

      // Success! Show virus scan status
      const virusStatusIcon = uploadedFile.virus_scan_status === 'clean' ? '✅' : 
                              uploadedFile.virus_scan_status === 'infected' ? '🛡️' :
                              uploadedFile.virus_scan_status === 'pending' ? '⏳' : '❓';
      const virusStatusText = uploadedFile.virus_scan_status === 'clean' ? 'Clean' :
                              uploadedFile.virus_scan_status === 'infected' ? 'Infected' :
                              uploadedFile.virus_scan_status === 'pending' ? 'Scanning...' :
                              uploadedFile.virus_scan_status || 'Unknown';
      
      setUploadProgress(100);
      setMessages(prev => prev.filter(m => m.id !== uploadMsgId));
      setMessages(prev => [...prev, {
        id: `success-${Date.now()}`,
        role: 'assistant',
        content: `✅ **Upload Complete!**\n\n**File:** ${uploadedFile.filename}\n**Size:** ${(uploadedFile.size / 1024).toFixed(1)} KB\n**Virus Scan:** ${virusStatusIcon} ${virusStatusText}\n\nYour file has been uploaded successfully and is ready to use.`,
        timestamp: new Date(),
        suggestions: ['My files', 'Upload another', 'Storage info'],
      }]);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
      console.error('Upload error:', err);
      
      setMessages(prev => prev.filter(m => m.id !== uploadMsgId));
      
      if (errorMessage.toLowerCase().includes('virus') || 
          errorMessage.toLowerCase().includes('malware') ||
          errorMessage.toLowerCase().includes('infected')) {
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `🛡️ **Security Alert**\n\nA virus has been detected in "${file.name}". The file has been quarantined for your safety.\n\nPlease ensure your files are virus-free before uploading.`,
          timestamp: new Date(),
          suggestions: ['My files', 'Help'],
        }]);
      } else {
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `❌ **Upload Failed**\n\n${errorMessage}\n\nPlease try again or contact support if the issue persists.`,
          timestamp: new Date(),
          suggestions: ['Try again', 'Help'],
        }]);
      }
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      event.target.value = '';
    }
  }, [currentUserId, user?.organization_id]);

  // Trigger file upload dialog
  const triggerFileUpload = useCallback(() => {
    const fileInput = document.getElementById('chat-file-upload') as HTMLInputElement;
    if (fileInput) {
      fileInput.click();
    }
  }, []);

  // Send message
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    // Add loading message
    const loadingId = `loading-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: loadingId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    }]);
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage(content, sessionId || undefined);
      setSessionId(response.session_id);

      // Remove loading and add response
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.response.message,
        timestamp: new Date(response.timestamp),
        actions: response.response.actions,
        suggestions: response.response.suggestions,
      };

      setMessages(prev => prev.filter(m => m.id !== loadingId).concat(assistantMessage));

      // Update suggestions
      if (response.response.suggestions.length > 0) {
        setSuggestions(response.response.suggestions);
      }

      // Auto-execute navigate actions if only one is present and no confirmation needed
      const navigateActions = response.response.actions.filter(a => a.type === 'navigate' && !a.requires_confirmation);
      if (navigateActions.length === 1) {
        // Auto-navigate after a short delay
        setTimeout(() => handleAction(navigateActions[0]), 1000);
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      
      setMessages(prev => prev.filter(m => m.id !== loadingId).concat({
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: error instanceof Error ? error.message : 'Sorry, something went wrong. Please try again.',
        timestamp: new Date(),
        isError: true,
      }));
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading, handleAction]);

  // Handle keyboard
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  // Clear chat
  const clearChat = () => {
    setMessages([]);
    setSessionId(null);
    loadSuggestions();
  };

  // Don't render if disabled
  if (!isEnabled) return null;

  return (
    <>
      {/* Floating Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className={`fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg z-50 flex items-center justify-center transition-all duration-300 hover:scale-110 ${
            isDark
              ? 'bg-gradient-to-br from-purple-600 to-blue-600 text-white shadow-purple-500/25'
              : 'bg-gradient-to-br from-blue-500 to-purple-500 text-white shadow-blue-500/25'
          }`}
          aria-label="Open chat"
        >
          <MessageCircle className="w-6 h-6" />
          {/* Status indicator */}
          <span className={`absolute top-1 right-1 w-3 h-3 rounded-full border-2 ${
            isDark ? 'border-gray-900' : 'border-white'
          } ${isConnected ? 'bg-green-500' : 'bg-yellow-500'}`} />
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div
          className={`fixed z-50 transition-all duration-300 ${
            isMinimized
              ? 'bottom-6 right-6 w-72'
              : 'bottom-6 right-6 w-[400px] h-[600px] max-h-[80vh]'
          } ${
            isDark
              ? 'bg-gray-900 border-gray-800'
              : 'bg-white border-gray-200'
          } rounded-2xl shadow-2xl border overflow-hidden flex flex-col`}
        >
          {/* Header */}
          <div className={`px-4 py-3 flex items-center justify-between border-b ${
            isDark
              ? 'bg-gradient-to-r from-purple-900/50 to-blue-900/50 border-gray-800'
              : 'bg-gradient-to-r from-blue-500 to-purple-500'
          }`}>
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                isDark ? 'bg-purple-600' : 'bg-white/20'
              }`}>
                <Sparkles className={`w-5 h-5 ${isDark ? 'text-white' : 'text-white'}`} />
              </div>
              <div>
                <h3 className="font-semibold text-white text-sm">FileVault AI</h3>
                <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-white/80'}`}>
                  {isConnected ? (
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                      {health?.provider?.provider || 'AI'} ready
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Connecting...
                    </span>
                  )}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={clearChat}
                className={`p-2 rounded-lg transition-colors ${
                  isDark ? 'hover:bg-white/10 text-gray-300' : 'hover:bg-white/20 text-white'
                }`}
                title="Clear chat"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                className={`p-2 rounded-lg transition-colors ${
                  isDark ? 'hover:bg-white/10 text-gray-300' : 'hover:bg-white/20 text-white'
                }`}
                title={isMinimized ? "Expand" : "Minimize"}
              >
                {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className={`p-2 rounded-lg transition-colors ${
                  isDark ? 'hover:bg-white/10 text-gray-300' : 'hover:bg-white/20 text-white'
                }`}
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Content - hidden when minimized */}
          {!isMinimized && (
            <>
              {/* Messages Area */}
              <div className={`flex-1 overflow-y-auto p-4 ${
                isDark ? 'bg-gray-900' : 'bg-gray-50'
              }`}>
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center px-4">
                    <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
                      isDark ? 'bg-purple-900/50' : 'bg-purple-100'
                    }`}>
                      <Sparkles className={`w-8 h-8 ${isDark ? 'text-purple-400' : 'text-purple-500'}`} />
                    </div>
                    <h4 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      Welcome to FileVault AI! 👋
                    </h4>
                    <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      I can help you navigate, upload files, search, and more. Just ask!
                    </p>
                    <QuickActions
                      onAction={sendMessage}
                      isDark={isDark}
                      disabled={isLoading}
                    />
                  </div>
                ) : (
                  <>
                    {messages.map((msg) => (
                      <MessageBubble
                        key={msg.id}
                        message={msg}
                        isDark={isDark}
                        onAction={handleAction}
                        onSuggestionClick={sendMessage}
                      />
                    ))}
                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>

              {/* Suggestions Bar */}
              {suggestions.length > 0 && messages.length > 0 && (
                <div className={`px-4 py-2 border-t overflow-x-auto ${
                  isDark ? 'border-gray-800 bg-gray-900' : 'border-gray-100 bg-white'
                }`}>
                  <div className="flex gap-2">
                    {suggestions.slice(0, 4).map((suggestion, idx) => (
                      <button
                        key={idx}
                        onClick={() => sendMessage(suggestion)}
                        disabled={isLoading}
                        className={`flex-shrink-0 text-xs px-3 py-1.5 rounded-full transition-all ${
                          isDark
                            ? 'bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700 disabled:opacity-50'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-50'
                        }`}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Input Area */}
              <div className={`p-4 border-t ${
                isDark ? 'border-gray-800 bg-gray-900' : 'border-gray-100 bg-white'
              }`}>
                {/* Upload Progress Bar */}
                {isUploading && (
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-medium ${isDark ? 'text-purple-400' : 'text-blue-600'}`}>
                        Uploading...
                      </span>
                      <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {uploadProgress}%
                      </span>
                    </div>
                    <div className={`w-full h-2 rounded-full ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          isDark ? 'bg-purple-500' : 'bg-blue-500'
                        }`}
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                )}
                {/* Hidden file input */}
                <input
                  type="file"
                  id="chat-file-upload"
                  className="hidden"
                  onChange={handleFileUpload}
                  accept="*/*"
                  disabled={isUploading}
                />
                <div className={`flex items-end gap-2 p-2 rounded-xl ${
                  isDark ? 'bg-gray-800' : 'bg-gray-100'
                }`}>
                  {/* Attachment button */}
                  <button
                    onClick={triggerFileUpload}
                    disabled={isLoading || isUploading}
                    className={`p-2 rounded-lg transition-all ${
                      isUploading
                        ? isDark
                          ? 'text-purple-400 bg-purple-900/30'
                          : 'text-blue-500 bg-blue-100'
                        : isDark
                          ? 'text-gray-400 hover:text-purple-400 hover:bg-gray-700'
                          : 'text-gray-500 hover:text-blue-500 hover:bg-gray-200'
                    } disabled:opacity-50`}
                    title={isUploading ? "Uploading..." : "Attach file"}
                  >
                    {isUploading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Paperclip className="w-5 h-5" />
                    )}
                  </button>
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask me anything..."
                    rows={1}
                    className={`flex-1 resize-none bg-transparent text-sm outline-none px-2 py-1.5 max-h-24 ${
                      isDark ? 'text-white placeholder-gray-500' : 'text-gray-900 placeholder-gray-400'
                    }`}
                    style={{ minHeight: '36px' }}
                    disabled={isLoading}
                  />
                  <button
                    onClick={() => sendMessage(input)}
                    disabled={!input.trim() || isLoading}
                    className={`p-2 rounded-lg transition-all ${
                      input.trim() && !isLoading
                        ? isDark
                          ? 'bg-purple-600 text-white hover:bg-purple-700'
                          : 'bg-blue-500 text-white hover:bg-blue-600'
                        : isDark
                          ? 'bg-gray-700 text-gray-500'
                          : 'bg-gray-200 text-gray-400'
                    }`}
                  >
                    {isLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </div>
                <p className={`text-[10px] mt-2 text-center ${
                  isDark ? 'text-gray-600' : 'text-gray-400'
                }`}>
                  Powered by {health?.provider?.provider || 'AI'} • Press Enter to send
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
