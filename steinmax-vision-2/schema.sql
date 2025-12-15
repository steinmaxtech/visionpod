-- SteinMax Vision Cloud Database Schema
-- Version: 1.0.0

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- ORGANIZATIONS & PROPERTIES
-- ============================================================================

-- Organizations (your customers - property management companies, HOAs, etc.)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE,  -- for URLs: steinmax.com/org/pine-valley-hoa
    settings JSONB DEFAULT '{}',  -- org-level preferences
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Properties/Sites (individual gates, buildings, communities)
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    settings JSONB DEFAULT '{}',  -- property-level preferences
    status VARCHAR(50) DEFAULT 'active',  -- active, inactive, suspended
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- DEVICES
-- ============================================================================

-- Edge devices deployed at properties
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,  -- "Main Gate", "Visitor Entrance"
    device_type VARCHAR(50) DEFAULT 'lpr',  -- lpr, camera, relay
    
    -- Networking
    tailscale_ip VARCHAR(45),
    tailscale_hostname VARCHAR(255),
    local_ip VARCHAR(45),
    
    -- Integrations
    gatewise_device_id VARCHAR(255),
    gatewise_api_key VARCHAR(255),  -- encrypted in production
    plate_recognizer_token VARCHAR(255),
    camera_rtsp_url VARCHAR(500),
    
    -- Status
    status VARCHAR(50) DEFAULT 'offline',  -- online, offline, error
    last_seen TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    firmware_version VARCHAR(50),
    
    -- Config
    config JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- ACCESS CONTROL
-- ============================================================================

-- Plate allow/deny lists
CREATE TABLE plates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    -- Plate info
    plate_number VARCHAR(20) NOT NULL,
    plate_state VARCHAR(10),  -- FL, GA, etc. (optional)
    description VARCHAR(255),  -- "John Smith - Unit 204", "FedEx Delivery"
    
    -- List configuration
    list_type VARCHAR(50) DEFAULT 'allow',  -- allow, deny, visitor, vendor
    
    -- Time restrictions (NULL = always valid)
    starts_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Recurring schedule (optional)
    schedule JSONB,  -- {"days": ["mon","tue","wed","thu","fri"], "start": "08:00", "end": "17:00"}
    
    -- Metadata
    notes TEXT,
    created_by UUID,  -- user who added it
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Prevent duplicate plates per property
    UNIQUE(property_id, plate_number)
);

-- ============================================================================
-- EVENTS & LOGGING
-- ============================================================================

-- Access events (every plate detection)
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    -- Detection data
    plate_number VARCHAR(20),
    plate_confidence DECIMAL(5,2),  -- 0.00 to 100.00
    plate_region VARCHAR(10),  -- detected state/region
    
    -- Decision
    decision VARCHAR(20) NOT NULL,  -- granted, denied, unknown, manual
    decision_reason VARCHAR(255),  -- "Matched allow list", "Plate not found", "Expired"
    matched_plate_id UUID REFERENCES plates(id) ON DELETE SET NULL,
    
    -- Media
    image_url TEXT,  -- S3 presigned URL or path
    image_s3_key VARCHAR(500),  -- actual S3 key
    clip_url TEXT,
    clip_s3_key VARCHAR(500),
    
    -- Integration responses
    gatewise_response JSONB,
    plate_recognizer_response JSONB,
    
    -- Processing metadata
    processing_time_ms INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Partition events by month for performance (optional, for scale)
-- CREATE TABLE events_2025_01 PARTITION OF events FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- ============================================================================
-- USERS & AUTH
-- ============================================================================

-- Users (synced from Clerk)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,
    
    -- Organization membership
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    role VARCHAR(50) DEFAULT 'member',  -- owner, admin, member, viewer
    
    -- Permissions (can be extended)
    permissions JSONB DEFAULT '[]',  -- ["manage_plates", "view_events", "manage_devices"]
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, invited, suspended
    last_login TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User property access (for multi-property orgs)
CREATE TABLE user_property_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    access_level VARCHAR(50) DEFAULT 'view',  -- view, manage, admin
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, property_id)
);

-- ============================================================================
-- AUDIT LOG
-- ============================================================================

-- Track changes for compliance
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,  -- plate.created, plate.deleted, device.updated
    resource_type VARCHAR(50),  -- plate, device, property
    resource_id UUID,
    changes JSONB,  -- {"plate_number": {"old": null, "new": "ABC123"}}
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Events (most queried table)
CREATE INDEX idx_events_property_created ON events(property_id, created_at DESC);
CREATE INDEX idx_events_device_created ON events(device_id, created_at DESC);
CREATE INDEX idx_events_plate_number ON events(plate_number, created_at DESC);
CREATE INDEX idx_events_decision ON events(decision, created_at DESC);

-- Plates
CREATE INDEX idx_plates_property_number ON plates(property_id, plate_number);
CREATE INDEX idx_plates_property_type ON plates(property_id, list_type);
CREATE INDEX idx_plates_expires ON plates(expires_at) WHERE expires_at IS NOT NULL;

-- Devices
CREATE INDEX idx_devices_property ON devices(property_id);
CREATE INDEX idx_devices_tailscale ON devices(tailscale_ip) WHERE tailscale_ip IS NOT NULL;
CREATE INDEX idx_devices_status ON devices(status);

-- Users
CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_users_clerk ON users(clerk_id);

-- Audit
CREATE INDEX idx_audit_user ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id, created_at DESC);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to relevant tables
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_plates_updated_at BEFORE UPDATE ON plates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- SEED DATA (for development)
-- ============================================================================

-- Demo organization
INSERT INTO organizations (id, name, slug) VALUES 
    ('11111111-1111-1111-1111-111111111111', 'Demo Property Management', 'demo-pm');

-- Demo property
INSERT INTO properties (id, organization_id, name, address, timezone) VALUES 
    ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 
     'Pine Valley Community', '123 Main Gate Dr, Tampa, FL 33601', 'America/New_York');

-- Demo device
INSERT INTO devices (id, property_id, name, device_type, status) VALUES 
    ('33333333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222',
     'Main Entrance Gate', 'lpr', 'offline');

-- Demo plates
INSERT INTO plates (property_id, plate_number, description, list_type) VALUES 
    ('22222222-2222-2222-2222-222222222222', 'ABC1234', 'John Smith - Unit 101', 'allow'),
    ('22222222-2222-2222-2222-222222222222', 'XYZ9999', 'Jane Doe - Unit 204', 'allow'),
    ('22222222-2222-2222-2222-222222222222', 'TEST123', 'Test Vehicle', 'allow');
