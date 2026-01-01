"""
INTAKE Node - Accept and validate invoice payload
Server: COMMON
"""
import logging
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState
from src.mcp.client import get_mcp_client, MCPServer
from src.bigtool.picker import get_bigtool_picker

logger = logging.getLogger(__name__)


async def intake_node(state: InvoiceState) -> Dict[str, Any]:
    """
    INTAKE Stage: Accept invoice payload, validate schema, persist raw invoice
    
    This is a DETERMINISTIC node - always executes the same sequence.
    Server: COMMON
    """
    logger.info("=" * 50)
    logger.info("STAGE: INTAKE - Accepting invoice payload")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    bigtool = get_bigtool_picker()
    
    invoice_payload = state.get("invoice_payload", {})
    
    # Select storage tool using Bigtool
    storage_tool = bigtool.select(
        capability="storage",
        context={"attachments": invoice_payload.get("attachments", [])},
        pool_hint=["s3", "gcs", "local_fs"]
    )
    logger.info(f"Bigtool selected storage: {storage_tool.name}")
    
    # Validate schema via COMMON server
    validation_result = await mcp.execute_ability(
        server=MCPServer.COMMON,
        ability="validate_schema",
        params={"invoice_payload": invoice_payload}
    )
    
    if not validation_result.success:
        logger.error(f"Schema validation failed: {validation_result.error}")
        return {
            "current_stage": "INTAKE",
            "validated": False,
            "errors": state.get("errors", []) + [{
                "stage": "INTAKE",
                "error": validation_result.error,
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
    
    validated = validation_result.data.get("validated", False)
    
    if not validated:
        missing = validation_result.data.get("missing_fields", [])
        logger.warning(f"Invoice validation failed. Missing fields: {missing}")
        return {
            "current_stage": "INTAKE",
            "validated": False,
            "errors": state.get("errors", []) + [{
                "stage": "INTAKE",
                "error": f"Missing required fields: {missing}",
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
    
    # Persist raw invoice via COMMON server
    persist_result = await mcp.execute_ability(
        server=MCPServer.COMMON,
        ability="persist_invoice",
        params={
            "invoice_payload": invoice_payload,
            "invoice_id": invoice_payload.get("invoice_id"),
            "storage_tool": storage_tool.name
        }
    )
    
    raw_id = persist_result.data.get("raw_id", "")
    ingest_ts = persist_result.data.get("ingest_ts", datetime.utcnow().isoformat())
    
    logger.info(f"Invoice ingested successfully. raw_id={raw_id}")
    
    # Update bigtool selections
    bigtool_selections = state.get("bigtool_selections", {})
    bigtool_selections["storage"] = storage_tool.name
    
    return {
        "current_stage": "INTAKE",
        "raw_id": raw_id,
        "ingest_ts": ingest_ts,
        "validated": True,
        "updated_at": datetime.utcnow().isoformat(),
        "bigtool_selections": bigtool_selections
    }
