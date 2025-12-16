# SteinMax Vision Cloud

Vehicle Access Control Platform - LPR-based gate access with Gatewise integration.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for portal frontend)

### 1. Start the Database

```bash
# From project root
docker compose -f docker-compose.dev.yml up -d

# Verify it's running
docker ps
```

This starts:
- PostgreSQL 16 on port 5432
- Redis on port 6379
- Automatically runs schema.sql to create tables + seed data

### 2. Run the Backend API

```bash
cd cloud/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app.main:app --reload
```

API is now running at http://localhost:8000

- Swagger docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. Test the API

```bash
# List properties (should show demo property)
curl http://localhost:8000/api/v1/properties

# List plates for demo property
curl http://localhost:8000/api/v1/plates/property/22222222-2222-2222-2222-222222222222

# Check if a plate is allowed
curl http://localhost:8000/api/v1/plates/check/22222222-2222-2222-2222-222222222222/ABC1234

# Add a new plate
curl -X POST http://localhost:8000/api/v1/plates \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "22222222-2222-2222-2222-222222222222",
    "plate_number": "NEW1234",
    "description": "New resident - Unit 305",
    "list_type": "allow"
  }'
```

## Project Structure

```
steinmax-vision/
├── docker-compose.dev.yml    # Local development services
├── schema.sql                # Database schema
│
├── cloud/
│   ├── backend/              # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py       # FastAPI application
│   │   │   ├── config.py     # Settings management
│   │   │   ├── database.py   # Database connection
│   │   │   ├── models.py     # SQLAlchemy ORM models
│   │   │   ├── schemas.py    # Pydantic schemas
│   │   │   └── routers/      # API endpoints
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── portal/               # Next.js frontend (coming soon)
│
├── edge/                     # Edge device agent (coming soon)
│   └── agent/
│
└── infra/                    # Infrastructure configs
```

## API Endpoints

### Properties
- `GET /api/v1/properties` - List properties
- `GET /api/v1/properties/{id}` - Get property with stats
- `POST /api/v1/properties` - Create property
- `PATCH /api/v1/properties/{id}` - Update property
- `DELETE /api/v1/properties/{id}` - Delete property

### Devices
- `GET /api/v1/devices` - List devices
- `GET /api/v1/devices/{id}` - Get device
- `POST /api/v1/devices` - Create device
- `PATCH /api/v1/devices/{id}` - Update device
- `DELETE /api/v1/devices/{id}` - Delete device
- `POST /api/v1/devices/{id}/heartbeat` - Device heartbeat

### Plates (Allow List)
- `GET /api/v1/plates` - List plates with filters
- `GET /api/v1/plates/property/{id}` - Get property plates
- `GET /api/v1/plates/{id}` - Get single plate
- `POST /api/v1/plates` - Create plate
- `POST /api/v1/plates/bulk` - Bulk create plates
- `PATCH /api/v1/plates/{id}` - Update plate
- `DELETE /api/v1/plates/{id}` - Delete plate
- `GET /api/v1/plates/check/{property_id}/{plate_number}` - Check if plate is allowed

### Events
- `GET /api/v1/events` - List events with filters
- `GET /api/v1/events/stats` - Get event statistics
- `GET /api/v1/events/{id}` - Get single event
- `GET /api/v1/events/property/{id}/recent` - Recent events for property

### Webhooks
- `POST /api/v1/webhooks/plate-recognizer/{device_id}` - Plate Recognizer webhook
- `POST /api/v1/webhooks/test` - Test webhook endpoint

### Sync (for Edge Devices)
- `GET /api/v1/sync/devices/{id}/plates` - Get plates for device sync
- `GET /api/v1/sync/devices/{id}/config` - Get device configuration
- `GET /api/v1/sync/plates/hash/{property_id}` - Get plate list hash

## Webhook Flow

When Plate Recognizer detects a plate:

1. PR Stream sends webhook to `/api/v1/webhooks/plate-recognizer/{device_id}`
2. Backend extracts plate number and confidence
3. Looks up plate in allow list for that property
4. If allowed: triggers Gatewise API to open gate
5. Logs event to database
6. Returns decision to webhook

## Environment Variables

See `.env.example` for all available options.

## Next Steps

1. **Portal Frontend** - Next.js + shadcn/ui dashboard
2. **Edge Agent** - Python service for edge devices  
3. **Tailscale Setup** - Secure networking
4. **S3 Integration** - Image/clip storage
5. **Clerk Auth** - User authentication
6. **Gatewise Integration** - Live API calls
