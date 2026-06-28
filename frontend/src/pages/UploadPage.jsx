import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Loader2 } from 'lucide-react';
import { claimsAPI } from '../api/client';
import { getTodayDate } from '../utils/formatters';

/**
 * UploadPage - Claim submission form
 * Task 16: Simple form with file upload
 */
export default function UploadPage() {
  const navigate = useNavigate();
  
  // Form state
  const [formData, setFormData] = useState({
    member_id: '',
    policy_id: 'PLUM_GHI_2024',
    claim_category: 'CONSULTATION',
    treatment_date: getTodayDate(),
    claimed_amount: '',
    hospital_name: ''
  });
  
  const [files, setFiles] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [simulateFailure, setSimulateFailure] = useState(false);

  /**
   * Handle input changes
   */
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  /**
   * Handle file selection
   * Appends newly selected files to the existing list (deduped by name+size)
   * so selecting files in multiple steps doesn't replace earlier ones.
   */
  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);

    setFiles((prev) => {
      const merged = [...prev];
      selectedFiles.forEach((file) => {
        const isDuplicate = merged.some(
          (f) => f.name === file.name && f.size === file.size
        );
        if (!isDuplicate) {
          merged.push(file);
        }
      });
      return merged;
    });

    // Reset the input so selecting the same file again still triggers onChange
    e.target.value = '';

    // Clear file error
    if (errors.files) {
      setErrors(prev => ({ ...prev, files: null }));
    }
  };

  /**
   * Remove a selected file by index
   */
  const handleRemoveFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  /**
   * Validate form before submission
   */
  const validateForm = () => {
    const newErrors = {};

    if (!formData.member_id.trim()) {
      newErrors.member_id = 'Member ID is required';
    }

    if (!formData.claimed_amount) {
      newErrors.claimed_amount = 'Claimed amount is required';
    } else if (parseFloat(formData.claimed_amount) <= 0) {
      newErrors.claimed_amount = 'Amount must be greater than 0';
    }

    if (!formData.treatment_date) {
      newErrors.treatment_date = 'Treatment date is required';
    } else if (new Date(formData.treatment_date) > new Date()) {
      newErrors.treatment_date = 'Treatment date cannot be in the future';
    }

    if (files.length === 0) {
      newErrors.files = 'Please upload at least one document';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      // Build FormData with individual fields (backend expects Form fields, not a JSON blob)
      const submitData = new FormData();

      submitData.append('member_id', formData.member_id.trim());
      submitData.append('policy_id', formData.policy_id);
      submitData.append('claim_category', formData.claim_category);
      submitData.append('treatment_date', formData.treatment_date);
      submitData.append('claimed_amount', parseFloat(formData.claimed_amount));
      if (formData.hospital_name.trim()) {
        submitData.append('hospital_name', formData.hospital_name.trim());
      }
      submitData.append('simulate_component_failure', simulateFailure);

      // Add files (backend reads these under the "files" key)
      files.forEach((file) => {
        submitData.append('files', file);
      });

      // Submit to backend
      const response = await claimsAPI.submitClaim(submitData);
      
      // Navigate to status page
      navigate(`/status/${response.claim_id}`);
      
    } catch (error) {
      console.error('Claim submission error:', error);
      setErrors({
        submit: error.response?.data?.detail || error.message || 'Failed to submit claim. Please try again.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="card">
        <div className="mb-6">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-2">
            Submit Insurance Claim
          </h1>
          <p className="text-gray-600 text-sm">Fill in the details below to process your health insurance claim</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Member ID */}
          <div>
            <label htmlFor="member_id" className="block text-sm font-medium text-gray-700 mb-1">
              Member ID *
            </label>
            <input
              type="text"
              id="member_id"
              name="member_id"
              value={formData.member_id}
              onChange={handleInputChange}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.member_id ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="e.g., EMP001"
              disabled={isSubmitting}
            />
            {errors.member_id && (
              <p className="mt-1 text-sm text-red-600">{errors.member_id}</p>
            )}
          </div>

          {/* Policy ID */}
          <div>
            <label htmlFor="policy_id" className="block text-sm font-medium text-gray-700 mb-1">
              Policy ID *
            </label>
            <input
              type="text"
              id="policy_id"
              name="policy_id"
              value={formData.policy_id}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
              disabled
            />
          </div>

          {/* Claim Category */}
          <div>
            <label htmlFor="claim_category" className="block text-sm font-medium text-gray-700 mb-1">
              Claim Category *
            </label>
            <select
              id="claim_category"
              name="claim_category"
              value={formData.claim_category}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isSubmitting}
            >
              <option value="CONSULTATION">Consultation</option>
              <option value="DIAGNOSTIC">Diagnostic</option>
              <option value="PHARMACY">Pharmacy</option>
              <option value="DENTAL">Dental</option>
              <option value="VISION">Vision</option>
              <option value="ALTERNATIVE_MEDICINE">Alternative Medicine</option>
            </select>
          </div>

          {/* Treatment Date */}
          <div>
            <label htmlFor="treatment_date" className="block text-sm font-medium text-gray-700 mb-1">
              Treatment Date *
            </label>
            <input
              type="date"
              id="treatment_date"
              name="treatment_date"
              value={formData.treatment_date}
              onChange={handleInputChange}
              max={getTodayDate()}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.treatment_date ? 'border-red-500' : 'border-gray-300'
              }`}
              disabled={isSubmitting}
            />
            {errors.treatment_date && (
              <p className="mt-1 text-sm text-red-600">{errors.treatment_date}</p>
            )}
          </div>

          {/* Claimed Amount */}
          <div>
            <label htmlFor="claimed_amount" className="block text-sm font-medium text-gray-700 mb-1">
              Claimed Amount (₹) *
            </label>
            <input
              type="number"
              id="claimed_amount"
              name="claimed_amount"
              value={formData.claimed_amount}
              onChange={handleInputChange}
              min="0"
              step="0.01"
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.claimed_amount ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="e.g., 1500.00"
              disabled={isSubmitting}
            />
            {errors.claimed_amount && (
              <p className="mt-1 text-sm text-red-600">{errors.claimed_amount}</p>
            )}
          </div>

          {/* Hospital Name (Optional) */}
          <div>
            <label htmlFor="hospital_name" className="block text-sm font-medium text-gray-700 mb-1">
              Hospital Name (Optional)
            </label>
            <input
              type="text"
              id="hospital_name"
              name="hospital_name"
              value={formData.hospital_name}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Apollo Hospitals"
              disabled={isSubmitting}
            />
          </div>

          {/* File Upload */}
          <div>
            <label htmlFor="files" className="block text-sm font-medium text-gray-700 mb-1">
              Upload Documents *
            </label>
            <div className="mt-1">
              <label
                htmlFor="files"
                className={`flex items-center justify-center px-4 py-6 border-2 border-dashed rounded-md cursor-pointer hover:border-blue-500 transition-colors ${
                  errors.files ? 'border-red-500' : 'border-gray-300'
                }`}
              >
                <div className="text-center">
                  <Upload className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-600">
                    {files.length > 0 ? `${files.length} file(s) selected` : 'Click to upload files'}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    PNG, JPG, PDF up to 10MB each
                  </p>
                </div>
                <input
                  type="file"
                  id="files"
                  name="files"
                  multiple
                  accept="image/*,application/pdf"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={isSubmitting}
                />
              </label>
            </div>
            {errors.files && (
              <p className="mt-1 text-sm text-red-600">{errors.files}</p>
            )}
            {files.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm text-gray-600">
                {files.map((file, index) => (
                  <li
                    key={`${file.name}-${file.size}-${index}`}
                    className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded px-3 py-1.5"
                  >
                    <span className="truncate mr-2">• {file.name}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveFile(index)}
                      disabled={isSubmitting}
                      className="text-red-600 hover:text-red-800 text-xs font-medium disabled:opacity-50"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Submit Error */}
          {errors.submit && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-sm text-red-800">{errors.submit}</p>
            </div>
          )}

          {/* Simulate component failure (TC011 resilience test) */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="simulate_component_failure"
              checked={simulateFailure}
              onChange={(e) => setSimulateFailure(e.target.checked)}
              disabled={isSubmitting}
              className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="simulate_component_failure" className="ml-2 text-sm text-gray-600">
              Simulate component failure (resilience test)
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex items-center justify-center px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold rounded-xl hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl text-lg"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="animate-spin -ml-1 mr-3 h-6 w-6" />
                Processing Your Claim...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-5 w-5" />
                Submit Claim for Processing
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
