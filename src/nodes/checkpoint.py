"""
CHECKPOINT_HITL Node - Create checkpoint for human review
Server: COMMON
"""
import logging
import uuid
import json
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState, WorkflowStatus
from src.mcp.client import get_mcp_client, MCPServer
from src.bigtool.picker import get_bigtool_picker
from src.database import get_db
from src.database.models import CheckpointModel

logger = logging.getLogger(__name__)


async def checkpoint_hitl_node(state: InvoiceState) -> Dict[str, Any]:
    """
    CHECKPOINT_HITL Stage: Create checkpoint for human review
    
    Triggered ONLY IF match_result == 'FAILED'
    This is a DETERMINISTIC node.
    
    Actions:
    - Create a LangGraph Checkpoint
    - Persist full workflow state to DB
    - Add entry into Human Review queue
    - Generate a review_url for the reviewer
    - Pause execution (PAUSED state)
    
    Server: COMMON
    Bigtool selects DB tool (Postgres / SQLite / Dynamo)
    """
    logger.info("=" * 50)
    logger.info("STAGE: CHECKPOINT_HITL - Creating human review checkpoint")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    bigtool = get_bigtool_picker()
    db = get_db()
    
    invoice_payload = state.get("invoice_payload", {})
    workflow_id = state.get("workflow_id", "")
    match_score = state.get("match_score", 0)
    match_evidence = state.get("match_evidence", {})
    
    # Select DB tool using Bigtool
    db_tool = bigtool.select(
        capability="db",
        context={"workflow_id": workflow_id},
        pool_hint=["postgres", "sqlite", "dynamodb"]
    )
    logger.info(f"Bigtool selected DB: {db_tool.name}")
    
    # Create checkpoint via COMMON server
    checkpoint_result = await mcp.execute_ability(
        server=MCPServer.COMMON,
        ability="create_checkpoint",
        params={
            "workflow_id": workflow_id,
            "reason": f"Match score {match_score:.3f} below threshold"
        }
    )
    
    checkpoint_id = checkpoint_result.data.get("checkpoint_id", f"CHKPT-{uuid.uuid4().hex[:8].upper()}")
    review_url = checkpoint_result.data.get("review_url", f"/human-review/{checkpoint_id}")
    paused_reason = checkpoint_result.data.get("paused_reason", "Match score below threshold")
    
    # Prepare state blob for persistence (exclude non-serializable items)
    state_blob = {
        "workflow_id": workflow_id,
        "invoice_payload": invoice_payload,
        "vendor_profile": state.get("vendor_profile", {}),
        "normalized_invoice": state.get("normalized_invoice", {}),
        "matched_pos": state.get("matched_pos", []),
        "match_score": match_score,
        "match_result": state.get("match_result", "FAILED"),
        "match_evidence": match_evidence,
        "flags": state.get("flags", {}),
        "bigtool_selections": state.get("bigtool_selections", {})
    }
    
    # Persist checkpoint to database
    with db.get_session() as session:
        checkpoint = CheckpointModel(
            checkpoint_id=checkpoint_id,
            workflow_id=workflow_id,
            invoice_id=invoice_payload.get("invoice_id", ""),
            vendor_name=invoice_payload.get("vendor_name", ""),
            amount=invoice_payload.get("amount", 0),
            state_blob=state_blob,
            reason_for_hold=paused_reason,
            review_url=review_url,
            status="PENDING"
        )
        session.add(checkpoint)
        session.commit()
    
    logger.info(f"Checkpoint created: {checkpoint_id}")
    logger.info(f"Review URL: {review_url}")
    logger.info("Workflow PAUSED - Awaiting human decision")
    
    # Update bigtool selections
    bigtool_selections = state.get("bigtool_selections", {})
    bigtool_selections["db"] = db_tool.name
    
    return {
        "current_stage": "CHECKPOINT_HITL",
        "workflow_status": WorkflowStatus.PAUSED.value,
        "hitl_checkpoint_id": checkpoint_id,
        "review_url": review_url,
        "paused_reason": paused_reason,
        "db_tool_used": db_tool.name,
        "updated_at": datetime.utcnow().isoformat(),
        "bigtool_selections": bigtool_selections
    }
