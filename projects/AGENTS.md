# AGENTS.md - B2B Customer Growth System

## Project Overview
Cross-border B2B customer discovery, scoring, and outreach automation platform.

## Architecture
- **Backend**: Python FastAPI (port 8000) - `backend/`
- **Frontend**: React + Vite + TypeScript + Tailwind CSS (port 5173) - `frontend/`
- **Database**: PostgreSQL 16 (port 5432)
- **Cache/Queue**: Redis 7 (port 6379)
- **Deployment**: Docker Compose

## Directory Structure
```
backend/
  app/
    main.py          # FastAPI entry point, router registration
    config.py        # Pydantic settings (env vars)
    database.py      # Async SQLAlchemy engine + session
    models/          # SQLAlchemy ORM models
      project.py     # Project config table
      company.py     # Company/customer table (core)
      contact.py     # Decision-maker contacts
      task.py        # SearchTask, ScheduledJob, DraftMessage
    schemas/         # Pydantic request/response schemas
    api/             # FastAPI route handlers
      projects.py    # CRUD for projects
      companies.py   # CRUD + filtering + CSV export + batch scoring
      contacts.py    # CRUD for contacts
      search.py      # Task queue management
      drafts.py      # Draft generation + review
      dashboard.py   # Aggregated stats
    services/        # Business logic
      google_search.py   # SerpAPI integration + keyword matrix
      scorer.py          # 100-point scoring system
      whatsapp_sniffer.py # Phone/link extraction
      customs.py         # ImportYeti interface
    utils/
      email_validator.py # Email validation + inference
frontend/
  src/
    api/client.ts    # API client (fetch wrapper)
    types/index.ts   # TypeScript type definitions
    components/      # Shared UI components
    pages/           # Route pages (Dashboard, ProjectList, etc.)
```

## Key Commands
```bash
# Backend
cd backend && pip install -r requirements.txt
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend && npm install && npm run dev

# Docker
docker compose up -d
docker compose --profile worker up -d worker
```

## Database Tables
- `projects` - Campaign configurations
- `companies` - Discovered B2B companies with scoring
- `contacts` - Decision-maker contacts with grading (GOLD/SILVER/BRONZE)
- `search_tasks` - Background task queue
- `scheduled_jobs` - Cron-like scheduled jobs
- `draft_messages` - Outreach draft messages

## API Endpoints
- `GET /api/dashboard/stats` - Aggregated dashboard stats
- `GET/POST /api/projects` - Project CRUD
- `GET/POST /api/companies` - Company CRUD with filtering
- `GET /api/companies/export/csv` - CSV export
- `POST /api/companies/batch-score` - Batch scoring trigger
- `GET/POST /api/contacts` - Contact CRUD
- `GET/POST /api/tasks` - Task queue management
- `POST /api/tasks/search` - Trigger search
- `GET/POST /api/drafts` - Draft management
- `POST /api/drafts/generate` - AI draft generation

## Scoring System (100 points)
- Product Match: 25pts
- Customer Type Match: 20pts
- Procurement Capability: 20pts
- Business Scale: 15pts
- Market Value: 10pts
- Info Credibility: 10pts
- Grades: A(75-100), B(60-74), C(45-59), D(0-44), excluded

## Environment Variables
See `.env.example` for required variables (SerpAPI key, DB connection, Redis, etc.)
