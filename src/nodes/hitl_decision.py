"""
HITL_DECISION Node - Process human decision (Accept/Reject)
Server: ATLAS
"""
import logging
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState, WorkflowStatus
from src.mcp.client import get_mcp_client, MCPServer
from src.database import get_db
from src.database.models import CheckpointModel

logger = logging.getLogger(__name__)


async def hitl_decision_node(state: InvoiceState) -> Dict[str, Any]:
    """
    HITL_DECISION Stage: Process human decision after review
    
    This is a NON-DETERMINISTIC node - behavior depends on human decision.
    
    Actions:
    - Read stored checkpoint state
    - Get reviewer decision (ACCEPT / REJECT)
    - If ACCEPT → resume workflow at RECONCILE
    - If REJECT → finalize workflow with status MANUAL_HANDOFF
    
    Server: ATLAS
    """
    logger.info("=" * 50)
    logger.info("STAGE: HITL_DECISION - Processing human decision")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    db = get_db()
    
    checkpoint_id = state.get("hitl_checkpoint_id", "")
    human_decision = state.get("human_decision", "")
    reviewer_id = state.get("reviewer_id", "")
    
    if not human_decision:
        logger.error("No human decision provided")
        return {
            "current_stage": "HITL_DECISION",
            "errors": state.get("errors", []) + [{
                "stage": "HITL_DECISION",
                "error": "No human decision provided",
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
    
    logger.info(f"Human decision: {human_decision} by reviewer: {reviewer_id}")
    
    # Get decision details via ATLAS server
    decision_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="get_human_decision",
        params={
            "checkpoint_id": checkpoint_id,
            "decision": human_decision,
            "reviewer_id": reviewer_id
        }
    )
    
    resume_token = decision_result.data.get("resume_token")
    next_stage = decision_result.data.get("next_stage", "COMPLETE")
    
    # Update checkpoint in database
    with db.get_session() as session:
        checkpoint = session.query(CheckpointModel).filter(
            CheckpointModel.checkpoint_id == checkpoint_id
        ).first()
        
        if checkpoint:
            checkpoint.status = "ACCEPTED" if human_decision == "ACCEPT" else "REJECTED"
            checkpoint.reviewer_id = reviewer_id
            checkpoint.decision_at = datetime.utcnow()
            session.commit()
    
    if human_decision == "ACCEPT":
        logger.info("Invoice ACCEPTED - Resuming workflow at RECONCILE")
        return {
            "current_stage": "HITL_DECISION",
            "workflow_status": WorkflowStatus.RUNNING.value,
            "human_decision": human_decision,
            "reviewer_id": reviewer_id,
            "resume_token": resume_token,
            "next_stage": "RECONCILE",
            "updated_at": datetime.utcnow().isoformat()
        }
    else:
        logger.info("Invoice REJECTED - Finalizing with MANUAL_HANDOFF status")
        return {
            "current_stage": "HITL_DECISION",
            "workflow_status": WorkflowStatus.MANUAL_HANDOFF.value,
            "human_decision": human_decision,
            "reviewer_id": reviewer_id,
            "resume_token": None,
            "next_stage": "COMPLETE",
            "updated_at": datetime.utcnow().isoformat()
        }
