import { useState, useEffect } from 'react';
import FileUploader from './FileUploader';
import { Appointment, FileData, User } from '../types';

const API_BASE_URL = '/api/v1/file';

interface FileDashboardProps {
  appointment: Appointment;
  user: User;
  onBack: () => void;
}

export default function FileDashboard({ appointment, user, onBack }: FileDashboardProps) {
  const [files, setFiles] = useState<FileData[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/appointment/${appointment.id}`);
        const result = await response.json();
        if (result.success) {
          setFiles(result.data);
        }
      } catch (error) {
        console.error('Failed to fetch files:', error);
      }
    };

    fetchFiles();
  }, [appointment.id, refreshKey]);

  const handleUploadSuccess = (newFile: FileData) => {
    setFiles((prevFiles) => [...prevFiles, newFile]);
  };

  const triggerRefresh = () => {
    setRefreshKey(prevKey => prevKey + 1);
  };

  const handleDelete = async (fileId: string) => {
    try {
      await fetch(`${API_BASE_URL}/${fileId}`, { method: 'DELETE' });
      setFiles((prevFiles) => prevFiles.filter((file) => file.id !== fileId));
    } catch (error) {
      console.error('Failed to delete file:', error);
    }
  };

  return (
    <main className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <div className="container mx-auto p-4 sm:p-6 lg:p-8">
        <header className="flex justify-between items-center mb-8 pb-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
              Appointment: <span className="text-blue-600 dark:text-blue-400">{appointment.name}</span>
            </h1>
            <p className="text-gray-500 dark:text-gray-400">Manage files for this appointment.</p>
          </div>
          <button 
            onClick={onBack} 
            className="px-5 py-2 font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors"
          >
            &larr; Back to Dashboard
          </button>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">Upload New File</h2>
            <FileUploader 
              appointmentId={appointment.id}
              userId={user.id}
              onUploadSuccess={handleUploadSuccess} 
              onUploadComplete={triggerRefresh}
            />
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">Existing Files</h2>
            <div className="space-y-4">
              {files.length > 0 ? (
                files.map((file) => (
                  <div key={file.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
                    <a href={file.download_url} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 truncate transition-colors" title={file.filename}>
                      {file.filename}
                    </a>
                    <button onClick={() => handleDelete(file.id)} className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 font-semibold transition-colors">
                      Remove
                    </button>
                  </div>
                ))
              ) : (
                <p className="text-center text-gray-500 dark:text-gray-400 py-8">No files found for this appointment.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
