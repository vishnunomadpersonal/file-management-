'use client';

import { useState, useEffect } from 'react';
import { User } from '../types';

/**
 * Build absolute URLs from .env:
 *   NEXT_PUBLIC_API_ORIGIN=https://localhost:9443   (recommended)
 * Falls back to window.location.origin.
 * Strip trailing slashes to keep paths clean.
 */
const ORIGIN =
  (process.env.NEXT_PUBLIC_API_ORIGIN || (typeof window !== 'undefined' ? window.location.origin : ''))
    .replace(/\/+$/, '');

// Base (no trailing slash) + explicit collection URL (with trailing slash) to avoid FastAPI 308s.
const USERS_API_BASE = `${ORIGIN}/api/v1/users`;
const USERS_LIST_URL = `${USERS_API_BASE}/`; // collection endpoint

interface LoginPageProps {
  onUserSelect: (user: User) => void;
}

export default function LoginPage({ onUserSelect }: LoginPageProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [newUserName, setNewUserName] = useState('');
  const [loading, setLoading] = useState(false);

  // Helpful warning if you accidentally open http://localhost:3000 instead of the Caddy URL
  useEffect(() => {
    if (typeof window !== 'undefined' && window.location.origin !== ORIGIN) {
      console.warn(
        `[LoginPage] App origin (${window.location.origin}) != API origin (${ORIGIN}). ` +
        `For no-CORS dev, open the app at ${ORIGIN} so UI+API share the same origin.`
      );
    }
  }, []);

  const parseJsonSafe = async (res: Response) => {
    const text = await res.text();
    try {
      return text ? JSON.parse(text) : null;
    } catch {
      throw new Error(text || `Non-JSON response (status ${res.status})`);
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      console.log('USERS_LIST_URL =', USERS_LIST_URL);
      const res = await fetch(`${USERS_LIST_URL}?t=${Date.now()}`, {
        method: 'GET',
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache' },
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`GET /users failed: ${res.status} ${errText}`);
      }

      const result = await res.json();
      if (result?.success) {
        setUsers(result.data);
      } else {
        console.warn('GET /users returned unexpected payload:', result);
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateUser = async () => {
    if (!newUserName.trim()) return;

    try {
      const res = await fetch(USERS_LIST_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newUserName.trim() }),
      });

      if (!res.ok) {
        const body = await res.text();
        throw new Error(`POST /users failed: ${res.status} ${body}`);
      }

      const result = await parseJsonSafe(res);
      if (result?.success) {
        setUsers((prev) => [...prev, result.data]);
        setNewUserName('');
      } else {
        console.warn('POST /users returned unexpected payload:', result);
      }
    } catch (error) {
      console.error('Failed to create user:', error);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user and all their data?')) return;

    try {
      // Use the base (no trailing slash) for item routes
      const res = await fetch(`${USERS_API_BASE}/${userId}`, { method: 'DELETE' });

      if (!res.ok) {
        const body = await res.text();
        throw new Error(`DELETE /users/${userId} failed: ${res.status} ${body}`);
      }

      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (error) {
      console.error('Failed to delete user:', error);
    }
  };

  return (
    <main className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-extrabold text-gray-800 dark:text-white mb-2">
              File Management System
            </h1>
            <p className="text-lg text-gray-500 dark:text-gray-400">
              Select a user to continue
            </p>
          </div>

          <div className="space-y-4 mb-8">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-white">Users</h2>

            {loading ? (
              <p className="text-center text-gray-500 dark:text-gray-400 py-8">Loading users…</p>
            ) : users.length > 0 ? (
              <div className="space-y-3">
                {users.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 border-l-4 border-transparent hover:border-blue-500 rounded-lg transition-all duration-200 ease-in-out"
                  >
                    <div
                      onClick={() => onUserSelect(user)}
                      className="flex-1 cursor-pointer"
                    >
                      <p className="font-semibold text-lg text-gray-800 dark:text-white">
                        {user.name}
                      </p>
                      {user.created_at && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Created: {new Date(user.created_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteUser(user.id);
                      }}
                      className="ml-3 px-3 py-1 text-sm font-semibold text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 transition-colors"
                      title="Delete user and all their data"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-gray-500 dark:text-gray-400 py-8">
                No users found. Create one to get started.
              </p>
            )}
          </div>

          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-4">
              Create New User
            </h3>
            <div className="flex space-x-3">
              <input
                type="text"
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
                placeholder="Enter user name"
                className="flex-grow px-4 py-2 text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-md focus:border-blue-500 focus:ring-blue-500 focus:outline-none focus:ring focus:ring-opacity-40"
                onKeyDown={(e) => e.key === 'Enter' && handleCreateUser()}
              />
              <button
                onClick={handleCreateUser}
                className="px-6 py-2 font-semibold text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
