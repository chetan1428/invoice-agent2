"""
MATCH_TWO_WAY Node - Compute 2-way match score between Invoice and PO
Server: COMMON
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState
from src.mcp.client import get_mcp_client, MCPServer

logger = logging.getLogger(__name__)


async def match_two_way_node(state: InvoiceState) -> Dict[str, Any]:
    """
    MATCH_TWO_WAY Stage: Compute 2-way match score between invoice and PO
    
    This is a DETERMINISTIC node.
    If match_score < threshold → mark for HITL CHECKPOINT
    Server: COMMON
    """
    logger.info("=" * 50)
    logger.info("STAGE: MATCH_TWO_WAY - Computing match score")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    
    invoice_payload = state.get("invoice_payload", {})
    normalized_invoice = state.get("normalized_invoice", {})
    matched_pos = state.get("matched_pos", [])
    
    # Get threshold from config
    threshold = float(os.getenv("MATCH_THRESHOLD", "0.90"))
    tolerance_pct = float(os.getenv("TWO_WAY_TOLERANCE_PCT", "5"))
    
    # Prepare invoice data for matching
    invoice_for_match = {
        "invoice_id": invoice_payload.get("invoice_id"),
        "amount": normalized_invoice.get("amount", invoice_payload.get("amount", 0)),
        "line_items": normalized_invoice.get("line_items", []),
        "po_number": invoice_payload.get("po_number")
    }
    
    # Compute match score via COMMON server
    match_result = await mcp.execute_ability(
        server=MCPServer.COMMON,
        ability="compute_match_score",
        params={
            "invoice": invoice_for_match,
            "matched_pos": matched_pos,
            "threshold": threshold,
            "tolerance_pct": tolerance_pct
        }
    )
    
    match_score = match_result.data.get("match_score", 0.0)
    match_status = match_result.data.get("match_result", "FAILED")
    match_evidence = match_result.data.get("match_evidence", {})
    
    logger.info(f"Match score: {match_score:.3f} (threshold: {threshold})")
    logger.info(f"Match result: {match_status}")
    
    if match_status == "FAILED":
        logger.warning("Match FAILED - Invoice will be routed to HITL checkpoint")
    else:
        logger.info("Match PASSED - Invoice will proceed to reconciliation")
    
    return {
        "current_stage": "MATCH_TWO_WAY",
        "match_score": match_score,
        "match_result": match_status,
        "tolerance_pct": tolerance_pct,
        "match_evidence": match_evidence,
        "updated_at": datetime.utcnow().isoformat()
    }
