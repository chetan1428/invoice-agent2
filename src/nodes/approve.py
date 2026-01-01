"""
APPROVE Node - Apply invoice approval policy
Server: ATLAS
"""
import logging
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState
from src.mcp.client import get_mcp_client, MCPServer

logger = logging.getLogger(__name__)


async def approve_node(state: InvoiceState) -> Dict[str, Any]:
    """
    APPROVE Stage: Apply approval policies (auto-approve or escalate)
    
    This is a DETERMINISTIC node.
    Server: ATLAS (if integration needed)
    """
    logger.info("=" * 50)
    logger.info("STAGE: APPROVE - Applying approval policy")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    
    invoice_payload = state.get("invoice_payload", {})
    normalized_invoice = state.get("normalized_invoice", {})
    
    amount = normalized_invoice.get("amount", invoice_payload.get("amount", 0))
    
    # Apply approval policy via ATLAS server
    approval_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="apply_approval_policy",
        params={
            "invoice_id": invoice_payload.get("invoice_id"),
            "amount": amount,
            "vendor_name": invoice_payload.get("vendor_name"),
            "auto_approve_threshold": 10000  # Could be configurable
        }
    )
    
    approval_status = approval_result.data.get("approval_status", "PENDING")
    approver_id = approval_result.data.get("approver_id")
    approval_reason = approval_result.data.get("approval_reason", "")
    
    logger.info(f"Approval status: {approval_status}")
    if approver_id:
        logger.info(f"Approver: {approver_id}")
    logger.info(f"Reason: {approval_reason}")
    
    return {
        "current_stage": "APPROVE",
        "approval_status": approval_status,
        "approver_id": approver_id,
        "updated_at": datetime.utcnow().isoformat()
    }
