"use client";

import React, { useState } from 'react';
import {
  Building2,
  Search,
  Filter,
  Plus,
  MoreVertical,
  Users,
  FileStack,
  HardDrive,
  Eye,
  Edit,
  Trash2,
  Ban,
  CheckCircle,
  XCircle,
  Download,
  Clock,
  TrendingUp,
  ArrowUpRight,
} from 'lucide-react';

// Format bytes to human readable
const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Mock organizations data
const mockOrganizations = [
  {
    id: 'org_001',
    name: 'Acme Healthcare',
    slug: 'acme-healthcare',
    plan: 'enterprise',
    status: 'active',
    owner: 'john@acmehealthcare.com',
    members: 47,
    files: 128473,
    storage_used: 32 * 1024 * 1024 * 1024,
    storage_limit: 100 * 1024 * 1024 * 1024,
    created_at: '2024-01-15',
    last_active: '2 minutes ago',
  },
  {
    id: 'org_002',
    name: 'TechCorp Finance',
    slug: 'techcorp-finance',
    plan: 'enterprise',
    status: 'active',
    owner: 'admin@techcorp.com',
    members: 89,
    files: 89234,
    storage_used: 24 * 1024 * 1024 * 1024,
    storage_limit: 100 * 1024 * 1024 * 1024,
    created_at: '2024-02-20',
    last_active: '5 minutes ago',
  },
  {
    id: 'org_003',
    name: 'DataFlow Systems',
    slug: 'dataflow-systems',
    plan: 'pro',
    status: 'active',
    owner: 'ceo@dataflow.io',
    members: 23,
    files: 67891,
    storage_used: 18 * 1024 * 1024 * 1024,
    storage_limit: 50 * 1024 * 1024 * 1024,
    created_at: '2024-03-10',
    last_active: '1 hour ago',
  },
  {
    id: 'org_004',
    name: 'CloudNine Inc',
    slug: 'cloudnine-inc',
    plan: 'pro',
    status: 'active',
    owner: 'hello@cloudnine.com',
    members: 15,
    files: 45672,
    storage_used: 12 * 1024 * 1024 * 1024,
    storage_limit: 50 * 1024 * 1024 * 1024,
    created_at: '2024-04-05',
    last_active: '30 minutes ago',
  },
  {
    id: 'org_005',
    name: 'StartupX',
    slug: 'startupx',
    plan: 'free',
    status: 'active',
    owner: 'founder@startupx.io',
    members: 5,
    files: 2345,
    storage_used: 2 * 1024 * 1024 * 1024,
    storage_limit: 5 * 1024 * 1024 * 1024,
    created_at: '2024-05-15',
    last_active: '2 hours ago',
  },
  {
    id: 'org_006',
    name: 'MegaCorp Global',
    slug: 'megacorp-global',
    plan: 'enterprise',
    status: 'suspended',
    owner: 'admin@megacorp.com',
    members: 234,
    files: 456789,
    storage_used: 89 * 1024 * 1024 * 1024,
    storage_limit: 100 * 1024 * 1024 * 1024,
    created_at: '2023-11-20',
    last_active: '3 days ago',
  },
  {
    id: 'org_007',
    name: 'InnovateTech',
    slug: 'innovatetech',
    plan: 'pro',
    status: 'trial',
    owner: 'team@innovatetech.dev',
    members: 8,
    files: 1234,
    storage_used: 500 * 1024 * 1024,
    storage_limit: 50 * 1024 * 1024 * 1024,
    created_at: '2024-06-01',
    last_active: '10 minutes ago',
  },
];

export default function AdminOrganizations() {
  const [searchQuery, setSearchQuery] = useState('');
  const [planFilter, setPlanFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<string | null>(null);

  const filteredOrgs = mockOrganizations.filter(org => {
    const matchesSearch = org.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         org.owner.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPlan = planFilter === 'all' || org.plan === planFilter;
    const matchesStatus = statusFilter === 'all' || org.status === statusFilter;
    return matchesSearch && matchesPlan && matchesStatus;
  });

  const stats = {
    total: mockOrganizations.length,
    active: mockOrganizations.filter(o => o.status === 'active').length,
    enterprise: mockOrganizations.filter(o => o.plan === 'enterprise').length,
    trial: mockOrganizations.filter(o => o.status === 'trial').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Organizations</h1>
          <p className="text-gray-400 mt-1">Manage all organizations on the platform</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add Organization
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <Building2 className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total}</p>
              <p className="text-sm text-gray-400">Total Orgs</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.active}</p>
              <p className="text-sm text-gray-400">Active</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <TrendingUp className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.enterprise}</p>
              <p className="text-sm text-gray-400">Enterprise</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <Clock className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.trial}</p>
              <p className="text-sm text-gray-400">On Trial</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[300px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Search organizations or owners..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-400" />
          <select
            value={planFilter}
            onChange={(e) => setPlanFilter(e.target.value)}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-red-500"
          >
            <option value="all">All Plans</option>
            <option value="free">Free</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-red-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="trial">Trial</option>
          </select>
        </div>
        <button className="flex items-center gap-2 px-3 py-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg">
          <Download className="w-5 h-5" />
          Export
        </button>
      </div>

      {/* Organizations Table */}
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700/50 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-gray-400 border-b border-gray-700 bg-gray-800/50">
                <th className="px-6 py-4 font-medium">Organization</th>
                <th className="px-6 py-4 font-medium">Owner</th>
                <th className="px-6 py-4 font-medium">Plan</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Members</th>
                <th className="px-6 py-4 font-medium">Files</th>
                <th className="px-6 py-4 font-medium">Storage</th>
                <th className="px-6 py-4 font-medium">Last Active</th>
                <th className="px-6 py-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {filteredOrgs.map((org) => (
                <tr key={org.id} className="hover:bg-gray-700/30">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center text-white font-bold">
                        {org.name.charAt(0)}
                      </div>
                      <div>
                        <p className="text-white font-medium">{org.name}</p>
                        <p className="text-xs text-gray-500">{org.slug}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-sm text-white">{org.owner}</p>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      org.plan === 'enterprise' ? 'bg-purple-500/20 text-purple-400' :
                      org.plan === 'pro' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {org.plan}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`flex items-center gap-1 text-xs ${
                      org.status === 'active' ? 'text-green-400' :
                      org.status === 'suspended' ? 'text-red-400' :
                      'text-yellow-400'
                    }`}>
                      {org.status === 'active' ? <CheckCircle className="w-3 h-3" /> :
                       org.status === 'suspended' ? <XCircle className="w-3 h-3" /> :
                       <Clock className="w-3 h-3" />}
                      {org.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 text-white">
                      <Users className="w-4 h-4 text-gray-500" />
                      {org.members}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 text-white">
                      <FileStack className="w-4 h-4 text-gray-500" />
                      {org.files.toLocaleString()}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 w-20 h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            (org.storage_used / org.storage_limit) > 0.9 ? 'bg-red-500' :
                            (org.storage_used / org.storage_limit) > 0.7 ? 'bg-yellow-500' :
                            'bg-green-500'
                          }`}
                          style={{ width: `${(org.storage_used / org.storage_limit) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-400">{formatBytes(org.storage_used)}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs text-gray-400">{org.last_active}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="relative">
                      <button
                        onClick={() => setSelectedOrg(selectedOrg === org.id ? null : org.id)}
                        className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
                      >
                        <MoreVertical className="w-5 h-5" />
                      </button>
                      {selectedOrg === org.id && (
                        <div className="absolute right-0 mt-2 w-48 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden z-10">
                          <button className="w-full flex items-center gap-3 px-4 py-3 text-gray-300 hover:bg-gray-800 text-left">
                            <Eye className="w-4 h-4" />
                            View Details
                          </button>
                          <button className="w-full flex items-center gap-3 px-4 py-3 text-gray-300 hover:bg-gray-800 text-left">
                            <Edit className="w-4 h-4" />
                            Edit
                          </button>
                          <button className="w-full flex items-center gap-3 px-4 py-3 text-gray-300 hover:bg-gray-800 text-left">
                            <ArrowUpRight className="w-4 h-4" />
                            Login As
                          </button>
                          {org.status === 'active' ? (
                            <button className="w-full flex items-center gap-3 px-4 py-3 text-yellow-400 hover:bg-gray-800 text-left">
                              <Ban className="w-4 h-4" />
                              Suspend
                            </button>
                          ) : (
                            <button className="w-full flex items-center gap-3 px-4 py-3 text-green-400 hover:bg-gray-800 text-left">
                              <CheckCircle className="w-4 h-4" />
                              Activate
                            </button>
                          )}
                          <button className="w-full flex items-center gap-3 px-4 py-3 text-red-400 hover:bg-gray-800 text-left">
                            <Trash2 className="w-4 h-4" />
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        <div className="px-6 py-4 border-t border-gray-700 flex items-center justify-between">
          <p className="text-sm text-gray-400">
            Showing {filteredOrgs.length} of {mockOrganizations.length} organizations
          </p>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg text-sm">
              Previous
            </button>
            <button className="px-3 py-1 bg-red-500 text-white rounded-lg text-sm">1</button>
            <button className="px-3 py-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg text-sm">2</button>
            <button className="px-3 py-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg text-sm">3</button>
            <button className="px-3 py-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg text-sm">
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-gray-900 rounded-2xl w-full max-w-lg border border-gray-700 shadow-2xl">
            <div className="p-6 border-b border-gray-700">
              <h3 className="text-xl font-semibold text-white">Create Organization</h3>
              <p className="text-sm text-gray-400 mt-1">Add a new organization to the platform</p>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Organization Name</label>
                <input
                  type="text"
                  placeholder="Enter organization name"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Owner Email</label>
                <input
                  type="email"
                  placeholder="owner@company.com"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Plan</label>
                <select className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-red-500">
                  <option value="free">Free</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Storage Limit</label>
                <select className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-red-500">
                  <option value="5">5 GB</option>
                  <option value="50">50 GB</option>
                  <option value="100">100 GB</option>
                  <option value="500">500 GB</option>
                  <option value="1000">1 TB</option>
                </select>
              </div>
            </div>
            <div className="p-6 border-t border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg"
              >
                Cancel
              </button>
              <button className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg">
                Create Organization
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
