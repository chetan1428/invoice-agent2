"""
Verify the complete 12-step workflow path with HITL ACCEPT
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from src.database import get_db
from src.graph.workflow import InvoiceProcessingGraph

# Reset database
db = get_db()
db.drop_tables()
db.create_tables()

# Invoice that will FAIL match (no PO, triggers HITL)
invoice = {
    'invoice_id': 'TEST-12STEP',
    'vendor_name': 'Unknown Vendor XYZ',
    'vendor_tax_id': 'TAX999999',
    'invoice_date': '2024-01-15',
    'due_date': '2024-02-15',
    'amount': 999999.00,  # Very high amount to ensure mismatch
    'currency': 'USD',
    'line_items': [{'desc': 'Special Service', 'qty': 1, 'unit_price': 999999, 'total': 999999}],
    'attachments': [],
    'po_number': None  # No PO reference
}

async def verify_12_steps():
    graph = InvoiceProcessingGraph()
    
    print('=' * 70)
    print('VERIFYING 12-STEP WORKFLOW PATH')
    print('1.INTAKE -> 2.UNDERSTAND -> 3.PREPARE -> 4.RETRIEVE -> 5.MATCH_TWO_WAY')
    print('-> 6.CHECKPOINT_HITL -> [PAUSE] -> 7.HITL_DECISION(ACCEPT)')
    print('-> 8.RECONCILE -> 9.APPROVE -> 10.POSTING -> 11.NOTIFY -> 12.COMPLETE')
    print('=' * 70)
    print()
    
    # Start workflow - executes Steps 1-6, then PAUSES
    print('>>> Starting workflow (Steps 1-6)...')
    result = await graph.start_workflow(invoice)
    
    if result.get('status') != 'PAUSED':
        print(f'ERROR: Expected PAUSED, got {result.get("status")}')
        return False
    
    checkpoint_id = result.get('checkpoint_id')
    print(f'>>> Workflow PAUSED at Step 6 (CHECKPOINT_HITL)')
    print(f'>>> Checkpoint ID: {checkpoint_id}')
    print()
    
    # Resume with ACCEPT - executes Steps 7-12
    print('>>> Resuming workflow with ACCEPT decision (Steps 7-12)...')
    resume_result = await graph.resume_workflow(
        checkpoint_id=checkpoint_id,
        decision='ACCEPT',
        reviewer_id='test-reviewer'
    )
    
    if resume_result.get('status') != 'COMPLETED':
        print(f'ERROR: Expected COMPLETED, got {resume_result.get("status")}')
        return False
    
    print(f'>>> Workflow COMPLETED at Step 12')
    print()
    
    # Show final payload
    final = resume_result.get('final_payload', {})
    print('=' * 70)
    print('FINAL PAYLOAD:')
    print('=' * 70)
    print(f'  workflow_id: {final.get("workflow_id")}')
    print(f'  invoice_id: {final.get("invoice_id")}')
    print(f'  vendor_name: {final.get("vendor_name")}')
    print(f'  amount: ${final.get("amount"):,.2f}')
    print(f'  status: {final.get("status")}')
    print(f'  match_score: {final.get("match_score")}')
    print(f'  match_result: {final.get("match_result")}')
    print(f'  approval_status: {final.get("approval_status")}')
    print(f'  posted: {final.get("posted")}')
    print(f'  erp_txn_id: {final.get("erp_txn_id")}')
    print(f'  notified_parties: {final.get("notified_parties")}')
    print()
    
    return True

if __name__ == '__main__':
    success = asyncio.run(verify_12_steps())
    print('=' * 70)
    if success:
        print('✅ 12-STEP WORKFLOW VERIFICATION: PASSED')
    else:
        print('❌ 12-STEP WORKFLOW VERIFICATION: FAILED')
    print('=' * 70)
