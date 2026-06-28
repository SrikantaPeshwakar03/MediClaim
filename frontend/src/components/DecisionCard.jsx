import { CheckCircle, XCircle, AlertTriangle, AlertCircle, Info, TrendingUp, Shield, DollarSign } from 'lucide-react';
import { formatCurrency, getDecisionColor } from '../utils/formatters';

/**
 * DecisionCard - Enhanced display of claim decision with full explainability
 * Shows decision badge, amounts, reasons, confidence score, and detailed breakdown
 * Requirement: Make every decision explainable
 */
export default function DecisionCard({ decision }) {
  if (!decision) return null;

  /**
   * Render decision icon
   */
  const renderDecisionIcon = () => {
    switch (decision.decision) {
      case 'APPROVED':
        return <CheckCircle className="h-16 w-16 text-green-600" />;
      case 'REJECTED':
        return <XCircle className="h-16 w-16 text-red-600" />;
      case 'PARTIAL':
        return <AlertTriangle className="h-16 w-16 text-yellow-600" />;
      case 'MANUAL_REVIEW':
        return <AlertCircle className="h-16 w-16 text-orange-600" />;
      default:
        return <AlertCircle className="h-16 w-16 text-gray-600" />;
    }
  };

  /**
   * Get confidence level description
   */
  const getConfidenceLevel = (score) => {
    if (score >= 0.9) return { label: 'Very High', color: 'text-green-700', bg: 'bg-green-100' };
    if (score >= 0.7) return { label: 'High', color: 'text-blue-700', bg: 'bg-blue-100' };
    if (score >= 0.5) return { label: 'Medium', color: 'text-yellow-700', bg: 'bg-yellow-100' };
    return { label: 'Low', color: 'text-orange-700', bg: 'bg-orange-100' };
  };

  const confidenceLevel = decision.confidence_score !== null && decision.confidence_score !== undefined 
    ? getConfidenceLevel(decision.confidence_score) 
    : null;

  return (
    <div className="explainability-section">
      {/* Explainability Header */}
      <div className="flex items-center gap-2 mb-6 pb-4 border-b-2 border-blue-100">
        <Info className="h-6 w-6 text-blue-600" />
        <h2 className="text-2xl font-bold text-gray-900">Decision Explanation</h2>
      </div>

      {/* Decision Header */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* Left: Decision Icon and Status */}
        <div className="flex items-center gap-4">
          {renderDecisionIcon()}
          <div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Final Decision</h3>
            <span className={`badge ${getDecisionColor(decision.decision)} text-lg px-6 py-2`}>
              {decision.decision?.replace('_', ' ')}
            </span>
          </div>
        </div>
        
        {/* Right: Confidence Score */}
        {confidenceLevel && (
          <div className={`${confidenceLevel.bg} rounded-xl p-6 border-2 border-${confidenceLevel.color.replace('text-', '')}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-700 mb-1 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Decision Confidence
                </p>
                <p className={`text-3xl font-bold ${confidenceLevel.color}`}>
                  {Math.round(decision.confidence_score * 100)}%
                </p>
                <p className="text-sm text-gray-600 mt-1">{confidenceLevel.label} Confidence</p>
              </div>
              <Shield className={`h-12 w-12 ${confidenceLevel.color} opacity-20`} />
            </div>
          </div>
        )}
      </div>

      {/* Decision Message */}
      {decision.decision_message && (
        <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-4 mb-6">
          <p className="text-gray-800 font-medium">{decision.decision_message}</p>
        </div>
      )}

      {/* Financial Summary - Enhanced */}
      <div className="mb-8">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-green-600" />
          Financial Breakdown
        </h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Original Amount */}
          {decision.original_amount !== null && decision.original_amount !== undefined && (
            <div className="info-card">
              <p className="text-xs font-semibold text-gray-600 mb-1 uppercase tracking-wide">Original Amount</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(decision.original_amount)}
              </p>
            </div>
          )}

          {/* Approved Amount */}
          {decision.approved_amount !== null && decision.approved_amount !== undefined && (
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-4 border-2 border-green-300 shadow-sm">
              <p className="text-xs font-semibold text-green-700 mb-1 uppercase tracking-wide">Approved Amount</p>
              <p className="text-2xl font-bold text-green-900">
                {formatCurrency(decision.approved_amount)}
              </p>
            </div>
          )}

          {/* Deductions */}
          {decision.copay_deducted > 0 && (
            <div className="info-card border-orange-200">
              <p className="text-xs font-semibold text-orange-700 mb-1 uppercase tracking-wide">Co-pay Deducted</p>
              <p className="text-2xl font-bold text-orange-900">
                {formatCurrency(decision.copay_deducted)}
              </p>
            </div>
          )}

          {decision.network_discount_applied > 0 && (
            <div className="info-card border-blue-200">
              <p className="text-xs font-semibold text-blue-700 mb-1 uppercase tracking-wide">Network Discount</p>
              <p className="text-2xl font-bold text-blue-900">
                {formatCurrency(decision.network_discount_applied)}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Rejection Reasons - Enhanced */}
      {decision.rejection_reasons && decision.rejection_reasons.length > 0 && (
        <div className="bg-red-50 border-2 border-red-300 rounded-xl p-6 mb-6">
          <h3 className="text-base font-bold text-red-900 mb-3 flex items-center gap-2">
            <XCircle className="h-5 w-5" />
            Why was this claim rejected?
          </h3>
          <ul className="space-y-2">
            {decision.rejection_reasons.map((reason, index) => (
              <li key={index} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-red-200 rounded-full flex items-center justify-center text-red-800 font-bold text-sm">
                  {index + 1}
                </span>
                <span className="text-sm text-red-900 font-medium pt-0.5">{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings - Enhanced */}
      {decision.warnings && decision.warnings.length > 0 && (
        <div className="bg-yellow-50 border-2 border-yellow-300 rounded-xl p-6 mb-6">
          <h3 className="text-base font-bold text-yellow-900 mb-3 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Important Notices
          </h3>
          <ul className="space-y-2">
            {decision.warnings.map((warning, index) => (
              <li key={index} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-yellow-200 rounded-full flex items-center justify-center text-yellow-800 font-bold text-sm">
                  ⚠
                </span>
                <span className="text-sm text-yellow-900 font-medium pt-0.5">{warning}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Line Item Decisions (for PARTIAL) - Enhanced */}
      {decision.line_item_decisions && decision.line_item_decisions.length > 0 && (
        <div className="border-2 border-gray-300 rounded-xl overflow-hidden mb-6 shadow-sm">
          <div className="bg-gradient-to-r from-gray-100 to-gray-200 px-6 py-4 border-b-2 border-gray-300">
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Info className="h-5 w-5 text-gray-700" />
              Itemized Decision Breakdown
            </h3>
            <p className="text-xs text-gray-600 mt-1">Detailed explanation for each line item</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Item Description</th>
                  <th className="px-6 py-4 text-right text-xs font-bold text-gray-700 uppercase tracking-wider">Amount</th>
                  <th className="px-6 py-4 text-center text-xs font-bold text-gray-700 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Explanation</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {decision.line_item_decisions.map((item, index) => (
                  <tr key={index} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{item.description || item.item}</td>
                    <td className="px-6 py-4 text-sm font-bold text-gray-900 text-right">{formatCurrency(item.amount)}</td>
                    <td className="px-6 py-4 text-center">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border-2 ${
                        item.status === 'APPROVED' 
                          ? 'bg-green-100 text-green-800 border-green-300' 
                          : 'bg-red-100 text-red-800 border-red-300'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">{item.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Component Failures (graceful degradation) - Enhanced */}
      {decision.components_failed && decision.components_failed.length > 0 && (
        <div className="bg-orange-50 border-2 border-orange-300 rounded-xl p-6">
          <h3 className="text-base font-bold text-orange-900 mb-3 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            Processing Limitations Detected
          </h3>
          <p className="text-sm text-orange-800 mb-4 font-medium">
            Some components encountered issues during processing. The decision was made with the available information, but may require manual review.
          </p>
          <div className="bg-white rounded-lg p-4 border border-orange-200 mb-4">
            <p className="text-xs font-semibold text-orange-900 mb-2">Failed Components:</p>
            <ul className="space-y-1">
              {[...new Set(decision.components_failed)].map((failure, index) => (
                <li key={index} className="text-sm text-orange-800 flex items-center gap-2">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                  <strong>{failure}</strong>
                </li>
              ))}
            </ul>
          </div>
          {decision.manual_review_reason && (
            <p className="text-sm text-orange-900 font-bold bg-orange-100 rounded-lg p-3 border border-orange-300">
              📋 {decision.manual_review_reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
