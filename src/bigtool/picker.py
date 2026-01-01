"""
Bigtool Picker - Dynamically selects tools from pool based on context
"""
import os
import logging
from typing import Dict, Any, Optional, List
from .tools import ToolPool, Tool

logger = logging.getLogger(__name__)


class BigtoolPicker:
    """
    Bigtool dynamically selects the best tool from a pool based on:
    - Context (invoice amount, vendor, etc.)
    - Tool availability
    - Priority/preference
    - Environment configuration
    """
    
    def __init__(self):
        self.pool = ToolPool()
        self.selection_log: List[Dict[str, Any]] = []
        
        # Default tool preferences from environment
        self.defaults = {
            "ocr": os.getenv("DEFAULT_OCR_TOOL", "tesseract"),
            "enrichment": os.getenv("DEFAULT_ENRICHMENT_TOOL", "vendor_db"),
            "erp_connector": os.getenv("DEFAULT_ERP_TOOL", "mock_erp"),
            "db": os.getenv("DEFAULT_DB_TOOL", "sqlite"),
            "email": os.getenv("DEFAULT_EMAIL_TOOL", "ses"),
            "storage": os.getenv("DEFAULT_STORAGE_TOOL", "local_fs"),
        }
    
    def select(
        self, 
        capability: str, 
        context: Dict[str, Any] = None,
        pool_hint: List[str] = None,
        prefer: str = None
    ) -> Tool:
        """
        Select the best tool for a capability
        
        Args:
            capability: The capability needed (ocr, enrichment, etc.)
            context: Context data to influence selection
            pool_hint: List of acceptable tools
            prefer: Explicitly preferred tool name
        
        Returns:
            Selected Tool object
        """
        context = context or {}
        available_tools = self.pool.get_available_tools(capability)
        
        if not available_tools:
            logger.warning(f"No available tools for capability: {capability}")
            return None
        
        # Filter by pool_hint if provided
        if pool_hint:
            available_tools = [t for t in available_tools if t.name in pool_hint]
        
        if not available_tools:
            logger.warning(f"No tools match pool_hint for {capability}")
            return None
        
        selected = None
        selection_reason = ""
        
        # 1. Check explicit preference
        if prefer:
            for tool in available_tools:
                if tool.name == prefer:
                    selected = tool
                    selection_reason = f"Explicit preference: {prefer}"
                    break
        
        # 2. Check environment default
        if not selected and capability in self.defaults:
            default_name = self.defaults[capability]
            for tool in available_tools:
                if tool.name == default_name:
                    selected = tool
                    selection_reason = f"Environment default: {default_name}"
                    break
        
        # 3. Context-based selection
        if not selected and context:
            selected = self._select_by_context(capability, available_tools, context)
            if selected:
                selection_reason = f"Context-based selection"
        
        # 4. Fallback to highest priority
        if not selected:
            selected = max(available_tools, key=lambda t: t.priority)
            selection_reason = f"Highest priority fallback"
        
        # Log selection
        log_entry = {
            "capability": capability,
            "selected_tool": selected.name,
            "reason": selection_reason,
            "context_keys": list(context.keys()) if context else [],
            "available_options": [t.name for t in available_tools]
        }
        self.selection_log.append(log_entry)
        logger.info(f"Bigtool selected '{selected.name}' for '{capability}': {selection_reason}")
        
        return selected
    
    def _select_by_context(
        self, 
        capability: str, 
        tools: List[Tool], 
        context: Dict[str, Any]
    ) -> Optional[Tool]:
        """Apply context-based selection rules"""
        
        # OCR selection based on attachment type
        if capability == "ocr":
            attachments = context.get("attachments", [])
            if any(".pdf" in a.lower() for a in attachments):
                # Prefer AWS Textract for PDFs
                for t in tools:
                    if t.name == "aws_textract":
                        return t
        
        # Enrichment selection based on vendor region
        if capability == "enrichment":
            vendor_tax_id = context.get("vendor_tax_id", "")
            # Indian vendors (GST/PAN)
            if vendor_tax_id and len(vendor_tax_id) in [10, 15]:
                for t in tools:
                    if t.name == "vendor_db":
                        return t
        
        # ERP selection based on amount (high value = production ERP)
        if capability == "erp_connector":
            amount = context.get("amount", 0)
            if amount > 100000:
                for t in tools:
                    if t.name == "sap_sandbox":
                        return t
        
        return None
    
    def get_selection_log(self) -> List[Dict[str, Any]]:
        """Get all tool selections made"""
        return self.selection_log
    
    def clear_log(self):
        """Clear selection log"""
        self.selection_log = []


# Global instance
_picker_instance = None


def get_bigtool_picker() -> BigtoolPicker:
    global _picker_instance
    if _picker_instance is None:
        _picker_instance = BigtoolPicker()
    return _picker_instance
