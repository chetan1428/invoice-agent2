# LangGraph Invoice Processing Agent with HITL

A complete invoice processing workflow built with LangGraph, featuring Human-In-The-Loop (HITL) checkpoints, Bigtool dynamic tool selection, and MCP client orchestration.

## Features

- **12 Workflow Stages**: INTAKE → UNDERSTAND → PREPARE → RETRIEVE → MATCH_TWO_WAY → CHECKPOINT_HITL → HITL_DECISION → RECONCILE → APPROVE → POSTING → NOTIFY → COMPLETE
- **HITL Checkpoints**: Pause workflow for human review when matching fails, resume after decision
- **Bigtool Integration**: Dynamic tool selection from pools (OCR, enrichment, ERP, DB, email)
- **MCP Client Orchestration**: Routes abilities to COMMON (internal) and ATLAS (external) servers
- **State Persistence**: Full state management across all stages with SQLite/PostgreSQL
- **REST API**: FastAPI endpoints for workflow management and human review

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work for demo)
```

### 3. Run the Demo

```bash
# Run full demo with both MATCHED and FAILED scenarios
python demo.py

# Run demo with REJECT decision
python demo.py --reject
```

### 4. Start the API Server

```bash
python main.py
# Or with uvicorn:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access the Application

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Workflow Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/workflow/start` | Start new invoice workflow |
| GET | `/api/workflow/{id}/status` | Get workflow status |
| GET | `/api/workflow/{id}/audit-log` | Get audit log |

### Human Review (HITL)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/human-review/pending` | List pending reviews |
| GET | `/api/human-review/{checkpoint_id}` | Get review details |
| POST | `/api/human-review/decision` | Submit ACCEPT/REJECT decision |

### Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/bigtool/selections` | View Bigtool tool selections |
| GET | `/api/mcp/execution-log` | View MCP execution log |

## Sample Invoice Payload

```json
{
  "invoice_id": "INV-2024-001",
  "vendor_name": "Acme Corp",
  "vendor_tax_id": "TAX123456789",
  "invoice_date": "2024-01-15",
  "due_date": "2024-02-15",
  "amount": 10000.00,
  "currency": "USD",
  "line_items": [
    {"desc": "Consulting Services", "qty": 10, "unit_price": 500, "total": 5000},
    {"desc": "Software License", "qty": 1, "unit_price": 5000, "total": 5000}
  ],
  "attachments": ["invoice.pdf"],
  "po_number": "PO-2024-001"
}
```

## Workflow Stages

| Stage | Mode | Server | Description |
|-------|------|--------|-------------|
| INTAKE | Deterministic | COMMON | Validate and persist invoice |
| UNDERSTAND | Deterministic | ATLAS | OCR extraction, parse line items |
| PREPARE | Deterministic | COMMON/ATLAS | Normalize vendor, enrich data |
| RETRIEVE | Deterministic | ATLAS | Fetch PO, GRN, history from ERP |
| MATCH_TWO_WAY | Deterministic | COMMON | Compute 2-way match score |
| CHECKPOINT_HITL | Deterministic | COMMON | Create checkpoint if match fails |
| HITL_DECISION | Non-Deterministic | ATLAS | Process human decision |
| RECONCILE | Deterministic | COMMON | Build accounting entries |
| APPROVE | Deterministic | ATLAS | Apply approval policies |
| POSTING | Deterministic | ATLAS | Post to ERP, schedule payment |
| NOTIFY | Deterministic | ATLAS | Send notifications |
| COMPLETE | Deterministic | COMMON | Finalize workflow |

## Bigtool Pools

| Capability | Available Tools |
|------------|-----------------|
| OCR | google_vision, tesseract, aws_textract |
| Enrichment | clearbit, people_data_labs, vendor_db |
| ERP Connector | sap_sandbox, netsuite, mock_erp |
| Database | postgres, sqlite, dynamodb |
| Email | sendgrid, smartlead, ses |
| Storage | s3, gcs, local_fs |

## Project Structure

```
├── main.py                 # FastAPI application
├── demo.py                 # Demo script
├── workflow.json           # Workflow configuration
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── sample_invoices.json    # Sample invoice data
└── src/
    ├── api/
    │   └── routes.py       # API endpoints
    ├── bigtool/
    │   ├── picker.py       # Bigtool selector
    │   └── tools.py        # Tool pool definitions
    ├── database/
    │   ├── db.py           # Database connection
    │   └── models.py       # SQLAlchemy models
    ├── graph/
    │   └── workflow.py     # LangGraph workflow
    ├── mcp/
    │   ├── client.py       # MCP client
    │   └── abilities.py    # COMMON/ATLAS abilities
    ├── models/
    │   ├── state.py        # LangGraph state
    │   └── schemas.py      # Pydantic schemas
    └── nodes/
        ├── intake.py       # Stage 1
        ├── understand.py   # Stage 2
        ├── prepare.py      # Stage 3
        ├── retrieve.py     # Stage 4
        ├── match.py        # Stage 5
        ├── checkpoint.py   # Stage 6
        ├── hitl_decision.py # Stage 7
        ├── reconcile.py    # Stage 8
        ├── approve.py      # Stage 9
        ├── posting.py      # Stage 10
        ├── notify.py       # Stage 11
        └── complete.py     # Stage 12
```

## Testing the HITL Flow

1. Start the server: `python main.py`
2. Submit an invoice without PO number (will fail match)
3. Check pending reviews: `GET /api/human-review/pending`
4. Submit decision: `POST /api/human-review/decision`
5. Workflow resumes automatically

## License

MIT
