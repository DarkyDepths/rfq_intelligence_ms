# rfq_intelligence_ms

A separate, read-heavy analytical microservice that transforms RFQ source
material and historical records into persistent intelligence artifacts for
multiple consumers such as the UI, chatbot, and dashboards.

Current status: partial but operational V1 slices are implemented.

Today the service can build and persist:
- `rfq_intake_profile`
- `intelligence_briefing`
- `workbook_profile`
- `cost_breakdown_profile`
- `parser_report`
- `workbook_review_report`
- `rfq_analytical_record`
- `rfq_intelligence_snapshot`

What is still transitional:
- manual lifecycle trigger routes are still the active integration bridge
- manual reprocess endpoints are still accepted/stubbed, not fully executed
- autonomous event-bus ingestion is not wired yet

## What This Service Owns

- Document and RFQ parsing triggered from manager-side lifecycle events
- Intelligence artifact creation, versioning, and persistence
- Analytical projections such as the snapshot read model
- Historical enrichment through the analytical record
- Read APIs for intelligence consumers

## What This Service Does Not Own

- RFQ lifecycle state, workflows, stages, and reminders: `rfq_manager_ms`
- File storage: `rfq_manager_ms`
- Chatbot sessions and intent detection: `rfq_chatbot_ms`
- IAM and authentication
- Operational workflow execution

## Core Intelligence Artifacts

| Artifact | Role |
|---|---|
| `rfq_intake_profile` | Structured extraction from the source package |
| `intelligence_briefing` | Proactive dossier generated on RFQ creation |
| `workbook_profile` | Structured extraction from the GHI estimation workbook |
| `workbook_review_report` | Bridge artifact comparing intake vs workbook |
| `rfq_intelligence_snapshot` | Consumer-facing read model per RFQ |
| `rfq_analytical_record` | Historical enrichment seed, not directly user-facing |
| `cost_breakdown_profile` | Cost decomposition emitted by the workbook parser |
| `parser_report` | Parser execution and failure metadata |

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/intelligence/v1/rfqs/{rfq_id}/snapshot` | Main consumer snapshot |
| GET | `/intelligence/v1/rfqs/{rfq_id}/briefing` | Latest intelligence briefing |
| GET | `/intelligence/v1/rfqs/{rfq_id}/workbook-profile` | Latest workbook profile |
| GET | `/intelligence/v1/rfqs/{rfq_id}/workbook-review` | Latest workbook review report |
| GET | `/intelligence/v1/rfqs/{rfq_id}/artifacts` | Artifact index with versions and statuses |
| POST | `/intelligence/v1/rfqs/{rfq_id}/reprocess/intake` | Manual re-run request accepted, still stubbed |
| POST | `/intelligence/v1/rfqs/{rfq_id}/reprocess/workbook` | Manual re-run request accepted, still stubbed |
| POST | `/intelligence/v1/rfqs/{rfq_id}/trigger/intake` | Manual lifecycle bridge for current integrated flows |
| POST | `/intelligence/v1/rfqs/{rfq_id}/trigger/workbook` | Manual lifecycle bridge for current integrated flows |
| POST | `/intelligence/v1/rfqs/{rfq_id}/trigger/outcome` | Manual lifecycle bridge for current integrated flows |
| GET | `/health` | Health check |

## Running Locally

### Integrated platform path

For the real RFQMGMT local platform flow, prefer the scenario stack:

```bash
python d:\PFE\scripts\rfqmgmt_scenario_stack.py all --seed-set full
```

That path brings up:
- manager at `http://localhost:18000`
- intelligence at `http://localhost:18001`

It also aligns seeded scenarios and mounts manager uploads into intelligence.

### Standalone intelligence compose

```bash
docker-compose up --build
```

The API is then available at `http://localhost:8001`, and the container expects
the manager API to be reachable at `http://host.docker.internal:18000`.

### Without Docker

```bash
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn src.app:app --port 8001 --reload
```

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The test suite now defaults to an in-memory SQLite `DATABASE_URL` when one is
not already provided by the shell.

## Architecture

The service follows the BACAB layered pattern used in `rfq_manager_ms`.

```text
HTTP path:  routes -> controllers -> services -> datasources/connectors
Event path: event_handlers -> services -> datasources/connectors
```

Controllers and event handlers do not access datasources directly. The service
owns its own PostgreSQL database and stores intelligence artifacts as versioned
records.
