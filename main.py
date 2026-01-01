"""
LangGraph Invoice Processing Agent - Main Application
"""
import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Import after env loaded
from src.api.routes import router
from src.database import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 LangGraph Invoice Processing Agent Starting...")
    logger.info("=" * 60)
    
    # Initialize database
    db = get_db()
    db.create_tables()
    logger.info("✅ Database initialized")
    
    logger.info("✅ Application ready")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="LangGraph Invoice Processing Agent",
    description="""
    ## Invoice Processing Workflow with HITL
    
    This agent processes invoices through 12 stages using LangGraph:
    
    1. **INTAKE** - Accept and validate invoice payload
    2. **UNDERSTAND** - OCR extraction and line item parsing
    3. **PREPARE** - Vendor normalization and enrichment
    4. **RETRIEVE** - Fetch PO, GRN, historical data from ERP
    5. **MATCH_TWO_WAY** - Compute 2-way match score
    6. **CHECKPOINT_HITL** - Create checkpoint for human review (if match fails)
    7. **HITL_DECISION** - Process human accept/reject decision
    8. **RECONCILE** - Build accounting entries
    9. **APPROVE** - Apply approval policies
    10. **POSTING** - Post to ERP and schedule payment
    11. **NOTIFY** - Send notifications
    12. **COMPLETE** - Finalize and output results
    
    ### Key Features:
    - **Bigtool**: Dynamic tool selection from pools (OCR, enrichment, ERP, etc.)
    - **MCP Integration**: Routes abilities to COMMON/ATLAS servers
    - **HITL Checkpoints**: Pause workflow for human review, resume after decision
    - **State Persistence**: Full state management across all stages
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api", tags=["Invoice Processing"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with basic UI"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LangGraph Invoice Processing Agent</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            h1 { color: #333; }
            .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .endpoint { background: #e8f4f8; padding: 10px; margin: 5px 0; border-radius: 4px; font-family: monospace; }
            .method { font-weight: bold; color: #0066cc; }
            .post { color: #28a745; }
            .get { color: #007bff; }
            .delete { color: #dc3545; }
            a { color: #0066cc; }
            pre { background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; }
            .stage { display: inline-block; padding: 5px 10px; margin: 2px; background: #e9ecef; border-radius: 4px; font-size: 12px; }
            .stage.hitl { background: #fff3cd; }
            .btn { display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
            .btn:hover { background: #5a6fd6; }
        </style>
    </head>
    <body>
        <h1>🧾 LangGraph Invoice Processing Agent</h1>
        
        <div class="card">
            <h2>🚀 Quick Links</h2>
            <a href="/dashboard" class="btn">📊 Live Dashboard</a>
            <a href="/review" class="btn">👨‍💼 Human Review</a>
            <a href="/docs" class="btn">📖 API Docs</a>
        </div>
        
        <div class="card">
            <h2>📋 Workflow Stages</h2>
            <span class="stage">1. INTAKE</span>
            <span class="stage">2. UNDERSTAND</span>
            <span class="stage">3. PREPARE</span>
            <span class="stage">4. RETRIEVE</span>
            <span class="stage">5. MATCH_TWO_WAY</span>
            <span class="stage hitl">6. CHECKPOINT_HITL</span>
            <span class="stage hitl">7. HITL_DECISION</span>
            <span class="stage">8. RECONCILE</span>
            <span class="stage">9. APPROVE</span>
            <span class="stage">10. POSTING</span>
            <span class="stage">11. NOTIFY</span>
            <span class="stage">12. COMPLETE</span>
        </div>
        
        <div class="card">
            <h2>🔗 API Endpoints</h2>
            
            <h3>Workflow</h3>
            <div class="endpoint"><span class="method post">POST</span> /api/workflow/start - Start new invoice workflow</div>
            <div class="endpoint"><span class="method get">GET</span> /api/workflow/{workflow_id}/status - Get workflow status</div>
            <div class="endpoint"><span class="method get">GET</span> /api/workflow/{workflow_id}/audit-log - Get audit log</div>
            
            <h3>Human Review (HITL)</h3>
            <div class="endpoint"><span class="method get">GET</span> /api/human-review/pending - List pending reviews</div>
            <div class="endpoint"><span class="method get">GET</span> /api/human-review/{checkpoint_id} - Get review details</div>
            <div class="endpoint"><span class="method post">POST</span> /api/human-review/decision - Submit decision (ACCEPT/REJECT)</div>
            
            <h3>Monitoring</h3>
            <div class="endpoint"><span class="method get">GET</span> /api/bigtool/selections - View Bigtool selections</div>
            <div class="endpoint"><span class="method get">GET</span> /api/mcp/execution-log - View MCP execution log</div>
        </div>
        
        <div class="card">
            <h2>🧪 Sample Invoice Payload</h2>
            <pre>{
  "invoice_id": "INV-2024-001",
  "vendor_name": "Acme Corp",
  "vendor_tax_id": "TAX123456789",
  "invoice_date": "2024-01-15",
  "due_date": "2024-02-15",
  "amount": 10000.00,
  "currency": "USD",
  "line_items": [
    {"desc": "Consulting Services", "qty": 10, "unit_price": 500, "total": 5000},
    {"desc": "Software License", "qty": 1, "unit_price": 5000, "total": 5000}
  ],
  "attachments": ["invoice.pdf"],
  "po_number": "PO-2024-001"
}</pre>
        </div>
    </body>
    </html>
    """


@app.get("/review", response_class=HTMLResponse)
async def review_dashboard():
    """Human Review Dashboard"""
    with open("templates/review.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/dashboard", response_class=HTMLResponse)
async def live_dashboard():
    """Live Visual Dashboard - Shows workflow progress in real-time"""
    with open("templates/dashboard.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "langgraph-invoice-agent"}


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("🌐 Open in browser: http://localhost:8000")
    print("📊 Live Dashboard: http://localhost:8000/dashboard")
    print("👨‍💼 Human Review: http://localhost:8000/review")
    print("📖 API Docs: http://localhost:8000/docs")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
