"""
POSTING Node - Post to ERP and schedule payment
Server: ATLAS
"""
import logging
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState
from src.mcp.client import get_mcp_client, MCPServer
from src.bigtool.picker import get_bigtool_picker

logger = logging.getLogger(__name__)


async def posting_node(state: InvoiceState) -> Dict[str, Any]:
    """
    POSTING Stage: Post journal entries to ERP and schedule payment
    
    This is a DETERMINISTIC node.
    Bigtool selects ERP connector.
    Server: ATLAS
    """
    logger.info("=" * 50)
    logger.info("STAGE: POSTING - Posting to ERP and scheduling payment")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    bigtool = get_bigtool_picker()
    
    invoice_payload = state.get("invoice_payload", {})
    normalized_invoice = state.get("normalized_invoice", {})
    accounting_entries = state.get("accounting_entries", [])
    
    amount = normalized_invoice.get("amount", invoice_payload.get("amount", 0))
    due_date = invoice_payload.get("due_date", "")
    
    # Select ERP connector using Bigtool (may reuse previous selection)
    erp_tool = bigtool.select(
        capability="erp_connector",
        context={"amount": amount},
        pool_hint=["sap_sandbox", "netsuite", "mock_erp"]
    )
    logger.info(f"Bigtool selected ERP connector: {erp_tool.name}")
    
    # Post to ERP via ATLAS server
    post_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="post_to_erp",
        params={
            "invoice_id": invoice_payload.get("invoice_id"),
            "accounting_entries": accounting_entries,
            "erp_tool": erp_tool.name
        }
    )
    
    posted = post_result.data.get("posted", False)
    erp_txn_id = post_result.data.get("erp_txn_id")
    
    # Schedule payment via ATLAS server
    payment_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="schedule_payment",
        params={
            "invoice_id": invoice_payload.get("invoice_id"),
            "amount": amount,
            "due_date": due_date,
            "vendor_name": invoice_payload.get("vendor_name")
        }
    )
    
    scheduled_payment_id = payment_result.data.get("scheduled_payment_id")
    
    logger.info(f"Posted to ERP: {posted}, txn_id: {erp_txn_id}")
    logger.info(f"Payment scheduled: {scheduled_payment_id}")
    
    return {
        "current_stage": "POSTING",
        "posted": posted,
        "erp_txn_id": erp_txn_id,
        "scheduled_payment_id": scheduled_payment_id,
        "updated_at": datetime.utcnow().isoformat()
    }
