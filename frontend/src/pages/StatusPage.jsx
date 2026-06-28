import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import { Loader2, CheckCircle, XCircle, Clock, AlertCircle, Zap } from 'lucide-react';
import { claimsAPI } from '../api/client';
import { useSmartPolling } from '../hooks/useSmartPolling';
import { formatDate, getStatusColor } from '../utils/formatters';

/**
 * StatusPage - Display claim processing status with smart polling and auto-redirect
 * Task 17: Smart polling with exponential backoff + auto-redirect when completed
 */
export default function StatusPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  
  const {
    attempts,
    isTabVisible,
    maxAttempts,
    getPollingInterval,
    incrementAttempt,
    shouldContinuePolling,
  } = useSmartPolling(60);

  /**
   * Fetch claim status with React Query
   */
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['claimStatus', claimId],
    queryFn: async () => {
      incrementAttempt();
      return await claimsAPI.getStatus(claimId);
    },
    enabled: isTabVisible,
    refetchInterval: (data) => {
      if (!data || !shouldContinuePolling(data.status)) {
        return false;
      }
      return getPollingInterval(attempts);
    },
    retry: false,
    refetchOnWindowFocus: false,
  });

  /**
   * Auto-redirect to decision page when completed
   */
  useEffect(() => {
    if (data?.status === 'COMPLETED') {
      const timer = setTimeout(() => {
        navigate(`/decision/${claimId}`, { replace: true });
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [data?.status, claimId, navigate]);

  /**
   * Render status icon based on current status
   */
  const renderStatusIcon = () => {
    if (!data) return null;

    switch (data.status) {
      case 'PENDING':
        return <Clock className="h-20 w-20 text-yellow-500 animate-pulse-slow" />;
      case 'PROCESSING':
        return <Loader2 className="h-20 w-20 text-blue-600 animate-spin" />;
      case 'COMPLETED':
        return <CheckCircle className="h-20 w-20 text-green-600 animate-pulse" />;
      case 'FAILED':
        return <XCircle className="h-20 w-20 text-red-600" />;
      default:
        return <AlertCircle className="h-20 w-20 text-gray-600" />;
    }
  };

  /**
   * Get processing stage info with icons
   */
  const getStageInfo = (stage) => {
    const stages = {
      'OCR Extraction': { icon: '📄', color: 'blue' },
      'Document Verification': { icon: '✓', color: 'indigo' },
      'Policy Validation': { icon: '📋', color: 'purple' },
      'Fraud Detection': { icon: '🔍', color: 'pink' },
      'Final Decision': { icon: '⚖️', color: 'green' },
    };
    return stages[stage] || { icon: '⚡', color: 'gray' };
  };

  /**
   * Render loading state
   */
  if (isLoading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="card max-w-md text-center">
          <Loader2 className="h-12 w-12 text-blue-600 animate-spin mb-4 mx-auto" />
          <p className="text-gray-600 font-medium">Loading claim status...</p>
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-red-50 border-2 border-red-200 rounded-xl p-6 shadow-lg">
          <div className="flex items-start">
            <XCircle className="h-6 w-6 text-red-600 mt-0.5 mr-3" />
            <div>
              <h2 className="text-lg font-bold text-red-900 mb-2">
                Error Loading Claim
              </h2>
              <p className="text-red-700 mb-4">
                {error.response?.data?.detail || error.message || 'Failed to load claim status'}
              </p>
              <button
                onClick={() => refetch()}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /**
   * Render max attempts reached
   */
  if (attempts >= maxAttempts && data?.status !== 'COMPLETED' && data?.status !== 'FAILED') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-yellow-50 border-2 border-yellow-200 rounded-xl p-6 shadow-lg">
          <div className="flex items-start">
            <AlertCircle className="h-6 w-6 text-yellow-600 mt-0.5 mr-3" />
            <div>
              <h2 className="text-lg font-bold text-yellow-900 mb-2">
                Polling Timeout
              </h2>
              <p className="text-yellow-700 mb-4">
                Maximum polling attempts reached. The claim is still being processed.
                Please refresh the page or check back later.
              </p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
              >
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const stageInfo = data?.current_stage ? getStageInfo(data.current_stage) : null;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="card">
        {/* Status Icon */}
        <div className="flex justify-center mb-6">
          {renderStatusIcon()}
        </div>

        {/* Claim ID */}
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Claim Status</h1>
          <div className="inline-flex items-center gap-2 bg-gray-100 px-4 py-2 rounded-full">
            <span className="text-sm text-gray-600">Claim ID:</span>
            <span className="font-mono font-bold text-gray-900">{claimId}</span>
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex justify-center mb-6">
          <span className={`badge ${getStatusColor(data?.status)} text-base px-6 py-2`}>
            {data?.status?.replace('_', ' ')}
          </span>
        </div>

        {/* Current Stage with enhanced styling */}
        {data?.current_stage && (
          <div className={`bg-gradient-to-r from-${stageInfo?.color}-50 to-${stageInfo?.color}-100 border-2 border-${stageInfo?.color}-200 rounded-xl p-6 mb-6`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-700 mb-1 flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  Current Stage:
                </p>
                <p className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <span className="text-2xl">{stageInfo?.icon}</span>
                  {data.current_stage}
                </p>
              </div>
              {data?.status === 'PROCESSING' && (
                <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
              )}
            </div>
          </div>
        )}

        {/* Progress indicator for processing */}
        {data?.status === 'PROCESSING' && (
          <div className="mb-6">
            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <div className="bg-gradient-to-r from-blue-600 to-indigo-600 h-2 rounded-full animate-pulse" style={{ width: '75%' }}></div>
            </div>
            <p className="text-center text-xs text-gray-500 mt-2">Processing your claim...</p>
          </div>
        )}

        {/* Last Updated */}
        {data?.updated_at && (
          <div className="text-center text-sm text-gray-600 mb-6 flex items-center justify-center gap-2">
            <Clock className="h-4 w-4" />
            <span>Last updated: {formatDate(data.updated_at)}</span>
          </div>
        )}

        {/* Polling Info */}
        {data?.status === 'PROCESSING' && isTabVisible && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-blue-800 text-center font-medium">
              🔄 Auto-refreshing every {getPollingInterval(attempts) / 1000} seconds...
            </p>
            <p className="text-xs text-blue-600 text-center mt-1">
              Attempt {attempts} of {maxAttempts}
            </p>
          </div>
        )}

        {/* Tab Hidden Warning */}
        {!isTabVisible && data?.status === 'PROCESSING' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-yellow-800 text-center font-medium">
              ⚠️ Polling paused (tab not visible)
            </p>
          </div>
        )}

        {/* Completed - Redirecting */}
        {data?.status === 'COMPLETED' && (
          <div className="bg-green-50 border-2 border-green-300 rounded-xl p-6 mb-6 animate-pulse">
            <p className="text-base text-green-900 text-center font-bold flex items-center justify-center gap-2">
              <CheckCircle className="h-5 w-5" />
              Processing complete! Redirecting to results...
            </p>
          </div>
        )}

        {/* Failed Status */}
        {data?.status === 'FAILED' && (
          <div className="bg-red-50 border-2 border-red-200 rounded-xl p-6 mb-6">
            <p className="text-base font-bold text-red-900 mb-2 flex items-center gap-2">
              <XCircle className="h-5 w-5" />
              Processing Failed
            </p>
            <p className="text-sm text-red-700">
              {data.error_message || 'An error occurred during claim processing.'}
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-center space-x-4">
          <button
            onClick={() => navigate('/')}
            className="btn-secondary"
          >
            Submit New Claim
          </button>
          
          {data?.status === 'COMPLETED' && (
            <button
              onClick={() => navigate(`/decision/${claimId}`)}
              className="btn-primary"
            >
              View Decision Now
            </button>
          )}
          
          {data?.status === 'FAILED' && (
            <button
              onClick={() => refetch()}
              className="btn-primary"
            >
              Retry Loading
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
