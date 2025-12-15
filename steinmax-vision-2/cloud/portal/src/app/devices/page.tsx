'use client';

import { useEffect, useState } from 'react';
import { Cpu, Wifi, WifiOff, Settings, RefreshCw, Activity } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { LoadingSpinner, EmptyState, Modal } from '@/components/ui';
import { api, type Device } from '@/lib/api';
import { formatRelativeTime, cn } from '@/lib/utils';

const DEMO_PROPERTY_ID = '22222222-2222-2222-2222-222222222222';

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);

  useEffect(() => {
    fetchDevices();
  }, []);

  async function fetchDevices() {
    try {
      setLoading(true);
      const data = await api.getDevices(DEMO_PROPERTY_ID);
      setDevices(data);
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <Layout propertyName="Pine Valley Community">
        <div className="flex items-center justify-center h-screen">
          <LoadingSpinner />
        </div>
      </Layout>
    );
  }

  return (
    <Layout propertyName="Pine Valley Community">
      <div className="p-8 page-transition">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-text-primary">Devices</h1>
            <p className="text-text-secondary mt-1">
              Manage edge devices and cameras
            </p>
          </div>
          <button onClick={fetchDevices} className="btn-secondary">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Device Grid */}
        {devices.length === 0 ? (
          <div className="card">
            <EmptyState
              icon={Cpu}
              title="No devices configured"
              description="Add an edge device to start processing plates"
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {devices.map((device) => (
              <div
                key={device.id}
                onClick={() => setSelectedDevice(device)}
                className={cn(
                  'card-hover p-6 cursor-pointer',
                  device.status === 'online' && 'border-l-2 border-l-status-online'
                )}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'w-10 h-10 rounded-lg flex items-center justify-center',
                      device.status === 'online' 
                        ? 'bg-status-online/20' 
                        : 'bg-surface-raised'
                    )}>
                      <Cpu className={cn(
                        'w-5 h-5',
                        device.status === 'online' ? 'text-status-online' : 'text-text-muted'
                      )} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-text-primary">{device.name}</h3>
                      <p className="text-sm text-text-muted">{device.device_type.toUpperCase()}</p>
                    </div>
                  </div>
                  <button className="p-2 text-text-muted hover:text-text-primary transition-colors">
                    <Settings className="w-4 h-4" />
                  </button>
                </div>

                {/* Status */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-text-muted">Status</span>
                    <div className="flex items-center gap-2">
                      {device.status === 'online' ? (
                        <Wifi className="w-4 h-4 text-status-online" />
                      ) : (
                        <WifiOff className="w-4 h-4 text-status-offline" />
                      )}
                      <span className={cn(
                        'text-sm font-medium capitalize',
                        device.status === 'online' ? 'text-status-online' : 'text-status-offline'
                      )}>
                        {device.status}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-text-muted">Last Seen</span>
                    <span className="text-sm text-text-secondary">
                      {device.last_seen 
                        ? formatRelativeTime(device.last_seen) 
                        : 'Never'}
                    </span>
                  </div>

                  {device.tailscale_ip && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-text-muted">Tailscale IP</span>
                      <span className="text-sm font-mono text-text-secondary">
                        {device.tailscale_ip}
                      </span>
                    </div>
                  )}
                </div>

                {/* Error */}
                {device.last_error && (
                  <div className="mt-4 p-3 bg-status-denied/10 rounded-md">
                    <p className="text-sm text-status-denied">{device.last_error}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Device Detail Modal */}
        <Modal
          isOpen={!!selectedDevice}
          onClose={() => setSelectedDevice(null)}
          title="Device Details"
          size="md"
        >
          {selectedDevice && (
            <div className="space-y-6">
              {/* Status Banner */}
              <div className={cn(
                'p-4 rounded-lg flex items-center gap-3',
                selectedDevice.status === 'online' 
                  ? 'bg-status-online/10' 
                  : 'bg-status-offline/10'
              )}>
                {selectedDevice.status === 'online' ? (
                  <Wifi className="w-6 h-6 text-status-online" />
                ) : (
                  <WifiOff className="w-6 h-6 text-status-offline" />
                )}
                <div>
                  <p className={cn(
                    'font-medium capitalize',
                    selectedDevice.status === 'online' ? 'text-status-online' : 'text-status-offline'
                  )}>
                    {selectedDevice.status}
                  </p>
                  <p className="text-sm text-text-muted">
                    {selectedDevice.last_seen 
                      ? `Last seen ${formatRelativeTime(selectedDevice.last_seen)}`
                      : 'Never connected'}
                  </p>
                </div>
              </div>

              {/* Details */}
              <div className="space-y-4">
                <div className="flex justify-between py-2 border-b border-border/50">
                  <span className="text-text-muted">Name</span>
                  <span className="text-text-primary font-medium">{selectedDevice.name}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-border/50">
                  <span className="text-text-muted">Type</span>
                  <span className="text-text-primary">{selectedDevice.device_type.toUpperCase()}</span>
                </div>
                {selectedDevice.tailscale_ip && (
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-text-muted">Tailscale IP</span>
                    <span className="text-text-primary font-mono">{selectedDevice.tailscale_ip}</span>
                  </div>
                )}
                {selectedDevice.local_ip && (
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-text-muted">Local IP</span>
                    <span className="text-text-primary font-mono">{selectedDevice.local_ip}</span>
                  </div>
                )}
                <div className="flex justify-between py-2 border-b border-border/50">
                  <span className="text-text-muted">Device ID</span>
                  <span className="text-text-secondary font-mono text-sm">{selectedDevice.id}</span>
                </div>
              </div>

              {/* Error */}
              {selectedDevice.last_error && (
                <div className="p-4 bg-status-denied/10 rounded-lg">
                  <p className="text-sm font-medium text-status-denied mb-1">Last Error</p>
                  <p className="text-sm text-status-denied/80">{selectedDevice.last_error}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t border-border">
                <button className="btn-secondary">
                  <Activity className="w-4 h-4" />
                  View Events
                </button>
                <button className="btn-primary">
                  <Settings className="w-4 h-4" />
                  Configure
                </button>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </Layout>
  );
}
