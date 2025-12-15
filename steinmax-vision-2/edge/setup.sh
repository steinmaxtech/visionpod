#!/bin/bash

# =============================================================================
# STEINMAX VISION EDGE DEVICE SETUP
# =============================================================================
# Run this script on a fresh Ubuntu 22.04/24.04 mini PC to set up everything.
#
# Usage:
#   curl -fsSL https://your-domain.com/edge-setup.sh | sudo bash
#
# Or download and run:
#   chmod +x setup.sh
#   sudo ./setup.sh
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# CONFIGURATION
# =============================================================================

INSTALL_DIR="/opt/steinmax-edge"
RECORDINGS_DIR="/opt/steinmax-edge/recordings"

# These can be set as environment variables before running
TAILSCALE_AUTH_KEY="${TAILSCALE_AUTH_KEY:-}"
SITE_ID="${SITE_ID:-edge-$(hostname)}"

# =============================================================================
# CHECKS
# =============================================================================

echo ""
echo "=============================================="
echo "   STEINMAX VISION EDGE SETUP"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root: sudo ./setup.sh"
    exit 1
fi

# Check Ubuntu version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        log_warn "This script is designed for Ubuntu. Your OS: $ID"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# =============================================================================
# SYSTEM UPDATE
# =============================================================================

log_info "Updating system packages..."
apt-get update
apt-get upgrade -y

# =============================================================================
# INSTALL DOCKER
# =============================================================================

log_info "Installing Docker..."

if command -v docker &> /dev/null; then
    log_info "Docker already installed: $(docker --version)"
else
    curl -fsSL https://get.docker.com | sh
    
    # Add current user to docker group
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker "$SUDO_USER"
    fi
    
    log_info "Docker installed: $(docker --version)"
fi

# Install Docker Compose plugin
if ! docker compose version &> /dev/null; then
    apt-get install -y docker-compose-plugin
fi

log_info "Docker Compose: $(docker compose version)"

# =============================================================================
# INSTALL TAILSCALE
# =============================================================================

log_info "Installing Tailscale..."

if command -v tailscale &> /dev/null; then
    log_info "Tailscale already installed"
else
    curl -fsSL https://tailscale.com/install.sh | sh
fi

# Connect to Tailscale if auth key provided
if [ -n "$TAILSCALE_AUTH_KEY" ]; then
    log_info "Connecting to Tailscale network..."
    tailscale up --authkey="$TAILSCALE_AUTH_KEY" --hostname="$SITE_ID"
    TAILSCALE_IP=$(tailscale ip -4)
    log_info "Tailscale IP: $TAILSCALE_IP"
else
    log_warn "No TAILSCALE_AUTH_KEY provided. Run manually:"
    log_warn "  sudo tailscale up --hostname=$SITE_ID"
fi

# =============================================================================
# CREATE DIRECTORY STRUCTURE
# =============================================================================

log_info "Creating directory structure..."

mkdir -p "$INSTALL_DIR"/{config,data}
mkdir -p "$RECORDINGS_DIR"

# =============================================================================
# DOWNLOAD CONFIGURATION FILES
# =============================================================================

log_info "Setting up configuration files..."

# Create docker-compose.yml
cat > "$INSTALL_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: steinmax-redis
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - ./data/redis:/data
    networks:
      - edge-net

  plate-recognizer:
    image: platerecognizer/alpr-stream:latest
    container_name: steinmax-plate-recognizer
    restart: always
    environment:
      - TOKEN=${PLATE_RECOGNIZER_TOKEN}
    volumes:
      - ./config/stream.yaml:/user-data/config.yaml:ro
      - ./data/plate-recognizer:/user-data
    networks:
      - edge-net
    depends_on:
      - edge-agent

  edge-agent:
    image: steinmax/edge-agent:latest
    build: ./agent
    container_name: steinmax-edge-agent
    restart: always
    ports:
      - "8080:8080"
    env_file:
      - .env
    environment:
      - REDIS_URL=redis://redis:6379/0
      - FRIGATE_URL=http://frigate:5000
    volumes:
      - ./data/agent:/data
    networks:
      - edge-net
    depends_on:
      - redis

  frigate:
    image: ghcr.io/blakeblackshear/frigate:stable
    container_name: steinmax-frigate
    restart: always
    privileged: true
    ports:
      - "5000:5000"
      - "8554:8554"
      - "8555:8555"
    environment:
      - FRIGATE_RTSP_PASSWORD=${CAMERA_PASSWORD:-}
    volumes:
      - ./config/frigate.yaml:/config/config.yml:ro
      - ./data/frigate:/config
      - ${FRIGATE_MEDIA_PATH:-./recordings}:/media/frigate
      - /etc/localtime:/etc/localtime:ro
    shm_size: "256mb"
    networks:
      - edge-net

  go2rtc:
    image: alexxit/go2rtc:latest
    container_name: steinmax-go2rtc
    restart: always
    ports:
      - "1984:1984"
      - "8556:8555"
    environment:
      - CAMERA_RTSP_URL=${CAMERA_RTSP_URL}
    volumes:
      - ./config/go2rtc.yaml:/config/go2rtc.yaml:ro
    networks:
      - edge-net

networks:
  edge-net:
    driver: bridge
EOF

# Create Plate Recognizer config
cat > "$INSTALL_DIR/config/stream.yaml" << 'EOF'
cameras:
  - id: gate-camera-1
    name: Main Gate Camera
    url: "${CAMERA_RTSP_URL}"
    fps: 2
    mmc: 0.7
    regions:
      - us

webhook_targets:
  - url: "http://edge-agent:8080/webhook/plate"
    image: true
    send_all: true
EOF

# Create Frigate config
cat > "$INSTALL_DIR/config/frigate.yaml" << 'EOF'
database:
  path: /config/frigate.db

detectors:
  cpu:
    type: cpu
    num_threads: 2

record:
  enabled: true
  retain:
    days: 7
    mode: motion
  events:
    retain:
      default: 14

snapshots:
  enabled: true
  timestamp: true
  retain:
    default: 14

cameras:
  gate_camera:
    enabled: true
    ffmpeg:
      inputs:
        - path: ${CAMERA_RTSP_URL}
          roles:
            - record
            - detect
    detect:
      enabled: true
      width: 1280
      height: 720
      fps: 5
    objects:
      track:
        - car
        - motorcycle
        - person
EOF

# Create go2rtc config
cat > "$INSTALL_DIR/config/go2rtc.yaml" << 'EOF'
api:
  listen: ":1984"
  origin: "*"

webrtc:
  listen: ":8555"

streams:
  gate_camera:
    - "${CAMERA_RTSP_URL}"
  gate_camera_frigate:
    - "rtsp://frigate:8554/gate_camera"

rtsp:
  listen: ":8554"
EOF

# Create .env template
cat > "$INSTALL_DIR/.env" << 'EOF'
# Device Identity (get from cloud portal)
DEVICE_ID=
PROPERTY_ID=

# Cloud Connection
CLOUD_API_URL=https://api.yourdomain.com/api/v1

# Gatewise
GATEWISE_ENABLED=true
GATEWISE_API_KEY=
GATEWISE_DEVICE_ID=

# Plate Recognizer
PLATE_RECOGNIZER_TOKEN=

# Camera
CAMERA_RTSP_URL=rtsp://admin:password@192.168.1.100:554/stream1
CAMERA_PASSWORD=

# Frigate
FRIGATE_ENABLED=true
FRIGATE_MEDIA_PATH=/opt/steinmax-edge/recordings

# Sync
SYNC_INTERVAL_SECONDS=60
HEARTBEAT_INTERVAL_SECONDS=30
LOG_LEVEL=INFO
EOF

# =============================================================================
# SET PERMISSIONS
# =============================================================================

log_info "Setting permissions..."

chmod 600 "$INSTALL_DIR/.env"
chown -R root:root "$INSTALL_DIR"

# =============================================================================
# CREATE SYSTEMD SERVICE
# =============================================================================

log_info "Creating systemd service..."

cat > /etc/systemd/system/steinmax-edge.service << EOF
[Unit]
Description=SteinMax Vision Edge Stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable steinmax-edge.service

# =============================================================================
# FIREWALL
# =============================================================================

log_info "Configuring firewall..."

if command -v ufw &> /dev/null; then
    ufw allow 8080/tcp comment 'SteinMax Edge Agent'
    ufw allow 5000/tcp comment 'Frigate Web UI'
    ufw allow 1984/tcp comment 'go2rtc Web UI'
fi

# =============================================================================
# DONE
# =============================================================================

echo ""
echo "=============================================="
echo "   SETUP COMPLETE!"
echo "=============================================="
echo ""
log_info "Installation directory: $INSTALL_DIR"
log_info "Recordings directory: $RECORDINGS_DIR"

if [ -n "$TAILSCALE_AUTH_KEY" ]; then
    log_info "Tailscale IP: $(tailscale ip -4)"
fi

echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Edit the configuration file:"
echo "   sudo nano $INSTALL_DIR/.env"
echo ""
echo "2. Fill in these required values:"
echo "   - DEVICE_ID (from cloud portal)"
echo "   - PROPERTY_ID (from cloud portal)"
echo "   - CLOUD_API_URL (your backend URL)"
echo "   - GATEWISE_API_KEY"
echo "   - GATEWISE_DEVICE_ID"
echo "   - PLATE_RECOGNIZER_TOKEN"
echo "   - CAMERA_RTSP_URL"
echo ""
echo "3. Start the services:"
echo "   cd $INSTALL_DIR"
echo "   sudo docker compose up -d"
echo ""
echo "4. Check status:"
echo "   sudo docker compose ps"
echo "   sudo docker compose logs -f"
echo ""
echo "5. Test the edge agent:"
echo "   curl http://localhost:8080/health"
echo ""
echo "Web UIs (after starting):"
echo "   - Frigate: http://localhost:5000"
echo "   - go2rtc:  http://localhost:1984"
echo ""
