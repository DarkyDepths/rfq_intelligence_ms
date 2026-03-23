# rfq_intelligence_ms

A separate, read-heavy analytical microservice that transforms RFQ source material and historical records into persistent intelligence artifacts for multiple consumers (UI, chatbot, dashboards).

**Current status: Skeleton only — no business logic implemented yet.**

---

## What This Service Owns

- Document / RFQ parsing (triggered by events from manager)
- Intelligence artifact creation, versioning, persistence
- Analytical projections (snapshot read model)
- Historical enrichment (analytical record)
- Read APIs for intelligence consumers

## What This Service Does NOT Own

- RFQ lifecycle state, workflows, stages, reminders → `rfq_manager_ms`
- File storage (Azure Blob) → `rfq_manager_ms`
- Chatbot sessions, intent detection → `rfq_chatbot_ms`
- IAM / authentication
- Operational decisions or workflow execution

---

## The 6 Intelligence Artifacts

| # | Artifact | Role |
|---|----------|------|
| 1 | `rfq_intake_profile` | Structured extraction from ZIP/MR package |
| 2 | `intelligence_briefing` | Proactive dossier generated on RFQ creation |
| 3 | `workbook_profile` | Structured extraction from GHI estimation workbook |
| 4 | `workbook_review_report` | Bridge artifact comparing intake vs workbook |
| 5 | `rfq_intelligence_snapshot` | Consumer-facing read model per RFQ |
| 6 | `rfq_analytical_record` | Historical enrichment seed (not user-facing) |

---

## API Endpoints (V1)

| Method | Endpoint | Status Code | Purpose |
|--------|----------|-------------|---------|
| GET | `/intelligence/v1/rfqs/{rfq_id}/snapshot` | 200 / 404 | Main entry point — returns snapshot |
| GET | `/intelligence/v1/rfqs/{rfq_id}/briefing` | 200 / 404 | Latest intelligence briefing |
| GET | `/intelligence/v1/rfqs/{rfq_id}/workbook-profile` | 200 / 404 | Latest workbook profile |
| GET | `/intelligence/v1/rfqs/{rfq_id}/workbook-review` | 200 / 404 | Latest workbook review report |
| POST | `/intelligence/v1/rfqs/{rfq_id}/reprocess/intake` | 202 | Manual re-run of intake parsing |
| POST | `/intelligence/v1/rfqs/{rfq_id}/reprocess/workbook` | 202 | Manual re-run of workbook parsing |
| GET | `/intelligence/v1/rfqs/{rfq_id}/artifacts` | 200 | Artifact index with versions/statuses |
| GET | `/health` | 200 | Health check |

---

## Running Locally

### With Docker Compose

```bash
docker-compose up --build
# API available at http://localhost:8001
# DB available at localhost:5433
```

The API container automatically runs `alembic upgrade head` on startup.

### Without Docker

```bash
# 1. Start PostgreSQL (port 5433, db: rfq_intelligence_db)

# 2. Create .env from template
cp .env.example .env

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
alembic upgrade head

# 5. Start the server
uvicorn src.app:app --port 8001 --reload
```

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Architecture

Follows the **BACAB layered pattern** consistent with `rfq_manager_ms`:

```
HTTP path:    routes → controllers → services → datasources/connectors
Event path:   event_handlers → services → datasources/connectors
```

Own PostgreSQL database (separate from manager). JSONB artifact storage with versioning.
