'use client';

import { useState, ChangeEvent, useRef } from 'react';
import { FileData } from '../types';

// Define the structure of the API responses
interface UploadInitResponse {
  data: {
    chunk_size: number;
    upload_id: string;
  };
}

interface SuccessResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

interface UploadCompleteResponse {
  id: string;
  path: string;
  download_url: string;
  filename: string;
  content_type: string;
  size: number;
}

interface FileUploaderProps {
  appointmentId: string;
  userId: string;
  onUploadSuccess: (newFile: FileData) => void;
  onUploadComplete: () => void;
}

const API_BASE_URL = '/api/v1/file';

export default function FileUploader({ appointmentId, userId, onUploadSuccess, onUploadComplete }: FileUploaderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('Click or drag to select a file');
  const [uploadedFile, setUploadedFile] = useState<FileData | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [virusWarning, setVirusWarning] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus(`Selected file: ${e.target.files[0].name}`);
      setProgress(0);
      setUploadedFile(null);
      setVirusWarning(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setStatus('Please select a file first.');
      return;
    }

    setIsUploading(true);
    setUploadedFile(null);
    setProgress(0);
    setVirusWarning(null);

    try {
      // 1. Initialize Upload
      setStatus('Initializing upload...');
      const initResponse = await fetch(`${API_BASE_URL}/upload/init/`, { method: 'POST' });
      if (!initResponse.ok) throw new Error('Failed to initialize upload.');
      const initJson: UploadInitResponse = await initResponse.json();
      const { chunk_size, upload_id } = initJson.data;

      // 2. Upload Chunks
      const totalChunks = Math.ceil(file.size / chunk_size);
      for (let i = 0; i < totalChunks; i++) {
        const start = i * chunk_size;
        const end = Math.min(start + chunk_size, file.size);
        const chunk = file.slice(start, end);

        const formData = new FormData();
        formData.append('chunk_size', chunk.size.toString());
        formData.append('upload_id', upload_id);
        formData.append('chunk_index', i.toString());
        formData.append('file', chunk, file.name);
        
        setStatus(`Uploading chunk ${i + 1} of ${totalChunks}...`);
        
        const chunkResponse = await fetch(`${API_BASE_URL}/upload/chunk/`, {
          method: 'POST',
          body: formData,
        });

        if (!chunkResponse.ok) {
           const errorData = await chunkResponse.json();
           throw new Error(`Failed to upload chunk ${i + 1}: ${errorData.message || 'Unknown error'}`);
        }
        
        setProgress(Math.round(((i + 1) / totalChunks) * 100));
      }

      // 3. Complete Upload
      setStatus('Completing upload...');
      const completeFormData = new FormData();
      const fileExtension = file.name.split('.').pop() || '';
      completeFormData.append('upload_id', upload_id);
      completeFormData.append('total_chunks', totalChunks.toString());
      completeFormData.append('total_size', file.size.toString());
      completeFormData.append('file_extension', fileExtension);
      completeFormData.append('content_type', file.type);
      completeFormData.append('appointment_id', appointmentId);
      completeFormData.append('user_id', userId);
      completeFormData.append('filename', file.name);
      
      const completeResponse = await fetch(`${API_BASE_URL}/upload/complete/`, {
        method: 'POST',
        body: completeFormData,
      });

      if (!completeResponse.ok) {
        // Try to parse the error response
        try {
          const errorData = await completeResponse.json();
          const errorMessage = errorData.message || errorData.errors?.[0] || 'Failed to complete upload.';
          throw new Error(errorMessage);
        } catch (parseError) {
          // If we can't parse the error response, use a generic message
          throw new Error('Failed to complete upload.');
        }
      }

      const completeJson: SuccessResponse<UploadCompleteResponse> = await completeResponse.json();
      
      const newFileData: FileData = {
          id: completeJson.data.id,
          filename: completeJson.data.filename,
          content_type: completeJson.data.content_type,
          size: completeJson.data.size,
          download_url: completeJson.data.download_url
      };

      setUploadedFile(newFileData);
      setStatus('Upload successful! Your file is being processed.');
      onUploadSuccess(newFileData);
      onUploadComplete();

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred.';
      
      // Check if this is a virus detection error
      if (errorMessage.toLowerCase().includes('virus') || errorMessage.toLowerCase().includes('malware') || errorMessage.toLowerCase().includes('infected')) {
        setVirusWarning('⚠️ A virus has been detected in the file you have attempted to upload. The file has been quarantined for security.');
        setStatus('File rejected due to security concerns.');
      } else {
        setStatus(`Error: ${errorMessage}`);
      }
      setProgress(0);
    } finally {
      setIsUploading(false);
    }
  };

  const triggerFileSelect = () => fileInputRef.current?.click();

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
        disabled={isUploading}
      />

      <div 
        className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center cursor-pointer hover:border-blue-500 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        onClick={triggerFileSelect}
      >
        <p className="text-gray-500 dark:text-gray-400">{status}</p>
      </div>

      <div className="mt-6">
        <button
          onClick={handleUpload}
          disabled={!file || isUploading}
          className="w-full bg-blue-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-all duration-200 ease-in-out"
        >
          {isUploading ? `Uploading... ${progress}%` : 'Upload File'}
        </button>
      </div>

      {isUploading && (
        <div className="mt-4 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
          <div
            className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      )}

      {virusWarning && (
        <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg text-center">
          <p className="font-semibold text-red-800 dark:text-red-300">{virusWarning}</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Please ensure your files are virus-free before uploading.
          </p>
        </div>
      )}

      {uploadedFile && (
        <div className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-center">
          <p className="font-semibold text-green-800 dark:text-green-300">Processing Complete!</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">File: {uploadedFile.filename}</p>
          <a
            href={uploadedFile.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 font-semibold"
          >
            Download File
          </a>
        </div>
      )}
    </div>
  );
}