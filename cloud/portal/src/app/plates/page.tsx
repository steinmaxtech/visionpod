'use client';

import { useEffect, useState } from 'react';
import { Plus, Search, Car, Trash2, Edit2, X } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { 
  Table, 
  StatusBadge, 
  Modal, 
  Input, 
  Select, 
  LoadingSpinner, 
  EmptyState,
  Toast 
} from '@/components/ui';
import { api, type Plate } from '@/lib/api';
import { formatDateTime, formatPlateNumber } from '@/lib/utils';

const DEMO_PROPERTY_ID = '22222222-2222-2222-2222-222222222222';

const LIST_TYPE_OPTIONS = [
  { value: 'allow', label: 'Allow' },
  { value: 'deny', label: 'Deny' },
  { value: 'visitor', label: 'Visitor' },
  { value: 'vendor', label: 'Vendor' },
];

export default function PlatesPage() {
  const [plates, setPlates] = useState<Plate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPlate, setEditingPlate] = useState<Plate | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    plate_number: '',
    description: '',
    list_type: 'allow',
  });
  const [formLoading, setFormLoading] = useState(false);

  useEffect(() => {
    fetchPlates();
  }, [filterType]);

  async function fetchPlates() {
    try {
      setLoading(true);
      const data = await api.getPlates(DEMO_PROPERTY_ID, {
        listType: filterType || undefined,
      });
      setPlates(data);
    } catch (error) {
      console.error('Failed to fetch plates:', error);
      showToast('Failed to load plates', 'error');
    } finally {
      setLoading(false);
    }
  }

  function showToast(message: string, type: 'success' | 'error') {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }

  function openCreateModal() {
    setEditingPlate(null);
    setFormData({ plate_number: '', description: '', list_type: 'allow' });
    setIsModalOpen(true);
  }

  function openEditModal(plate: Plate) {
    setEditingPlate(plate);
    setFormData({
      plate_number: plate.plate_number,
      description: plate.description || '',
      list_type: plate.list_type,
    });
    setIsModalOpen(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormLoading(true);

    try {
      const plateNumber = formatPlateNumber(formData.plate_number);
      
      if (editingPlate) {
        await api.updatePlate(editingPlate.id, {
          plate_number: plateNumber,
          description: formData.description || null,
          list_type: formData.list_type as Plate['list_type'],
        });
        showToast('Plate updated successfully', 'success');
      } else {
        await api.createPlate({
          property_id: DEMO_PROPERTY_ID,
          plate_number: plateNumber,
          plate_state: null,
          description: formData.description || null,
          list_type: formData.list_type as Plate['list_type'],
          starts_at: null,
          expires_at: null,
          schedule: null,
          notes: null,
        });
        showToast('Plate added successfully', 'success');
      }

      setIsModalOpen(false);
      fetchPlates();
    } catch (error: any) {
      showToast(error.message || 'Failed to save plate', 'error');
    } finally {
      setFormLoading(false);
    }
  }

  async function handleDelete(plate: Plate) {
    if (!confirm(`Delete plate ${plate.plate_number}?`)) return;

    try {
      await api.deletePlate(plate.id);
      showToast('Plate deleted', 'success');
      fetchPlates();
    } catch (error) {
      showToast('Failed to delete plate', 'error');
    }
  }

  // Filter plates by search query
  const filteredPlates = plates.filter((plate) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      plate.plate_number.toLowerCase().includes(query) ||
      plate.description?.toLowerCase().includes(query)
    );
  });

  const columns = [
    {
      key: 'plate_number',
      header: 'Plate Number',
      render: (plate: Plate) => (
        <span className="font-mono font-semibold text-text-primary text-base tracking-wider">
          {plate.plate_number}
        </span>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      render: (plate: Plate) => (
        <span className="text-text-secondary">
          {plate.description || '—'}
        </span>
      ),
    },
    {
      key: 'list_type',
      header: 'Type',
      render: (plate: Plate) => <StatusBadge status={plate.list_type} />,
    },
    {
      key: 'expires_at',
      header: 'Expires',
      render: (plate: Plate) => (
        <span className="text-text-muted">
          {plate.expires_at ? formatDateTime(plate.expires_at) : 'Never'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-24',
      render: (plate: Plate) => (
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              openEditModal(plate);
            }}
            className="p-2 text-text-muted hover:text-text-primary transition-colors"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(plate);
            }}
            className="p-2 text-text-muted hover:text-status-denied transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <Layout propertyName="Pine Valley Community">
      <div className="p-8 page-transition">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-text-primary">Plates</h1>
            <p className="text-text-secondary mt-1">
              Manage vehicle access lists
            </p>
          </div>
          <button onClick={openCreateModal} className="btn-primary">
            <Plus className="w-4 h-4" />
            Add Plate
          </button>
        </div>

        {/* Filters */}
        <div className="card mb-6">
          <div className="p-4 flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input
                type="text"
                placeholder="Search plates or descriptions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-10"
              />
            </div>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="input w-40"
            >
              <option value="">All Types</option>
              {LIST_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="card">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : filteredPlates.length === 0 ? (
            <EmptyState
              icon={Car}
              title={searchQuery ? 'No plates found' : 'No plates yet'}
              description={
                searchQuery
                  ? 'Try a different search term'
                  : 'Add your first plate to get started'
              }
              action={
                !searchQuery && (
                  <button onClick={openCreateModal} className="btn-primary">
                    <Plus className="w-4 h-4" />
                    Add Plate
                  </button>
                )
              }
            />
          ) : (
            <Table
              columns={columns}
              data={filteredPlates}
              keyExtractor={(p) => p.id}
            />
          )}
        </div>

        {/* Add/Edit Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title={editingPlate ? 'Edit Plate' : 'Add Plate'}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Plate Number"
              placeholder="ABC1234"
              value={formData.plate_number}
              onChange={(e) =>
                setFormData({ ...formData, plate_number: e.target.value.toUpperCase() })
              }
              required
              autoFocus
              className="font-mono text-lg tracking-wider"
            />
            <Input
              label="Description"
              placeholder="John Smith - Unit 204"
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
            />
            <Select
              label="List Type"
              options={LIST_TYPE_OPTIONS}
              value={formData.list_type}
              onChange={(e) =>
                setFormData({ ...formData, list_type: e.target.value })
              }
            />
            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="btn-secondary"
                disabled={formLoading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={formLoading}
              >
                {formLoading ? (
                  <LoadingSpinner className="w-4 h-4" />
                ) : editingPlate ? (
                  'Save Changes'
                ) : (
                  'Add Plate'
                )}
              </button>
            </div>
          </form>
        </Modal>

        {/* Toast */}
        {toast && (
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        )}
      </div>
    </Layout>
  );
}
