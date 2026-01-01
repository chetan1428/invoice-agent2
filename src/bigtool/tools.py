"""
Tool Pool definitions for Bigtool
Each capability has multiple tool implementations
"""
from typing import Dict, List, Any, Callable
from dataclasses import dataclass
import random


@dataclass
class Tool:
    name: str
    capability: str
    description: str
    priority: int = 1  # Higher = preferred
    available: bool = True
    execute: Callable = None


class ToolPool:
    """Pool of available tools organized by capability"""
    
    def __init__(self):
        self.pools: Dict[str, List[Tool]] = {
            "ocr": [
                Tool("google_vision", "ocr", "Google Cloud Vision OCR", priority=3),
                Tool("tesseract", "ocr", "Open source Tesseract OCR", priority=2),
                Tool("aws_textract", "ocr", "AWS Textract OCR", priority=3),
            ],
            "enrichment": [
                Tool("clearbit", "enrichment", "Clearbit company enrichment", priority=3),
                Tool("people_data_labs", "enrichment", "PDL enrichment service", priority=2),
                Tool("vendor_db", "enrichment", "Internal vendor database", priority=1),
            ],
            "erp_connector": [
                Tool("sap_sandbox", "erp_connector", "SAP sandbox connector", priority=3),
                Tool("netsuite", "erp_connector", "NetSuite connector", priority=2),
                Tool("mock_erp", "erp_connector", "Mock ERP for testing", priority=1),
            ],
            "db": [
                Tool("postgres", "db", "PostgreSQL database", priority=3),
                Tool("sqlite", "db", "SQLite database", priority=1),
                Tool("dynamodb", "db", "AWS DynamoDB", priority=2),
            ],
            "email": [
                Tool("sendgrid", "email", "SendGrid email service", priority=3),
                Tool("smartlead", "email", "Smartlead email service", priority=2),
                Tool("ses", "email", "AWS SES email service", priority=2),
            ],
            "storage": [
                Tool("s3", "storage", "AWS S3 storage", priority=3),
                Tool("gcs", "storage", "Google Cloud Storage", priority=3),
                Tool("local_fs", "storage", "Local filesystem", priority=1),
            ],
        }
    
    def get_tools(self, capability: str) -> List[Tool]:
        """Get all tools for a capability"""
        return self.pools.get(capability, [])
    
    def get_available_tools(self, capability: str) -> List[Tool]:
        """Get only available tools for a capability"""
        return [t for t in self.get_tools(capability) if t.available]
    
    def get_tool_by_name(self, capability: str, name: str) -> Tool:
        """Get specific tool by name"""
        for tool in self.get_tools(capability):
            if tool.name == name:
                return tool
        return None
    
    def set_tool_availability(self, capability: str, name: str, available: bool):
        """Enable/disable a tool"""
        tool = self.get_tool_by_name(capability, name)
        if tool:
            tool.available = available
