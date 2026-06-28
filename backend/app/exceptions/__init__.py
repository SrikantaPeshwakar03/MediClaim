"""
MediClaim Exception Module

Provides standardized exception types for consistent error handling across the application.
All exceptions inherit from MediClaimException for easy catching of application-specific errors.
"""

import sys
from typing import Optional, Dict, Any

__all__ = [
    "error_message_detail",
    "MediClaimException",
    "DocumentVerificationError",
    "OCRExtractionError",
    "PolicyValidationError",
    "FraudDetectionError",
    "DecisionMakingError",
    "AuthenticationError",
    "NotFoundError",
    "AccessDeniedError",
    "ConfigurationError",
]


def error_message_detail(error, error_detail: Optional[Any] = None):
    """
    Create a detailed error message with filename, line number, and description.
    
    Args:
        error: The Exception object.
        error_detail (sys): sys module for traceback extraction. Optional.
    
    Returns:
        str: Formatted error message with context details.
    """
    if error_detail is not None and hasattr(error_detail, 'exc_info'):
        _, _, exc_tb = error_detail.exc_info()
        file_name = exc_tb.tb_frame.f_code.co_filename if exc_tb else "Unknown file"
        line_number = exc_tb.tb_lineno if exc_tb else "Unknown line"
        return f"Error occurred in [{file_name}] at line [{line_number}] — {str(error)}"
    else:
        return f"Error occurred — {str(error)}"


# === Base Exception ===

class MediClaimException(Exception):
    """Base exception for all MediClaim errors with user-safe messaging"""
    
    def __init__(
        self, 
        message: str, 
        user_message: str = "Internal server error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message  # Detailed message for logs
        self.user_message = user_message  # Generic message for clients
        self.details = details or {}
    
    def __str__(self):
        return self.message


# === Agent-Specific Exceptions ===

class DocumentVerificationError(MediClaimException):
    """Raised when document verification fails"""
    def __init__(self, reason: str, missing_docs: list = None, details: Optional[Dict[str, Any]] = None):
        message = f"Document verification failed: {reason}"
        user_message = reason  # Use specific message for user
        if details is None:
            details = {}
        if missing_docs:
            details["missing_documents"] = missing_docs
        super().__init__(message, user_message=user_message, details=details)


class OCRExtractionError(MediClaimException):
    """Raised when OCR extraction encounters issues"""
    def __init__(self, reason: str, document_id: str = None, details: Optional[Dict[str, Any]] = None):
        message = f"OCR extraction error: {reason}"
        user_message = "Unable to read document. Please upload a clearer image."
        if details is None:
            details = {}
        if document_id:
            details["document_id"] = document_id
        super().__init__(message, user_message=user_message, details=details)


class PolicyValidationError(MediClaimException):
    """Raised when policy validation logic encounters errors"""
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Policy validation error: {reason}"
        user_message = "Unable to validate claim against policy terms"
        super().__init__(message, user_message=user_message, details=details)


class FraudDetectionError(MediClaimException):
    """Raised when fraud detection encounters issues"""
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Fraud detection error: {reason}"
        user_message = "Unable to complete fraud analysis"
        super().__init__(message, user_message=user_message, details=details)


class DecisionMakingError(MediClaimException):
    """Raised when decision making logic encounters errors"""
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Decision making error: {reason}"
        user_message = "Unable to complete claim decision"
        super().__init__(message, user_message=user_message, details=details)


# === General Application Exceptions ===

class AuthenticationError(MediClaimException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, user_message="Invalid credentials", details=details)


class NotFoundError(MediClaimException):
    """Raised when a requested resource is not found"""
    def __init__(self, resource: str, identifier: str, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found: {identifier}"
        user_message = f"{resource} not found"
        super().__init__(message, user_message=user_message, details=details)


class AccessDeniedError(MediClaimException):
    """Raised when user does not have permission to access a resource"""
    def __init__(self, reason: str = "", details: Optional[Dict[str, Any]] = None):
        message = f"Access denied: {reason}" if reason else "Access denied"
        user_message = "You do not have permission to perform this action"
        super().__init__(message, user_message=user_message, details=details)


class ConfigurationError(MediClaimException):
    """Raised when configuration is invalid or missing"""
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Configuration error: {reason}"
        user_message = "System configuration error. Please contact support."
        super().__init__(message, user_message=user_message, details=details)
