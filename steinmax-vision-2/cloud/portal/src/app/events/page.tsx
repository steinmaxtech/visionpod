'use client';

import { useEffect, useState } from 'react';
import { Search, Filter, Activity, Calendar, Download } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { 
  Table, 
  StatusBadge, 
  Modal, 
  LoadingSpinner, 
  EmptyState 
} from '@/components/ui';
import { api, type Event } from '@/lib/api';
import { formatDateTime, formatTime, formatRelativeTime, cn } from '@/lib/utils';

const DEMO_PROPERTY_ID = '22222222-2222-2222-2222-222222222222';

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [decisionFilter, setDecisionFilter] = useState<string>('');
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const LIMIT = 50;

  useEffect(() => {
    fetchEvents();
  }, [decisionFilter, page]);

  async function fetchEvents() {
    try {
      setLoading(true);
      const data = await api.getEvents({
        propertyId: DEMO_PROPERTY_ID,
        decision: decisionFilter || undefined,
        plateNumber: searchQuery || undefined,
        limit: LIMIT,
        offset: page * LIMIT,
      });
      setEvents(data);
      setHasMore(data.length === LIMIT);
    } catch (error) {
      console.error('Failed to fetch events:', error);
    } finally {
      setLoading(false);
    }
  }

  function handleSearch() {
    setPage(0);
    fetchEvents();
  }

  const columns = [
    {
      key: 'created_at',
      header: 'Time',
      render: (event: Event) => (
        <div>
          <div className="text-text-primary">{formatTime(event.created_at)}</div>
          <div className="text-xs text-text-muted">{formatRelativeTime(event.created_at)}</div>
        </div>
      ),
    },
    {
      key: 'plate_number',
      header: 'Plate',
      render: (event: Event) => (
        <div>
          <span className="font-mono font-semibold text-text-primary tracking-wider">
            {event.plate_number || '—'}
          </span>
          {event.matched_plate_description && (
            <div className="text-xs text-text-muted mt-0.5">
              {event.matched_plate_description}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'decision',
      header: 'Decision',
      render: (event: Event) => <StatusBadge status={event.decision} />,
    },
    {
      key: 'decision_reason',
      header: 'Reason',
      render: (event: Event) => (
        <span className="text-text-secondary text-sm">
          {event.decision_reason || '—'}
        </span>
      ),
    },
    {
      key: 'device_name',
      header: 'Device',
      render: (event: Event) => (
        <span className="text-text-muted">{event.device_name || 'Unknown'}</span>
      ),
    },
    {
      key: 'confidence',
      header: 'Conf.',
      className: 'text-right',
      render: (event: Event) => (
        <span className={cn(
          'font-mono text-sm',
          event.plate_confidence && event.plate_confidence >= 90 
            ? 'text-status-granted' 
            : event.plate_confidence && event.plate_confidence >= 70
              ? 'text-status-unknown'
              : 'text-text-muted'
        )}>
          {event.plate_confidence ? `${event.plate_confidence.toFixed(0)}%` : '—'}
        </span>
      ),
    },
    {
      key: 'processing',
      header: 'Time',
      className: 'text-right',
      render: (event: Event) => (
        <span className="font-mono text-xs text-text-muted">
          {event.processing_time_ms ? `${event.processing_time_ms}ms` : '—'}
        </span>
      ),
    },
  ];

  return (
    <Layout propertyName="Pine Valley Community">
      <div className="p-8 page-transition">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-text-primary">Events</h1>
            <p className="text-text-secondary mt-1">
              Access control event log
            </p>
          </div>
          <button className="btn-secondary">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>

        {/* Filters */}
        <div className="card mb-6">
          <div className="p-4 flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input
                type="text"
                placeholder="Search by plate number..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="input pl-10"
              />
            </div>
            <select
              value={decisionFilter}
              onChange={(e) => {
                setDecisionFilter(e.target.value);
                setPage(0);
              }}
              className="input w-40"
            >
              <option value="">All Decisions</option>
              <option value="granted">Granted</option>
              <option value="denied">Denied</option>
              <option value="unknown">Unknown</option>
            </select>
            <button onClick={handleSearch} className="btn-secondary">
              <Filter className="w-4 h-4" />
              Apply
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="card">
          {loading && events.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : events.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="No events yet"
              description="Events will appear here when plates are detected"
            />
          ) : (
            <>
              <Table
                columns={columns}
                data={events}
                keyExtractor={(e) => e.id}
                onRowClick={(e) => setSelectedEvent(e)}
              />
              
              {/* Pagination */}
              <div className="px-4 py-3 border-t border-border flex items-center justify-between">
                <span className="text-sm text-text-muted">
                  Showing {events.length} events
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                    className="btn-secondary text-sm"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={!hasMore}
                    className="btn-secondary text-sm"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Event Detail Modal */}
        <Modal
          isOpen={!!selectedEvent}
          onClose={() => setSelectedEvent(null)}
          title="Event Details"
          size="lg"
        >
          {selectedEvent && (
            <div className="space-y-6">
              {/* Plate & Decision */}
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-mono text-3xl font-bold text-text-primary tracking-wider">
                    {selectedEvent.plate_number || 'Unknown'}
                  </span>
                  {selectedEvent.matched_plate_description && (
                    <p className="text-text-secondary mt-1">
                      {selectedEvent.matched_plate_description}
                    </p>
                  )}
                </div>
                <StatusBadge status={selectedEvent.decision} className="text-base px-3 py-1" />
              </div>

              {/* Image placeholder */}
              {selectedEvent.image_url ? (
                <div className="rounded-lg overflow-hidden bg-surface-raised">
                  <img 
                    src={selectedEvent.image_url} 
                    alt="Plate capture"
                    className="w-full h-64 object-cover"
                  />
                </div>
              ) : (
                <div className="rounded-lg bg-surface-raised h-48 flex items-center justify-center">
                  <span className="text-text-muted">No image available</span>
                </div>
              )}

              {/* Details grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <p className="text-sm text-text-muted">Time</p>
                  <p className="text-text-primary">{formatDateTime(selectedEvent.created_at)}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-text-muted">Device</p>
                  <p className="text-text-primary">{selectedEvent.device_name || 'Unknown'}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-text-muted">Confidence</p>
                  <p className="text-text-primary">
                    {selectedEvent.plate_confidence 
                      ? `${selectedEvent.plate_confidence.toFixed(1)}%` 
                      : '—'}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-text-muted">Processing Time</p>
                  <p className="text-text-primary">
                    {selectedEvent.processing_time_ms 
                      ? `${selectedEvent.processing_time_ms}ms` 
                      : '—'}
                  </p>
                </div>
                <div className="col-span-2 space-y-1">
                  <p className="text-sm text-text-muted">Reason</p>
                  <p className="text-text-primary">
                    {selectedEvent.decision_reason || 'No reason provided'}
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t border-border">
                {selectedEvent.clip_url && (
                  <a href={selectedEvent.clip_url} target="_blank" className="btn-secondary">
                    View Clip
                  </a>
                )}
                <button onClick={() => setSelectedEvent(null)} className="btn-primary">
                  Close
                </button>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </Layout>
  );
}
