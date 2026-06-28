import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, XCircle, AlertCircle, Clock, Activity } from 'lucide-react';
import { formatDate } from '../utils/formatters';

/**
 * TraceViewer - Enhanced collapsible agent trace for full explainability
 * Shows each agent's execution with status, timestamp, inputs, and detailed outputs
 * Requirement: Make every decision explainable - show what was checked, what passed/failed, and why
 */
export default function TraceViewer({ trace }) {
  const [expandedAgents, setExpandedAgents] = useState({});

  // Backend returns the trace under `agent_traces`; each entry uses `agent` for
  // the name and a lowercase `status` ("success"/"failed").
  const rawAgents = trace?.agent_traces || trace?.agents || [];

  // Normalize entries into a consistent shape for rendering
  const seen = new Set();
  const agents = rawAgents
    .map((entry, index) => ({
      name: entry.agent || entry.name || `Step ${index + 1}`,
      status: (entry.status || 'unknown').toString().toUpperCase(),
      timestamp: entry.timestamp,
      output: entry.output,
      input: entry.input,
      error: entry.error,
    }))
    // Drop duplicate entries (same agent + timestamp + status)
    .filter((a) => {
      const key = `${a.name}-${a.timestamp}-${a.status}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((a, index) => ({ ...a, _key: `${a.name}-${a.timestamp}-${index}` }));

  if (agents.length === 0) {
    return (
      <div className="explainability-section">
        <h2 className="section-title">
          <Activity className="h-6 w-6 text-blue-600" />
          Execution Trace
        </h2>
        <p className="text-gray-600">No trace data available.</p>
      </div>
    );
  }

  /**
   * Toggle agent expansion
   */
  const toggleAgent = (agentKey) => {
    setExpandedAgents(prev => ({
      ...prev,
      [agentKey]: !prev[agentKey]
    }));
  };

  /**
   * Expand all agents
   */
  const expandAll = () => {
    const expanded = {};
    agents.forEach(agent => {
      expanded[agent._key] = true;
    });
    setExpandedAgents(expanded);
  };

  /**
   * Collapse all agents
   */
  const collapseAll = () => {
    setExpandedAgents({});
  };

  /**
   * Render agent status icon
   */
  const renderStatusIcon = (status) => {
    switch (status) {
      case 'PASSED':
      case 'SUCCESS':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'FAILED':
      case 'ERROR':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'SKIPPED':
      case 'PARTIAL_FAILURE':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-600" />;
    }
  };

  /**
   * Get agent description for explainability
   */
  const getAgentDescription = (agentName) => {
    const descriptions = {
      'OCR Extraction': 'Extracted text and data from uploaded documents using Optical Character Recognition',
      'Document Verification': 'Verified document authenticity, quality, and completeness',
      'Policy Validation': 'Checked claim against policy terms, limits, and coverage rules',
      'Fraud Detection': 'Analyzed claim for potential fraud indicators and anomalies',
      'Final Decision': 'Synthesized all checks and made the final claim decision',
    };
    return descriptions[agentName] || 'Processed claim data';
  };

  /**
   * Render agent output in an explainable format
   */
  const renderAgentOutput = (agent) => {
    if (agent.error) {
      return (
        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4">
          <p className="text-sm font-bold text-red-900 mb-2 flex items-center gap-2">
            <XCircle className="h-4 w-4" />
            Error Occurred:
          </p>
          <p className="text-sm text-red-800 font-mono bg-red-100 p-3 rounded">{agent.error}</p>
        </div>
      );
    }

    if (!agent.output) {
      return <p className="text-gray-600 text-sm italic">No output data available</p>;
    }

    // Extract key fields for display
    const output = agent.output;
    const keyFields = [];

    // Common fields across agents
    if (output.status) keyFields.push({ label: 'Status', value: output.status, type: 'status' });
    if (output.message) keyFields.push({ label: 'Message', value: output.message, type: 'text' });
    if (output.verification_passed !== undefined) keyFields.push({ 
      label: 'Verification Passed', 
      value: output.verification_passed ? '✓ Yes' : '✗ No',
      type: output.verification_passed ? 'success' : 'error'
    });
    if (output.all_checks_passed !== undefined) keyFields.push({ 
      label: 'All Checks Passed', 
      value: output.all_checks_passed ? '✓ Yes' : '✗ No',
      type: output.all_checks_passed ? 'success' : 'error'
    });
    if (output.eligible_amount !== undefined) keyFields.push({ 
      label: 'Eligible Amount', 
      value: `₹${Number(output.eligible_amount).toLocaleString()}`,
      type: 'currency'
    });
    if (output.fraud_score !== undefined) keyFields.push({ 
      label: 'Fraud Score', 
      value: (output.fraud_score * 100).toFixed(1) + '%',
      type: output.fraud_score > 0.5 ? 'warning' : 'success'
    });
    if (output.decision) keyFields.push({ label: 'Decision', value: output.decision, type: 'decision' });
    if (output.approved_amount !== undefined) keyFields.push({ 
      label: 'Approved Amount', 
      value: `₹${Number(output.approved_amount).toLocaleString()}`,
      type: 'currency'
    });

    return (
      <div className="space-y-4">
        {/* Agent Description */}
        <div className="bg-blue-50 border-l-4 border-blue-500 rounded p-3">
          <p className="text-sm text-blue-900 font-medium">
            <strong>What this agent did:</strong> {getAgentDescription(agent.name)}
          </p>
        </div>

        {/* Key Fields with Enhanced Styling */}
        {keyFields.length > 0 && (
          <div className="grid md:grid-cols-2 gap-3">
            {keyFields.map((field, index) => {
              const bgColors = {
                success: 'bg-green-50 border-green-300',
                error: 'bg-red-50 border-red-300',
                warning: 'bg-yellow-50 border-yellow-300',
                currency: 'bg-blue-50 border-blue-300',
                decision: 'bg-purple-50 border-purple-300',
                status: 'bg-gray-50 border-gray-300',
                text: 'bg-gray-50 border-gray-300',
              };
              const textColors = {
                success: 'text-green-900',
                error: 'text-red-900',
                warning: 'text-yellow-900',
                currency: 'text-blue-900',
                decision: 'text-purple-900',
                status: 'text-gray-900',
                text: 'text-gray-900',
              };
              
              return (
                <div key={index} className={`${bgColors[field.type] || bgColors.text} border rounded-lg p-3`}>
                  <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">{field.label}</p>
                  <p className={`text-base font-bold ${textColors[field.type] || textColors.text}`}>
                    {field.value}
                  </p>
                </div>
              );
            })}
          </div>
        )}

        {/* Policy check breakdown - Enhanced for Explainability */}
        {output.checks && output.checks.length > 0 && (
          <div className="bg-white border-2 border-gray-300 rounded-lg overflow-hidden">
            <div className="bg-gray-100 px-4 py-3 border-b-2 border-gray-300">
              <p className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-gray-700" />
                Policy Checks Performed:
              </p>
            </div>
            <div className="p-4 space-y-2">
              {output.checks.map((check, index) => (
                <div key={index} className={`flex items-center justify-between p-3 rounded-lg border-2 ${
                  check.result === 'PASSED' 
                    ? 'bg-green-50 border-green-300' 
                    : 'bg-red-50 border-red-300'
                }`}>
                  <div className="flex items-center gap-2">
                    {check.result === 'PASSED' ? (
                      <CheckCircle className="h-4 w-4 text-green-700 flex-shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-700 flex-shrink-0" />
                    )}
                    <span className="text-sm font-medium text-gray-900">{check.name}</span>
                  </div>
                  <span className={`text-sm font-bold px-3 py-1 rounded-full ${
                    check.result === 'PASSED' 
                      ? 'bg-green-200 text-green-900' 
                      : 'bg-red-200 text-red-900'
                  }`}>
                    {check.result}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Errors - Enhanced */}
        {output.errors && output.errors.length > 0 && (
          <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4">
            <p className="text-sm font-bold text-red-900 mb-3 flex items-center gap-2">
              <XCircle className="h-5 w-5" />
              Issues Found:
            </p>
            <ul className="space-y-2">
              {output.errors.map((issue, index) => (
                <li key={index} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-5 h-5 bg-red-200 rounded-full flex items-center justify-center text-red-800 font-bold text-xs">
                    !
                  </span>
                  <span className="text-sm text-red-900 font-medium pt-0.5">{issue}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Full JSON Output (collapsible) - for technical users */}
        <details className="bg-gray-100 rounded-lg border border-gray-300">
          <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-200 rounded-lg transition-colors">
            📋 View Technical Details (JSON)
          </summary>
          <div className="p-4 border-t border-gray-300">
            <pre className="text-xs text-gray-800 overflow-x-auto whitespace-pre-wrap break-words bg-white p-3 rounded border border-gray-200">
              {JSON.stringify(output, null, 2)}
            </pre>
          </div>
        </details>
      </div>
    );
  };

  return (
    <div className="explainability-section">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 pb-4 border-b-2 border-blue-100">
        <h2 className="section-title">
          <Activity className="h-6 w-6 text-blue-600" />
          Processing Timeline & Decisions
        </h2>
        <div className="flex space-x-2">
          <button
            onClick={expandAll}
            className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-200"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors border border-gray-200"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Explainability Notice */}
      <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-900 font-medium">
          <strong>Complete Audit Trail:</strong> This trace shows every step taken to process your claim, 
          including what was checked, what passed or failed, and why the final decision was made.
        </p>
      </div>

      {/* Agent Trace */}
      <div className="space-y-3">
        {agents.map((agent, agentIndex) => {
          const isExpanded = expandedAgents[agent._key];
          
          return (
            <div key={agent._key} className="border-2 border-gray-300 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
              {/* Agent Header (clickable) */}
              <button
                onClick={() => toggleAgent(agent._key)}
                className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  {/* Step Number */}
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-sm">
                    {agentIndex + 1}
                  </div>

                  {/* Expand/Collapse Icon */}
                  {isExpanded ? (
                    <ChevronDown className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-500" />
                  )}
                  
                  {/* Status Icon */}
                  {renderStatusIcon(agent.status)}
                  
                  {/* Agent Name */}
                  <span className="font-bold text-gray-900 text-lg">{agent.name}</span>
                  
                  {/* Status Badge */}
                  <span className={`px-3 py-1 rounded-full text-xs font-bold border-2 ${
                    agent.status === 'PASSED' || agent.status === 'SUCCESS'
                      ? 'bg-green-100 text-green-800 border-green-300'
                      : agent.status === 'FAILED' || agent.status === 'ERROR'
                      ? 'bg-red-100 text-red-800 border-red-300'
                      : 'bg-yellow-100 text-yellow-800 border-yellow-300'
                  }`}>
                    {agent.status}
                  </span>
                </div>
                
                {/* Timestamp */}
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Clock className="h-4 w-4" />
                  <span>{formatDate(agent.timestamp)}</span>
                </div>
              </button>

              {/* Agent Output (expanded) */}
              {isExpanded && (
                <div className="border-t-2 border-gray-200 p-6 bg-gradient-to-br from-gray-50 to-white">
                  {renderAgentOutput(agent)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Trace Metadata */}
      {trace?.processing_time_seconds !== undefined && trace?.processing_time_seconds !== null && (
        <div className="mt-6 pt-4 border-t-2 border-gray-200">
          <div className="flex items-center justify-between bg-gray-50 rounded-lg p-4">
            <span className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Total Processing Time:
            </span>
            <span className="text-lg font-bold text-gray-900">
              {trace.processing_time_seconds.toFixed(2)}s
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
