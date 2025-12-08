"use client";

import React, { useState, useEffect } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { filesApi } from '@/lib/api';

// ============================================================================
// Icons
// ============================================================================

const Icons = {
  X: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  Download: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
  Trash: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  ),
  ChevronLeft: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
  ),
  ChevronRight: ({ className = "w-6 h-6" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
  File: ({ className = "w-16 h-16" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  Spinner: ({ className = "w-8 h-8" }: { className?: string }) => (
    <svg className={`${className} animate-spin`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  ),
  ZoomIn: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
    </svg>
  ),
  ZoomOut: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
    </svg>
  ),
};

// ============================================================================
// Types
// ============================================================================

export interface PreviewFile {
  id: string;
  name: string;
  type: string;
  size: number;
  contentType: string;
  downloadUrl?: string;
  status: 'clean' | 'scanning' | 'quarantined';
}

interface FilePreviewModalProps {
  file: PreviewFile | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete?: (fileId: string) => void;
  onDownload?: (fileId: string, filename: string) => void;
  files?: PreviewFile[]; // For navigation between files
  canDelete?: boolean;
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function getFileCategory(contentType: string, filename: string): 'image' | 'video' | 'pdf' | 'text' | 'audio' | 'other' {
  if (contentType.startsWith('image/')) return 'image';
  if (contentType.startsWith('video/')) return 'video';
  if (contentType.startsWith('audio/')) return 'audio';
  if (contentType === 'application/pdf') return 'pdf';
  if (contentType.startsWith('text/') || 
      ['json', 'xml', 'js', 'ts', 'jsx', 'tsx', 'css', 'html', 'md', 'py', 'java', 'c', 'cpp', 'h'].some(ext => 
        filename.toLowerCase().endsWith(`.${ext}`)
      )) return 'text';
  return 'other';
}

// ============================================================================
// Image Preview Component
// ============================================================================

function ImagePreview({ url, filename }: { url: string; filename: string }) {
  const [zoom, setZoom] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  return (
    <div className="relative flex-1 flex items-center justify-center overflow-hidden bg-black/50">
      {loading && !error && (
        <div className="absolute inset-0 flex items-center justify-center">
          <Icons.Spinner className="w-12 h-12 text-white" />
        </div>
      )}
      {error ? (
        <div className="text-center text-white">
          <Icons.File className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <p>Failed to load image</p>
        </div>
      ) : (
        <img
          src={url}
          alt={filename}
          className="max-h-full max-w-full object-contain transition-transform duration-200"
          style={{ transform: `scale(${zoom})` }}
          onLoad={() => setLoading(false)}
          onError={() => { setLoading(false); setError(true); }}
        />
      )}
      
      {/* Zoom Controls */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-black/70 rounded-full px-4 py-2">
        <button
          onClick={() => setZoom(z => Math.max(0.5, z - 0.25))}
          className="p-1 text-white hover:text-gray-300 transition-colors"
          disabled={zoom <= 0.5}
        >
          <Icons.ZoomOut />
        </button>
        <span className="text-white text-sm min-w-[60px] text-center">{Math.round(zoom * 100)}%</span>
        <button
          onClick={() => setZoom(z => Math.min(3, z + 0.25))}
          className="p-1 text-white hover:text-gray-300 transition-colors"
          disabled={zoom >= 3}
        >
          <Icons.ZoomIn />
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Video Preview Component
// ============================================================================

function VideoPreview({ url, contentType }: { url: string; contentType: string }) {
  return (
    <div className="flex-1 flex items-center justify-center bg-black">
      <video
        controls
        className="max-h-full max-w-full"
        autoPlay={false}
      >
        <source src={url} type={contentType} />
        Your browser does not support video playback.
      </video>
    </div>
  );
}

// ============================================================================
// Audio Preview Component
// ============================================================================

function AudioPreview({ url, contentType, filename }: { url: string; contentType: string; filename: string }) {
  const { isDark } = useTheme();
  
  return (
    <div className={`flex-1 flex flex-col items-center justify-center p-8 ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
      <Icons.File className={`w-24 h-24 mb-6 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
      <p className={`text-lg font-medium mb-6 ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>{filename}</p>
      <audio controls className="w-full max-w-md">
        <source src={url} type={contentType} />
        Your browser does not support audio playback.
      </audio>
    </div>
  );
}

// ============================================================================
// PDF Preview Component
// ============================================================================

function PDFPreview({ url, filename }: { url: string; filename: string }) {
  const [loading, setLoading] = useState(true);

  return (
    <div className="flex-1 flex flex-col bg-gray-900">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
          <Icons.Spinner className="w-12 h-12 text-white" />
        </div>
      )}
      <iframe
        src={`${url}#toolbar=1&navpanes=0`}
        title={filename}
        className="flex-1 w-full"
        onLoad={() => setLoading(false)}
      />
    </div>
  );
}

// ============================================================================
// Text Preview Component
// ============================================================================

function TextPreview({ url, filename }: { url: string; filename: string }) {
  const { isDark } = useTheme();
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchContent = async () => {
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch');
        const text = await response.text();
        setContent(text);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    fetchContent();
  }, [url]);

  if (loading) {
    return (
      <div className={`flex-1 flex items-center justify-center ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
        <Icons.Spinner className={`w-12 h-12 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex-1 flex items-center justify-center ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
        <div className="text-center">
          <Icons.File className={`w-16 h-16 mx-auto mb-4 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
          <p className={isDark ? 'text-gray-400' : 'text-gray-500'}>Failed to load file content</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex-1 overflow-auto ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      <pre className={`p-6 text-sm font-mono whitespace-pre-wrap break-words ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
        {content}
      </pre>
    </div>
  );
}

// ============================================================================
// Other File Preview Component
// ============================================================================

function OtherFilePreview({ file, onDownload }: { file: PreviewFile; onDownload?: () => void }) {
  const { isDark } = useTheme();

  return (
    <div className={`flex-1 flex flex-col items-center justify-center p-8 ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
      <Icons.File className={`w-24 h-24 mb-6 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
      <p className={`text-lg font-medium mb-2 ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>{file.name}</p>
      <p className={`text-sm mb-6 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
        {file.contentType} • {formatBytes(file.size)}
      </p>
      <p className={`text-sm mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
        Preview not available for this file type
      </p>
      {onDownload && (
        <button
          onClick={onDownload}
          className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
        >
          <Icons.Download />
          Download File
        </button>
      )}
    </div>
  );
}

// ============================================================================
// Delete Confirmation Modal
// ============================================================================

function DeleteConfirmModal({ 
  isOpen, 
  filename, 
  onConfirm, 
  onCancel 
}: { 
  isOpen: boolean; 
  filename: string; 
  onConfirm: () => void; 
  onCancel: () => void;
}) {
  const { isDark } = useTheme();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={onCancel} />
      <div className={`relative w-full max-w-md rounded-2xl p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <h3 className={`text-lg font-bold mb-2 ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
          Delete File?
        </h3>
        <p className={`mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Are you sure you want to delete <strong>{filename}</strong>? This action cannot be undone.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className={`flex-1 px-4 py-2.5 rounded-xl font-medium border transition-colors ${
              isDark 
                ? 'border-gray-600 text-gray-300 hover:bg-gray-700' 
                : 'border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main File Preview Modal Component
// ============================================================================

export default function FilePreviewModal({
  file,
  isOpen,
  onClose,
  onDelete,
  onDownload,
  files = [],
  canDelete = true,
}: FilePreviewModalProps) {
  const { isDark } = useTheme();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Get current file index for navigation
  const currentIndex = files.findIndex(f => f.id === file?.id);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < files.length - 1;

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft' && hasPrev) {
        // Navigate to previous - handled by parent
      }
      if (e.key === 'ArrowRight' && hasNext) {
        // Navigate to next - handled by parent
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, hasPrev, hasNext, onClose]);

  if (!isOpen || !file) return null;

  const fileCategory = getFileCategory(file.contentType, file.name);
  const downloadUrl = file.downloadUrl || filesApi.getDownloadUrl(file.id);

  const handleDownload = async () => {
    if (downloading) return;
    setDownloading(true);
    try {
      if (onDownload) {
        await onDownload(file.id, file.name);
      } else {
        await filesApi.download(file.id, file.name);
      }
    } catch (error) {
      console.error('Download failed:', error);
    } finally {
      setDownloading(false);
    }
  };

  const handleDelete = async () => {
    if (deleting || !onDelete) return;
    setDeleting(true);
    try {
      await onDelete(file.id);
      setShowDeleteConfirm(false);
      onClose();
    } catch (error) {
      console.error('Delete failed:', error);
    } finally {
      setDeleting(false);
    }
  };

  const renderPreview = () => {
    if (file.status === 'quarantined') {
      return (
        <div className={`flex-1 flex flex-col items-center justify-center p-8 ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
          <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center mb-6">
            <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className={`text-lg font-medium mb-2 ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>
            File Quarantined
          </p>
          <p className={`text-sm text-center max-w-md ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            This file has been quarantined due to a potential security threat. Preview and download are disabled.
          </p>
        </div>
      );
    }

    switch (fileCategory) {
      case 'image':
        return <ImagePreview url={downloadUrl} filename={file.name} />;
      case 'video':
        return <VideoPreview url={downloadUrl} contentType={file.contentType} />;
      case 'audio':
        return <AudioPreview url={downloadUrl} contentType={file.contentType} filename={file.name} />;
      case 'pdf':
        return <PDFPreview url={downloadUrl} filename={file.name} />;
      case 'text':
        return <TextPreview url={downloadUrl} filename={file.name} />;
      default:
        return <OtherFilePreview file={file} onDownload={handleDownload} />;
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-50 flex flex-col">
        {/* Backdrop */}
        <div className="absolute inset-0 bg-black/90" onClick={onClose} />

        {/* Header */}
        <div className={`relative z-10 flex items-center justify-between px-4 py-3 ${isDark ? 'bg-gray-900/95' : 'bg-white/95'} backdrop-blur-sm`}>
          <div className="flex items-center gap-4 min-w-0">
            <button
              onClick={onClose}
              className={`p-2 rounded-lg transition-colors ${isDark ? 'hover:bg-gray-800 text-gray-400 hover:text-white' : 'hover:bg-gray-100 text-gray-500 hover:text-gray-900'}`}
            >
              <Icons.X />
            </button>
            <div className="min-w-0">
              <h2 className={`font-medium truncate ${isDark ? 'text-white' : 'text-gray-900'}`}>{file.name}</h2>
              <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                {formatBytes(file.size)} • {file.contentType}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {file.status !== 'quarantined' && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  isDark 
                    ? 'bg-gray-800 text-white hover:bg-gray-700' 
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {downloading ? <Icons.Spinner className="w-5 h-5" /> : <Icons.Download />}
                Download
              </button>
            )}
            {canDelete && onDelete && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className={`p-2 rounded-lg transition-colors ${
                  isDark 
                    ? 'text-red-400 hover:bg-red-900/30' 
                    : 'text-red-600 hover:bg-red-50'
                }`}
              >
                <Icons.Trash />
              </button>
            )}
          </div>
        </div>

        {/* Preview Area */}
        <div className="relative flex-1 flex">
          {renderPreview()}
        </div>

        {/* File Info Footer */}
        <div className={`relative z-10 px-4 py-2 text-center text-sm ${isDark ? 'bg-gray-900/95 text-gray-500' : 'bg-white/95 text-gray-500'}`}>
          {files.length > 1 && (
            <span>{currentIndex + 1} of {files.length} files</span>
          )}
        </div>
      </div>

      {/* Delete Confirmation */}
      <DeleteConfirmModal
        isOpen={showDeleteConfirm}
        filename={file.name}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </>
  );
}
