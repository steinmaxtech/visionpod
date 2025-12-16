// API client for SteinMax Vision backend

const API_BASE = '/api';

export interface Property {
  id: string;
  organization_id: string;
  name: string;
  address: string | null;
  timezone: string;
  status: string;
  created_at: string;
  updated_at: string;
  device_count?: number;
  plate_count?: number;
  events_today?: number;
}

export interface Device {
  id: string;
  property_id: string;
  name: string;
  device_type: string;
  tailscale_ip: string | null;
  status: 'online' | 'offline' | 'error';
  last_seen: string | null;
  last_error: string | null;
  created_at: string;
}

export interface Plate {
  id: string;
  property_id: string;
  plate_number: string;
  plate_state: string | null;
  description: string | null;
  list_type: 'allow' | 'deny' | 'visitor' | 'vendor';
  starts_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Event {
  id: string;
  device_id: string;
  property_id: string;
  plate_number: string | null;
  plate_confidence: number | null;
  decision: 'granted' | 'denied' | 'unknown';
  decision_reason: string | null;
  matched_plate_id: string | null;
  image_url: string | null;
  clip_url: string | null;
  processing_time_ms: number | null;
  created_at: string;
  device_name?: string;
  matched_plate_description?: string;
}

export interface EventStats {
  total: number;
  granted: number;
  denied: number;
  days: number;
  daily: { date: string; count: number }[];
}

class ApiClient {
  private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Properties
  async getProperties(): Promise<Property[]> {
    return this.fetch('/properties');
  }

  async getProperty(id: string): Promise<Property> {
    return this.fetch(`/properties/${id}`);
  }

  // Devices
  async getDevices(propertyId?: string): Promise<Device[]> {
    const params = propertyId ? `?property_id=${propertyId}` : '';
    return this.fetch(`/devices${params}`);
  }

  async getDevice(id: string): Promise<Device> {
    return this.fetch(`/devices/${id}`);
  }

  // Plates
  async getPlates(propertyId: string, options?: { listType?: string; search?: string }): Promise<Plate[]> {
    const params = new URLSearchParams({ property_id: propertyId });
    if (options?.listType) params.append('list_type', options.listType);
    if (options?.search) params.append('search', options.search);
    return this.fetch(`/plates?${params}`);
  }

  async getPropertyPlates(propertyId: string): Promise<Plate[]> {
    return this.fetch(`/plates/property/${propertyId}`);
  }

  async createPlate(plate: Omit<Plate, 'id' | 'created_at' | 'updated_at'>): Promise<Plate> {
    return this.fetch('/plates', {
      method: 'POST',
      body: JSON.stringify(plate),
    });
  }

  async updatePlate(id: string, updates: Partial<Plate>): Promise<Plate> {
    return this.fetch(`/plates/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  async deletePlate(id: string): Promise<void> {
    await this.fetch(`/plates/${id}`, { method: 'DELETE' });
  }

  // Events
  async getEvents(options?: {
    propertyId?: string;
    deviceId?: string;
    decision?: string;
    plateNumber?: string;
    limit?: number;
    offset?: number;
  }): Promise<Event[]> {
    const params = new URLSearchParams();
    if (options?.propertyId) params.append('property_id', options.propertyId);
    if (options?.deviceId) params.append('device_id', options.deviceId);
    if (options?.decision) params.append('decision', options.decision);
    if (options?.plateNumber) params.append('plate_number', options.plateNumber);
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());
    return this.fetch(`/events?${params}`);
  }

  async getRecentEvents(propertyId: string, limit = 10): Promise<Event[]> {
    return this.fetch(`/events/property/${propertyId}/recent?limit=${limit}`);
  }

  async getEventStats(propertyId?: string, days = 7): Promise<EventStats> {
    const params = new URLSearchParams({ days: days.toString() });
    if (propertyId) params.append('property_id', propertyId);
    return this.fetch(`/events/stats?${params}`);
  }

  async getEvent(id: string): Promise<Event> {
    return this.fetch(`/events/${id}`);
  }
}

export const api = new ApiClient();
