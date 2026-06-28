import { useState, useEffect, useRef } from 'react';

/**
 * Custom hook for smart polling with exponential backoff
 * Pauses when tab is hidden and stops after max attempts
 * 
 * @param {number} maxAttempts - Maximum number of polling attempts
 * @returns {Object} Polling state and controls
 */
export function useSmartPolling(maxAttempts = 60) {
  const [attempts, setAttempts] = useState(0);
  const [isTabVisible, setIsTabVisible] = useState(!document.hidden);
  const attemptRef = useRef(0);

  // Track tab visibility
  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsTabVisible(!document.hidden);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  /**
   * Calculate polling interval based on attempt count
   * - Attempts 1-5: 3 seconds
   * - Attempts 6-10: 5 seconds
   * - Attempts 11+: 10 seconds
   */
  const getPollingInterval = (currentAttempts) => {
    if (currentAttempts <= 5) return 3000;
    if (currentAttempts <= 10) return 5000;
    return 10000;
  };

  /**
   * Increment attempt counter
   */
  const incrementAttempt = () => {
    attemptRef.current += 1;
    setAttempts(attemptRef.current);
  };

  /**
   * Reset attempt counter
   */
  const resetAttempts = () => {
    attemptRef.current = 0;
    setAttempts(0);
  };

  /**
   * Check if polling should continue
   */
  const shouldContinuePolling = (status) => {
    if (attemptRef.current >= maxAttempts) return false;
    if (status === 'COMPLETED' || status === 'FAILED') return false;
    return true;
  };

  return {
    attempts,
    isTabVisible,
    maxAttempts,
    getPollingInterval,
    incrementAttempt,
    resetAttempts,
    shouldContinuePolling,
  };
}
