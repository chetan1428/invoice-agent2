"""
PREPARE Node - Normalize vendor, enrich data, compute flags
Server: COMMON (normalize, flags), ATLAS (enrichment)
"""
import logging
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState
from src.mcp.client import get_mcp_client, MCPServer
from src.bigtool.picker import get_bigtool_picker

logger = logging.getLogger(__name__)


async def prepare_node(state: InvoiceState) -> Dict[str, Any]:
    """
    PREPARE Stage: Normalize vendor name, enrich vendor data, compute flags
    
    This is a DETERMINISTIC node.
    Bigtool selects enrichment provider (Clearbit / PDL / Vendor DB)
    Server: COMMON for normalization/flags, ATLAS for enrichment
    """
    logger.info("=" * 50)
    logger.info("STAGE: PREPARE - Vendor normalization and enrichment")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    bigtool = get_bigtool_picker()
    
    invoice_payload = state.get("invoice_payload", {})
    parsed_invoice = state.get("parsed_invoice", {})
    
    vendor_name = invoice_payload.get("vendor_name", "")
    vendor_tax_id = invoice_payload.get("vendor_tax_id", "")
    
    # Normalize vendor via COMMON server
    normalize_result = await mcp.execute_ability(
        server=MCPServer.COMMON,
        ability="normalize_vendor",
        params={"vendor_name": vendor_name}
    )
    
    normalized_name = normalize_result.data.get("normalized_name", vendor_name)
    
    # Select enrichment tool using Bigtool
    enrichment_tool = bigtool.select(
        capability="enrichment",
        context={
            "vendor_name": vendor_name,
            "vendor_tax_id": vendor_tax_id,
            "amount": invoice_payload.get("amount", 0)
        },
        pool_hint=["clearbit", "people_data_labs", "vendor_db"]
    )
    logger.info(f"Bigtool selected enrichment: {enrichment_tool.name}")
    
    # Enrich vendor via ATLAS server
    enrich_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="enrich_vendor",
        params={
            "vendor_name": vendor_name,
            "vendor_tax_id": vendor_tax_id,
            "enrichment_tool": enrichment_tool.name
        }
    )
    
    vendor_profile = {
        "normalized_name": normalized_name,
        "tax_id": enrich_result.data.get("verified_tax_id", vendor_tax_id),
        "enrichment_meta": enrich_result.data.get("enrichment_meta", {}),
        "credit_score": enrich_result.data.get("credit_score"),
        "risk_score": enrich_result.data.get("risk_score")
    }
    
    # Compute flags via COMMON server
    flags_result = await mcp.execute_ability(
        server=MCPServer.COMMON,
        ability="compute_flags",
        params={
            "vendor_profile": vendor_profile,
            "invoice": invoice_payload
        }
    )
    
    flags = {
        "missing_info": flags_result.data.get("missing_info", []),
        "risk_score": flags_result.data.get("risk_score", 0)
    }
    
    # Normalized invoice data
    normalized_invoice = {
        "amount": invoice_payload.get("amount", 0),
        "currency": parsed_invoice.get("currency", invoice_payload.get("currency", "USD")),
        "line_items": parsed_invoice.get("parsed_line_items", invoice_payload.get("line_items", []))
    }
    
    logger.info(f"Vendor enriched: {normalized_name}, risk_score={flags['risk_score']}")
    
    # Update bigtool selections
    bigtool_selections = state.get("bigtool_selections", {})
    bigtool_selections["enrichment"] = enrichment_tool.name
    
    return {
        "current_stage": "PREPARE",
        "vendor_profile": vendor_profile,
        "normalized_invoice": normalized_invoice,
        "flags": flags,
        "enrichment_tool_used": enrichment_tool.name,
        "updated_at": datetime.utcnow().isoformat(),
        "bigtool_selections": bigtool_selections
    }
