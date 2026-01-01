"""
Demo Script - Run the full invoice processing workflow
"""
import asyncio
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("DEMO")

# Sample invoice payloads
SAMPLE_INVOICE_MATCHED = {
    "invoice_id": "INV-2024-001",
    "vendor_name": "Acme Corporation",
    "vendor_tax_id": "TAX123456789",
    "invoice_date": "2024-01-15",
    "due_date": "2024-02-15",
    "amount": 10000.00,
    "currency": "USD",
    "line_items": [
        {"desc": "Consulting Services", "qty": 10, "unit_price": 500, "total": 5000},
        {"desc": "Software License", "qty": 1, "unit_price": 5000, "total": 5000}
    ],
    "attachments": ["invoice_001.pdf"],
    "po_number": "PO-2024-001"
}

SAMPLE_INVOICE_FAILED_MATCH = {
    "invoice_id": "INV-2024-002",
    "vendor_name": "Beta Industries",
    "vendor_tax_id": "TAX987654321",
    "invoice_date": "2024-01-20",
    "due_date": "2024-02-20",
    "amount": 75000.00,  # High amount, likely to fail match
    "currency": "USD",
    "line_items": [
        {"desc": "Hardware Equipment", "qty": 5, "unit_price": 10000, "total": 50000},
        {"desc": "Installation Services", "qty": 1, "unit_price": 25000, "total": 25000}
    ],
    "attachments": ["invoice_002.pdf", "receipt.jpg"],
    "po_number": None  # No PO reference - will likely fail match
}


async def run_demo():
    """Run the demo workflow"""
    from dotenv import load_dotenv
    load_dotenv()
    
    from src.database import get_db
    from src.graph.workflow import get_invoice_graph
    from src.bigtool.picker import get_bigtool_picker
    from src.mcp.client import get_mcp_client
    
    # Initialize
    db = get_db()
    db.create_tables()
    
    graph = get_invoice_graph()
    bigtool = get_bigtool_picker()
    mcp = get_mcp_client()
    
    print("\n" + "=" * 70)
    print("🧾 LANGGRAPH INVOICE PROCESSING AGENT - DEMO")
    print("=" * 70)
    
    # Demo 1: Invoice that should MATCH
    print("\n" + "-" * 70)
    print("📋 DEMO 1: Processing invoice that should MATCH")
    print("-" * 70)
    print(f"Invoice ID: {SAMPLE_INVOICE_MATCHED['invoice_id']}")
    print(f"Vendor: {SAMPLE_INVOICE_MATCHED['vendor_name']}")
    print(f"Amount: ${SAMPLE_INVOICE_MATCHED['amount']:,.2f}")
    print(f"PO Number: {SAMPLE_INVOICE_MATCHED['po_number']}")
    print("-" * 70)
    
    result1 = await graph.start_workflow(SAMPLE_INVOICE_MATCHED)
    
    print("\n📊 RESULT:")
    print(json.dumps(result1, indent=2, default=str))
    
    # Demo 2: Invoice that should FAIL match (trigger HITL)
    print("\n" + "-" * 70)
    print("📋 DEMO 2: Processing invoice that should FAIL match (HITL)")
    print("-" * 70)
    print(f"Invoice ID: {SAMPLE_INVOICE_FAILED_MATCH['invoice_id']}")
    print(f"Vendor: {SAMPLE_INVOICE_FAILED_MATCH['vendor_name']}")
    print(f"Amount: ${SAMPLE_INVOICE_FAILED_MATCH['amount']:,.2f}")
    print(f"PO Number: {SAMPLE_INVOICE_FAILED_MATCH['po_number']}")
    print("-" * 70)
    
    result2 = await graph.start_workflow(SAMPLE_INVOICE_FAILED_MATCH)
    
    print("\n📊 RESULT:")
    print(json.dumps(result2, indent=2, default=str))
    
    # If workflow paused, simulate human decision
    if result2.get("status") == "PAUSED":
        checkpoint_id = result2.get("checkpoint_id")
        print("\n" + "-" * 70)
        print("👨‍💼 HUMAN REVIEW SIMULATION")
        print("-" * 70)
        print(f"Checkpoint ID: {checkpoint_id}")
        print("Simulating ACCEPT decision...")
        
        resume_result = await graph.resume_workflow(
            checkpoint_id=checkpoint_id,
            decision="ACCEPT",
            reviewer_id="reviewer-001",
            notes="Approved after manual verification"
        )
        
        print("\n📊 RESUME RESULT:")
        print(json.dumps(resume_result, indent=2, default=str))
    
    # Print Bigtool selections
    print("\n" + "-" * 70)
    print("🔧 BIGTOOL SELECTIONS")
    print("-" * 70)
    for selection in bigtool.get_selection_log():
        print(f"  {selection['capability']}: {selection['selected_tool']} ({selection['reason']})")
    
    # Print MCP execution log
    print("\n" + "-" * 70)
    print("🌐 MCP EXECUTION LOG")
    print("-" * 70)
    for execution in mcp.get_execution_log():
        status = "✅" if execution.get("success") else "❌"
        print(f"  {status} [{execution['server']}] {execution['ability']}")
    
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)


async def run_demo_with_reject():
    """Run demo with REJECT decision"""
    from dotenv import load_dotenv
    load_dotenv()
    
    from src.database import get_db
    from src.graph.workflow import get_invoice_graph
    
    db = get_db()
    db.drop_tables()
    db.create_tables()
    
    graph = get_invoice_graph()
    
    print("\n" + "=" * 70)
    print("🧾 DEMO: HITL with REJECT Decision")
    print("=" * 70)
    
    result = await graph.start_workflow(SAMPLE_INVOICE_FAILED_MATCH)
    
    if result.get("status") == "PAUSED":
        checkpoint_id = result.get("checkpoint_id")
        print(f"\nWorkflow PAUSED at checkpoint: {checkpoint_id}")
        print("Simulating REJECT decision...")
        
        resume_result = await graph.resume_workflow(
            checkpoint_id=checkpoint_id,
            decision="REJECT",
            reviewer_id="reviewer-002",
            notes="Rejected - vendor not verified"
        )
        
        print("\n📊 RESULT:")
        print(json.dumps(resume_result, indent=2, default=str))


async def run_all_five_invoices():
    """Test all 5 sample invoices"""
    from dotenv import load_dotenv
    load_dotenv()
    
    from src.database import get_db
    from src.graph.workflow import InvoiceProcessingGraph
    
    invoices = [
        {'invoice_id': 'INV-2024-001', 'vendor_name': 'Acme Corporation', 'vendor_tax_id': 'TAX123456789', 'invoice_date': '2024-01-15', 'due_date': '2024-02-15', 'amount': 10000.00, 'currency': 'USD', 'line_items': [{'desc': 'Consulting Services', 'qty': 10, 'unit_price': 500, 'total': 5000}, {'desc': 'Software License', 'qty': 1, 'unit_price': 5000, 'total': 5000}], 'attachments': ['invoice_001.pdf'], 'po_number': 'PO-2024-001'},
        {'invoice_id': 'INV-2024-002', 'vendor_name': 'Beta Industries', 'vendor_tax_id': 'TAX987654321', 'invoice_date': '2024-01-20', 'due_date': '2024-02-20', 'amount': 75000.00, 'currency': 'USD', 'line_items': [{'desc': 'Hardware Equipment', 'qty': 5, 'unit_price': 10000, 'total': 50000}, {'desc': 'Installation Services', 'qty': 1, 'unit_price': 25000, 'total': 25000}], 'attachments': ['invoice_002.pdf', 'receipt.jpg'], 'po_number': None},
        {'invoice_id': 'INV-2024-003', 'vendor_name': 'Global Tech Solutions', 'vendor_tax_id': 'GSTIN29ABCDE1234F1Z5', 'invoice_date': '2024-01-25', 'due_date': '2024-02-25', 'amount': 5500.00, 'currency': 'USD', 'line_items': [{'desc': 'Cloud Services - Monthly', 'qty': 1, 'unit_price': 3000, 'total': 3000}, {'desc': 'Support Package', 'qty': 1, 'unit_price': 2500, 'total': 2500}], 'attachments': ['invoice_003.pdf'], 'po_number': 'PO-2024-003'},
        {'invoice_id': 'INV-2024-004', 'vendor_name': 'Office Supplies Inc', 'vendor_tax_id': 'TAX555666777', 'invoice_date': '2024-01-28', 'due_date': '2024-02-28', 'amount': 1250.00, 'currency': 'USD', 'line_items': [{'desc': 'Printer Paper (Box)', 'qty': 10, 'unit_price': 50, 'total': 500}, {'desc': 'Ink Cartridges', 'qty': 5, 'unit_price': 100, 'total': 500}, {'desc': 'Office Chairs', 'qty': 1, 'unit_price': 250, 'total': 250}], 'attachments': [], 'po_number': 'PO-2024-004'},
        {'invoice_id': 'INV-2024-005', 'vendor_name': 'Premium Catering Services', 'vendor_tax_id': 'TAX888999000', 'invoice_date': '2024-02-01', 'due_date': '2024-03-01', 'amount': 15000.00, 'currency': 'USD', 'line_items': [{'desc': 'Corporate Event Catering', 'qty': 1, 'unit_price': 12000, 'total': 12000}, {'desc': 'Equipment Rental', 'qty': 1, 'unit_price': 3000, 'total': 3000}], 'attachments': ['invoice_005.pdf', 'event_photos.zip'], 'po_number': None}
    ]
    
    db = get_db()
    db.drop_tables()
    db.create_tables()
    
    print('=' * 60)
    print('TESTING 5 SAMPLE INVOICES')
    print('=' * 60)
    
    results = []
    paused = []
    
    for inv in invoices:
        graph = InvoiceProcessingGraph()
        r = await graph.start_workflow(inv)
        status = r.get('status')
        results.append((inv['invoice_id'], inv['vendor_name'], inv['amount'], status))
        if status == 'PAUSED':
            paused.append((inv['invoice_id'], r.get('checkpoint_id')))
        print(f"{inv['invoice_id']}: {status}")
    
    # Resume paused
    for inv_id, chkpt in paused:
        graph = InvoiceProcessingGraph()
        r = await graph.resume_workflow(chkpt, 'ACCEPT', 'reviewer')
        print(f"{inv_id} resumed: {r.get('status')}")
    
    print('=' * 60)
    print('RESULTS:')
    for inv_id, vendor, amt, status in results:
        print(f"  {inv_id} | {vendor} | ${amt:,.2f} | {status}")
    print('=' * 60)
    print('ALL 5 INVOICES TESTED SUCCESSFULLY!')


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--reject":
        asyncio.run(run_demo_with_reject())
    elif len(sys.argv) > 1 and sys.argv[1] == "--all":
        asyncio.run(run_all_five_invoices())
    else:
        asyncio.run(run_demo())
