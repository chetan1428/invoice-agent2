"""
MCP Abilities - Simulated implementations for COMMON and ATLAS servers
"""
import uuid
import random
from datetime import datetime
from typing import Dict, Any, List


class CommonAbilities:
    """
    COMMON Server Abilities - Internal processing, no external data needed
    """
    
    @staticmethod
    async def execute(ability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        abilities = {
            "validate_schema": CommonAbilities.validate_schema,
            "persist_invoice": CommonAbilities.persist_invoice,
            "normalize_vendor": CommonAbilities.normalize_vendor,
            "compute_flags": CommonAbilities.compute_flags,
            "compute_match_score": CommonAbilities.compute_match_score,
            "create_checkpoint": CommonAbilities.create_checkpoint,
            "build_accounting_entries": CommonAbilities.build_accounting_entries,
            "finalize_workflow": CommonAbilities.finalize_workflow,
        }
        
        if ability in abilities:
            return await abilities[ability](params)
        raise ValueError(f"Unknown COMMON ability: {ability}")
    
    @staticmethod
    async def validate_schema(params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate invoice payload schema"""
        payload = params.get("invoice_payload", {})
        required_fields = ["invoice_id", "vendor_name", "amount", "line_items"]
        
        missing = [f for f in required_fields if f not in payload or not payload[f]]
        
        return {
            "validated": len(missing) == 0,
            "missing_fields": missing,
            "validation_ts": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def persist_invoice(params: Dict[str, Any]) -> Dict[str, Any]:
        """Persist raw invoice to storage"""
        return {
            "raw_id": f"RAW-{uuid.uuid4().hex[:8].upper()}",
            "ingest_ts": datetime.utcnow().isoformat(),
            "storage_path": f"/invoices/{params.get('invoice_id', 'unknown')}"
        }
    
    @staticmethod
    async def normalize_vendor(params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize vendor name"""
        vendor_name = params.get("vendor_name", "")
        
        # Simple normalization: uppercase, remove extra spaces
        normalized = " ".join(vendor_name.upper().split())
        
        return {
            "original_name": vendor_name,
            "normalized_name": normalized,
            "normalization_rules_applied": ["uppercase", "trim_spaces"]
        }
    
    @staticmethod
    async def compute_flags(params: Dict[str, Any]) -> Dict[str, Any]:
        """Compute validation flags"""
        vendor_profile = params.get("vendor_profile", {})
        invoice = params.get("invoice", {})
        
        missing_info = []
        if not vendor_profile.get("tax_id"):
            missing_info.append("vendor_tax_id")
        if not invoice.get("po_number"):
            missing_info.append("po_reference")
        
        # Simulate risk score calculation
        risk_score = random.uniform(0.1, 0.5)
        if invoice.get("amount", 0) > 50000:
            risk_score += 0.2
        
        return {
            "missing_info": missing_info,
            "risk_score": round(min(risk_score, 1.0), 2),
            "flags_computed_at": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def compute_match_score(params: Dict[str, Any]) -> Dict[str, Any]:
        """Compute 2-way match score between invoice and PO"""
        invoice = params.get("invoice", {})
        pos = params.get("matched_pos", [])
        threshold = params.get("threshold", 0.90)
        tolerance_pct = params.get("tolerance_pct", 5)
        
        if not pos:
            return {
                "match_score": 0.0,
                "match_result": "FAILED",
                "tolerance_pct": tolerance_pct,
                "match_evidence": {"reason": "No POs found to match"}
            }
        
        # Simulate matching logic
        invoice_amount = invoice.get("amount", 0)
        best_match = None
        best_score = 0.0
        
        for po in pos:
            po_amount = po.get("amount", 0)
            if po_amount == 0:
                continue
            
            # Calculate amount match
            diff_pct = abs(invoice_amount - po_amount) / po_amount * 100
            amount_score = max(0, 1 - (diff_pct / 100))
            
            # Line items match (simplified)
            line_score = 0.8 if invoice.get("line_items") else 0.5
            
            # Combined score
            score = (amount_score * 0.6) + (line_score * 0.4)
            
            if score > best_score:
                best_score = score
                best_match = po
        
        match_result = "MATCHED" if best_score >= threshold else "FAILED"
        
        return {
            "match_score": round(best_score, 3),
            "match_result": match_result,
            "tolerance_pct": tolerance_pct,
            "match_evidence": {
                "best_po": best_match.get("po_number") if best_match else None,
                "invoice_amount": invoice_amount,
                "po_amount": best_match.get("amount") if best_match else None,
                "threshold_used": threshold
            }
        }
    
    @staticmethod
    async def create_checkpoint(params: Dict[str, Any]) -> Dict[str, Any]:
        """Create HITL checkpoint"""
        checkpoint_id = f"CHKPT-{uuid.uuid4().hex[:8].upper()}"
        workflow_id = params.get("workflow_id", "unknown")
        
        return {
            "checkpoint_id": checkpoint_id,
            "review_url": f"/human-review/{checkpoint_id}",
            "paused_reason": params.get("reason", "Match score below threshold"),
            "created_at": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def build_accounting_entries(params: Dict[str, Any]) -> Dict[str, Any]:
        """Build accounting entries for reconciliation"""
        invoice = params.get("invoice", {})
        amount = invoice.get("amount", 0)
        vendor = params.get("vendor_name", "Unknown Vendor")
        
        entries = [
            {
                "entry_id": f"JE-{uuid.uuid4().hex[:6].upper()}",
                "account_code": "2100",
                "account_name": "Accounts Payable",
                "debit": 0,
                "credit": amount,
                "description": f"AP for invoice from {vendor}"
            },
            {
                "entry_id": f"JE-{uuid.uuid4().hex[:6].upper()}",
                "account_code": "5000",
                "account_name": "Expense",
                "debit": amount,
                "credit": 0,
                "description": f"Expense for invoice from {vendor}"
            }
        ]
        
        return {
            "accounting_entries": entries,
            "total_debit": amount,
            "total_credit": amount,
            "balanced": True
        }
    
    @staticmethod
    async def finalize_workflow(params: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize workflow and produce audit log"""
        return {
            "finalized": True,
            "finalized_at": datetime.utcnow().isoformat(),
            "status": params.get("status", "COMPLETED")
        }


class AtlasAbilities:
    """
    ATLAS Server Abilities - External system interactions
    """
    
    @staticmethod
    async def execute(ability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        abilities = {
            "ocr_extract": AtlasAbilities.ocr_extract,
            "parse_line_items": AtlasAbilities.parse_line_items,
            "enrich_vendor": AtlasAbilities.enrich_vendor,
            "fetch_po": AtlasAbilities.fetch_po,
            "fetch_grn": AtlasAbilities.fetch_grn,
            "fetch_history": AtlasAbilities.fetch_history,
            "apply_approval_policy": AtlasAbilities.apply_approval_policy,
            "post_to_erp": AtlasAbilities.post_to_erp,
            "schedule_payment": AtlasAbilities.schedule_payment,
            "notify_vendor": AtlasAbilities.notify_vendor,
            "notify_finance_team": AtlasAbilities.notify_finance_team,
            "get_human_decision": AtlasAbilities.get_human_decision,
        }
        
        if ability in abilities:
            return await abilities[ability](params)
        raise ValueError(f"Unknown ATLAS ability: {ability}")
    
    @staticmethod
    async def ocr_extract(params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from invoice attachments using OCR"""
        attachments = params.get("attachments", [])
        tool_used = params.get("ocr_tool", "tesseract")
        
        # Simulate OCR extraction
        extracted_text = f"Invoice extracted using {tool_used}\n"
        extracted_text += "INVOICE #12345\nDate: 2024-01-15\nAmount: $10,000.00"
        
        return {
            "invoice_text": extracted_text,
            "ocr_tool_used": tool_used,
            "pages_processed": len(attachments) or 1,
            "confidence": 0.95
        }
    
    @staticmethod
    async def parse_line_items(params: Dict[str, Any]) -> Dict[str, Any]:
        """Parse line items from OCR text"""
        invoice_payload = params.get("invoice_payload", {})
        
        # Use provided line items or generate mock ones
        line_items = invoice_payload.get("line_items", [
            {"desc": "Service A", "qty": 1, "unit_price": 5000, "total": 5000},
            {"desc": "Service B", "qty": 2, "unit_price": 2500, "total": 5000}
        ])
        
        return {
            "parsed_line_items": line_items,
            "detected_pos": [invoice_payload.get("po_number", "PO-2024-001")],
            "currency": invoice_payload.get("currency", "USD"),
            "parsed_dates": {
                "invoice_date": invoice_payload.get("invoice_date", "2024-01-15"),
                "due_date": invoice_payload.get("due_date", "2024-02-15")
            }
        }
    
    @staticmethod
    async def enrich_vendor(params: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich vendor data from external sources"""
        vendor_name = params.get("vendor_name", "")
        tax_id = params.get("vendor_tax_id", "")
        tool_used = params.get("enrichment_tool", "vendor_db")
        
        return {
            "enrichment_meta": {
                "source": tool_used,
                "company_size": "Medium",
                "industry": "Technology",
                "founded_year": 2010,
                "headquarters": "New York, USA"
            },
            "credit_score": round(random.uniform(650, 850), 0),
            "risk_score": round(random.uniform(0.1, 0.4), 2),
            "verified_tax_id": tax_id or "TAX-UNKNOWN"
        }
    
    @staticmethod
    async def fetch_po(params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch Purchase Orders from ERP"""
        vendor_name = params.get("vendor_name", "")
        invoice_amount = params.get("amount", 0)
        po_number = params.get("po_number")
        
        # Simulate PO fetch - return matching PO if amount is close
        pos = []
        if po_number or invoice_amount > 0:
            # Create a PO that may or may not match
            po_amount = invoice_amount * random.uniform(0.85, 1.05)
            pos.append({
                "po_number": po_number or f"PO-{uuid.uuid4().hex[:6].upper()}",
                "vendor_name": vendor_name,
                "amount": round(po_amount, 2),
                "status": "APPROVED",
                "created_date": "2024-01-01"
            })
        
        return {"matched_pos": pos}
    
    @staticmethod
    async def fetch_grn(params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch Goods Received Notes from ERP"""
        po_numbers = params.get("po_numbers", [])
        
        grns = []
        for po in po_numbers[:3]:  # Limit to 3
            grns.append({
                "grn_number": f"GRN-{uuid.uuid4().hex[:6].upper()}",
                "po_number": po,
                "received_date": "2024-01-10",
                "status": "COMPLETE"
            })
        
        return {"matched_grns": grns}
    
    @staticmethod
    async def fetch_history(params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch historical invoices for vendor"""
        vendor_name = params.get("vendor_name", "")
        
        history = [
            {
                "invoice_id": f"INV-{uuid.uuid4().hex[:6].upper()}",
                "amount": random.uniform(5000, 50000),
                "date": "2023-12-15",
                "status": "PAID"
            }
        ]
        
        return {"history": history}
    
    @staticmethod
    async def apply_approval_policy(params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply approval policies"""
        amount = params.get("amount", 0)
        auto_approve_threshold = params.get("auto_approve_threshold", 10000)
        
        if amount <= auto_approve_threshold:
            return {
                "approval_status": "AUTO_APPROVED",
                "approver_id": "SYSTEM",
                "approval_reason": f"Amount ${amount} below threshold ${auto_approve_threshold}"
            }
        else:
            return {
                "approval_status": "ESCALATED",
                "approver_id": "MGR-001",
                "approval_reason": f"Amount ${amount} exceeds threshold ${auto_approve_threshold}"
            }
    
    @staticmethod
    async def post_to_erp(params: Dict[str, Any]) -> Dict[str, Any]:
        """Post journal entries to ERP"""
        entries = params.get("accounting_entries", [])
        
        return {
            "posted": True,
            "erp_txn_id": f"ERP-TXN-{uuid.uuid4().hex[:8].upper()}",
            "entries_posted": len(entries),
            "posted_at": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def schedule_payment(params: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule payment for invoice"""
        due_date = params.get("due_date", "2024-02-15")
        amount = params.get("amount", 0)
        
        return {
            "scheduled_payment_id": f"PAY-{uuid.uuid4().hex[:8].upper()}",
            "scheduled_date": due_date,
            "amount": amount,
            "payment_method": "ACH"
        }
    
    @staticmethod
    async def notify_vendor(params: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification to vendor"""
        vendor_name = params.get("vendor_name", "")
        invoice_id = params.get("invoice_id", "")
        
        return {
            "notification_sent": True,
            "recipient": vendor_name,
            "channel": "email",
            "message": f"Invoice {invoice_id} has been processed",
            "sent_at": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def notify_finance_team(params: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification to finance team"""
        invoice_id = params.get("invoice_id", "")
        status = params.get("status", "COMPLETED")
        
        return {
            "notification_sent": True,
            "recipient": "finance-team@company.com",
            "channel": "slack",
            "message": f"Invoice {invoice_id} status: {status}",
            "sent_at": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def get_human_decision(params: Dict[str, Any]) -> Dict[str, Any]:
        """Get human decision from review (called after human acts)"""
        checkpoint_id = params.get("checkpoint_id", "")
        decision = params.get("decision", "PENDING")
        
        return {
            "human_decision": decision,
            "reviewer_id": params.get("reviewer_id", ""),
            "resume_token": f"RESUME-{uuid.uuid4().hex[:8].upper()}" if decision == "ACCEPT" else None,
            "next_stage": "RECONCILE" if decision == "ACCEPT" else "COMPLETE"
        }
