"""
RETRIEVE Node - Fetch PO, GRN, and historical data from ERP
Server: ATLAS
"""
import logging
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState
from src.mcp.client import get_mcp_client, MCPServer
from src.bigtool.picker import get_bigtool_picker

logger = logging.getLogger(__name__)


async def retrieve_node(state: InvoiceState) -> Dict[str, Any]:
    """
    RETRIEVE Stage: Fetch POs, GRNs, and historical invoices from ERP
    
    This is a DETERMINISTIC node.
    Bigtool selects ERP connector (SAP / NetSuite / Mock ERP)
    Server: ATLAS
    """
    logger.info("=" * 50)
    logger.info("STAGE: RETRIEVE - Fetching ERP data")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    bigtool = get_bigtool_picker()
    
    invoice_payload = state.get("invoice_payload", {})
    vendor_profile = state.get("vendor_profile", {})
    parsed_invoice = state.get("parsed_invoice", {})
    
    vendor_name = vendor_profile.get("normalized_name", invoice_payload.get("vendor_name", ""))
    amount = invoice_payload.get("amount", 0)
    po_number = invoice_payload.get("po_number") or (
        parsed_invoice.get("detected_pos", [None])[0] if parsed_invoice.get("detected_pos") else None
    )
    
    # Select ERP connector using Bigtool
    erp_tool = bigtool.select(
        capability="erp_connector",
        context={
            "vendor_name": vendor_name,
            "amount": amount
        },
        pool_hint=["sap_sandbox", "netsuite", "mock_erp"]
    )
    logger.info(f"Bigtool selected ERP connector: {erp_tool.name}")
    
    # Fetch POs via ATLAS server
    po_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="fetch_po",
        params={
            "vendor_name": vendor_name,
            "amount": amount,
            "po_number": po_number,
            "erp_tool": erp_tool.name
        }
    )
    
    matched_pos = po_result.data.get("matched_pos", [])
    po_numbers = [po.get("po_number") for po in matched_pos]
    
    # Fetch GRNs via ATLAS server
    grn_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="fetch_grn",
        params={
            "po_numbers": po_numbers,
            "erp_tool": erp_tool.name
        }
    )
    
    matched_grns = grn_result.data.get("matched_grns", [])
    
    # Fetch historical invoices via ATLAS server
    history_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="fetch_history",
        params={
            "vendor_name": vendor_name,
            "erp_tool": erp_tool.name
        }
    )
    
    history = history_result.data.get("history", [])
    
    logger.info(f"Retrieved {len(matched_pos)} POs, {len(matched_grns)} GRNs, {len(history)} historical invoices")
    
    # Update bigtool selections
    bigtool_selections = state.get("bigtool_selections", {})
    bigtool_selections["erp_connector"] = erp_tool.name
    
    return {
        "current_stage": "RETRIEVE",
        "matched_pos": matched_pos,
        "matched_grns": matched_grns,
        "history": history,
        "erp_tool_used": erp_tool.name,
        "updated_at": datetime.utcnow().isoformat(),
        "bigtool_selections": bigtool_selections
    }
