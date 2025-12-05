export interface User {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Appointment {
  id: string;
  name: string;
  date: string; // ISO date string
  files: FileData[];
}

export interface FileData {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  download_url: string;
  appointment_name?: string;
} 