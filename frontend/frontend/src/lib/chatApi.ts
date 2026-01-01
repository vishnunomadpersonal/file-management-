/**
 * Chatbot API - Connect to AI chatbot backend
 */

const API_ORIGIN = (
  process.env.NEXT_PUBLIC_API_ORIGIN ||
  (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000')
).replace(/\/+$/, '');

const API_BASE = `${API_ORIGIN}/api/v1/chat`;

// ============================================================================
// Types
// ============================================================================

export interface ChatAction {
  type: 'navigate' | 'execute' | 'confirm' | 'info' | 'error' | 'upload';
  payload: Record<string, unknown>;
  description: string;
  requires_confirmation: boolean;
}

export interface ChatMessageResponse {
  message: string;
  actions: ChatAction[];
  suggestions: string[];
  provider: string;
  processing_time_ms: number;
  tokens_used?: number;
}

export interface ChatResponse {
  session_id: string;
  response: ChatMessageResponse;
  message_count: number;
  timestamp: string;
}

export interface SuggestionsResponse {
  suggestions: string[];
  accessible_pages: { path: string; name: string }[];
  allowed_actions: { action: string; description: string }[];
}

export interface ChatHealthResponse {
  enabled: boolean;
  provider: {
    status: string;
    provider: string;
    model?: string;
    [key: string]: unknown;
  };
  sessions: {
    total_sessions: number;
    unique_users: number;
  };
  config: {
    provider_type: string;
    max_history: number;
  };
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  actions?: ChatAction[];
  suggestions?: string[];
  isLoading?: boolean;
}

// ============================================================================
// Helper Functions
// ============================================================================

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('filevault_access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function handleResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  let data;
  
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`Invalid JSON response: ${text}`);
  }
  
  if (!response.ok) {
    if (response.status === 503) {
      throw new Error('Chatbot is currently disabled');
    }
    // Handle token expiration - trigger logout
    if (response.status === 401 || 
        (data?.detail && typeof data.detail === 'string' && 
         (data.detail.toLowerCase().includes('expired') || 
          data.detail.toLowerCase().includes('invalid token')))) {
      // Dispatch custom event to trigger logout
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth:session-expired'));
      }
      throw new Error('Session expired. Please log in again.');
    }
    throw new Error(data?.detail || data?.message || `API Error: ${response.status}`);
  }
  
  return data;
}

// ============================================================================
// Chat API
// ============================================================================

export const chatApi = {
  /**
   * Check if chatbot is enabled and healthy
   */
  async health(): Promise<ChatHealthResponse> {
    const response = await fetch(`${API_BASE}/health`, {
      method: 'GET',
      headers: { ...getAuthHeaders() },
    });
    return handleResponse<ChatHealthResponse>(response);
  },

  /**
   * Send a message to the chatbot
   */
  async sendMessage(message: string, sessionId?: string): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
      }),
    });
    return handleResponse<ChatResponse>(response);
  },

  /**
   * Get initial suggestions for the user
   */
  async getSuggestions(): Promise<SuggestionsResponse> {
    const response = await fetch(`${API_BASE}/suggestions`, {
      method: 'GET',
      headers: { ...getAuthHeaders() },
    });
    return handleResponse<SuggestionsResponse>(response);
  },

  /**
   * End a chat session
   */
  async endSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/session/${sessionId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() },
    });
    await handleResponse<{ status: string }>(response);
  },

  /**
   * Get session history
   */
  async getHistory(sessionId: string): Promise<{ session_id: string; history: unknown[] }> {
    const response = await fetch(`${API_BASE}/session/${sessionId}/history`, {
      method: 'GET',
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(response);
  },

  /**
   * Create WebSocket connection for real-time chat
   */
  createWebSocket(): WebSocket | null {
    const token = localStorage.getItem('filevault_access_token');
    if (!token) {
      console.error('No auth token for WebSocket');
      return null;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = API_ORIGIN.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/chat/ws?token=${encodeURIComponent(token)}`;

    try {
      return new WebSocket(wsUrl);
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      return null;
    }
  },
};

// ============================================================================
// WebSocket Hook Types
// ============================================================================

export interface WebSocketMessage {
  type: 'connected' | 'typing' | 'response' | 'error' | 'pong' | 'session_ended';
  message?: string;
  suggestions?: string[];
  session_id?: string;
  data?: ChatMessageResponse;
}
