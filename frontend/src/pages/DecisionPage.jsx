import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import { Loader2, XCircle, ArrowLeft } from 'lucide-react';
import { claimsAPI } from '../api/client';
import DecisionCard from '../components/DecisionCard';
import TraceViewer from '../components/TraceViewer';

/**
 * DecisionPage - Display final claim decision with full trace
 * Task 18: Decision card + trace viewer for explainability
 */
export default function DecisionPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();

  /**
   * Fetch claim decision
   */
  const { data, isLoading, error } = useQuery({
    queryKey: ['claimDecision', claimId],
    queryFn: () => claimsAPI.getDecision(claimId),
    retry: 1,
    refetchOnWindowFocus: false,
  });

  /**
   * Render loading state
   */
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-12 w-12 text-blue-600 animate-spin mb-4" />
        <p className="text-gray-600">Loading claim decision...</p>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-start">
            <XCircle className="h-6 w-6 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-red-900 mb-2">
                Error Loading Decision
              </h2>
              <p className="text-red-700 mb-4">
                {error.response?.data?.detail || error.message || 'Failed to load claim decision'}
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => navigate(`/status/${claimId}`)}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                >
                  Check Status
                </button>
                <button
                  onClick={() => navigate('/')}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  Submit New Claim
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /**
   * Render claim not processed yet
   */
  if (data && data.status !== 'COMPLETED') {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-yellow-900 mb-2">
            Claim Still Processing
          </h2>
          <p className="text-yellow-700 mb-4">
            The claim decision is not yet available. Current status: <strong>{data.status}</strong>
          </p>
          <button
            onClick={() => navigate(`/status/${claimId}`)}
            className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700"
          >
            Back to Status Page
          </button>
        </div>
      </div>
    );
  }

  const decision = data?.decision;
  const trace = data?.trace;

  return (
    <div className="max-w-5xl mx-auto">
      {/* Back Button */}
      <button
        onClick={() => navigate('/')}
        className="mb-6 flex items-center text-blue-600 hover:text-blue-700 font-medium transition-colors group no-print"
      >
        <ArrowLeft className="h-5 w-5 mr-2 group-hover:-translate-x-1 transition-transform" />
        Submit New Claim
      </button>

      {/* Claim ID Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-3">
          Claim Decision Report
        </h1>
        <div className="inline-flex items-center gap-3 bg-white px-6 py-3 rounded-xl shadow-sm border border-gray-200">
          <span className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Claim ID:</span>
          <span className="font-mono font-bold text-gray-900 text-lg">{claimId}</span>
        </div>
      </div>

      {/* Decision Card */}
      {decision && <DecisionCard decision={decision} />}

      {/* Trace Viewer */}
      {trace && <TraceViewer trace={trace} />}

      {/* Actions */}
      <div className="mt-8 flex justify-center space-x-4 no-print">
        <button
          onClick={() => navigate('/')}
          className="btn-primary px-8 py-3 text-base"
        >
          Submit Another Claim
        </button>
        <button
          onClick={() => window.print()}
          className="btn-secondary px-8 py-3 text-base"
        >
          Print Report
        </button>
      </div>
    </div>
  );
}
