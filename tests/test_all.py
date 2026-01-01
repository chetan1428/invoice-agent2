"""
Complete Test Suite for LangGraph Invoice Processing Agent
All tests consolidated in one file
"""
import asyncio
import json
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio(loop_scope="function")


# ============================================================================
# TEST DATA
# ============================================================================

SAMPLE_INVOICE_MATCHED = {
    "invoice_id": "TEST-INV-001",
    "vendor_name": "Test Vendor Corp",
    "vendor_tax_id": "TAX123456789",
    "invoice_date": "2024-01-15",
    "due_date": "2024-02-15",
    "amount": 10000.00,
    "currency": "USD",
    "line_items": [
        {"desc": "Service A", "qty": 10, "unit_price": 500, "total": 5000},
        {"desc": "Service B", "qty": 1, "unit_price": 5000, "total": 5000}
    ],
    "attachments": ["invoice.pdf"],
    "po_number": "PO-TEST-001"
}

SAMPLE_INVOICE_FAILED = {
    "invoice_id": "TEST-INV-002",
    "vendor_name": "Failed Match Vendor",
    "vendor_tax_id": "TAX987654321",
    "invoice_date": "2024-01-20",
    "due_date": "2024-02-20",
    "amount": 75000.00,
    "currency": "USD",
    "line_items": [
        {"desc": "Hardware", "qty": 5, "unit_price": 10000, "total": 50000},
        {"desc": "Installation", "qty": 1, "unit_price": 25000, "total": 25000}
    ],
    "attachments": ["invoice.pdf", "receipt.jpg"],
    "po_number": None
}


# ============================================================================
# 1. BIGTOOL TESTS
# ============================================================================

def test_bigtool():
    """Test Bigtool tool selection"""
    print("\n📦 BIGTOOL TESTS")
    print("-" * 40)
    
    from src.bigtool.tools import ToolPool
    from src.bigtool.picker import BigtoolPicker
    
    # Test pool initialization
    pool = ToolPool()
    assert "ocr" in pool.pools
    assert "enrichment" in pool.pools
    assert "erp_connector" in pool.pools
    assert "db" in pool.pools
    assert "email" in pool.pools
    assert "storage" in pool.pools
    print("✅ Tool pool initialization: PASSED")
    
    picker = BigtoolPicker()
    
    # Test OCR selection
    tool = picker.select(capability="ocr", pool_hint=["google_vision", "tesseract", "aws_textract"])
    assert tool is not None and tool.name in ["google_vision", "tesseract", "aws_textract"]
    print(f"✅ OCR tool selection: {tool.name} - PASSED")
    
    # Test enrichment selection
    tool = picker.select(capability="enrichment", pool_hint=["clearbit", "people_data_labs", "vendor_db"])
    assert tool is not None
    print(f"✅ Enrichment tool selection: {tool.name} - PASSED")
    
    # Test ERP selection
    tool = picker.select(capability="erp_connector", pool_hint=["sap_sandbox", "netsuite", "mock_erp"])
    assert tool is not None
    print(f"✅ ERP tool selection: {tool.name} - PASSED")
    
    # Test DB selection
    tool = picker.select(capability="db", pool_hint=["postgres", "sqlite", "dynamodb"])
    assert tool is not None
    print(f"✅ DB tool selection: {tool.name} - PASSED")
    
    # Test email selection
    tool = picker.select(capability="email", pool_hint=["sendgrid", "smartlead", "ses"])
    assert tool is not None
    print(f"✅ Email tool selection: {tool.name} - PASSED")
    
    # Test storage selection
    tool = picker.select(capability="storage", pool_hint=["s3", "gcs", "local_fs"])
    assert tool is not None
    print(f"✅ Storage tool selection: {tool.name} - PASSED")


# ============================================================================
# 2. MCP CLIENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_mcp_client():
    """Test MCP Client abilities"""
    print("\n🌐 MCP CLIENT TESTS")
    print("-" * 40)
    
    from src.mcp.client import get_mcp_client, MCPServer
    
    mcp = get_mcp_client()
    
    # Test COMMON abilities
    result = await mcp.execute_ability(MCPServer.COMMON, "validate_schema", {"invoice_payload": SAMPLE_INVOICE_MATCHED})
    assert result.success
    print("✅ COMMON validate_schema: PASSED")
    
    result = await mcp.execute_ability(MCPServer.COMMON, "normalize_vendor", {"vendor_name": "  test vendor  "})
    assert result.success and result.data.get("normalized_name") == "TEST VENDOR"
    print("✅ COMMON normalize_vendor: PASSED")
    
    result = await mcp.execute_ability(MCPServer.COMMON, "compute_match_score", {
        "invoice": {"amount": 10000}, "matched_pos": [{"amount": 10000}], "threshold": 0.9
    })
    assert result.success and "match_score" in result.data
    print("✅ COMMON compute_match_score: PASSED")
    
    # Test ATLAS abilities
    result = await mcp.execute_ability(MCPServer.ATLAS, "ocr_extract", {"attachments": ["test.pdf"]})
    assert result.success
    print("✅ ATLAS ocr_extract: PASSED")
    
    result = await mcp.execute_ability(MCPServer.ATLAS, "enrich_vendor", {"vendor_name": "Test"})
    assert result.success
    print("✅ ATLAS enrich_vendor: PASSED")
    
    result = await mcp.execute_ability(MCPServer.ATLAS, "fetch_po", {"vendor_name": "Test", "amount": 1000})
    assert result.success
    print("✅ ATLAS fetch_po: PASSED")


# ============================================================================
# 3. DATABASE TESTS
# ============================================================================

def test_database():
    """Test database operations"""
    print("\n💾 DATABASE TESTS")
    print("-" * 40)
    
    from src.database import get_db
    from src.database.models import CheckpointModel
    import uuid
    
    db = get_db()
    db.create_tables()
    print("✅ Database initialization: PASSED")
    
    # Test checkpoint CRUD
    checkpoint_id = f"TEST-CHKPT-{uuid.uuid4().hex[:8]}"
    
    with db.get_session() as session:
        checkpoint = CheckpointModel(
            checkpoint_id=checkpoint_id, workflow_id="TEST-WF", invoice_id="TEST-INV",
            vendor_name="Test", amount=1000, state_blob={}, reason_for_hold="Test",
            review_url=f"/review/{checkpoint_id}", status="PENDING"
        )
        session.add(checkpoint)
        session.commit()
    
    with db.get_session() as session:
        found = session.query(CheckpointModel).filter(CheckpointModel.checkpoint_id == checkpoint_id).first()
        assert found is not None
        session.delete(found)
        session.commit()
    
    print("✅ Checkpoint CRUD: PASSED")


# ============================================================================
# 4. NODE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_nodes():
    """Test individual workflow nodes"""
    print("\n🔧 NODE TESTS")
    print("-" * 40)
    
    from src.models.state import InvoiceState
    from src.nodes.intake import intake_node
    from src.nodes.understand import understand_node
    from src.nodes.prepare import prepare_node
    from src.nodes.retrieve import retrieve_node
    from src.nodes.match import match_two_way_node
    from src.nodes.reconcile import reconcile_node
    from src.nodes.approve import approve_node
    from src.nodes.posting import posting_node
    from src.nodes.notify import notify_node
    from src.nodes.hitl_decision import hitl_decision_node
    
    # INTAKE
    state: InvoiceState = {"workflow_id": "TEST", "invoice_payload": SAMPLE_INVOICE_MATCHED, "bigtool_selections": {}}
    result = await intake_node(state)
    assert result.get("validated") == True
    print("✅ INTAKE node: PASSED")
    
    # UNDERSTAND
    result = await understand_node(state)
    assert result.get("parsed_invoice") is not None
    print("✅ UNDERSTAND node: PASSED")
    
    # PREPARE
    state["parsed_invoice"] = {"line_items": []}
    result = await prepare_node(state)
    assert result.get("vendor_profile") is not None
    print("✅ PREPARE node: PASSED")
    
    # RETRIEVE
    state["vendor_profile"] = {"normalized_name": "TEST"}
    result = await retrieve_node(state)
    assert "matched_pos" in result
    print("✅ RETRIEVE node: PASSED")
    
    # MATCH_TWO_WAY
    state["normalized_invoice"] = {"amount": 10000, "line_items": []}
    state["matched_pos"] = [{"po_number": "PO-001", "amount": 10000}]
    result = await match_two_way_node(state)
    assert "match_score" in result
    print("✅ MATCH_TWO_WAY node: PASSED")
    
    # RECONCILE
    result = await reconcile_node(state)
    assert "accounting_entries" in result
    print("✅ RECONCILE node: PASSED")
    
    # APPROVE
    result = await approve_node(state)
    assert "approval_status" in result
    print("✅ APPROVE node: PASSED")
    
    # POSTING
    state["accounting_entries"] = []
    result = await posting_node(state)
    assert "posted" in result
    print("✅ POSTING node: PASSED")
    
    # NOTIFY
    result = await notify_node(state)
    assert "notified_parties" in result
    print("✅ NOTIFY node: PASSED")
    
    # HITL_DECISION - ACCEPT
    state["hitl_checkpoint_id"] = "TEST-CHKPT"
    state["human_decision"] = "ACCEPT"
    state["reviewer_id"] = "test"
    state["errors"] = []
    result = await hitl_decision_node(state)
    assert result.get("next_stage") == "RECONCILE"
    print("✅ HITL_DECISION (ACCEPT): PASSED")
    
    # HITL_DECISION - REJECT
    state["human_decision"] = "REJECT"
    result = await hitl_decision_node(state)
    assert result.get("next_stage") == "COMPLETE"
    print("✅ HITL_DECISION (REJECT): PASSED")


# ============================================================================
# 5. WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_workflow():
    """Test full workflow execution"""
    print("\n🔄 WORKFLOW TESTS")
    print("-" * 40)
    
    from src.database import get_db
    from src.graph.workflow import InvoiceProcessingGraph
    
    db = get_db()
    db.drop_tables()
    db.create_tables()
    
    graph = InvoiceProcessingGraph()
    
    # Test workflow execution
    result = await graph.start_workflow(SAMPLE_INVOICE_MATCHED)
    assert result.get("workflow_id") is not None
    assert result.get("status") in ["COMPLETED", "PAUSED"]
    
    if result.get("status") == "COMPLETED":
        print("✅ Workflow (MATCHED): COMPLETED - PASSED")
    else:
        checkpoint_id = result.get("checkpoint_id")
        print(f"✅ Workflow PAUSED at checkpoint: {checkpoint_id}")
        
        # Test resume with ACCEPT
        resume_result = await graph.resume_workflow(checkpoint_id, "ACCEPT", "test-reviewer")
        assert resume_result.get("status") == "COMPLETED"
        print("✅ Workflow resume (ACCEPT): PASSED")
    
    # Test REJECT scenario
    db.drop_tables()
    db.create_tables()
    
    result = await graph.start_workflow(SAMPLE_INVOICE_FAILED)
    if result.get("status") == "PAUSED":
        resume_result = await graph.resume_workflow(result.get("checkpoint_id"), "REJECT", "test-reviewer")
        assert resume_result.get("status") == "MANUAL_HANDOFF"
        print("✅ Workflow resume (REJECT): PASSED")


# ============================================================================
# 6. API TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_api():
    """Test API endpoints"""
    print("\n🌍 API TESTS")
    print("-" * 40)
    
    from fastapi.testclient import TestClient
    from main import app
    from src.database import get_db
    
    db = get_db()
    db.drop_tables()
    db.create_tables()
    
    client = TestClient(app)
    
    # Health check
    response = client.get("/health")
    assert response.status_code == 200
    print("✅ GET /health: PASSED")
    
    # Start workflow
    response = client.post("/api/workflow/start", json=SAMPLE_INVOICE_MATCHED)
    assert response.status_code == 200
    print("✅ POST /api/workflow/start: PASSED")
    
    # List pending reviews
    response = client.get("/api/human-review/pending")
    assert response.status_code == 200
    print("✅ GET /api/human-review/pending: PASSED")
    
    # Bigtool selections
    response = client.get("/api/bigtool/selections")
    assert response.status_code == 200
    print("✅ GET /api/bigtool/selections: PASSED")
    
    # MCP execution log
    response = client.get("/api/mcp/execution-log")
    assert response.status_code == 200
    print("✅ GET /api/mcp/execution-log: PASSED")


# ============================================================================
# 7. SAMPLE INVOICES TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_sample_invoices():
    """Test all sample invoices from sample_invoices.json"""
    print("\n📋 SAMPLE INVOICES TESTS")
    print("-" * 40)
    
    from src.database import get_db
    from src.graph.workflow import InvoiceProcessingGraph
    
    # Load sample invoices
    with open("sample_invoices.json", "r") as f:
        data = json.load(f)
    
    invoices = data.get("invoices", [])
    print(f"Testing {len(invoices)} sample invoices...")
    
    db = get_db()
    db.drop_tables()
    db.create_tables()
    
    passed = 0
    paused_checkpoints = []
    
    for invoice in invoices:
        graph = InvoiceProcessingGraph()
        result = await graph.start_workflow(invoice)
        
        if result.get("status") in ["COMPLETED", "PAUSED"]:
            passed += 1
            if result.get("status") == "PAUSED":
                paused_checkpoints.append((invoice["invoice_id"], result.get("checkpoint_id")))
    
    print(f"✅ {passed}/{len(invoices)} invoices processed successfully")
    
    # Resume paused workflows
    if paused_checkpoints:
        print(f"  Resuming {len(paused_checkpoints)} paused workflows...")
        for inv_id, chkpt_id in paused_checkpoints:
            graph = InvoiceProcessingGraph()
            resume_result = await graph.resume_workflow(chkpt_id, "ACCEPT", "test-reviewer")
            assert resume_result.get("status") in ["COMPLETED", "ERROR"]
        print(f"✅ All paused workflows resumed: PASSED")


# ============================================================================
# 8. REQUIREMENTS VALIDATION
# ============================================================================

def test_requirements():
    """Validate all task requirements are met"""
    print("\n📝 REQUIREMENTS VALIDATION")
    print("-" * 40)
    
    # Check all 12 nodes exist
    from src.nodes import (
        intake_node, understand_node, prepare_node, retrieve_node,
        match_two_way_node, checkpoint_hitl_node, hitl_decision_node,
        reconcile_node, approve_node, posting_node, notify_node, complete_node
    )
    
    nodes = [intake_node, understand_node, prepare_node, retrieve_node,
             match_two_way_node, checkpoint_hitl_node, hitl_decision_node,
             reconcile_node, approve_node, posting_node, notify_node, complete_node]
    
    assert all(callable(n) for n in nodes)
    print("✅ All 12 LangGraph nodes exist: PASSED")
    
    # Check graph has all nodes
    from src.graph.workflow import create_invoice_graph
    graph = create_invoice_graph()
    expected = ["intake", "understand", "prepare", "retrieve", "match_two_way",
                "checkpoint_hitl", "hitl_decision", "reconcile", "approve", 
                "posting", "notify", "complete"]
    assert all(n in graph.nodes for n in expected)
    print("✅ Graph contains all 12 nodes: PASSED")
    
    # Check workflow.json
    with open("workflow.json", "r") as f:
        config = json.load(f)
    assert config.get("version") == "1.0"
    assert len(config.get("stages", [])) == 12
    print("✅ workflow.json valid with 12 stages: PASSED")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 COMPLETE TEST SUITE - LangGraph Invoice Processing Agent")
    print("=" * 70)
    
    # 1. Bigtool
    test_bigtool()
    
    # 2. MCP Client
    await test_mcp_client()
    
    # 3. Database
    test_database()
    
    # 4. Nodes
    await test_nodes()
    
    # 5. Workflow
    await test_workflow()
    
    # 6. API
    await test_api()
    
    # 7. Sample Invoices
    await test_sample_invoices()
    
    # 8. Requirements
    test_requirements()
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
