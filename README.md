# Velnio

**Turn products into winning campaigns.**

AI-powered product launches for modern ecommerce. Velnio analyzes your product, finds powerful selling angles, and builds a Shopify-ready landing page using AI.

---

## What Velnio Solves

Dropshipping sellers waste time and money launching products without understanding the best way to sell them. Velnio automates the entire pre-launch workflow:

**Product** → **Analyze** → **Find Angles** → **Build Offer** → **Generate Landing** → **Publish to Shopify**

---

## Stack

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy 2 (async)
- Pydantic v2
- Alembic
- PostgreSQL
- pytest

### Frontend
- React 18
- TypeScript (strict)
- Vite
- Tailwind CSS
- React Router
- TanStack Query
- Zustand

### Infrastructure
- Docker / Docker Compose
- PostgreSQL 16

---

## Architecture

```
velnio/
├── backend/           # FastAPI modular monolith
│   ├── app/
│   │   ├── core/      # Config, security, encryption, exceptions
│   │   ├── db/        # SQLAlchemy session and base
│   │   ├── models/    # SQLAlchemy models (11 tables)
│   │   ├── schemas/   # Pydantic v2 schemas
│   │   ├── api/       # Route handlers (thin controllers)
│   │   ├── services/  # Business logic
│   │   │   ├── ai/    # AI provider (mock + OpenAI)
│   │   │   ├── shopify/ # Shopify provider (mock + real)
│   │   │   └── credits/ # Credit management
│   │   ├── repositories/
│   │   └── tests/     # pytest async tests
│   ├── alembic/       # Database migrations
│   └── Dockerfile
├── frontend/          # React SPA
│   ├── src/
│   │   ├── api/       # API client
│   │   ├── pages/     # 12 pages
│   │   ├── stores/    # Zustand stores
│   │   ├── hooks/     # Custom hooks
│   │   ├── layouts/   # Main + Auth layouts
│   │   ├── types/     # TypeScript types
│   │   └── lib/       # Utilities
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Installation

### With Docker (Recommended)

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your values (defaults work for development)

# Start everything
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create PostgreSQL database
createdb velnio

# Run migrations
alembic upgrade head

# Seed demo data
python -m app.seed

# Start server
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Database Migrations

```bash
cd backend

# Generate a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Seeding

```bash
cd backend
python -m app.seed
```

Creates:
- **Plans**: FREE (10 credits), LAUNCH ($19, 100), GROWTH ($49, 400), SCALE ($99, 1200)
- **Demo user**: demo@velnio.local / Demo12345!
- **Demo workspace**: Velnio Demo Store
- **Demo store**: Connected Shopify mock
- **3 demo products**: Portable Car Vacuum (READY), Pet Hair Remover (ANALYZED), Neck Massager (DRAFT)
- **500 credits**

---

## Tests

```bash
cd backend
python -m pytest app/tests/ -v
```

### Test Coverage
| Test | What it covers |
|------|---------------|
| test_auth | Register, login, refresh token, /me |
| test_workspace | Auto workspace creation on register |
| test_products | CRUD, list, workspace isolation |
| test_analysis | Product analysis, credit consumption |
| test_angles | Generate angles, select, uniqueness |
| test_landings | Generate landing, update sections |
| test_shopify | Mock Shopify publish |
| test_campaigns | Campaign CRUD, angles, offer, landing, publish |
| test_import | Product import preview, SSRF blocking |
| test_enrichment | Product enrichment, credit consumption |
| test_images | Image upload, generation, selection |
| test_visual_direction | Visual direction generate/update/isolation |
| test_publish_readiness | Readiness checks |
| test_landing_v2 | Landing uses product images |
| test_renderer | HTML sanitization |
| test_storage | Local storage, content type validation |
| test_tracking | Tracking events, batch, deduplication |
| test_variants | Variant CRUD, clone, traffic split |
| test_performance | Campaign metrics, timeline, angle metrics |
| test_experiments | Leader detection, z-test, recommendations |
| test_demo | Demo event generation |

---

## Mock Integrations

### Mock AI (AI_PROVIDER=mock)
Works fully offline. Generates realistic:
- Product analysis with 8 subscores
- 3 selling angles per product
- Complete landing page with 11 sections

### Mock Shopify (SHOPIFY_MODE=mock)
Simulates Shopify API responses:
- Connect store
- Publish products
- Create pages

### Mock Billing (BILLING_PROVIDER=mock)
Simulates billing operations without Stripe.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql+asyncpg://... | Async database URL |
| JWT_SECRET | dev-secret | JWT signing key |
| ENCRYPTION_KEY | dev-key | Fernet encryption key |
| AI_PROVIDER | mock | `mock` or `openai` |
| OPENAI_API_KEY | | OpenAI API key (if using openai) |
| SHOPIFY_MODE | mock | `mock` or `real` |
| BILLING_PROVIDER | mock | `mock` or `stripe` |
| FRONTEND_URL | http://localhost:5173 | Frontend URL for CORS |

---

## Data Model

| Table | Description |
|-------|-------------|
| users | User accounts |
| workspaces | Multi-tenant workspaces |
| workspace_members | User-workspace membership + roles |
| stores | Connected Shopify stores |
| products | Products being analyzed |
| product_images | Product images |
| product_analyses | AI analysis results |
| selling_angles | Generated selling angles |
| landing_pages | Generated landing pages |
| landing_sections | Individual landing sections (JSON) |
| plans | Subscription plans |
| subscriptions | Workspace subscriptions |
| credit_wallets | Credit balances |
| credit_transactions | Credit transaction history |

---

## API Endpoints

### Auth
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`

### Workspace
- `GET /api/workspace`

### Products
- `GET /api/products`
- `POST /api/products`
- `GET /api/products/{id}`
- `PATCH /api/products/{id}`
- `DELETE /api/products/{id}`

### AI Analysis
- `POST /api/products/{id}/analyze`

### Selling Angles
- `GET /api/products/{id}/angles`
- `POST /api/products/{id}/angles/generate`
- `POST /api/products/{id}/angles/{angle_id}/select`

### Landing
- `GET /api/products/{id}/landing`
- `POST /api/products/{id}/landing/generate`
- `PATCH /api/products/landings/{id}`
- `PATCH /api/products/landing-sections/{id}`

### Shopify
- `POST /api/products/{id}/publish`

### Stores
- `GET /api/stores`
- `POST /api/stores/mock-connect`
- `POST /api/stores/{id}/disconnect`

### Credits
- `GET /api/credits`
- `GET /api/credits/transactions`

### Billing
- `GET /api/billing/plans`
- `GET /api/billing/subscription`

### Dashboard
- `GET /api/dashboard/summary`

---

## Demo Account

- **Email**: demo@velnio.local
- **Password**: Demo12345!

---

## How to Run

```bash
# Quick start with Docker
docker compose up --build

# Or manual start
# Terminal 1 - Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend && npm run dev
```

---

## V0.4 — Experimentation & Performance

- Campaign tracking events (PAGE_VIEW, CTA_CLICK, ADD_TO_CART, PURCHASE, etc.)
- Public tracking endpoints per campaign (tracking_key)
- Batch event ingestion
- Campaign performance metrics (visitors, sessions, purchases, revenue, CVR, AOV)
- Conversion funnel visualization
- Performance timeline with Recharts
- Landing variants (A/B/C/D/E)
- Traffic split management (weights must sum to 100%)
- Experiment leader detection (two-proportion z-test, 95% confidence)
- Selling angle performance breakdown
- AI performance analysis with winning patterns, weak points, recommendations
- Next-test recommendations (headline, angle, offer, price, hero image, CTA)
- Demo event generation for development
- Frontend Performance tab with KPIs, funnel, timeline, AI insights
- Frontend Experiments tab with variants, traffic editor, leader badge

---

## Next Phase

1. Real Shopify OAuth integration
2. OpenAI provider with real API
3. Stripe billing integration
4. Meta Ads integration
5. TikTok Ads integration
