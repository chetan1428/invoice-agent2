"""
NOTIFY Node - Send notifications to vendor and finance team
Server: ATLAS
"""
import logging
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState
from src.mcp.client import get_mcp_client, MCPServer
from src.bigtool.picker import get_bigtool_picker

logger = logging.getLogger(__name__)


async def notify_node(state: InvoiceState) -> Dict[str, Any]:
    """
    NOTIFY Stage: Send notifications to vendor and internal finance team
    
    This is a DETERMINISTIC node.
    Bigtool selects email provider.
    Server: ATLAS
    """
    logger.info("=" * 50)
    logger.info("STAGE: NOTIFY - Sending notifications")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    bigtool = get_bigtool_picker()
    
    invoice_payload = state.get("invoice_payload", {})
    workflow_status = state.get("workflow_status", "COMPLETED")
    
    invoice_id = invoice_payload.get("invoice_id", "")
    vendor_name = invoice_payload.get("vendor_name", "")
    
    # Select email tool using Bigtool
    email_tool = bigtool.select(
        capability="email",
        context={"vendor_name": vendor_name},
        pool_hint=["sendgrid", "smartlead", "ses"]
    )
    logger.info(f"Bigtool selected email: {email_tool.name}")
    
    # Notify vendor via ATLAS server
    vendor_notify_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="notify_vendor",
        params={
            "invoice_id": invoice_id,
            "vendor_name": vendor_name,
            "status": workflow_status,
            "email_tool": email_tool.name
        }
    )
    
    # Notify finance team via ATLAS server
    finance_notify_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="notify_finance_team",
        params={
            "invoice_id": invoice_id,
            "vendor_name": vendor_name,
            "status": workflow_status,
            "amount": invoice_payload.get("amount", 0)
        }
    )
    
    notify_status = {
        "vendor_notified": vendor_notify_result.data.get("notification_sent", False),
        "vendor_channel": vendor_notify_result.data.get("channel", "email"),
        "finance_notified": finance_notify_result.data.get("notification_sent", False),
        "finance_channel": finance_notify_result.data.get("channel", "slack")
    }
    
    notified_parties = []
    if notify_status["vendor_notified"]:
        notified_parties.append(vendor_name)
    if notify_status["finance_notified"]:
        notified_parties.append("finance-team")
    
    logger.info(f"Notified parties: {notified_parties}")
    
    # Update bigtool selections
    bigtool_selections = state.get("bigtool_selections", {})
    bigtool_selections["email"] = email_tool.name
    
    return {
        "current_stage": "NOTIFY",
        "notify_status": notify_status,
        "notified_parties": notified_parties,
        "email_tool_used": email_tool.name,
        "updated_at": datetime.utcnow().isoformat(),
        "bigtool_selections": bigtool_selections
    }
