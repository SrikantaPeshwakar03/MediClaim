/**
 * API Client
 * 
 * Axios-based client for communicating with the backend API.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
    const response = await apiClient.post('/api/v1/claims/submit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
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
