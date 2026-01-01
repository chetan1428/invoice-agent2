"""
COMPLETE Node - Finalize workflow and output final payload
Server: COMMON
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState, WorkflowStatus
from src.mcp.client import get_mcp_client, MCPServer
from src.bigtool.picker import get_bigtool_picker
from src.database import get_db
from src.database.models import AuditLogModel, WorkflowStateModel

logger = logging.getLogger(__name__)


async def complete_node(state: InvoiceState) -> Dict[str, Any]:
    """
    COMPLETE Stage: Produce final payload and audit log, mark workflow complete
    
    This is a DETERMINISTIC node.
    Bigtool selects DB tool.
    Server: COMMON
    """
    logger.info("=" * 50)
    logger.info("STAGE: COMPLETE - Finalizing workflow")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    bigtool = get_bigtool_picker()
    db = get_db()
    
    workflow_id = state.get("workflow_id", "")
    invoice_payload = state.get("invoice_payload", {})
    workflow_status = state.get("workflow_status", WorkflowStatus.COMPLETED.value)
    
    # Determine final status
    human_decision = state.get("human_decision")
    if human_decision == "REJECT":
        final_status = WorkflowStatus.MANUAL_HANDOFF.value
    elif workflow_status == WorkflowStatus.PAUSED.value:
        final_status = WorkflowStatus.PAUSED.value
    else:
        final_status = WorkflowStatus.COMPLETED.value
    
    # Select DB tool using Bigtool
    db_tool = bigtool.select(
        capability="db",
        context={"workflow_id": workflow_id},
        pool_hint=["postgres", "sqlite", "dynamodb"]
    )
    logger.info(f"Bigtool selected DB: {db_tool.name}")
    
    # Build final payload
    final_payload = {
        "workflow_id": workflow_id,
        "invoice_id": invoice_payload.get("invoice_id"),
        "vendor_name": invoice_payload.get("vendor_name"),
        "amount": invoice_payload.get("amount"),
        "currency": invoice_payload.get("currency", "USD"),
        "status": final_status,
        "match_score": state.get("match_score"),
        "match_result": state.get("match_result"),
        "approval_status": state.get("approval_status"),
        "posted": state.get("posted", False),
        "erp_txn_id": state.get("erp_txn_id"),
        "scheduled_payment_id": state.get("scheduled_payment_id"),
        "accounting_entries_count": len(state.get("accounting_entries", [])),
        "notified_parties": state.get("notified_parties", []),
        "bigtool_selections": state.get("bigtool_selections", {}),
        "completed_at": datetime.utcnow().isoformat()
    }
    
    # Build audit log
    audit_log = [
        {"stage": "INTAKE", "timestamp": state.get("ingest_ts"), "action": "Invoice ingested"},
        {"stage": "UNDERSTAND", "timestamp": state.get("updated_at"), "action": f"OCR via {state.get('ocr_tool_used', 'unknown')}"},
        {"stage": "PREPARE", "timestamp": state.get("updated_at"), "action": f"Enrichment via {state.get('enrichment_tool_used', 'unknown')}"},
        {"stage": "RETRIEVE", "timestamp": state.get("updated_at"), "action": f"ERP fetch via {state.get('erp_tool_used', 'unknown')}"},
        {"stage": "MATCH_TWO_WAY", "timestamp": state.get("updated_at"), "action": f"Match score: {state.get('match_score', 0):.3f}"},
    ]
    
    if state.get("hitl_checkpoint_id"):
        audit_log.append({
            "stage": "CHECKPOINT_HITL",
            "timestamp": state.get("updated_at"),
            "action": f"Checkpoint created: {state.get('hitl_checkpoint_id')}"
        })
    
    if human_decision:
        audit_log.append({
            "stage": "HITL_DECISION",
            "timestamp": state.get("updated_at"),
            "action": f"Human decision: {human_decision} by {state.get('reviewer_id', 'unknown')}"
        })
    
    if state.get("match_result") == "MATCHED" or human_decision == "ACCEPT":
        audit_log.extend([
            {"stage": "RECONCILE", "timestamp": state.get("updated_at"), "action": "Accounting entries created"},
            {"stage": "APPROVE", "timestamp": state.get("updated_at"), "action": f"Approval: {state.get('approval_status', 'N/A')}"},
            {"stage": "POSTING", "timestamp": state.get("updated_at"), "action": f"Posted: {state.get('posted', False)}"},
            {"stage": "NOTIFY", "timestamp": state.get("updated_at"), "action": f"Notified: {state.get('notified_parties', [])}"},
        ])
    
    audit_log.append({
        "stage": "COMPLETE",
        "timestamp": datetime.utcnow().isoformat(),
        "action": f"Workflow completed with status: {final_status}"
    })
    
    # Persist audit log to database
    with db.get_session() as session:
        for entry in audit_log:
            audit = AuditLogModel(
                id=f"AUDIT-{uuid.uuid4().hex[:8]}",
                workflow_id=workflow_id,
                stage=entry["stage"],
                action=entry["action"],
                details=entry,
                timestamp=datetime.utcnow()
            )
            session.add(audit)
        
        # Update workflow state
        workflow_state = session.query(WorkflowStateModel).filter(
            WorkflowStateModel.workflow_id == workflow_id
        ).first()
        
        if workflow_state:
            workflow_state.status = final_status
            workflow_state.current_stage = "COMPLETE"
            workflow_state.completed_at = datetime.utcnow()
        
        session.commit()
    
    # Finalize via COMMON server
    await mcp.execute_ability(
        server=MCPServer.COMMON,
        ability="finalize_workflow",
        params={
            "workflow_id": workflow_id,
            "status": final_status
        }
    )
    
    logger.info(f"Workflow {workflow_id} completed with status: {final_status}")
    logger.info("=" * 50)
    logger.info("FINAL PAYLOAD:")
    for key, value in final_payload.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 50)
    
    return {
        "current_stage": "COMPLETE",
        "workflow_status": final_status,
        "final_payload": final_payload,
        "audit_log": audit_log,
        "updated_at": datetime.utcnow().isoformat()
    }
