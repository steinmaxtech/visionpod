# SteinMax Vision Portal

Customer-facing web portal for managing vehicle access control.

## Features

- **Dashboard** - Real-time overview of access events and device status
- **Plates** - Add, edit, delete vehicles from allow/deny lists
- **Events** - View access log with filtering and search
- **Devices** - Monitor edge device status and configuration

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Lucide Icons

## Development

### Prerequisites

- Node.js 18+
- Backend API running (see `/cloud/backend`)

### Setup

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Start development server
npm run dev
```

Open http://localhost:3000

### API Proxy

In development, API requests to `/api/*` are proxied to the backend (default: `http://localhost:8000/api/v1/*`).

To change the backend URL, set `API_URL` in `.env.local`.

## Build

```bash
npm run build
npm start
```

## Project Structure

```
src/
├── app/                    # Next.js pages
│   ├── page.tsx            # Dashboard
│   ├── plates/page.tsx     # Plates management
│   ├── events/page.tsx     # Events log
│   ├── devices/page.tsx    # Devices
│   ├── layout.tsx          # Root layout
│   └── globals.css         # Global styles
├── components/
│   ├── Layout.tsx          # App shell with sidebar
│   └── ui.tsx              # Reusable UI components
└── lib/
    ├── api.ts              # API client
    └── utils.ts            # Utility functions
```

## Customization

### Theming

Colors are defined in `tailwind.config.js`. The design uses a dark theme optimized for security/monitoring dashboards.

Key color tokens:
- `void` - Background
- `surface` - Card backgrounds
- `accent` - Primary action color (green)
- `status-*` - Status indicators

### Adding Pages

1. Create a new directory in `src/app/`
2. Add `page.tsx`
3. Add navigation link in `src/components/Layout.tsx`

## Deployment

### Vercel (Recommended)

```bash
npm i -g vercel
vercel
```

### Docker

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_URL` | Backend API base URL | `http://localhost:8000` |
