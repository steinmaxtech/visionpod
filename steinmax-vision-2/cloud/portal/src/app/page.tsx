'use client';

import { useEffect, useState } from 'react';
import { 
  Activity, 
  Car, 
  ShieldCheck, 
  ShieldX, 
  Cpu,
  TrendingUp,
  Clock
} from 'lucide-react';
import { Layout } from '@/components/Layout';
import { StatCard, StatusBadge, Table, LoadingSpinner, EmptyState } from '@/components/ui';
import { api, type Event, type EventStats, type Device } from '@/lib/api';
import { formatRelativeTime, formatTime } from '@/lib/utils';

// Demo property ID - in production, get from user context/auth
const DEMO_PROPERTY_ID = '22222222-2222-2222-2222-222222222222';

export default function DashboardPage() {
  const [stats, setStats] = useState<EventStats | null>(null);
  const [recentEvents, setRecentEvents] = useState<Event[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsData, eventsData, devicesData] = await Promise.all([
          api.getEventStats(DEMO_PROPERTY_ID, 7),
          api.getRecentEvents(DEMO_PROPERTY_ID, 10),
          api.getDevices(DEMO_PROPERTY_ID),
        ]);
        setStats(statsData);
        setRecentEvents(eventsData);
        setDevices(devicesData);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const eventColumns = [
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
        <span className="font-mono text-text-primary">
          {event.plate_number || '—'}
        </span>
      ),
    },
    {
      key: 'decision',
      header: 'Decision',
      render: (event: Event) => <StatusBadge status={event.decision} />,
    },
    {
      key: 'device_name',
      header: 'Device',
      render: (event: Event) => (
        <span className="text-text-secondary">{event.device_name || 'Unknown'}</span>
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      render: (event: Event) => (
        <span className="text-text-muted">
          {event.plate_confidence ? `${event.plate_confidence.toFixed(0)}%` : '—'}
        </span>
      ),
    },
  ];

  if (loading) {
    return (
      <Layout propertyName="Pine Valley Community">
        <div className="flex items-center justify-center h-screen">
          <LoadingSpinner />
        </div>
      </Layout>
    );
  }

  const onlineDevices = devices.filter(d => d.status === 'online').length;
  const grantRate = stats && stats.total > 0 
    ? ((stats.granted / stats.total) * 100).toFixed(1)
    : '0';

  return (
    <Layout propertyName="Pine Valley Community">
      <div className="p-8 page-transition">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-text-primary">Dashboard</h1>
          <p className="text-text-secondary mt-1">
            Real-time overview of your access control system
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Events Today"
            value={stats?.total || 0}
            icon={Activity}
          />
          <StatCard
            label="Access Granted"
            value={stats?.granted || 0}
            change={`${grantRate}% grant rate`}
            changeType="positive"
            icon={ShieldCheck}
          />
          <StatCard
            label="Access Denied"
            value={stats?.denied || 0}
            icon={ShieldX}
          />
          <StatCard
            label="Devices Online"
            value={`${onlineDevices}/${devices.length}`}
            changeType={onlineDevices === devices.length ? 'positive' : 'negative'}
            icon={Cpu}
          />
        </div>

        {/* Two column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Recent Events */}
          <div className="lg:col-span-2 card">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <h2 className="font-semibold text-text-primary">Recent Events</h2>
              <a href="/events" className="text-sm text-accent hover:text-accent-hover">
                View all →
              </a>
            </div>
            <Table
              columns={eventColumns}
              data={recentEvents}
              keyExtractor={(e) => e.id}
              emptyMessage="No events yet"
            />
          </div>

          {/* Device Status */}
          <div className="card">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="font-semibold text-text-primary">Devices</h2>
            </div>
            <div className="divide-y divide-border/50">
              {devices.length === 0 ? (
                <EmptyState
                  icon={Cpu}
                  title="No devices"
                  description="Add a device to get started"
                />
              ) : (
                devices.map((device) => (
                  <div key={device.id} className="px-6 py-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-text-primary">{device.name}</p>
                      <p className="text-sm text-text-muted">
                        {device.last_seen 
                          ? `Last seen ${formatRelativeTime(device.last_seen)}`
                          : 'Never connected'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          device.status === 'online'
                            ? 'bg-status-online animate-pulse-slow'
                            : 'bg-status-offline'
                        }`}
                      />
                      <span className="text-sm text-text-secondary capitalize">
                        {device.status}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
