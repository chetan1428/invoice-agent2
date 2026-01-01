"""
LangGraph Invoice Processing Workflow
Main graph definition with all 12 stages
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from src.models.state import InvoiceState, WorkflowStatus
from src.nodes import (
    intake_node,
    understand_node,
    prepare_node,
    retrieve_node,
    match_two_way_node,
    checkpoint_hitl_node,
    hitl_decision_node,
    reconcile_node,
    approve_node,
    posting_node,
    notify_node,
    complete_node
)

logger = logging.getLogger(__name__)


def should_checkpoint(state: InvoiceState) -> Literal["checkpoint_hitl", "reconcile"]:
    """
    Conditional edge: Route to CHECKPOINT_HITL if match failed, else to RECONCILE
    """
    match_result = state.get("match_result", "")
    
    if match_result == "FAILED":
        logger.info("Routing to CHECKPOINT_HITL (match failed)")
        return "checkpoint_hitl"
    else:
        logger.info("Routing to RECONCILE (match passed)")
        return "reconcile"


def should_continue_after_hitl(state: InvoiceState) -> Literal["reconcile", "complete"]:
    """
    Conditional edge: After HITL decision, route based on human decision
    """
    human_decision = state.get("human_decision", "")
    
    if human_decision == "ACCEPT":
        logger.info("Human ACCEPTED - Routing to RECONCILE")
        return "reconcile"
    else:
        logger.info("Human REJECTED - Routing to COMPLETE")
        return "complete"


def create_invoice_graph() -> StateGraph:
    """
    Create the LangGraph workflow for invoice processing
    
    Flow:
    INTAKE -> UNDERSTAND -> PREPARE -> RETRIEVE -> MATCH_TWO_WAY
        -> (if FAILED) CHECKPOINT_HITL -> [PAUSE]
        -> (if MATCHED) RECONCILE -> APPROVE -> POSTING -> NOTIFY -> COMPLETE
    
    After HITL_DECISION:
        -> (if ACCEPT) RECONCILE -> ... -> COMPLETE
        -> (if REJECT) COMPLETE (with MANUAL_HANDOFF status)
    """
    
    # Create the graph with InvoiceState
    workflow = StateGraph(InvoiceState)
    
    # Add all nodes
    workflow.add_node("intake", intake_node)
    workflow.add_node("understand", understand_node)
    workflow.add_node("prepare", prepare_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("match_two_way", match_two_way_node)
    workflow.add_node("checkpoint_hitl", checkpoint_hitl_node)
    workflow.add_node("hitl_decision", hitl_decision_node)
    workflow.add_node("reconcile", reconcile_node)
    workflow.add_node("approve", approve_node)
    workflow.add_node("posting", posting_node)
    workflow.add_node("notify", notify_node)
    workflow.add_node("complete", complete_node)
    
    # Set entry point
    workflow.set_entry_point("intake")
    
    # Add edges (deterministic flow)
    workflow.add_edge("intake", "understand")
    workflow.add_edge("understand", "prepare")
    workflow.add_edge("prepare", "retrieve")
    workflow.add_edge("retrieve", "match_two_way")
    
    # Conditional edge after matching
    workflow.add_conditional_edges(
        "match_two_way",
        should_checkpoint,
        {
            "checkpoint_hitl": "checkpoint_hitl",
            "reconcile": "reconcile"
        }
    )
    
    # Checkpoint leads to END (workflow pauses)
    workflow.add_edge("checkpoint_hitl", END)
    
    # HITL decision has conditional routing
    workflow.add_conditional_edges(
        "hitl_decision",
        should_continue_after_hitl,
        {
            "reconcile": "reconcile",
            "complete": "complete"
        }
    )
    
    # Continue flow after reconcile
    workflow.add_edge("reconcile", "approve")
    workflow.add_edge("approve", "posting")
    workflow.add_edge("posting", "notify")
    workflow.add_edge("notify", "complete")
    
    # Complete leads to END
    workflow.add_edge("complete", END)
    
    return workflow


class InvoiceProcessingGraph:
    """
    Main class for managing invoice processing workflow
    """
    
    def __init__(self):
        self.graph = create_invoice_graph()
        self.compiled = self.graph.compile()
        self._running_workflows: Dict[str, InvoiceState] = {}
    
    async def start_workflow(self, invoice_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new invoice processing workflow
        """
        workflow_id = f"WF-{uuid.uuid4().hex[:8].upper()}"
        
        initial_state: InvoiceState = {
            "workflow_id": workflow_id,
            "workflow_status": WorkflowStatus.RUNNING.value,
            "current_stage": "INTAKE",
            "started_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "invoice_payload": invoice_payload,
            "errors": [],
            "bigtool_selections": {}
        }
        
        logger.info(f"Starting workflow {workflow_id} for invoice {invoice_payload.get('invoice_id')}")
        
        # Store initial state
        from src.database import get_db
        from src.database.models import WorkflowStateModel, InvoiceModel
        
        db = get_db()
        with db.get_session() as session:
            # Create invoice record
            invoice = InvoiceModel(
                id=f"INV-{uuid.uuid4().hex[:8]}",
                workflow_id=workflow_id,
                invoice_id=invoice_payload.get("invoice_id", ""),
                vendor_name=invoice_payload.get("vendor_name", ""),
                vendor_tax_id=invoice_payload.get("vendor_tax_id", ""),
                amount=invoice_payload.get("amount", 0),
                currency=invoice_payload.get("currency", "USD"),
                status="PROCESSING",
                raw_payload=invoice_payload
            )
            session.add(invoice)
            
            # Create workflow state record
            workflow_state = WorkflowStateModel(
                workflow_id=workflow_id,
                current_stage="INTAKE",
                status=WorkflowStatus.RUNNING.value,
                state_data=initial_state
            )
            session.add(workflow_state)
            session.commit()
        
        # Run the workflow
        try:
            final_state = await self.compiled.ainvoke(initial_state)
            self._running_workflows[workflow_id] = final_state
            
            # Check if workflow paused
            if final_state.get("workflow_status") == WorkflowStatus.PAUSED.value:
                logger.info(f"Workflow {workflow_id} PAUSED at checkpoint")
                return {
                    "workflow_id": workflow_id,
                    "status": "PAUSED",
                    "checkpoint_id": final_state.get("hitl_checkpoint_id"),
                    "review_url": final_state.get("review_url"),
                    "message": "Workflow paused for human review"
                }
            
            return {
                "workflow_id": workflow_id,
                "status": final_state.get("workflow_status", "COMPLETED"),
                "final_payload": final_state.get("final_payload"),
                "message": "Workflow completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            return {
                "workflow_id": workflow_id,
                "status": "FAILED",
                "error": str(e),
                "message": "Workflow execution failed"
            }
    
    async def resume_workflow(
        self, 
        checkpoint_id: str, 
        decision: str, 
        reviewer_id: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Resume a paused workflow after human decision
        """
        from src.database import get_db
        from src.database.models import CheckpointModel, WorkflowStateModel
        
        db = get_db()
        
        # Get checkpoint data
        with db.get_session() as session:
            checkpoint = session.query(CheckpointModel).filter(
                CheckpointModel.checkpoint_id == checkpoint_id
            ).first()
            
            if not checkpoint:
                return {
                    "status": "ERROR",
                    "message": f"Checkpoint {checkpoint_id} not found"
                }
            
            if checkpoint.status != "PENDING":
                return {
                    "status": "ERROR",
                    "message": f"Checkpoint already processed: {checkpoint.status}"
                }
            
            workflow_id = checkpoint.workflow_id
            state_blob = checkpoint.state_blob
        
        logger.info(f"Resuming workflow {workflow_id} with decision: {decision}")
        
        # Reconstruct state and add human decision
        resume_state: InvoiceState = {
            **state_blob,
            "workflow_status": WorkflowStatus.RUNNING.value,
            "human_decision": decision,
            "reviewer_id": reviewer_id,
            "hitl_checkpoint_id": checkpoint_id,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Create a graph that starts from HITL_DECISION
        resume_graph = StateGraph(InvoiceState)
        resume_graph.add_node("hitl_decision", hitl_decision_node)
        resume_graph.add_node("reconcile", reconcile_node)
        resume_graph.add_node("approve", approve_node)
        resume_graph.add_node("posting", posting_node)
        resume_graph.add_node("notify", notify_node)
        resume_graph.add_node("complete", complete_node)
        
        resume_graph.set_entry_point("hitl_decision")
        
        resume_graph.add_conditional_edges(
            "hitl_decision",
            should_continue_after_hitl,
            {
                "reconcile": "reconcile",
                "complete": "complete"
            }
        )
        
        resume_graph.add_edge("reconcile", "approve")
        resume_graph.add_edge("approve", "posting")
        resume_graph.add_edge("posting", "notify")
        resume_graph.add_edge("notify", "complete")
        resume_graph.add_edge("complete", END)
        
        compiled_resume = resume_graph.compile()
        
        try:
            final_state = await compiled_resume.ainvoke(resume_state)
            
            return {
                "workflow_id": workflow_id,
                "status": final_state.get("workflow_status", "COMPLETED"),
                "final_payload": final_state.get("final_payload"),
                "message": f"Workflow resumed and completed after {decision}"
            }
            
        except Exception as e:
            logger.error(f"Resume workflow {workflow_id} failed: {e}")
            return {
                "workflow_id": workflow_id,
                "status": "FAILED",
                "error": str(e),
                "message": "Workflow resume failed"
            }
    
    def get_workflow_state(self, workflow_id: str) -> Dict[str, Any]:
        """Get current state of a workflow"""
        return self._running_workflows.get(workflow_id, {})


# Global instance
_graph_instance = None


def get_invoice_graph() -> InvoiceProcessingGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = InvoiceProcessingGraph()
    return _graph_instance
