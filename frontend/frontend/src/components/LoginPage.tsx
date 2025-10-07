'use client';

import { useState, useEffect } from 'react';
import { User } from '../types';

const USERS_API_URL = '/api/v1/users/';

interface LoginPageProps {
  onUserSelect: (user: User) => void;
}

export default function LoginPage({ onUserSelect }: LoginPageProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [newUserName, setNewUserName] = useState('');

  const fetchUsers = async () => {
    try {
      console.log('USERS_API_URL =', USERS_API_URL);
      const response = await fetch(USERS_API_URL);
      const result = await response.json();
      if (result.success) {
        setUsers(result.data);
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async () => {
    if (!newUserName.trim()) return;
    try {
      const response = await fetch(USERS_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newUserName }),
      });
      const result = await response.json();
      if (result.success) {
        setUsers([...users, result.data]);
        setNewUserName('');
      }
    } catch (error) {
      console.error('Failed to create user:', error);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user and all their data?')) {
      return;
    }
    
    try {
      const response = await fetch(`${USERS_API_URL}/${userId}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setUsers(users.filter(user => user.id !== userId));
      }
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
            {users.length > 0 ? (
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
                      <p className="font-semibold text-lg text-gray-800 dark:text-white">{user.name}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Created: {new Date(user.created_at).toLocaleDateString()}
                      </p>
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
              <p className="text-center text-gray-500 dark:text-gray-400 py-8">No users found. Create one to get started.</p>
            )}
          </div>

          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-4">Create New User</h3>
            <div className="flex space-x-3">
              <input
                type="text"
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
                placeholder="Enter user name"
                className="flex-grow px-4 py-2 text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-md focus:border-blue-500 focus:ring-blue-500 focus:outline-none focus:ring focus:ring-opacity-40"
                onKeyPress={(e) => e.key === 'Enter' && handleCreateUser()}
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