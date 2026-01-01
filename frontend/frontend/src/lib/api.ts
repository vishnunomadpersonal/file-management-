/**
 * API Service - Connects frontend to FastAPI backend
 */

const API_ORIGIN = (
  process.env.NEXT_PUBLIC_API_ORIGIN ||
  (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000')
).replace(/\/+$/, '');

const API_BASE = `${API_ORIGIN}/api/v1`;
const API_ROOT = API_ORIGIN; // For endpoints without /api/v1 prefix

// ============================================================================
// Types
// ============================================================================

export interface ApiUser {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  organization_id?: string;
  is_active?: boolean;
  is_verified?: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ApiOrganization {
  id: string;
  name: string;
  slug: string;
  email?: string;
  description?: string;
  plan: string;
  storage_quota_bytes: number;
  storage_used_bytes: number;
  max_users: number;
  max_files: number;
  features?: Record<string, boolean> | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  organization_name?: string;
  organization_id?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  role: string;
  status: 'pending' | 'approved' | 'rejected';
  organization_id?: string | null;
}

export interface SuccessResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface ApiResponse<T> {
  data?: T;
  message?: string;
  status?: string;
  success?: boolean;
}

// ============================================================================
// Helper Functions
// ============================================================================

async function handleResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  let data;
  
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`Invalid JSON response: ${text}`);
  }
  
  if (!response.ok) {
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
    // Handle FastAPI validation errors (422)
    if (response.status === 422 && data?.detail) {
      if (Array.isArray(data.detail)) {
        // Pydantic validation errors
        const messages = data.detail.map((err: { loc?: string[]; msg?: string }) => {
          const field = err.loc?.slice(-1)[0] || 'field';
          return `${field}: ${err.msg}`;
        });
        throw new Error(messages.join(', '));
      }
      throw new Error(data.detail);
    }
    throw new Error(data?.message || data?.detail || `API Error: ${response.status}`);
  }
  
  return data;
}

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('filevault_access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// ============================================================================
// Auth API
// ============================================================================

export const authApi = {
  async register(data: RegisterRequest): Promise<SuccessResponse<AuthResponse>> {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<AuthResponse>>(response);
    
    // Store tokens
    if (result.data?.access_token) {
      localStorage.setItem('filevault_access_token', result.data.access_token);
    }
    if (result.data?.refresh_token) {
      localStorage.setItem('filevault_refresh_token', result.data.refresh_token);
    }
    
    return result;
  },

  async login(data: LoginRequest): Promise<SuccessResponse<AuthResponse>> {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<AuthResponse>>(response);
    
    // Store tokens
    if (result.data?.access_token) {
      localStorage.setItem('filevault_access_token', result.data.access_token);
    }
    if (result.data?.refresh_token) {
      localStorage.setItem('filevault_refresh_token', result.data.refresh_token);
    }
    
    return result;
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { ...getAuthHeaders() },
        credentials: 'include',
      });
    } finally {
      localStorage.removeItem('filevault_access_token');
      localStorage.removeItem('filevault_refresh_token');
    }
  },

  async refreshToken(): Promise<AuthResponse> {
    const refreshToken = localStorage.getItem('filevault_refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token');
    }
    
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
      credentials: 'include',
    });
    const result = await handleResponse<AuthResponse>(response);
    
    if (result.access_token) {
      localStorage.setItem('filevault_access_token', result.access_token);
    }
    
    return result;
  },

  async getCurrentUser(): Promise<ApiUser> {
    const response = await fetch(`${API_BASE}/auth/me`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<ApiResponse<ApiUser>>(response);
    return result.data!;
  },
};

// ============================================================================
// Users API
// ============================================================================

export const usersApi = {
  async list(organizationId?: string): Promise<ApiUser[]> {
    const url = organizationId 
      ? `${API_BASE}/users/?organization_id=${organizationId}`
      : `${API_BASE}/users/`;
    const response = await fetch(url, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<ApiResponse<ApiUser[]>>(response);
    return result.data || [];
  },

  async listByOrganization(organizationId: string): Promise<ApiUser[]> {
    return this.list(organizationId);
  },

  async create(data: { name: string; email: string; password: string; role?: string; organization_id?: string }): Promise<ApiUser> {
    const response = await fetch(`${API_BASE}/users/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify(data),
      credentials: 'include',
    });
    const result = await handleResponse<ApiResponse<ApiUser>>(response);
    return result.data!;
  },

  async delete(userId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/users/${userId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    await handleResponse(response);
  },

  async updateStatus(userId: string, status: 'approved' | 'rejected' | 'pending'): Promise<ApiUser> {
    const response = await fetch(`${API_BASE}/users/${userId}/status`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ status }),
      credentials: 'include',
    });
    const result = await handleResponse<ApiResponse<ApiUser>>(response);
    return result.data!;
  },
};

// ============================================================================
// Organizations API (uses /organizations endpoint, not /api/v1/organizations)
// ============================================================================

export interface PublicOrganization {
  id: string;
  name: string;
  slug: string;
}

export const organizationsApi = {
  /**
   * List organizations for signup dropdown (public endpoint, no auth required)
   */
  async listPublic(): Promise<PublicOrganization[]> {
    const response = await fetch(`${API_ROOT}/organizations/public`, {
      credentials: 'include',
    });
    const result = await handleResponse<{ items: PublicOrganization[] }>(response);
    return result.items || [];
  },

  async list(skip = 0, limit = 50): Promise<{ items: ApiOrganization[]; total: number }> {
    const token = localStorage.getItem('filevault_access_token');
    if (!token) {
      // Return empty list if not authenticated
      return { items: [], total: 0 };
    }
    const response = await fetch(`${API_ROOT}/organizations?skip=${skip}&limit=${limit}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    return handleResponse(response);
  },

  async get(orgId: string): Promise<ApiOrganization> {
    const response = await fetch(`${API_ROOT}/organizations/${orgId}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    return handleResponse<ApiOrganization>(response);
  },

  async create(data: { name: string; slug?: string; email?: string; description?: string; plan?: string }): Promise<ApiOrganization> {
    const response = await fetch(`${API_ROOT}/organizations`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify(data),
      credentials: 'include',
    });
    return handleResponse<ApiOrganization>(response);
  },

  async update(orgId: string, data: Partial<ApiOrganization>): Promise<ApiOrganization> {
    const response = await fetch(`${API_ROOT}/organizations/${orgId}`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify(data),
      credentials: 'include',
    });
    return handleResponse<ApiOrganization>(response);
  },

  async delete(orgId: string): Promise<void> {
    const response = await fetch(`${API_ROOT}/organizations/${orgId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    await handleResponse(response);
  },

  async getStats(orgId: string): Promise<Record<string, unknown>> {
    const response = await fetch(`${API_ROOT}/organizations/${orgId}/stats`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    return handleResponse(response);
  },

  async getMembers(orgId: string): Promise<ApiUser[]> {
    const response = await fetch(`${API_ROOT}/organizations/${orgId}/members`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<{ members: ApiUser[] }>(response);
    return result.members || [];
  },

  async addMember(orgId: string, data: { email: string; role: string }): Promise<ApiUser> {
    const response = await fetch(`${API_ROOT}/organizations/${orgId}/members`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify(data),
      credentials: 'include',
    });
    return handleResponse<ApiUser>(response);
  },

  async removeMember(orgId: string, userId: string): Promise<void> {
    const response = await fetch(`${API_ROOT}/organizations/${orgId}/members/${userId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    await handleResponse(response);
  },
};

// ============================================================================
// Export all APIs
// ============================================================================

// ============================================================================
// Files API
// ============================================================================

export interface ApiFile {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  download_url?: string;
  appointment_name?: string;
  folder_id?: string | null;
  folder_name?: string | null;
  organization_id?: string | null;
  organization_name?: string | null;
  user_id?: string | null;
  user_name?: string | null;
  user_email?: string | null;
  virus_scan_status: 'pending' | 'scanning' | 'clean' | 'infected';
  is_quarantined: boolean;
  quarantine_reason?: string;
  created_at?: string;
  updated_at?: string;
}

// Folder types
export interface ApiFolder {
  id: string;
  name: string;
  parent_id: string | null;
  organization_id: string;
  created_by: string;
  path: string;
  created_at: string;
  updated_at: string;
}

export interface ApiFolderWithContents extends ApiFolder {
  child_folders: ApiFolder[];
  file_count: number;
}

export interface UploadInitResponse {
  chunk_size: number;
  upload_id: string;
}

export interface UploadChunkResponse {
  chunk_index: number;
  received: boolean;
}

// Appointment types
export interface ApiAppointment {
  id: string;
  name: string;
  description?: string;
  user_id: string;
  created_at?: string;
}

export interface AppointmentCreate {
  name: string;
  description?: string;
  user_id: string;
}

/**
 * Transform internal Docker MinIO URL to external URL
 */
function transformMinioUrl(url: string | undefined): string | undefined {
  if (!url) return url;
  return url.replace('http://minio:9000', 'http://localhost:9001');
}

// ============================================================================
// Appointments API
// ============================================================================

export const appointmentsApi = {
  /**
   * List all appointments for a user
   */
  async list(userId: string): Promise<ApiAppointment[]> {
    const response = await fetch(`${API_BASE}/appointments/?user_id=${userId}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<ApiAppointment[]>>(response);
    return result.data || [];
  },

  /**
   * Create a new appointment
   */
  async create(data: AppointmentCreate): Promise<ApiAppointment> {
    const response = await fetch(`${API_BASE}/appointments/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify(data),
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<ApiAppointment>>(response);
    return result.data!;
  },

  /**
   * Delete an appointment
   */
  async delete(appointmentId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/appointments/${appointmentId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    await handleResponse(response);
  },

  /**
   * Get or create default appointment for uploads
   */
  async getOrCreateDefault(userId: string): Promise<ApiAppointment> {
    const appointments = await this.list(userId);
    
    // Look for existing "General Uploads" appointment
    const defaultAppointment = appointments.find(a => a.name === 'General Uploads');
    if (defaultAppointment) {
      return defaultAppointment;
    }
    
    // Create default appointment
    return this.create({
      name: 'General Uploads',
      description: 'Default appointment for general file uploads',
      user_id: userId,
    });
  },
};

export const filesApi = {
  /**
   * List all files for a user
   */
  async list(userId: string): Promise<ApiFile[]> {
    const response = await fetch(`${API_BASE}/file/all?user_id=${userId}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<ApiFile[]>>(response);
    // Transform MinIO URLs from internal Docker network to external
    return (result.data || []).map(file => ({
      ...file,
      download_url: transformMinioUrl(file.download_url),
    }));
  },

  /**
   * Get files by appointment
   */
  async getByAppointment(appointmentId: string): Promise<ApiFile[]> {
    const response = await fetch(`${API_BASE}/file/appointment/${appointmentId}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<ApiFile[]>>(response);
    return (result.data || []).map(file => ({
      ...file,
      download_url: transformMinioUrl(file.download_url),
    }));
  },

  /**
   * Get single file details
   */
  async get(fileId: string): Promise<ApiFile> {
    const response = await fetch(`${API_BASE}/file/get/${fileId}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<ApiFile>>(response);
    return {
      ...result.data!,
      download_url: transformMinioUrl(result.data?.download_url),
    };
  },

  /**
   * Initialize upload - get upload_id and chunk_size
   */
  async initUpload(): Promise<UploadInitResponse> {
    const response = await fetch(`${API_BASE}/file/upload/init/`, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<UploadInitResponse>>(response);
    return result.data!;
  },

  /**
   * Upload a chunk
   */
  async uploadChunk(data: {
    uploadId: string;
    chunkIndex: number;
    chunkSize: number;
    chunk: Blob;
  }): Promise<UploadChunkResponse> {
    const formData = new FormData();
    formData.append('upload_id', data.uploadId);
    formData.append('chunk_index', data.chunkIndex.toString());
    formData.append('chunk_size', data.chunkSize.toString());
    formData.append('file', data.chunk);

    const response = await fetch(`${API_BASE}/file/upload/chunk/`, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
      body: formData,
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<UploadChunkResponse>>(response);
    return result.data!;
  },

  /**
   * Complete upload
   */
  async completeUpload(data: {
    uploadId: string;
    totalChunks: number;
    totalSize: number;
    fileExtension: string;
    contentType: string;
    appointmentId: string;
    userId: string;
    filename: string;
    organizationId?: string;
    folderId?: string;
  }): Promise<ApiFile> {
    const formData = new FormData();
    formData.append('upload_id', data.uploadId);
    formData.append('total_chunks', data.totalChunks.toString());
    formData.append('total_size', data.totalSize.toString());
    formData.append('file_extension', data.fileExtension);
    formData.append('content_type', data.contentType);
    // Only append appointment_id if it's a valid value (not empty)
    if (data.appointmentId && data.appointmentId.length > 0) {
      formData.append('appointment_id', data.appointmentId);
    }
    formData.append('user_id', data.userId);
    formData.append('filename', data.filename);
    // Add organization and folder IDs for bucket organization
    if (data.organizationId && data.organizationId.length > 0) {
      formData.append('organization_id', data.organizationId);
    }
    if (data.folderId && data.folderId.length > 0) {
      formData.append('folder_id', data.folderId);
    }

    const response = await fetch(`${API_BASE}/file/upload/complete/`, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
      body: formData,
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<ApiFile>>(response);
    return result.data!;
  },

  /**
   * Simple single-file upload (for smaller files)
   * @param file - The file to upload
   * @param userId - The user ID
   * @param appointmentId - The appointment ID (optional)
   * @param organizationId - The organization ID (optional, for bucket organization)
   * @param folderId - The folder ID (optional)
   * @param onProgress - Progress callback
   */
  async uploadFile(file: File, userId: string, appointmentId?: string, organizationId?: string, folderId?: string, onProgress?: (progress: number) => void): Promise<ApiFile> {
    // Initialize upload
    const init = await this.initUpload();
    const chunkSize = init.chunk_size;
    const totalChunks = Math.ceil(file.size / chunkSize);

    // Upload chunks
    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      const chunk = file.slice(start, end);

      await this.uploadChunk({
        uploadId: init.upload_id,
        chunkIndex: i,
        chunkSize: chunk.size,
        chunk,
      });

      if (onProgress) {
        onProgress(Math.round(((i + 1) / totalChunks) * 100));
      }
    }

    // Complete upload - use empty string for no appointment (backend will handle as null)
    const ext = file.name.split('.').pop()?.toLowerCase() || 'bin';
    return this.completeUpload({
      uploadId: init.upload_id,
      totalChunks,
      totalSize: file.size,
      fileExtension: ext,
      contentType: file.type || 'application/octet-stream',
      appointmentId: appointmentId || '',
      userId,
      filename: file.name,
      organizationId: organizationId || '',
      folderId: folderId || '',
    });
  },

  /**
   * Delete a file
   */
  async delete(fileId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/file/${fileId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    await handleResponse(response);
  },

  /**
   * Get file download URL (authenticated endpoint)
   * This URL requires authentication - user must be logged in to download
   */
  getDownloadUrl(fileId: string): string {
    // Use the authenticated download endpoint instead of presigned URLs
    // This ensures users must be logged in to download files (like Google Cloud)
    return `${API_BASE}/file/download/${fileId}`;
  },

  /**
   * Get file as Blob with authentication
   * Used for previews (images, videos, PDFs) since HTML elements can't send auth headers
   */
  async getFileBlob(fileId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE}/file/download/${fileId}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    
    if (response.status === 401) {
      throw new Error('Please log in to view this file');
    }
    
    if (response.status === 403) {
      throw new Error('You don\'t have permission to view this file');
    }
    
    if (!response.ok) {
      throw new Error('Failed to load file');
    }

    return response.blob();
  },

  /**
   * Download file directly with authentication
   * Unlike presigned URLs, this requires the user to be logged in
   */
  async download(fileId: string, filename: string): Promise<void> {
    // Use getFileBlob to fetch the file with authentication
    const blob = await this.getFileBlob(fileId);
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },

  /**
   * Generate a shareable link for a file
   * The link can be shared with anyone and expires after the specified time
   */
  async generateShareLink(fileId: string, expiresInHours: number = 24): Promise<{
    share_url: string;
    expires_in_hours: number;
    filename: string;
    file_id: string;
  }> {
    const response = await fetch(`${API_BASE}/file/share/${fileId}?expires_in_hours=${expiresInHours}`, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    
    if (response.status === 401) {
      throw new Error('Please log in to generate share links');
    }
    
    if (response.status === 403) {
      throw new Error('You don\'t have permission to share this file');
    }
    
    if (!response.ok) {
      throw new Error('Failed to generate share link');
    }

    const result = await response.json();
    return result.data;
  },

  /**
   * Get upload status
   */
  async getStatus(fileId: string): Promise<{ status: string; progress?: number }> {
    const response = await fetch(`${API_BASE}/file/status/${fileId}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<{ status: string; progress?: number }>>(response);
    return result.data!;
  },

  /**
   * List files by organization
   */
  async listByOrganization(organizationId: string, folderId?: string): Promise<ApiFile[]> {
    const params = folderId ? `?folder_id=${folderId}` : '';
    const response = await fetch(`${API_BASE}/file/organization/${organizationId}${params}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<ApiFile[]>>(response);
    return (result.data || []).map(file => ({
      ...file,
      download_url: transformMinioUrl(file.download_url),
    }));
  },

  /**
   * List all files across all organizations (for platform admin)
   */
  async listAllPlatform(skip: number = 0, limit: number = 100): Promise<ApiFile[]> {
    const response = await fetch(`${API_BASE}/file/platform/all?skip=${skip}&limit=${limit}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<SuccessResponse<ApiFile[]>>(response);
    return (result.data || []).map(file => ({
      ...file,
      download_url: transformMinioUrl(file.download_url),
    }));
  },
};

// ============================================================================
// Folders API
// ============================================================================

export const foldersApi = {
  /**
   * List folders (optionally filtered by parent)
   */
  async list(parentId?: string | null): Promise<ApiFolder[]> {
    const params = parentId ? `?parent_id=${parentId}` : '';
    const response = await fetch(`${API_ROOT}/folders${params}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<ApiFolder[]>(response);
    return result;
  },

  /**
   * Get all folders as flat list (for tree view)
   */
  async getTree(): Promise<ApiFolder[]> {
    const response = await fetch(`${API_ROOT}/folders/tree`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<ApiFolder[]>(response);
    return result;
  },

  /**
   * Get folder contents (subfolders + file count)
   */
  async getContents(folderId?: string | null): Promise<ApiFolderWithContents> {
    const params = folderId ? `?folder_id=${folderId}` : '';
    const response = await fetch(`${API_ROOT}/folders/contents${params}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<ApiFolderWithContents>(response);
    return result;
  },

  /**
   * Get single folder
   */
  async get(folderId: string): Promise<ApiFolder> {
    const response = await fetch(`${API_ROOT}/folders/${folderId}`, {
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    const result = await handleResponse<ApiFolder>(response);
    return result;
  },

  /**
   * Create folder
   */
  async create(data: { name: string; parent_id?: string | null }): Promise<ApiFolder> {
    const response = await fetch(`${API_ROOT}/folders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify(data),
      credentials: 'include',
    });
    const result = await handleResponse<ApiFolder>(response);
    return result;
  },

  /**
   * Rename folder
   */
  async rename(folderId: string, name: string): Promise<ApiFolder> {
    const response = await fetch(`${API_ROOT}/folders/${folderId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ name }),
      credentials: 'include',
    });
    const result = await handleResponse<ApiFolder>(response);
    return result;
  },

  /**
   * Move folder to new parent
   */
  async move(folderId: string, newParentId: string | null): Promise<ApiFolder> {
    const response = await fetch(`${API_ROOT}/folders/${folderId}/move`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ new_parent_id: newParentId }),
      credentials: 'include',
    });
    const result = await handleResponse<ApiFolder>(response);
    return result;
  },

  /**
   * Delete folder
   */
  async delete(folderId: string, force: boolean = false): Promise<void> {
    const params = force ? '?force=true' : '';
    const response = await fetch(`${API_ROOT}/folders/${folderId}${params}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() },
      credentials: 'include',
    });
    await handleResponse(response);
  },
};

export const api = {
  auth: authApi,
  users: usersApi,
  organizations: organizationsApi,
  files: filesApi,
  folders: foldersApi,
};

export default api;
