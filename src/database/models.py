"""
SQLAlchemy ORM Models for persistence
"""
from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class InvoiceModel(Base):
    __tablename__ = "invoices"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, unique=True, index=True)
    invoice_id = Column(String, index=True)
    vendor_name = Column(String)
    vendor_tax_id = Column(String)
    amount = Column(Float)
    currency = Column(String, default="USD")
    status = Column(String, default="PENDING")
    raw_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CheckpointModel(Base):
    __tablename__ = "checkpoints"
    
    checkpoint_id = Column(String, primary_key=True)
    workflow_id = Column(String, index=True)
    invoice_id = Column(String, index=True)
    vendor_name = Column(String)
    amount = Column(Float)
    state_blob = Column(JSON)
    reason_for_hold = Column(String)
    review_url = Column(String)
    status = Column(String, default="PENDING")  # PENDING, ACCEPTED, REJECTED
    reviewer_id = Column(String, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    decision_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, index=True)
    stage = Column(String)
    action = Column(String)
    details = Column(JSON)
    bigtool_selection = Column(String, nullable=True)
    mcp_server = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class WorkflowStateModel(Base):
    __tablename__ = "workflow_states"
    
    workflow_id = Column(String, primary_key=True)
    current_stage = Column(String)
    status = Column(String)
    state_data = Column(JSON)
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
