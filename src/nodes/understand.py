"""
UNDERSTAND Node - OCR extraction and line item parsing
Server: ATLAS (OCR), COMMON (parsing)
"""
import logging
from datetime import datetime
from typing import Dict, Any
from src.models.state import InvoiceState
from src.mcp.client import get_mcp_client, MCPServer
from src.bigtool.picker import get_bigtool_picker

logger = logging.getLogger(__name__)


async def understand_node(state: InvoiceState) -> Dict[str, Any]:
    """
    UNDERSTAND Stage: Run OCR on attachments, parse line items
    
    This is a DETERMINISTIC node.
    Bigtool selects OCR provider (Google Vision / Tesseract / AWS Textract)
    Server: ATLAS for OCR, COMMON for parsing
    """
    logger.info("=" * 50)
    logger.info("STAGE: UNDERSTAND - OCR extraction and parsing")
    logger.info("=" * 50)
    
    mcp = get_mcp_client()
    bigtool = get_bigtool_picker()
    
    invoice_payload = state.get("invoice_payload", {})
    attachments = invoice_payload.get("attachments", [])
    
    # Select OCR tool using Bigtool
    ocr_tool = bigtool.select(
        capability="ocr",
        context={
            "attachments": attachments,
            "amount": invoice_payload.get("amount", 0)
        },
        pool_hint=["google_vision", "tesseract", "aws_textract"]
    )
    logger.info(f"Bigtool selected OCR: {ocr_tool.name}")
    
    # Run OCR via ATLAS server
    ocr_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="ocr_extract",
        params={
            "attachments": attachments,
            "ocr_tool": ocr_tool.name
        }
    )
    
    if not ocr_result.success:
        logger.error(f"OCR extraction failed: {ocr_result.error}")
        return {
            "current_stage": "UNDERSTAND",
            "errors": state.get("errors", []) + [{
                "stage": "UNDERSTAND",
                "error": ocr_result.error,
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
    
    invoice_text = ocr_result.data.get("invoice_text", "")
    
    # Parse line items via ATLAS server
    parse_result = await mcp.execute_ability(
        server=MCPServer.ATLAS,
        ability="parse_line_items",
        params={
            "invoice_text": invoice_text,
            "invoice_payload": invoice_payload
        }
    )
    
    parsed_invoice = {
        "invoice_text": invoice_text,
        "parsed_line_items": parse_result.data.get("parsed_line_items", []),
        "detected_pos": parse_result.data.get("detected_pos", []),
        "currency": parse_result.data.get("currency", "USD"),
        "parsed_dates": parse_result.data.get("parsed_dates", {})
    }
    
    logger.info(f"Parsed {len(parsed_invoice['parsed_line_items'])} line items")
    
    # Update bigtool selections
    bigtool_selections = state.get("bigtool_selections", {})
    bigtool_selections["ocr"] = ocr_tool.name
    
    return {
        "current_stage": "UNDERSTAND",
        "parsed_invoice": parsed_invoice,
        "ocr_tool_used": ocr_tool.name,
        "updated_at": datetime.utcnow().isoformat(),
        "bigtool_selections": bigtool_selections
    }
