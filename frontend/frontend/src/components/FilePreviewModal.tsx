"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { filesApi } from '@/lib/api';

// ============================================================================
// Custom Hook for Authenticated File URL
// ============================================================================

/**
 * Hook to fetch a file with authentication and create a blob URL for preview.
 * HTML elements like <img>, <video>, <iframe> can't send auth headers,
 * so we fetch the file first, then create a blob URL.
 */
function useAuthenticatedFileUrl(fileId: string, contentType: string) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    let objectUrl: string | null = null;

    const fetchFile = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch file through authenticated endpoint
        const blob = await filesApi.getFileBlob(fileId);
        
        if (!isMounted) return;
        
        // Create a blob URL that can be used in <img>, <video>, etc.
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      } catch (err) {
        if (!isMounted) return;
        console.error('Failed to fetch file for preview:', err);
        setError(err instanceof Error ? err.message : 'Failed to load file');
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchFile();

    // Cleanup: revoke the blob URL when component unmounts
    return () => {
      isMounted = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [fileId, contentType]);

  return { blobUrl, loading, error };
}

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
  Share: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
    </svg>
  ),
  Link: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
  ),
  Check: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  Copy: ({ className = "w-5 h-5" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
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

function ImagePreview({ fileId, filename, contentType }: { fileId: string; filename: string; contentType: string }) {
  const [zoom, setZoom] = useState(1);
  const { blobUrl, loading, error } = useAuthenticatedFileUrl(fileId, contentType);

  return (
    <div className="relative flex-1 flex items-center justify-center overflow-hidden bg-black/50">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <Icons.Spinner className="w-12 h-12 text-white" />
        </div>
      )}
      {error ? (
        <div className="text-center text-white">
          <Icons.File className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <p>Failed to load image</p>
          <p className="text-sm text-gray-400 mt-2">{error}</p>
        </div>
      ) : blobUrl ? (
        <img
          src={blobUrl}
          alt={filename}
          className="max-h-full max-w-full object-contain transition-transform duration-200"
          style={{ transform: `scale(${zoom})` }}
        />
      ) : null}
      
      {/* Zoom Controls */}
      {blobUrl && (
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
      )}
    </div>
  );
}

// ============================================================================
// Video Preview Component
// ============================================================================

function VideoPreview({ fileId, contentType }: { fileId: string; contentType: string }) {
  const { blobUrl, loading, error } = useAuthenticatedFileUrl(fileId, contentType);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-black">
        <Icons.Spinner className="w-12 h-12 text-white" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-black">
        <div className="text-center text-white">
          <Icons.File className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <p>Failed to load video</p>
          <p className="text-sm text-gray-400 mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex items-center justify-center bg-black">
      {blobUrl && (
        <video
          controls
          className="max-h-full max-w-full"
          autoPlay={false}
        >
          <source src={blobUrl} type={contentType} />
          Your browser does not support video playback.
        </video>
      )}
    </div>
  );
}

// ============================================================================
// Audio Preview Component
// ============================================================================

function AudioPreview({ fileId, contentType, filename }: { fileId: string; contentType: string; filename: string }) {
  const { isDark } = useTheme();
  const { blobUrl, loading, error } = useAuthenticatedFileUrl(fileId, contentType);

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
          <p className={isDark ? 'text-gray-400' : 'text-gray-500'}>Failed to load audio</p>
          <p className="text-sm text-gray-400 mt-2">{error}</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className={`flex-1 flex flex-col items-center justify-center p-8 ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
      <Icons.File className={`w-24 h-24 mb-6 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
      <p className={`text-lg font-medium mb-6 ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>{filename}</p>
      {blobUrl && (
        <audio controls className="w-full max-w-md">
          <source src={blobUrl} type={contentType} />
          Your browser does not support audio playback.
        </audio>
      )}
    </div>
  );
}

// ============================================================================
// PDF Preview Component
// ============================================================================

function PDFPreview({ fileId, filename, contentType }: { fileId: string; filename: string; contentType: string }) {
  const { blobUrl, loading, error } = useAuthenticatedFileUrl(fileId, contentType);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-900">
        <Icons.Spinner className="w-12 h-12 text-white" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-900">
        <div className="text-center text-white">
          <Icons.File className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <p>Failed to load PDF</p>
          <p className="text-sm text-gray-400 mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-900">
      {blobUrl && (
        <iframe
          src={`${blobUrl}#toolbar=1&navpanes=0`}
          title={filename}
          className="flex-1 w-full"
        />
      )}
    </div>
  );
}

// ============================================================================
// Text Preview Component
// ============================================================================

function TextPreview({ fileId, filename, contentType }: { fileId: string; filename: string; contentType: string }) {
  const { isDark } = useTheme();
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchContent = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch file through authenticated endpoint
        const blob = await filesApi.getFileBlob(fileId);
        const text = await blob.text();
        setContent(text);
      } catch (err) {
        console.error('Failed to fetch text content:', err);
        setError(err instanceof Error ? err.message : 'Failed to load file');
      } finally {
        setLoading(false);
      }
    };
    fetchContent();
  }, [fileId]);

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
          <p className="text-sm text-gray-400 mt-2">{error}</p>
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
// Share Link Modal
// ============================================================================

function ShareLinkModal({
  isOpen,
  file,
  onClose,
}: {
  isOpen: boolean;
  file: PreviewFile | null;
  onClose: () => void;
}) {
  const { isDark } = useTheme();
  const [expiryHours, setExpiryHours] = useState(24);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerateLink = async () => {
    if (!file) return;
    
    setLoading(true);
    setError(null);
    setCopied(false);
    
    try {
      const result = await filesApi.generateShareLink(file.id, expiryHours);
      setShareUrl(result.share_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate share link');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!shareUrl) return;
    
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = shareUrl;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleClose = () => {
    setShareUrl(null);
    setError(null);
    setCopied(false);
    onClose();
  };

  if (!isOpen || !file) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={handleClose} />
      <div className={`relative w-full max-w-md rounded-2xl p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className={`text-lg font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
            Share File
          </h3>
          <button onClick={handleClose} className={`p-1 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
            <Icons.X className="w-5 h-5" />
          </button>
        </div>
        
        <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Generate a shareable link for <strong className={isDark ? 'text-gray-200' : 'text-gray-800'}>{file.name}</strong>. 
          Anyone with the link can download this file.
        </p>

        {!shareUrl ? (
          <>
            {/* Expiry Selection */}
            <div className="mb-4">
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                Link expires in:
              </label>
              <select
                value={expiryHours}
                onChange={(e) => setExpiryHours(Number(e.target.value))}
                className={`w-full px-3 py-2 rounded-lg border ${
                  isDark 
                    ? 'bg-gray-700 border-gray-600 text-gray-200' 
                    : 'bg-white border-gray-300 text-gray-900'
                }`}
              >
                <option value={1}>1 hour</option>
                <option value={6}>6 hours</option>
                <option value={24}>24 hours</option>
                <option value={72}>3 days</option>
                <option value={168}>7 days</option>
              </select>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/20 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button
              onClick={handleGenerateLink}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {loading ? (
                <Icons.Spinner className="w-5 h-5" />
              ) : (
                <Icons.Link />
              )}
              {loading ? 'Generating...' : 'Generate Share Link'}
            </button>
          </>
        ) : (
          <>
            {/* Share URL Display */}
            <div className={`mb-4 p-3 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
              <div className="flex items-center gap-2 mb-2">
                <Icons.Link className={`w-4 h-4 ${isDark ? 'text-green-400' : 'text-green-600'}`} />
                <span className={`text-sm font-medium ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                  Link generated!
                </span>
              </div>
              <p className={`text-xs break-all ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {shareUrl}
              </p>
            </div>

            <div className={`mb-4 p-3 rounded-lg ${isDark ? 'bg-yellow-500/10 border border-yellow-500/30' : 'bg-yellow-50 border border-yellow-200'}`}>
              <p className={`text-xs ${isDark ? 'text-yellow-400' : 'text-yellow-700'}`}>
                ⚠️ This link will expire in {expiryHours} hour{expiryHours > 1 ? 's' : ''}. Anyone with this link can download the file.
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleCopy}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-colors ${
                  copied
                    ? 'bg-green-600 text-white'
                    : isDark
                    ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                    : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                }`}
              >
                {copied ? <Icons.Check /> : <Icons.Copy />}
                {copied ? 'Copied!' : 'Copy Link'}
              </button>
              <button
                onClick={() => setShareUrl(null)}
                className={`px-4 py-3 rounded-xl font-medium transition-colors ${
                  isDark
                    ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                    : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                }`}
              >
                New Link
              </button>
            </div>
          </>
        )}
      </div>
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
  const [shareStatus, setShareStatus] = useState<'idle' | 'loading' | 'copied'>('idle');
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

  const handleShare = async () => {
    if (shareStatus === 'loading') return;
    setShareStatus('loading');
    try {
      const response = await filesApi.generateShareLink(file.id, 24); // 24 hour link
      await navigator.clipboard.writeText(response.share_url);
      setShareStatus('copied');
      setTimeout(() => setShareStatus('idle'), 2000); // Reset after 2 seconds
    } catch (error) {
      console.error('Share link generation failed:', error);
      setShareStatus('idle');
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
        return <ImagePreview fileId={file.id} filename={file.name} contentType={file.contentType} />;
      case 'video':
        return <VideoPreview fileId={file.id} contentType={file.contentType} />;
      case 'audio':
        return <AudioPreview fileId={file.id} contentType={file.contentType} filename={file.name} />;
      case 'pdf':
        return <PDFPreview fileId={file.id} filename={file.name} contentType={file.contentType} />;
      case 'text':
        return <TextPreview fileId={file.id} filename={file.name} contentType={file.contentType} />;
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
              <>
                <button
                  onClick={handleShare}
                  disabled={shareStatus === 'loading'}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                    shareStatus === 'copied'
                      ? 'bg-green-600 text-white'
                      : isDark 
                        ? 'bg-blue-600 text-white hover:bg-blue-700' 
                        : 'bg-blue-500 text-white hover:bg-blue-600'
                  }`}
                >
                  {shareStatus === 'loading' ? (
                    <Icons.Spinner className="w-5 h-5" />
                  ) : shareStatus === 'copied' ? (
                    <Icons.Check />
                  ) : (
                    <Icons.Link />
                  )}
                  {shareStatus === 'copied' ? 'Copied!' : 'Share'}
                </button>
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
              </>
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
