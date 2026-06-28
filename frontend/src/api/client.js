/**
 * API Client
 * 
 * Axios-based client for communicating with the backend API.
 */

import axios from 'axios';

/**
 * Normalize the API base URL.
 * - Falls back to localhost for local dev.
 * - Ensures an absolute URL: if the scheme is missing (e.g. the deploy env var
 *   is set to "my-backend.up.railway.app" without "https://"), axios would
 *   treat it as a relative path and send requests to the frontend host. We
 *   prepend https:// to prevent that.
 * - Strips any trailing slashes so paths join cleanly.
 */
function normalizeBaseUrl(rawUrl) {
  const value = (rawUrl || '').trim();
  if (!value) {
    return 'http://localhost:8000';
  }
  let url = value.replace(/\/+$/, '');
  if (!/^https?:\/\//i.test(url)) {
    url = `https://${url}`;
  }
  return url;
}

const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_URL);

// Diagnostic: surfaces exactly which base URL the live bundle resolved to.
// If this log is absent in the browser console, you are running a stale build.
console.info('[MediClaim] API base URL:', API_BASE_URL, '| raw VITE_API_URL:', import.meta.env.VITE_API_URL);

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error
      console.error('API Error:', error.response.data);
    } else if (error.request) {
      // Request made but no response
      console.error('Network Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// API methods
export const claimsAPI = {
  /**
   * Submit a new claim
   */
  submitClaim: async (formData) => {
    // Do NOT hardcode the multipart Content-Type: the browser must set it so
    // it can include the correct multipart boundary. Setting it to undefined
    // lets axios/the browser generate "multipart/form-data; boundary=...".
    const response = await apiClient.post('/api/v1/claims/submit', formData, {
      headers: {
        'Content-Type': undefined,
      },
    });
    return response.data;
  },

  /**
   * Get claim status
   */
  getStatus: async (claimId) => {
    const response = await apiClient.get(`/api/v1/claims/${claimId}/status`);
    return response.data;
  },

  /**
   * Get claim decision
   */
  getDecision: async (claimId) => {
    const response = await apiClient.get(`/api/v1/claims/${claimId}/decision`);
    return response.data;
  },

  /**
   * Health check
   */
  healthCheck: async () => {
    const response = await apiClient.get('/api/v1/health');
    return response.data;
  },
};

export default apiClient;
