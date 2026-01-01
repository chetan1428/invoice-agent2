"""
LangGraph State Definition for Invoice Processing Workflow
"""
from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    MANUAL_HANDOFF = "MANUAL_HANDOFF"


class InvoiceState(TypedDict, total=False):
    """Main state object passed through all LangGraph nodes"""
    
    # Workflow metadata
    workflow_id: str
    workflow_status: str
    current_stage: str
    started_at: str
    updated_at: str
    
    # Original input
    invoice_payload: Dict[str, Any]
    
    # INTAKE stage outputs
    raw_id: str
    ingest_ts: str
    validated: bool
    
    # UNDERSTAND stage outputs
    parsed_invoice: Dict[str, Any]
    ocr_tool_used: str
    
    # PREPARE stage outputs
    vendor_profile: Dict[str, Any]
    normalized_invoice: Dict[str, Any]
    flags: Dict[str, Any]
    enrichment_tool_used: str
    
    # RETRIEVE stage outputs
    matched_pos: List[Dict[str, Any]]
    matched_grns: List[Dict[str, Any]]
    history: List[Dict[str, Any]]
    erp_tool_used: str
    
    # MATCH_TWO_WAY stage outputs
    match_score: float
    match_result: str
    tolerance_pct: float
    match_evidence: Dict[str, Any]
    
    # CHECKPOINT_HITL stage outputs
    hitl_checkpoint_id: Optional[str]
    review_url: Optional[str]
    paused_reason: Optional[str]
    db_tool_used: str
    
    # HITL_DECISION stage outputs
    human_decision: Optional[str]
    reviewer_id: Optional[str]
    resume_token: Optional[str]
    next_stage: Optional[str]
    
    # RECONCILE stage outputs
    accounting_entries: List[Dict[str, Any]]
    reconciliation_report: Dict[str, Any]
    
    # APPROVE stage outputs
    approval_status: str
    approver_id: Optional[str]
    
    # POSTING stage outputs
    posted: bool
    erp_txn_id: Optional[str]
    scheduled_payment_id: Optional[str]
    
    # NOTIFY stage outputs
    notify_status: Dict[str, Any]
    notified_parties: List[str]
    email_tool_used: str
    
    # COMPLETE stage outputs
    final_payload: Dict[str, Any]
    audit_log: List[Dict[str, Any]]
    
    # Error tracking
    errors: List[Dict[str, Any]]
    
    # Bigtool selections log
    bigtool_selections: Dict[str, str]
