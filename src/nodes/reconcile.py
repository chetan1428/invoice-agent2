"""
RECONCILE Node - Build accounting entries
Server: COMMON
"""
import logging
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState
from src.mcp.client import get_mcp_client, MCPServer

logger = logging.getLogger(__name__)


async def reconcile_node(state: InvoiceState) -> Dict[str, Any]:
    """
    RECONCILE Stage: Build accounting entries (debits/credits)
    
    This is a DETERMINISTIC node.
    Executed if invoice matched OR human accepted.
    Server: COMMON
    """
    logger.info("=" * 50)
    logger.info("STAGE: RECONCILE - Building accounting entries")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    
    invoice_payload = state.get("invoice_payload", {})
    normalized_invoice = state.get("normalized_invoice", {})
    vendor_profile = state.get("vendor_profile", {})
    
    vendor_name = vendor_profile.get("normalized_name", invoice_payload.get("vendor_name", ""))
    amount = normalized_invoice.get("amount", invoice_payload.get("amount", 0))
    
    # Build accounting entries via COMMON server
    accounting_result = await mcp.execute_ability(
        server=MCPServer.COMMON,
        ability="build_accounting_entries",
        params={
            "invoice": {
                "invoice_id": invoice_payload.get("invoice_id"),
                "amount": amount,
                "currency": normalized_invoice.get("currency", "USD"),
                "line_items": normalized_invoice.get("line_items", [])
            },
            "vendor_name": vendor_name
        }
    )
    
    accounting_entries = accounting_result.data.get("accounting_entries", [])
    
    reconciliation_report = {
        "invoice_id": invoice_payload.get("invoice_id"),
        "vendor_name": vendor_name,
        "total_amount": amount,
        "entries_count": len(accounting_entries),
        "total_debit": accounting_result.data.get("total_debit", 0),
        "total_credit": accounting_result.data.get("total_credit", 0),
        "balanced": accounting_result.data.get("balanced", True),
        "reconciled_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created {len(accounting_entries)} accounting entries")
    logger.info(f"Total debit: {reconciliation_report['total_debit']}, Total credit: {reconciliation_report['total_credit']}")
    
    return {
        "current_stage": "RECONCILE",
        "accounting_entries": accounting_entries,
        "reconciliation_report": reconciliation_report,
        "updated_at": datetime.utcnow().isoformat()
    }
