"""
LangGraph Invoice Processing Agent - Debug Check Script
"""
import sys
import json

print('=' * 70)
print('LANGGRAPH INVOICE PROCESSING AGENT - DEBUG CHECK')
print('=' * 70)

errors = []
passed = []

# 1. Check imports
print('\n1. CHECKING IMPORTS...')

try:
    from src.graph.workflow import create_invoice_graph, InvoiceProcessingGraph
    passed.append('Graph workflow')
    print('   [OK] Graph workflow')
except Exception as e:
    errors.append(f'Graph workflow: {e}')
    print(f'   [ERROR] Graph workflow: {e}')

try:
    from src.bigtool.picker import BigtoolPicker
    from src.bigtool.tools import ToolPool
    passed.append('Bigtool')
    print('   [OK] Bigtool')
except Exception as e:
    errors.append(f'Bigtool: {e}')
    print(f'   [ERROR] Bigtool: {e}')

try:
    from src.mcp.client import MCPClient, MCPServer
    passed.append('MCP Client')
    print('   [OK] MCP Client')
except Exception as e:
    errors.append(f'MCP Client: {e}')
    print(f'   [ERROR] MCP Client: {e}')

try:
    from src.database.models import CheckpointModel, AuditLogModel
    passed.append('Database models')
    print('   [OK] Database models')
except Exception as e:
    errors.append(f'Database models: {e}')
    print(f'   [ERROR] Database models: {e}')

try:
    from src.nodes import (
        intake_node, understand_node, prepare_node, retrieve_node,
        match_two_way_node, checkpoint_hitl_node, hitl_decision_node, 
        reconcile_node, approve_node, posting_node, notify_node, complete_node
    )
    passed.append('All 12 nodes')
    print('   [OK] All 12 nodes')
except Exception as e:
    errors.append(f'Nodes: {e}')
    print(f'   [ERROR] Nodes: {e}')

# 2. Check workflow.json
print('\n2. CHECKING WORKFLOW.JSON...')
try:
    with open('workflow.json', 'r') as f:
        wf = json.load(f)
    print(f'   Version: {wf["version"]}')
    print(f'   Stages: {len(wf["stages"])}')
    stage_ids = [s["id"] for s in wf["stages"]]
    print(f'   Stage IDs: {stage_ids}')
    passed.append('workflow.json')
    print('   [OK] workflow.json valid')
except Exception as e:
    errors.append(f'workflow.json: {e}')
    print(f'   [ERROR] workflow.json: {e}')

# 3. Check sample data
print('\n3. CHECKING SAMPLE DATA...')
try:
    with open('sample_invoices.json', 'r') as f:
        data = json.load(f)
    print(f'   Invoices: {len(data["invoices"])}')
    for inv in data["invoices"]:
        print(f'   - {inv["invoice_id"]}: ${inv["amount"]:,.2f}')
    passed.append('sample_invoices.json')
    print('   [OK] sample_invoices.json valid')
except Exception as e:
    errors.append(f'sample_invoices.json: {e}')
    print(f'   [ERROR] sample_invoices.json: {e}')

# 4. Check graph structure
print('\n4. CHECKING GRAPH STRUCTURE...')
try:
    graph = create_invoice_graph()
    nodes = list(graph.nodes.keys())
    print(f'   Nodes in graph: {len(nodes)}')
    print(f'   Node names: {nodes}')
    passed.append('Graph structure')
    print('   [OK] Graph structure valid')
except Exception as e:
    errors.append(f'Graph structure: {e}')
    print(f'   [ERROR] Graph structure: {e}')

# 5. Check Bigtool pools
print('\n5. CHECKING BIGTOOL POOLS...')
try:
    pool = ToolPool()
    for cap, tools in pool.pools.items():
        tool_names = [t.name for t in tools]
        print(f'   {cap}: {tool_names}')
    passed.append('Bigtool pools')
    print('   [OK] Bigtool pools configured')
except Exception as e:
    errors.append(f'Bigtool pools: {e}')
    print(f'   [ERROR] Bigtool pools: {e}')

# 6. Check MCP abilities
print('\n6. CHECKING MCP ABILITIES...')
try:
    from src.mcp.abilities import CommonAbilities, AtlasAbilities
    common_abilities = [m for m in dir(CommonAbilities) if not m.startswith('_') and m != 'execute']
    atlas_abilities = [m for m in dir(AtlasAbilities) if not m.startswith('_') and m != 'execute']
    print(f'   COMMON abilities: {len(common_abilities)}')
    print(f'   ATLAS abilities: {len(atlas_abilities)}')
    passed.append('MCP abilities')
    print('   [OK] MCP abilities configured')
except Exception as e:
    errors.append(f'MCP abilities: {e}')
    print(f'   [ERROR] MCP abilities: {e}')

# 7. Check API routes
print('\n7. CHECKING API ROUTES...')
try:
    from src.api.routes import router
    routes = []
    for route in router.routes:
        if hasattr(route, 'methods'):
            methods = list(route.methods)
            routes.append(f'{methods[0]} {route.path}')
    print(f'   Total routes: {len(routes)}')
    for r in routes:
        print(f'   - {r}')
    passed.append('API routes')
    print('   [OK] API routes configured')
except Exception as e:
    errors.append(f'API routes: {e}')
    print(f'   [ERROR] API routes: {e}')

# Summary
print('\n' + '=' * 70)
print('DEBUG CHECK SUMMARY')
print('=' * 70)
print(f'\nPassed: {len(passed)}')
print(f'Errors: {len(errors)}')

if errors:
    print('\nErrors found:')
    for e in errors:
        print(f'  - {e}')
else:
    print('\n[OK] All checks passed!')

print('\n' + '=' * 70)
