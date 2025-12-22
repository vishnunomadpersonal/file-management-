"use client";

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth, formatBytes } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { filesApi, foldersApi, ApiFile, ApiFolder } from '@/lib/api';
import FilePreviewModal, { PreviewFile } from '@/components/FilePreviewModal';

// ============================================================================
// Icons
// ============================================================================

const Icons = {
  Upload: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
    </svg>
  ),
  Folder: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  ),
  FolderOpen: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
    </svg>
  ),
  FolderPlus: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
    </svg>
  ),
  ChevronRight: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
  Home: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  ),
  Grid: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  ),
  List: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
    </svg>
  ),
  Filter: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
    </svg>
  ),
  Search: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  MoreVertical: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
    </svg>
  ),
  Download: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
  Trash: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  ),
  Share: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
    </svg>
  ),
  Check: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  X: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  File: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  Image: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  Video: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  ),
  Cloud: ({ className = "w-10 h-10" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
  ),
  Shield: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  AlertTriangle: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
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
  Building2: ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
    </svg>
  ),
};

// ============================================================================
// Types
// ============================================================================

interface FileItem {
  id: string;
  name: string;
  type: 'folder' | 'pdf' | 'image' | 'video' | 'spreadsheet' | 'document' | 'archive' | 'other';
  size?: number;
  modified: string;
  status: 'clean' | 'scanning' | 'quarantined';
  shared?: boolean;
  contentType?: string;
  downloadUrl?: string;
  folderId?: string | null;
  organizationName?: string | null;
}

interface BreadcrumbItem {
  id: string | null;
  name: string;
}

// ============================================================================
// File Icon Component
// ============================================================================

function FileIcon({ type, className = "w-10 h-10" }: { type: FileItem['type']; className?: string }) {
  const iconColors: Record<FileItem['type'], string> = {
    folder: 'text-amber-500',
    pdf: 'text-red-500',
    image: 'text-blue-500',
    video: 'text-purple-500',
    spreadsheet: 'text-emerald-500',
    document: 'text-indigo-500',
    archive: 'text-gray-500',
    other: 'text-gray-400',
  };

  if (type === 'folder') {
    return <Icons.Folder className={`${className} ${iconColors[type]}`} />;
  }
  if (type === 'image') {
    return <Icons.Image className={`${className} ${iconColors[type]}`} />;
  }
  if (type === 'video') {
    return <Icons.Video className={`${className} ${iconColors[type]}`} />;
  }
  return <Icons.File className={`${className} ${iconColors[type]}`} />;
}

// ============================================================================
// Upload Dropzone
// ============================================================================

function UploadDropzone({ 
  isOpen, 
  onClose, 
  onUpload,
  currentFolderId
}: { 
  isOpen: boolean; 
  onClose: () => void; 
  onUpload: (files: File[]) => void;
  currentFolderId: string | null;
}) {
  const { isDark } = useTheme();
  const { user } = useAuth();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadingFiles, setUploadingFiles] = useState<{name: string; progress: number; status: string}[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    await uploadFiles(files);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    await uploadFiles(files);
  };

  const uploadFiles = async (files: File[]) => {
    if (files.length === 0 || !user?.id) return;
    
    setUploading(true);
    setUploadProgress(0);
    setUploadingFiles(files.map(f => ({ name: f.name, progress: 0, status: 'uploading' })));
    
    const successfulFiles: File[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      try {
        // Update individual file progress
        setUploadingFiles(prev => prev.map((f, idx) => 
          idx === i ? { ...f, status: 'uploading' } : f
        ));
        
        // Use the real API upload with organization and folder context
        await filesApi.uploadFile(
          file, 
          user.id, 
          undefined,  // appointmentId 
          user.organization_id || undefined,  // organizationId for bucket organization
          currentFolderId || undefined,  // folderId for folder organization
          (progress: number) => {
            setUploadingFiles(prev => prev.map((f, idx) => 
              idx === i ? { ...f, progress } : f
            ));
            // Calculate overall progress
            const totalProgress = ((i * 100) + progress) / files.length;
            setUploadProgress(Math.round(totalProgress));
          }
        );
        
        setUploadingFiles(prev => prev.map((f, idx) => 
          idx === i ? { ...f, progress: 100, status: 'complete' } : f
        ));
        
        successfulFiles.push(file);
      } catch (err) {
        console.error(`Failed to upload ${file.name}:`, err);
        setUploadingFiles(prev => prev.map((f, idx) => 
          idx === i ? { ...f, status: 'error' } : f
        ));
      }
    }
    
    setUploadProgress(100);
    
    // Small delay to show completion
    await new Promise(resolve => setTimeout(resolve, 500));
    
    setUploading(false);
    setUploadingFiles([]);
    
    if (successfulFiles.length > 0) {
      onUpload(successfulFiles);
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className={`relative w-full max-w-xl rounded-2xl shadow-2xl p-8 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
          <button 
            onClick={onClose}
            className={`absolute top-4 right-4 p-2 rounded-lg ${isDark ? 'text-gray-500 hover:text-gray-300 hover:bg-gray-700' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
          >
            <Icons.X />
          </button>

          <h2 className={`text-xl font-bold mb-6 ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Upload Files</h2>

          {uploading ? (
            <div className="py-4">
              <div className="flex items-center justify-center mb-4">
                <Icons.Spinner className="w-8 h-8 text-indigo-600" />
              </div>
              <p className={`text-center mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                Uploading files...
              </p>
              
              {/* Individual file progress */}
              <div className="space-y-3 max-h-48 overflow-y-auto mb-4">
                {uploadingFiles.map((file, idx) => (
                  <div key={idx} className={`p-3 rounded-lg ${isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-sm truncate max-w-[200px] ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>
                        {file.name}
                      </span>
                      <span className={`text-xs ${
                        file.status === 'complete' ? 'text-emerald-500' : 
                        file.status === 'error' ? 'text-red-500' : 
                        (isDark ? 'text-gray-400' : 'text-gray-500')
                      }`}>
                        {file.status === 'complete' ? '✓ Done' : 
                         file.status === 'error' ? '✗ Failed' : 
                         `${file.progress}%`}
                      </span>
                    </div>
                    <div className={`w-full h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-gray-600' : 'bg-gray-200'}`}>
                      <div 
                        className={`h-full transition-all duration-300 ${
                          file.status === 'complete' ? 'bg-emerald-500' :
                          file.status === 'error' ? 'bg-red-500' :
                          'bg-indigo-500'
                        }`}
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Overall progress */}
              <div className={`w-full h-2 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
                <div 
                  className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className={`text-sm text-center mt-2 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                Overall: {uploadProgress}%
              </p>
            </div>
          ) : (
            <div
              className={`border-2 border-dashed rounded-2xl p-12 text-center transition-colors ${
                isDragging 
                  ? (isDark ? 'border-indigo-500 bg-indigo-900/30' : 'border-indigo-500 bg-indigo-50')
                  : (isDark ? 'border-gray-600 hover:border-gray-500' : 'border-gray-200 hover:border-gray-300')
              }`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              <Icons.Cloud className={`w-10 h-10 mx-auto mb-4 ${isDark ? 'text-gray-600' : 'text-gray-300'}`} />
              <p className={`mb-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                Drag and drop files here, or{' '}
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="text-indigo-500 hover:text-indigo-400 font-medium"
                >
                  browse
                </button>
              </p>
              <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                All files will be scanned for viruses before upload
              </p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>
          )}

          <div className={`mt-6 flex items-center gap-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            <Icons.Shield className="w-4 h-4 text-emerald-500" />
            <span>Files are automatically scanned with ClamAV</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// File Row (List View)
// ============================================================================

function FileRow({ 
  file, 
  selected, 
  onSelect,
  onPreview,
  onDownload,
  onDelete,
}: { 
  file: FileItem; 
  selected: boolean; 
  onSelect: () => void;
  onPreview: () => void;
  onDownload: () => void;
  onDelete?: () => void;
}) {
  const { isDark } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  const getStatusBadge = () => {
    switch (file.status) {
      case 'clean':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-emerald-700 bg-emerald-50 rounded-full">
            <Icons.Check className="w-3 h-3" />
            Clean
          </span>
        );
      case 'scanning':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-amber-700 bg-amber-50 rounded-full">
            <Icons.Spinner className="w-3 h-3" />
            Scanning
          </span>
        );
      case 'quarantined':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-700 bg-red-50 rounded-full">
            <Icons.AlertTriangle className="w-3 h-3" />
            Quarantined
          </span>
        );
    }
  };

  return (
    <tr className={`group ${isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'} ${selected ? (isDark ? 'bg-indigo-900/30' : 'bg-indigo-50') : ''}`}>
      <td className="px-4 py-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={onSelect}
          className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
        />
      </td>
      <td className="px-4 py-3">
        <div 
          className="flex items-center gap-3 cursor-pointer"
          onClick={onPreview}
        >
          <FileIcon type={file.type} className="w-8 h-8" />
          <div>
            <p className={`text-sm font-medium hover:text-indigo-600 transition-colors ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{file.name}</p>
            {file.shared && (
              <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Shared</span>
            )}
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <Icons.Building2 className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
          <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            {file.organizationName || 'No Organization'}
          </span>
        </div>
      </td>
      <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        {file.size ? formatBytes(file.size) : '—'}
      </td>
      <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        {file.modified}
      </td>
      <td className="px-4 py-3">
        {getStatusBadge()}
      </td>
      <td className="px-4 py-3">
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className={`p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity ${isDark ? 'text-gray-500 hover:text-gray-300 hover:bg-gray-700' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
          >
            <Icons.MoreVertical />
          </button>
          
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className={`absolute right-0 top-full mt-1 w-48 rounded-xl shadow-xl border py-2 z-20 ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
                <button 
                  onClick={() => { onPreview(); setMenuOpen(false); }}
                  className={`w-full flex items-center gap-3 px-4 py-2 text-sm ${isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-50'}`}
                >
                  <Icons.Eye className="w-4 h-4" />
                  Preview
                </button>
                <button 
                  onClick={() => { onDownload(); setMenuOpen(false); }}
                  className={`w-full flex items-center gap-3 px-4 py-2 text-sm ${isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-50'}`}
                >
                  <Icons.Download />
                  Download
                </button>
                {onDelete && (
                  <button 
                    onClick={() => { 
                      if (confirm(`Delete "${file.name}"? This cannot be undone.`)) {
                        onDelete(); 
                      }
                      setMenuOpen(false); 
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-2 text-sm ${isDark ? 'text-red-400 hover:bg-red-900/30' : 'text-red-600 hover:bg-red-50'}`}
                  >
                    <Icons.Trash />
                    Delete
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

// ============================================================================
// File Grid Card
// ============================================================================

function FileCard({ 
  file, 
  selected, 
  onSelect,
  onPreview,
}: { 
  file: FileItem; 
  selected: boolean; 
  onSelect: () => void;
  onPreview: () => void;
}) {
  const { isDark } = useTheme();
  
  return (
    <div 
      className={`group relative p-4 rounded-xl border transition-all cursor-pointer ${
        isDark 
          ? (selected 
              ? 'bg-gray-800 border-indigo-500 ring-2 ring-indigo-500/30' 
              : 'bg-gray-800 border-gray-700 hover:border-gray-600 hover:shadow-lg')
          : (selected 
              ? 'bg-white border-indigo-500 ring-2 ring-indigo-100' 
              : 'bg-white border-gray-100 hover:border-gray-200 hover:shadow-md')
      }`}
      onClick={onPreview}
    >
      <div className="absolute top-3 right-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={onSelect}
          onClick={(e) => e.stopPropagation()}
          className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity"
        />
      </div>
      
      <div className="flex flex-col items-center text-center">
        <FileIcon type={file.type} className="w-12 h-12 mb-3" />
        <p className={`text-sm font-medium truncate w-full ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>{file.name}</p>
        <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
          {file.size ? formatBytes(file.size) : file.modified}
        </p>
        
        {file.status === 'quarantined' && (
          <span className="mt-2 inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-700 bg-red-50 rounded-full">
            <Icons.AlertTriangle className="w-3 h-3" />
            Quarantined
          </span>
        )}
        
        {file.status === 'scanning' && (
          <span className="mt-2 inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-amber-700 bg-amber-50 rounded-full">
            <Icons.Spinner className="w-3 h-3" />
            Scanning
          </span>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Files Page
// ============================================================================

export default function FilesPage() {
  const { currentOrg, user } = useAuth();
  const { isDark } = useTheme();
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [showUpload, setShowUpload] = useState(false);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Folder navigation state
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [folders, setFolders] = useState<ApiFolder[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([{ id: null, name: 'My Files' }]);
  const [showNewFolderDialog, setShowNewFolderDialog] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [creatingFolder, setCreatingFolder] = useState(false);
  
  // Preview modal state
  const [previewFile, setPreviewFile] = useState<PreviewFile | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  // Role-based permissions
  const canUpload = ['user', 'manager', 'org_admin', 'super_admin'].includes(user?.role || '');
  const canDelete = ['manager', 'org_admin', 'super_admin'].includes(user?.role || '');
  const canShare = ['manager', 'org_admin', 'super_admin'].includes(user?.role || '');
  const isViewer = user?.role === 'viewer';

  // Fetch folders from API
  const fetchFolders = useCallback(async () => {
    try {
      const apiFolders = await foldersApi.list(currentFolderId);
      setFolders(apiFolders);
    } catch (err) {
      console.error('Failed to fetch folders:', err);
      setFolders([]);
    }
  }, [currentFolderId]);

  // Fetch files from API
  const fetchFiles = useCallback(async () => {
    if (!user?.id) return;
    
    setLoading(true);
    setError(null);
    try {
      // Fetch both folders and files
      await fetchFolders();
      
      const apiFiles = await filesApi.list(user.id);
      // Filter files by current folder
      const filteredApiFiles = apiFiles.filter(f => 
        (f.folder_id || null) === currentFolderId
      );
      
      const mappedFiles: FileItem[] = filteredApiFiles.map(f => ({
        id: f.id,
        name: f.filename,
        type: getFileType(f.filename),
        size: f.size,
        modified: f.created_at ? new Date(f.created_at).toLocaleDateString() : 'Unknown',
        status: f.is_quarantined ? 'quarantined' : (f.virus_scan_status === 'scanning' || f.virus_scan_status === 'pending' ? 'scanning' : 'clean'),
        contentType: f.content_type,
        downloadUrl: f.download_url,
        folderId: f.folder_id,
        organizationName: f.organization_name,
      }));
      setFiles(mappedFiles);
    } catch (err) {
      console.error('Failed to fetch files:', err);
      setError('Failed to load files. Please try again.');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }, [user?.id, currentFolderId, fetchFolders]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  // Navigate to folder
  const navigateToFolder = async (folder: ApiFolder) => {
    setCurrentFolderId(folder.id);
    // Build breadcrumbs from folder path
    const pathParts = folder.path.split('/').filter(Boolean);
    const newBreadcrumbs: BreadcrumbItem[] = [{ id: null, name: 'My Files' }];
    
    // We need to get parent folders - for now we'll build from path
    let currentPath = '';
    for (let i = 0; i < pathParts.length - 1; i++) {
      currentPath += '/' + pathParts[i];
      // In a real implementation, we'd fetch folder IDs from path
      newBreadcrumbs.push({ id: `path-${i}`, name: pathParts[i] });
    }
    newBreadcrumbs.push({ id: folder.id, name: folder.name });
    setBreadcrumbs(newBreadcrumbs);
  };

  // Navigate to breadcrumb
  const navigateToBreadcrumb = (item: BreadcrumbItem, index: number) => {
    setCurrentFolderId(item.id);
    setBreadcrumbs(prev => prev.slice(0, index + 1));
  };

  // Create new folder
  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    
    setCreatingFolder(true);
    try {
      await foldersApi.create({
        name: newFolderName.trim(),
        parent_id: currentFolderId,
      });
      setNewFolderName('');
      setShowNewFolderDialog(false);
      await fetchFolders();
    } catch (err) {
      console.error('Failed to create folder:', err);
      alert('Failed to create folder. Please try again.');
    } finally {
      setCreatingFolder(false);
    }
  };

  // Delete folder
  const handleDeleteFolder = async (folderId: string) => {
    if (!confirm('Delete this folder? This cannot be undone.')) return;
    
    try {
      await foldersApi.delete(folderId);
      await fetchFolders();
    } catch (err: unknown) {
      console.error('Failed to delete folder:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      if (errorMessage.includes('not empty') || errorMessage.includes('subfolders') || errorMessage.includes('files')) {
        alert('Cannot delete folder - it contains files or subfolders. Move or delete them first.');
      } else {
        alert('Failed to delete folder. Please try again.');
      }
    }
  };

  const filteredFiles = files.filter(file => 
    file.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedFiles(newSelected);
  };

  const selectAll = () => {
    if (selectedFiles.size === filteredFiles.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(filteredFiles.map(f => f.id)));
    }
  };

  // Handle file preview
  const handlePreview = (file: FileItem) => {
    const previewData: PreviewFile = {
      id: file.id,
      name: file.name,
      type: file.type,
      size: file.size || 0,
      contentType: file.contentType || 'application/octet-stream',
      downloadUrl: file.downloadUrl,
      status: file.status,
    };
    setPreviewFile(previewData);
    setShowPreview(true);
  };

  // Handle file download
  const handleDownload = async (fileId: string, filename: string) => {
    try {
      await filesApi.download(fileId, filename);
    } catch (err) {
      console.error('Download failed:', err);
      alert('Failed to download file. Please try again.');
    }
  };

  // Handle bulk download
  const handleBulkDownload = async () => {
    for (const fileId of selectedFiles) {
      const file = files.find(f => f.id === fileId);
      if (file) {
        await handleDownload(file.id, file.name);
      }
    }
  };

  // Handle file delete
  const handleDelete = async (fileId: string) => {
    try {
      await filesApi.delete(fileId);
      setFiles(prev => prev.filter(f => f.id !== fileId));
      setSelectedFiles(prev => {
        const next = new Set(prev);
        next.delete(fileId);
        return next;
      });
      // Close preview if deleted file was being previewed
      if (previewFile?.id === fileId) {
        setShowPreview(false);
        setPreviewFile(null);
      }
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete file. Please try again.');
    }
  };

  // Handle bulk delete
  const handleBulkDelete = async () => {
    if (!confirm(`Delete ${selectedFiles.size} file(s)? This cannot be undone.`)) return;
    
    for (const fileId of selectedFiles) {
      try {
        await filesApi.delete(fileId);
      } catch (err) {
        console.error(`Failed to delete file ${fileId}:`, err);
      }
    }
    setFiles(prev => prev.filter(f => !selectedFiles.has(f.id)));
    setSelectedFiles(new Set());
  };

  // Handle upload completion
  const handleUploadComplete = async (uploadedFiles: File[]) => {
    // Add files as "scanning" status immediately
    const newFiles: FileItem[] = uploadedFiles.map((file, i) => ({
      id: `temp-${Date.now()}-${i}`,
      name: file.name,
      type: getFileType(file.name),
      size: file.size,
      modified: 'Just now',
      status: 'scanning' as const,
      contentType: file.type,
    }));
    
    setFiles(prev => [...newFiles, ...prev]);
    
    // Refresh files list after upload to get real data
    setTimeout(() => {
      fetchFiles();
    }, 2000);
  };

  // Get preview files for navigation
  const previewFiles: PreviewFile[] = filteredFiles.map(f => ({
    id: f.id,
    name: f.name,
    type: f.type,
    size: f.size || 0,
    contentType: f.contentType || 'application/octet-stream',
    downloadUrl: f.downloadUrl,
    status: f.status,
  }));

  return (
    <div className="space-y-6">
      {/* Viewer Notice */}
      {isViewer && (
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-amber-900/20 border-amber-800 text-amber-300' : 'bg-amber-50 border-amber-200 text-amber-800'}`}>
          <div className="flex items-center gap-3">
            <Icons.Eye className="w-5 h-5" />
            <div>
              <p className="font-medium">View-Only Mode</p>
              <p className={`text-sm ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                You can view and download files, but cannot upload or modify them.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Files</h1>
          <p className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            {isViewer ? 'View' : 'Manage'} files for {currentOrg?.name}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {canUpload && (
            <>
              <button
                onClick={() => setShowNewFolderDialog(true)}
                className={`flex items-center gap-2 px-4 py-2.5 border rounded-xl font-medium transition-colors ${isDark ? 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}`}
              >
                <Icons.FolderPlus />
                New Folder
              </button>
              <button
                onClick={() => setShowUpload(true)}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
              >
                <Icons.Upload />
                Upload Files
              </button>
            </>
          )}
        </div>
      </div>

      {/* Breadcrumb Navigation */}
      <div className={`flex items-center gap-1 px-4 py-3 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-gray-50 border-gray-200'}`}>
        {breadcrumbs.map((item, index) => (
          <React.Fragment key={item.id || 'root'}>
            {index > 0 && (
              <Icons.ChevronRight className={`w-4 h-4 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
            )}
            <button
              onClick={() => navigateToBreadcrumb(item, index)}
              className={`flex items-center gap-2 px-2 py-1 rounded-lg text-sm font-medium transition-colors ${
                index === breadcrumbs.length - 1
                  ? (isDark ? 'text-gray-100' : 'text-gray-900')
                  : (isDark ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-200')
              }`}
            >
              {index === 0 && <Icons.Home className="w-4 h-4" />}
              {item.name}
            </button>
          </React.Fragment>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        {/* Search */}
        <div className={`flex-1 flex items-center gap-2 px-4 py-2.5 border rounded-xl ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
          <Icons.Search className={`w-5 h-5 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
          <input
            type="text"
            placeholder="Search files and folders..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`flex-1 bg-transparent border-none outline-none text-sm ${isDark ? 'text-gray-100 placeholder-gray-500' : 'text-gray-600 placeholder-gray-400'}`}
          />
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-2">
          <button 
            onClick={fetchFiles}
            className={`flex items-center gap-2 px-4 py-2.5 border rounded-xl text-sm transition-colors ${isDark ? 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}`}
          >
            <Icons.Filter />
            Refresh
          </button>
          
          <div className={`flex items-center border rounded-xl overflow-hidden ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2.5 ${viewMode === 'list' ? (isDark ? 'bg-gray-700 text-indigo-400' : 'bg-gray-100 text-indigo-600') : (isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600')}`}
            >
              <Icons.List />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2.5 ${viewMode === 'grid' ? (isDark ? 'bg-gray-700 text-indigo-400' : 'bg-gray-100 text-indigo-600') : (isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600')}`}
            >
              <Icons.Grid />
            </button>
          </div>
        </div>
      </div>

      {/* Selection bar */}
      {selectedFiles.size > 0 && (
        <div className={`flex items-center justify-between p-4 rounded-xl border ${isDark ? 'bg-indigo-900/30 border-indigo-800' : 'bg-indigo-50 border-indigo-100'}`}>
          <span className={`text-sm font-medium ${isDark ? 'text-indigo-300' : 'text-indigo-700'}`}>
            {selectedFiles.size} file{selectedFiles.size > 1 ? 's' : ''} selected
          </span>
          <div className="flex items-center gap-2">
            <button 
              onClick={handleBulkDownload}
              className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${isDark ? 'text-indigo-300 hover:bg-indigo-900/50' : 'text-indigo-700 hover:bg-indigo-100'}`}
            >
              <Icons.Download />
              Download
            </button>
            {canDelete && (
              <button 
                onClick={handleBulkDelete}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${isDark ? 'text-red-400 hover:bg-red-900/30' : 'text-red-600 hover:bg-red-50'}`}
              >
                <Icons.Trash />
                Delete
              </button>
            )}
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Icons.Spinner className="w-8 h-8 text-indigo-600" />
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className={`p-4 rounded-xl border ${isDark ? 'bg-red-900/20 border-red-800 text-red-300' : 'bg-red-50 border-red-200 text-red-700'}`}>
          {error}
        </div>
      )}

      {/* File List/Grid */}
      {!loading && (
        <>
          {viewMode === 'list' ? (
            <div className={`rounded-2xl border shadow-sm overflow-hidden ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
              <table className="w-full">
                <thead>
                  <tr className={`border-b ${isDark ? 'border-gray-700 bg-gray-700/50' : 'border-gray-100 bg-gray-50'}`}>
                    <th className="px-4 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={selectedFiles.size === filteredFiles.length && filteredFiles.length > 0}
                        onChange={selectAll}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                    </th>
                    <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Name</th>
                    <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Organization</th>
                    <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Size</th>
                    <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Modified</th>
                    <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Status</th>
                    <th className="px-4 py-3 w-20"></th>
                  </tr>
                </thead>
                <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-50'}`}>
                  {/* Folders first */}
                  {folders.filter(f => f.name.toLowerCase().includes(searchQuery.toLowerCase())).map((folder) => (
                    <tr 
                      key={`folder-${folder.id}`}
                      className={`group cursor-pointer ${isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}`}
                      onDoubleClick={() => navigateToFolder(folder)}
                    >
                      <td className="px-4 py-3">
                        {/* Empty checkbox space for folders */}
                      </td>
                      <td className="px-4 py-3">
                        <div 
                          className="flex items-center gap-3"
                          onClick={() => navigateToFolder(folder)}
                        >
                          <Icons.Folder className="w-8 h-8 text-amber-500" />
                          <div>
                            <p className={`text-sm font-medium hover:text-indigo-600 transition-colors ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                              {folder.name}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Icons.Building2 className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                          <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>—</span>
                        </div>
                      </td>
                      <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        —
                      </td>
                      <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {new Date(folder.updated_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${isDark ? 'text-gray-300 bg-gray-700' : 'text-gray-600 bg-gray-100'}`}>
                          Folder
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {canDelete && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id); }}
                            className={`p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity ${isDark ? 'text-red-400 hover:bg-red-900/30' : 'text-red-500 hover:bg-red-50'}`}
                          >
                            <Icons.Trash />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {/* Then files */}
                  {filteredFiles.map((file) => (
                    <FileRow
                      key={file.id}
                      file={file}
                      selected={selectedFiles.has(file.id)}
                      onSelect={() => toggleSelect(file.id)}
                      onPreview={() => handlePreview(file)}
                      onDownload={() => handleDownload(file.id, file.name)}
                      onDelete={canDelete ? () => handleDelete(file.id) : undefined}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {/* Folders first */}
              {folders.filter(f => f.name.toLowerCase().includes(searchQuery.toLowerCase())).map((folder) => (
                <div
                  key={`folder-${folder.id}`}
                  className={`group relative p-4 rounded-xl border transition-all cursor-pointer ${
                    isDark 
                      ? 'bg-gray-800 border-gray-700 hover:border-gray-600 hover:shadow-lg'
                      : 'bg-white border-gray-100 hover:border-gray-200 hover:shadow-md'
                  }`}
                  onClick={() => navigateToFolder(folder)}
                >
                  {canDelete && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id); }}
                      className={`absolute top-2 right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity ${isDark ? 'text-red-400 hover:bg-red-900/30' : 'text-red-500 hover:bg-red-50'}`}
                    >
                      <Icons.Trash className="w-3 h-3" />
                    </button>
                  )}
                  <div className="flex flex-col items-center text-center">
                    <Icons.Folder className="w-12 h-12 mb-3 text-amber-500" />
                    <p className={`text-sm font-medium truncate w-full ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                      {folder.name}
                    </p>
                    <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                      Folder
                    </p>
                  </div>
                </div>
              ))}
              {/* Then files */}
              {filteredFiles.map((file) => (
                <FileCard
                  key={file.id}
                  file={file}
                  selected={selectedFiles.has(file.id)}
                  onSelect={() => toggleSelect(file.id)}
                  onPreview={() => handlePreview(file)}
                />
              ))}
            </div>
          )}

          {/* Empty State */}
          {filteredFiles.length === 0 && folders.length === 0 && (
            <div className="text-center py-12">
              <Icons.FolderOpen className={`w-12 h-12 mx-auto mb-4 ${isDark ? 'text-gray-600' : 'text-gray-300'}`} />
              <p className={isDark ? 'text-gray-400' : 'text-gray-500'}>This folder is empty</p>
              {canUpload && (
                <div className="flex items-center justify-center gap-4 mt-4">
                  <button
                    onClick={() => setShowNewFolderDialog(true)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-600 hover:bg-gray-100'}`}
                  >
                    <Icons.FolderPlus className="w-4 h-4" />
                    Create folder
                  </button>
                  <button
                    onClick={() => setShowUpload(true)}
                    className="text-indigo-600 hover:text-indigo-700 font-medium"
                  >
                    Upload files
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* New Folder Dialog */}
      {showNewFolderDialog && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowNewFolderDialog(false)} />
          <div className="flex min-h-full items-center justify-center p-4">
            <div className={`relative w-full max-w-md rounded-2xl shadow-2xl p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
              <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                Create New Folder
              </h3>
              <input
                type="text"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="Folder name"
                className={`w-full px-4 py-3 rounded-xl border text-sm ${
                  isDark 
                    ? 'bg-gray-700 border-gray-600 text-gray-100 placeholder-gray-400 focus:border-indigo-500' 
                    : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-500'
                } focus:outline-none focus:ring-2 focus:ring-indigo-500/20`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newFolderName.trim()) {
                    handleCreateFolder();
                  }
                }}
                autoFocus
              />
              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={() => { setShowNewFolderDialog(false); setNewFolderName(''); }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium ${isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-600 hover:bg-gray-100'}`}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateFolder}
                  disabled={!newFolderName.trim() || creatingFolder}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {creatingFolder && <Icons.Spinner className="w-4 h-4" />}
                  Create Folder
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      <UploadDropzone
        isOpen={showUpload}
        onClose={() => setShowUpload(false)}
        onUpload={handleUploadComplete}
        currentFolderId={currentFolderId}
      />

      {/* Preview Modal */}
      <FilePreviewModal
        file={previewFile}
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        onDelete={canDelete ? handleDelete : undefined}
        onDownload={handleDownload}
        files={previewFiles}
        canDelete={canDelete}
      />
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function getFileType(filename: string): FileItem['type'] {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf': return 'pdf';
    case 'jpg': case 'jpeg': case 'png': case 'gif': case 'webp': return 'image';
    case 'mp4': case 'mov': case 'avi': case 'webm': return 'video';
    case 'xlsx': case 'xls': case 'csv': return 'spreadsheet';
    case 'doc': case 'docx': case 'txt': return 'document';
    case 'zip': case 'rar': case '7z': case 'tar': case 'gz': return 'archive';
    default: return 'other';
  }
}
