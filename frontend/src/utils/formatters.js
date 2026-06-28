/**
 * Utility functions for formatting data in the UI
 */

/**
 * Format currency in Indian Rupee format
 * @param {number} amount - Amount to format
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return '₹0.00';
  return `₹${amount.toLocaleString('en-IN', { 
    minimumFractionDigits: 2,
    maximumFractionDigits: 2 
  })}`;
};

/**
 * Format date to Indian locale
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
export const formatDate = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

/**
 * Get Tailwind CSS classes for status badges
 * @param {string} status - Status value
 * @returns {string} CSS classes
 */
export const getStatusColor = (status) => {
  const colors = {
    PENDING: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    PROCESSING: 'bg-blue-100 text-blue-800 border-blue-300',
    COMPLETED: 'bg-green-100 text-green-800 border-green-300',
    FAILED: 'bg-red-100 text-red-800 border-red-300'
  };
  return colors[status] || 'bg-gray-100 text-gray-800 border-gray-300';
};

/**
 * Get Tailwind CSS classes for decision badges
 * @param {string} decision - Decision value
 * @returns {string} CSS classes
 */
export const getDecisionColor = (decision) => {
  const colors = {
    APPROVED: 'bg-green-100 text-green-800 border-green-300',
    PARTIAL: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    REJECTED: 'bg-red-100 text-red-800 border-red-300',
    MANUAL_REVIEW: 'bg-orange-100 text-orange-800 border-orange-300'
  };
  return colors[decision] || 'bg-gray-100 text-gray-800 border-gray-300';
};

/**
 * Format input date for HTML date input (YYYY-MM-DD)
 * @param {Date} date - Date object
 * @returns {string} Formatted date string
 */
export const formatInputDate = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * Get today's date in YYYY-MM-DD format
 * @returns {string} Today's date
 */
export const getTodayDate = () => {
  return formatInputDate(new Date());
};
