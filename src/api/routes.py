"""
FastAPI Routes for Invoice Processing API
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from src.models.schemas import (
    InvoicePayload, HumanDecision, HumanDecisionResponse,
    HumanReviewItem, WorkflowResponse, WorkflowStatusResponse
)
from src.graph.workflow import get_invoice_graph
from src.database import get_db
from src.database.models import CheckpointModel, WorkflowStateModel, AuditLogModel
from src.bigtool.picker import get_bigtool_picker
from src.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/workflow/start", response_model=WorkflowResponse)
async def start_workflow(invoice: InvoicePayload):
    """
    Start a new invoice processing workflow
    
    This endpoint accepts an invoice payload and initiates the full
    LangGraph workflow with all 12 stages.
    """
    logger.info(f"Starting workflow for invoice: {invoice.invoice_id}")
    
    graph = get_invoice_graph()
    
    # Convert Pydantic model to dict
    invoice_dict = invoice.model_dump()
    
    result = await graph.start_workflow(invoice_dict)
    
    return WorkflowResponse(
        workflow_id=result.get("workflow_id", ""),
        status=result.get("status", "UNKNOWN"),
        current_stage=result.get("current_stage", "COMPLETE"),
        message=result.get("message", ""),
        data={
            "checkpoint_id": result.get("checkpoint_id"),
            "review_url": result.get("review_url"),
            "final_payload": result.get("final_payload")
        }
    )


@router.get("/workflow/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """
    Get the current status of a workflow
    """
    db = get_db()
    
    with db.get_session() as session:
        workflow = session.query(WorkflowStateModel).filter(
            WorkflowStateModel.workflow_id == workflow_id
        ).first()
        
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        
        # Check for checkpoint
        checkpoint = session.query(CheckpointModel).filter(
            CheckpointModel.workflow_id == workflow_id,
            CheckpointModel.status == "PENDING"
        ).first()
        
        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=workflow.status,
            current_stage=workflow.current_stage,
            started_at=workflow.started_at.isoformat() if workflow.started_at else "",
            updated_at=workflow.updated_at.isoformat() if workflow.updated_at else "",
            is_paused=workflow.status == "PAUSED",
            checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
            final_payload=workflow.state_data.get("final_payload") if workflow.state_data else None
        )


@router.get("/human-review/pending", response_model=List[HumanReviewItem])
async def list_pending_reviews():
    """
    List all pending human review items
    
    This endpoint returns all invoices that are waiting for human review
    due to failed matching or other issues.
    """
    db = get_db()
    
    with db.get_session() as session:
        checkpoints = session.query(CheckpointModel).filter(
            CheckpointModel.status == "PENDING"
        ).all()
        
        items = []
        for cp in checkpoints:
            items.append(HumanReviewItem(
                checkpoint_id=cp.checkpoint_id,
                invoice_id=cp.invoice_id,
                vendor_name=cp.vendor_name,
                amount=cp.amount,
                created_at=cp.created_at.isoformat() if cp.created_at else "",
                reason_for_hold=cp.reason_for_hold or "",
                review_url=cp.review_url or ""
            ))
        
        return items


@router.get("/human-review/{checkpoint_id}")
async def get_review_details(checkpoint_id: str):
    """
    Get detailed information for a specific review item
    """
    db = get_db()
    
    with db.get_session() as session:
        checkpoint = session.query(CheckpointModel).filter(
            CheckpointModel.checkpoint_id == checkpoint_id
        ).first()
        
        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"Checkpoint {checkpoint_id} not found")
        
        return {
            "checkpoint_id": checkpoint.checkpoint_id,
            "workflow_id": checkpoint.workflow_id,
            "invoice_id": checkpoint.invoice_id,
            "vendor_name": checkpoint.vendor_name,
            "amount": checkpoint.amount,
            "status": checkpoint.status,
            "reason_for_hold": checkpoint.reason_for_hold,
            "review_url": checkpoint.review_url,
            "created_at": checkpoint.created_at.isoformat() if checkpoint.created_at else "",
            "state_data": checkpoint.state_blob
        }


@router.post("/human-review/decision", response_model=HumanDecisionResponse)
async def submit_decision(decision: HumanDecision):
    """
    Submit a human review decision (ACCEPT or REJECT)
    
    This endpoint processes the human decision and resumes the workflow:
    - ACCEPT: Resume workflow at RECONCILE stage
    - REJECT: Finalize workflow with MANUAL_HANDOFF status
    """
    logger.info(f"Processing decision for checkpoint: {decision.checkpoint_id}")
    logger.info(f"Decision: {decision.decision} by {decision.reviewer_id}")
    
    graph = get_invoice_graph()
    
    result = await graph.resume_workflow(
        checkpoint_id=decision.checkpoint_id,
        decision=decision.decision.value,
        reviewer_id=decision.reviewer_id,
        notes=decision.notes
    )
    
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    next_stage = "RECONCILE" if decision.decision.value == "ACCEPT" else "COMPLETE"
    
    return HumanDecisionResponse(
        resume_token=f"RESUME-{decision.checkpoint_id}",
        next_stage=next_stage,
        message=result.get("message", "Decision processed")
    )


@router.get("/workflow/{workflow_id}/audit-log")
async def get_audit_log(workflow_id: str):
    """
    Get the audit log for a workflow
    """
    db = get_db()
    
    with db.get_session() as session:
        logs = session.query(AuditLogModel).filter(
            AuditLogModel.workflow_id == workflow_id
        ).order_by(AuditLogModel.timestamp).all()
        
        return [
            {
                "id": log.id,
                "stage": log.stage,
                "action": log.action,
                "details": log.details,
                "bigtool_selection": log.bigtool_selection,
                "mcp_server": log.mcp_server,
                "timestamp": log.timestamp.isoformat() if log.timestamp else ""
            }
            for log in logs
        ]


@router.get("/bigtool/selections")
async def get_bigtool_selections():
    """
    Get all Bigtool tool selections made during workflow execution
    """
    picker = get_bigtool_picker()
    return {
        "selections": picker.get_selection_log(),
        "available_pools": {
            "ocr": ["google_vision", "tesseract", "aws_textract"],
            "enrichment": ["clearbit", "people_data_labs", "vendor_db"],
            "erp_connector": ["sap_sandbox", "netsuite", "mock_erp"],
            "db": ["postgres", "sqlite", "dynamodb"],
            "email": ["sendgrid", "smartlead", "ses"],
            "storage": ["s3", "gcs", "local_fs"]
        }
    }


@router.get("/mcp/execution-log")
async def get_mcp_execution_log():
    """
    Get the MCP execution log showing all ability calls
    """
    mcp = get_mcp_client()
    return {
        "executions": mcp.get_execution_log(),
        "servers": {
            "COMMON": "Internal processing (validation, matching, normalization)",
            "ATLAS": "External integrations (ERP, enrichment, notifications)"
        }
    }


@router.delete("/workflow/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """
    Delete a workflow and all associated data (for testing)
    """
    db = get_db()
    
    with db.get_session() as session:
        # Delete audit logs
        session.query(AuditLogModel).filter(
            AuditLogModel.workflow_id == workflow_id
        ).delete()
        
        # Delete checkpoints
        session.query(CheckpointModel).filter(
            CheckpointModel.workflow_id == workflow_id
        ).delete()
        
        # Delete workflow state
        session.query(WorkflowStateModel).filter(
            WorkflowStateModel.workflow_id == workflow_id
        ).delete()
        
        session.commit()
    
    return {"message": f"Workflow {workflow_id} deleted"}


@router.post("/reset")
async def reset_system():
    """
    Reset the system (clear all data, for testing)
    """
    db = get_db()
    
    # Clear bigtool and MCP logs
    picker = get_bigtool_picker()
    picker.clear_log()
    
    mcp = get_mcp_client()
    mcp.clear_log()
    
    # Recreate tables
    db.drop_tables()
    db.create_tables()
    
    return {"message": "System reset complete"}
