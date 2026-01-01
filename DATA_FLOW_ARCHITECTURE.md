# LangGraph Invoice Processing Agent - Data Flow Architecture

## Overview

This document explains the complete data flow of the LangGraph Invoice Processing Agent, a 12-stage workflow system with Human-in-the-Loop (HITL) capabilities, dynamic tool selection (Bigtool), and MCP server integration.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INVOICE PROCESSING WORKFLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐   ┌────────────┐   ┌─────────┐   ┌──────────┐   ┌───────────┐ │
│  │ INTAKE  │──▶│ UNDERSTAND │──▶│ PREPARE │──▶│ RETRIEVE │──▶│MATCH_2WAY │ │
│  └─────────┘   └────────────┘   └─────────┘   └──────────┘   └─────┬─────┘ │
│                                                                     │       │
│                    ┌────────────────────────────────────────────────┘       │
│                    │                                                        │
│                    ▼                                                        │
│         ┌──────────────────┐                                                │
│         │  Match Result?   │                                                │
│         └────────┬─────────┘                                                │
│                  │                                                          │
│     ┌────────────┴────────────┐                                             │
│     │                         │                                             │
│     ▼ FAILED                  ▼ MATCHED                                     │
│  ┌──────────────┐      ┌───────────┐                                        │
│  │CHECKPOINT_   │      │ RECONCILE │◀─────────────────────┐                 │
│  │    HITL      │      └─────┬─────┘                      │                 │
│  └──────┬───────┘            │                            │                 │
│         │                    ▼                            │                 │
│         │ PAUSE       ┌───────────┐                       │                 │
│         ▼             │  APPROVE  │                       │                 │
│  ┌──────────────┐     └─────┬─────┘                       │                 │
│  │ HITL_DECISION│           │                             │                 │
│  └──────┬───────┘           ▼                             │                 │
│         │             ┌───────────┐                       │                 │
│    ┌────┴────┐        │  POSTING  │                       │                 │
│    │         │        └─────┬─────┘                       │                 │
│    ▼         ▼              │                             │                 │
│ ACCEPT    REJECT            ▼                             │                 │
│    │         │        ┌───────────┐                       │                 │
│    │         │        │  NOTIFY   │                       │                 │
│    │         │        └─────┬─────┘                       │                 │
│    │         │              │                             │                 │
│    │         │              ▼                             │                 │
│    │         │        ┌───────────┐                       │                 │
│    │         └───────▶│ COMPLETE  │◀──────────────────────┘                 │
│    │                  └───────────┘                                         │
│    └──────────────────────▲                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. InvoiceState (Central Data Object)
The `InvoiceState` TypedDict flows through all 12 nodes, accumulating data at each stage:

```python
InvoiceState = {
    # Workflow Metadata
    workflow_id: str           # Unique workflow identifier (WF-XXXXXXXX)
    workflow_status: str       # PENDING | RUNNING | PAUSED | COMPLETED | FAILED | MANUAL_HANDOFF
    current_stage: str         # Current processing stage
    
    # Input Data
    invoice_payload: Dict      # Original invoice data
    
    # Stage Outputs (accumulated)
    raw_id, parsed_invoice, vendor_profile, matched_pos, match_score...
    
    # Tool Tracking
    bigtool_selections: Dict   # Which tools were selected for each capability
}
```

### 2. MCP Servers (COMMON & ATLAS)
Two virtual servers handle different types of operations:

| Server | Purpose | Abilities |
|--------|---------|-----------|
| **COMMON** | Internal processing | validate_schema, persist_invoice, normalize_vendor, compute_flags, compute_match_score, create_checkpoint, build_accounting_entries, finalize_workflow |
| **ATLAS** | External integrations | ocr_extract, parse_line_items, enrich_vendor, fetch_po, fetch_grn, fetch_history, apply_approval_policy, post_to_erp, schedule_payment, notify_vendor, notify_finance_team |

### 3. Bigtool Picker (Dynamic Tool Selection)
Selects the best tool from pools based on context:

| Capability | Available Tools |
|------------|-----------------|
| ocr | google_vision, tesseract, aws_textract |
| enrichment | clearbit, people_data_labs, vendor_db |
| erp_connector | sap_sandbox, netsuite, mock_erp |
| db | postgres, sqlite, dynamodb |
| email | sendgrid, smartlead, ses |
| storage | s3, gcs, local_fs |

---

## Stage-by-Stage Data Flow

### Stage 1: INTAKE
**Purpose:** Accept and validate invoice payload, persist raw data

```
INPUT:
  └── invoice_payload: {invoice_id, vendor_name, amount, line_items, attachments...}

PROCESSING:
  ├── Bigtool selects STORAGE tool (s3/gcs/local_fs)
  ├── MCP COMMON: validate_schema() → Check required fields
  └── MCP COMMON: persist_invoice() → Store raw invoice

OUTPUT:
  ├── raw_id: "RAW-XXXXXXXX"
  ├── ingest_ts: "2024-01-15T10:00:00Z"
  ├── validated: true
  └── bigtool_selections.storage: "local_fs"
```

### Stage 2: UNDERSTAND
**Purpose:** OCR extraction and line item parsing

```
INPUT:
  └── invoice_payload.attachments: ["invoice.pdf"]

PROCESSING:
  ├── Bigtool selects OCR tool (google_vision/tesseract/aws_textract)
  ├── MCP ATLAS: ocr_extract() → Extract text from attachments
  └── MCP ATLAS: parse_line_items() → Parse structured data

OUTPUT:
  ├── parsed_invoice: {
  │     invoice_text: "...",
  │     parsed_line_items: [...],
  │     detected_pos: ["PO-2024-001"],
  │     currency: "USD",
  │     parsed_dates: {invoice_date, due_date}
  │   }
  ├── ocr_tool_used: "tesseract"
  └── bigtool_selections.ocr: "tesseract"
```

### Stage 3: PREPARE
**Purpose:** Normalize vendor data, enrich profile, compute risk flags

```
INPUT:
  ├── invoice_payload.vendor_name: "Acme Corp"
  └── invoice_payload.vendor_tax_id: "TAX123456"

PROCESSING:
  ├── MCP COMMON: normalize_vendor() → Standardize vendor name
  ├── Bigtool selects ENRICHMENT tool (clearbit/pdl/vendor_db)
  ├── MCP ATLAS: enrich_vendor() → Get company data
  └── MCP COMMON: compute_flags() → Calculate risk score

OUTPUT:
  ├── vendor_profile: {
  │     normalized_name: "ACME CORP",
  │     tax_id: "TAX123456",
  │     enrichment_meta: {industry, size...},
  │     credit_score: 750,
  │     risk_score: 0.25
  │   }
  ├── normalized_invoice: {amount, currency, line_items}
  ├── flags: {missing_info: [], risk_score: 0.25}
  └── bigtool_selections.enrichment: "vendor_db"
```

### Stage 4: RETRIEVE
**Purpose:** Fetch POs, GRNs, and historical data from ERP

```
INPUT:
  ├── vendor_profile.normalized_name: "ACME CORP"
  ├── invoice_payload.amount: 10000
  └── parsed_invoice.detected_pos: ["PO-2024-001"]

PROCESSING:
  ├── Bigtool selects ERP_CONNECTOR (sap/netsuite/mock_erp)
  ├── MCP ATLAS: fetch_po() → Get matching Purchase Orders
  ├── MCP ATLAS: fetch_grn() → Get Goods Received Notes
  └── MCP ATLAS: fetch_history() → Get vendor invoice history

OUTPUT:
  ├── matched_pos: [{po_number, vendor_name, amount, status}]
  ├── matched_grns: [{grn_number, po_number, received_date}]
  ├── history: [{invoice_id, amount, date, status}]
  └── bigtool_selections.erp_connector: "mock_erp"
```

### Stage 5: MATCH_TWO_WAY
**Purpose:** Compute 2-way match score between Invoice and PO

```
INPUT:
  ├── normalized_invoice.amount: 10000
  ├── normalized_invoice.line_items: [...]
  └── matched_pos: [{amount: 10200, ...}]

PROCESSING:
  └── MCP COMMON: compute_match_score() → Calculate match percentage

OUTPUT:
  ├── match_score: 0.85 (or 0.95)
  ├── match_result: "FAILED" (if < 0.90) or "MATCHED" (if >= 0.90)
  ├── tolerance_pct: 5
  └── match_evidence: {best_po, invoice_amount, po_amount, threshold_used}

ROUTING DECISION:
  ├── IF match_result == "MATCHED" → Go to RECONCILE (Stage 8)
  └── IF match_result == "FAILED" → Go to CHECKPOINT_HITL (Stage 6)
```

### Stage 6: CHECKPOINT_HITL (Conditional)
**Purpose:** Create checkpoint for human review when match fails

```
INPUT:
  ├── workflow_id: "WF-XXXXXXXX"
  ├── match_score: 0.85
  └── Full state blob for persistence

PROCESSING:
  ├── Bigtool selects DB tool (postgres/sqlite/dynamodb)
  ├── MCP COMMON: create_checkpoint() → Generate checkpoint ID
  └── Persist state_blob to CheckpointModel in database

OUTPUT:
  ├── hitl_checkpoint_id: "CHKPT-XXXXXXXX"
  ├── review_url: "/human-review/CHKPT-XXXXXXXX"
  ├── paused_reason: "Match score 0.850 below threshold"
  ├── workflow_status: "PAUSED"
  └── bigtool_selections.db: "sqlite"

⏸️ WORKFLOW PAUSES HERE - Awaiting Human Decision
```

### Stage 7: HITL_DECISION (After Human Action)
**Purpose:** Process human decision (Accept/Reject)

```
INPUT (from API call):
  ├── hitl_checkpoint_id: "CHKPT-XXXXXXXX"
  ├── human_decision: "ACCEPT" or "REJECT"
  └── reviewer_id: "reviewer@company.com"

PROCESSING:
  ├── MCP ATLAS: get_human_decision() → Validate decision
  └── Update CheckpointModel status in database

OUTPUT:
  ├── human_decision: "ACCEPT" or "REJECT"
  ├── reviewer_id: "reviewer@company.com"
  ├── resume_token: "RESUME-XXXXXXXX" (if ACCEPT)
  └── next_stage: "RECONCILE" (if ACCEPT) or "COMPLETE" (if REJECT)

ROUTING DECISION:
  ├── IF human_decision == "ACCEPT" → Go to RECONCILE (Stage 8)
  └── IF human_decision == "REJECT" → Go to COMPLETE (Stage 12) with MANUAL_HANDOFF
```

### Stage 8: RECONCILE
**Purpose:** Build accounting entries (debits/credits)

```
INPUT:
  ├── invoice_payload.invoice_id: "INV-2024-001"
  ├── normalized_invoice.amount: 10000
  └── vendor_profile.normalized_name: "ACME CORP"

PROCESSING:
  └── MCP COMMON: build_accounting_entries() → Create journal entries

OUTPUT:
  ├── accounting_entries: [
  │     {account: "2100-AP", debit: 0, credit: 10000},
  │     {account: "5000-Expense", debit: 10000, credit: 0}
  │   ]
  └── reconciliation_report: {
        invoice_id, vendor_name, total_amount,
        entries_count, total_debit, total_credit, balanced: true
      }
```

### Stage 9: APPROVE
**Purpose:** Apply approval policies (auto-approve or escalate)

```
INPUT:
  ├── invoice_payload.amount: 10000
  └── auto_approve_threshold: 10000 (configurable)

PROCESSING:
  └── MCP ATLAS: apply_approval_policy() → Check thresholds

OUTPUT:
  ├── approval_status: "AUTO_APPROVED" or "ESCALATED"
  ├── approver_id: "SYSTEM" or "MGR-001"
  └── approval_reason: "Amount $10000 at threshold"
```

### Stage 10: POSTING
**Purpose:** Post journal entries to ERP and schedule payment

```
INPUT:
  ├── accounting_entries: [...]
  ├── invoice_payload.due_date: "2024-02-15"
  └── invoice_payload.amount: 10000

PROCESSING:
  ├── Bigtool selects ERP_CONNECTOR
  ├── MCP ATLAS: post_to_erp() → Post journal entries
  └── MCP ATLAS: schedule_payment() → Schedule payment

OUTPUT:
  ├── posted: true
  ├── erp_txn_id: "ERP-TXN-XXXXXXXX"
  └── scheduled_payment_id: "PAY-XXXXXXXX"
```

### Stage 11: NOTIFY
**Purpose:** Send notifications to vendor and finance team

```
INPUT:
  ├── invoice_payload.vendor_name: "Acme Corp"
  ├── invoice_payload.invoice_id: "INV-2024-001"
  └── workflow_status: "COMPLETED"

PROCESSING:
  ├── Bigtool selects EMAIL tool (sendgrid/smartlead/ses)
  ├── MCP ATLAS: notify_vendor() → Email to vendor
  └── MCP ATLAS: notify_finance_team() → Slack to finance

OUTPUT:
  ├── notify_status: {vendor_notified: true, finance_notified: true}
  ├── notified_parties: ["Acme Corp", "finance-team"]
  └── bigtool_selections.email: "ses"
```

### Stage 12: COMPLETE
**Purpose:** Finalize workflow, produce final payload and audit log

```
INPUT:
  └── Full accumulated state from all previous stages

PROCESSING:
  ├── Bigtool selects DB tool
  ├── Build final_payload summary
  ├── Build audit_log with all stage actions
  ├── Persist AuditLogModel entries to database
  ├── Update WorkflowStateModel status
  └── MCP COMMON: finalize_workflow()

OUTPUT:
  ├── final_payload: {
  │     workflow_id, invoice_id, vendor_name, amount,
  │     status: "COMPLETED" | "MANUAL_HANDOFF",
  │     match_score, approval_status, posted,
  │     erp_txn_id, scheduled_payment_id,
  │     bigtool_selections, completed_at
  │   }
  ├── audit_log: [{stage, timestamp, action}, ...]
  └── workflow_status: "COMPLETED" or "MANUAL_HANDOFF"
```

---

## Data Flow Scenarios

### Scenario A: Happy Path (Match Succeeds)
```
INTAKE → UNDERSTAND → PREPARE → RETRIEVE → MATCH_TWO_WAY (MATCHED)
    → RECONCILE → APPROVE → POSTING → NOTIFY → COMPLETE
    
Status: COMPLETED
Stages Executed: 10
```

### Scenario B: HITL Accept Path
```
INTAKE → UNDERSTAND → PREPARE → RETRIEVE → MATCH_TWO_WAY (FAILED)
    → CHECKPOINT_HITL (PAUSED)
    
    [Human Reviews and ACCEPTS]
    
    → HITL_DECISION (ACCEPT) → RECONCILE → APPROVE → POSTING → NOTIFY → COMPLETE
    
Status: COMPLETED
Stages Executed: 12
```

### Scenario C: HITL Reject Path
```
INTAKE → UNDERSTAND → PREPARE → RETRIEVE → MATCH_TWO_WAY (FAILED)
    → CHECKPOINT_HITL (PAUSED)
    
    [Human Reviews and REJECTS]
    
    → HITL_DECISION (REJECT) → COMPLETE
    
Status: MANUAL_HANDOFF
Stages Executed: 8
```

---

## Database Models

```
┌─────────────────────┐     ┌─────────────────────┐
│   InvoiceModel      │     │  WorkflowStateModel │
├─────────────────────┤     ├─────────────────────┤
│ id                  │     │ workflow_id (PK)    │
│ workflow_id (FK)    │────▶│ current_stage       │
│ invoice_id          │     │ status              │
│ vendor_name         │     │ state_data (JSON)   │
│ amount              │     │ created_at          │
│ status              │     │ completed_at        │
│ raw_payload (JSON)  │     └─────────────────────┘
└─────────────────────┘              │
                                     │
┌─────────────────────┐     ┌────────▼────────────┐
│  CheckpointModel    │     │   AuditLogModel     │
├─────────────────────┤     ├─────────────────────┤
│ checkpoint_id (PK)  │     │ id (PK)             │
│ workflow_id (FK)    │     │ workflow_id (FK)    │
│ invoice_id          │     │ stage               │
│ state_blob (JSON)   │     │ action              │
│ reason_for_hold     │     │ details (JSON)      │
│ status              │     │ timestamp           │
│ reviewer_id         │     └─────────────────────┘
│ decision_at         │
└─────────────────────┘
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/workflow/start` | Start new invoice workflow |
| GET | `/workflow/{id}/status` | Get workflow status |
| GET | `/human-review/pending` | List pending HITL checkpoints |
| GET | `/human-review/{checkpoint_id}` | Get checkpoint details + UI |
| POST | `/human-review/decision` | Submit human decision |
| GET | `/workflow/{id}/audit-log` | Get workflow audit trail |
| GET | `/bigtool/selections` | Get tool selection log |
| GET | `/mcp/execution-log` | Get MCP execution log |

---

## Key Design Patterns

1. **State Accumulation**: Each node adds to `InvoiceState` without removing previous data
2. **Conditional Routing**: LangGraph conditional edges based on `match_result` and `human_decision`
3. **Checkpoint/Resume**: Full state serialization enables workflow pause and resume
4. **Tool Abstraction**: Bigtool decouples business logic from specific tool implementations
5. **Server Separation**: COMMON (internal) vs ATLAS (external) for clear responsibility boundaries

---

## Summary

The LangGraph Invoice Processing Agent processes invoices through 12 stages, with intelligent routing based on match scores and human decisions. The system uses:

- **LangGraph** for workflow orchestration
- **Bigtool** for dynamic tool selection
- **MCP** for server-based ability execution
- **SQLite** for state persistence and checkpointing
- **FastAPI** for REST API and Human Review UI

Total data transformations: 12 stages × multiple MCP abilities = ~25+ data transformations per invoice.
