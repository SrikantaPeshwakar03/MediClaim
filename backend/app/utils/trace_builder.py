"""
Trace Builder Utility

Builds human-readable trace from claim state for explainability.
"""

from typing import Dict, Any, List
from datetime import datetime

from ..models import ClaimState, ClaimTrace


def build_claim_trace(state: ClaimState) -> ClaimTrace:
    """
    Build comprehensive trace from claim state.
    
    Args:
        state: Final claim state
        
    Returns:
        ClaimTrace object with formatted trace data
    """
    claim_id = state["claim_id"]
    
    # Get trace entries
    agent_traces = state.get("trace", [])
    
    # Get errors and warnings
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    
    # Calculate processing time
    start_time = state.get("processing_start_time", 0)
    end_time = state.get("processing_end_time", 0)
    processing_time = end_time - start_time if end_time > 0 else 0
    
    # Build trace
    trace = ClaimTrace(
        claim_id=claim_id,
        agent_traces=agent_traces,
        errors=errors,
        warnings=warnings,
        processing_time_seconds=processing_time,
        timestamp=datetime.fromtimestamp(end_time) if end_time > 0 else datetime.utcnow()
    )
    
    return trace


def format_trace_for_display(trace: ClaimTrace) -> Dict[str, Any]:
    """
    Format trace for frontend display.
    
    Args:
        trace: ClaimTrace object
        
    Returns:
        Formatted trace dictionary
    """
    formatted = {
        "claim_id": trace.claim_id,
        "processing_time_seconds": round(trace.processing_time_seconds, 2),
        "timestamp": trace.timestamp.isoformat(),
        "agents": [],
        "summary": {
            "total_agents": len(trace.agent_traces),
            "successful": 0,
            "failed": 0,
            "warnings": len(trace.warnings)
        }
    }
    
    # Format each agent trace
    for agent_trace in trace.agent_traces:
        agent_name = agent_trace.get("agent", "Unknown")
        status = agent_trace.get("status", "unknown")
        
        # Update summary
        if status == "success":
            formatted["summary"]["successful"] += 1
        elif status in ["failed", "partial_failure"]:
            formatted["summary"]["failed"] += 1
        
        # Format agent entry
        formatted_agent = {
            "name": agent_name,
            "status": status,
            "duration_seconds": round(agent_trace.get("duration_seconds", 0), 3),
            "timestamp": datetime.fromtimestamp(
                agent_trace.get("timestamp", 0)
            ).isoformat() if agent_trace.get("timestamp") else None,
            "input_summary": _format_input_summary(agent_trace.get("input", {})),
            "output_summary": _format_output_summary(agent_trace.get("output", {})),
            "errors": agent_trace.get("errors"),
            "details": _extract_important_details(agent_trace)
        }
        
        formatted["agents"].append(formatted_agent)
    
    # Add errors
    formatted["errors"] = [
        {
            "agent": error.get("agent", "Unknown"),
            "message": error.get("error", ""),
            "timestamp": datetime.fromtimestamp(
                error.get("timestamp", 0)
            ).isoformat() if error.get("timestamp") else None
        }
        for error in trace.errors
    ]
    
    # Add warnings
    formatted["warnings"] = [
        {
            "agent": warning.get("agent", "Unknown"),
            "message": warning.get("message", ""),
            "details": warning.get("details")
        }
        for warning in trace.warnings
    ]
    
    return formatted


def _format_input_summary(input_data: Dict[str, Any]) -> str:
    """Format input data into a readable summary"""
    if not input_data:
        return "No input data"
    
    parts = []
    
    if "claim_id" in input_data:
        parts.append(f"Claim: {input_data['claim_id']}")
    
    if "member_id" in input_data:
        parts.append(f"Member: {input_data['member_id']}")
    
    if "num_documents" in input_data:
        parts.append(f"Documents: {input_data['num_documents']}")
    
    if "claimed_amount" in input_data:
        parts.append(f"Amount: ₹{input_data['claimed_amount']:,.2f}")
    
    if "category" in input_data:
        parts.append(f"Category: {input_data['category']}")
    
    return ", ".join(parts) if parts else "Input processed"


def _format_output_summary(output_data: Dict[str, Any]) -> str:
    """Format output data into a readable summary"""
    if not output_data:
        return "No output data"
    
    parts = []
    
    if "verification_passed" in output_data:
        parts.append(f"Verification: {'✓' if output_data['verification_passed'] else '✗'}")
    
    if "num_successful" in output_data:
        parts.append(f"Extracted: {output_data['num_successful']} docs")
    
    if "avg_confidence" in output_data:
        parts.append(f"Confidence: {output_data['avg_confidence']:.2f}")
    
    if "all_checks_passed" in output_data:
        parts.append(f"Policy: {'✓' if output_data['all_checks_passed'] else '✗'}")
    
    if "eligible_amount" in output_data:
        parts.append(f"Eligible: ₹{output_data['eligible_amount']:,.2f}")
    
    if "fraud_score" in output_data:
        parts.append(f"Fraud: {output_data['fraud_score']:.2f}")
    
    if "num_signals" in output_data:
        parts.append(f"Signals: {output_data['num_signals']}")
    
    if "decision" in output_data:
        parts.append(f"Decision: {output_data['decision']}")
    
    if "approved_amount" in output_data:
        parts.append(f"Approved: ₹{output_data['approved_amount']:,.2f}")
    
    return ", ".join(parts) if parts else "Output generated"


def _extract_important_details(agent_trace: Dict[str, Any]) -> Dict[str, Any]:
    """Extract important details from agent trace"""
    details = {}
    
    agent_name = agent_trace.get("agent", "")
    output_data = agent_trace.get("output", {})
    
    # DocumentVerifier details
    if agent_name == "DocumentVerifier":
        if "document_classifications" in output_data:
            details["documents"] = output_data["document_classifications"]
        if "errors" in output_data and output_data["errors"]:
            details["verification_errors"] = output_data["errors"]
    
    # OCRExtractor details
    elif agent_name == "OCRExtractor":
        if "extracted_fields" in output_data:
            details["extracted_fields"] = output_data["extracted_fields"]
        if "num_errors" in output_data and output_data["num_errors"] > 0:
            details["extraction_errors"] = output_data.get("num_errors")
    
    # PolicyValidator details
    elif agent_name == "PolicyValidator":
        if "checks" in output_data:
            details["policy_checks"] = [
                {
                    "name": check.get("name"),
                    "result": check.get("result"),
                    "message": check.get("message")
                }
                for check in output_data["checks"]
            ]
        if "applied_copay" in output_data and output_data["applied_copay"]:
            details["copay_deducted"] = output_data["applied_copay"]
        if "applied_network_discount" in output_data and output_data["applied_network_discount"]:
            details["network_discount"] = output_data["applied_network_discount"]
    
    # FraudDetector details
    elif agent_name == "FraudDetector":
        if "signals" in output_data and output_data["signals"]:
            details["fraud_signals"] = [
                {
                    "type": signal.get("type"),
                    "severity": signal.get("severity"),
                    "description": signal.get("description")
                }
                for signal in output_data["signals"]
            ]
        if "requires_manual_review" in output_data:
            details["manual_review_required"] = output_data["requires_manual_review"]
    
    # DecisionMaker details
    elif agent_name == "DecisionMaker":
        if "decision_message" in output_data:
            details["message"] = output_data["decision_message"]
        if "rejection_reasons" in output_data and output_data["rejection_reasons"]:
            details["rejection_reasons"] = output_data["rejection_reasons"]
        if "components_failed" in output_data and output_data["components_failed"]:
            details["failed_components"] = output_data["components_failed"]
    
    return details


def trace_to_json(trace: ClaimTrace) -> str:
    """
    Convert trace to JSON string.
    
    Args:
        trace: ClaimTrace object
        
    Returns:
        JSON string
    """
    import json
    
    trace_dict = {
        "claim_id": trace.claim_id,
        "agent_traces": trace.agent_traces,
        "errors": trace.errors,
        "warnings": trace.warnings,
        "processing_time_seconds": trace.processing_time_seconds,
        "timestamp": trace.timestamp.isoformat()
    }
    
    return json.dumps(trace_dict, indent=2, default=str)
