"""
Pydantic schemas for API requests/responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class LineItem(BaseModel):
    desc: str
    qty: float
    unit_price: float
    total: float


class InvoicePayload(BaseModel):
    invoice_id: str
    vendor_name: str
    vendor_tax_id: str
    invoice_date: str
    due_date: str
    amount: float
    currency: str = "USD"
    line_items: List[LineItem]
    attachments: List[str] = []
    po_number: Optional[str] = None


class VendorProfile(BaseModel):
    normalized_name: str
    tax_id: str
    enrichment_meta: Dict[str, Any] = {}
    credit_score: Optional[float] = None
    risk_score: Optional[float] = None


class MatchResult(BaseModel):
    match_score: float
    match_result: str  # MATCHED or FAILED
    tolerance_pct: float
    match_evidence: Dict[str, Any]


class CheckpointData(BaseModel):
    checkpoint_id: str
    workflow_id: str
    invoice_id: str
    vendor_name: str
    amount: float
    state_blob: Dict[str, Any]
    created_at: datetime
    reason_for_hold: str
    review_url: str
    status: str = "PENDING"


class HumanReviewItem(BaseModel):
    checkpoint_id: str
    invoice_id: str
    vendor_name: str
    amount: float
    created_at: str
    reason_for_hold: str
    review_url: str


class DecisionEnum(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class HumanDecision(BaseModel):
    checkpoint_id: str
    decision: DecisionEnum
    notes: str = ""
    reviewer_id: str


class HumanDecisionResponse(BaseModel):
    resume_token: str
    next_stage: str
    message: str


class AccountingEntry(BaseModel):
    entry_id: str
    account_code: str
    account_name: str
    debit: float = 0.0
    credit: float = 0.0
    description: str


class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    current_stage: str
    message: str
    data: Optional[Dict[str, Any]] = None


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    current_stage: str
    started_at: str
    updated_at: str
    is_paused: bool
    checkpoint_id: Optional[str] = None
    final_payload: Optional[Dict[str, Any]] = None
