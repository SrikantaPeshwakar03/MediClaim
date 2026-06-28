"""
LLM Service

Unified LLM service supporting multiple providers via litellm.
Handles provider selection, retries, and structured output parsing.
"""

import json
import time
from typing import Optional, Dict, Any, List
from enum import Enum

from ..config import settings
from ..exceptions import ConfigurationError
from ..loggers import logger


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class LLMService:
    """
    Unified LLM service with multi-provider support.
    
    Uses litellm for unified API across providers.
    """
    
    def __init__(self):
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate that at least one LLM provider is configured"""
        provider = settings.LLM_PROVIDER.lower()
        
        # Ollama doesn't need API key
        if provider != LLMProvider.OLLAMA and not settings.LLM_API_KEY:
            raise ConfigurationError(f"LLM_API_KEY not configured for provider: {provider}")
        
        logger.info(f"LLM service configured with provider: {provider}, model: {settings.LLM_MODEL}")
    
    def _get_model_name(self, provider: Optional[str] = None) -> str:
        """
        Get the LiteLLM-compatible model name for the specified provider.

        LiteLLM routes to the correct backend based on a provider prefix on the
        model name (e.g. "openrouter/openai/gpt-4o-mini", "gemini/gemini-1.5-pro").
        Without the prefix, LiteLLM may guess the wrong provider — e.g. treating an
        OpenRouter model as a plain OpenAI model and sending the key to OpenAI.
        """
        return self._apply_provider_prefix(settings.LLM_MODEL, provider)

    def _apply_provider_prefix(self, model: str, provider: Optional[str] = None) -> str:
        """Apply the LiteLLM provider prefix to a model name."""
        provider = (provider or settings.LLM_PROVIDER).lower()

        prefix_map = {
            LLMProvider.OPENROUTER: "openrouter/",
            LLMProvider.GEMINI: "gemini/",
            LLMProvider.OLLAMA: "ollama/",
            LLMProvider.ANTHROPIC: "anthropic/",
        }

        prefix = prefix_map.get(provider)
        if prefix and not model.startswith(prefix):
            return f"{prefix}{model}"

        # OpenAI (and any already-prefixed model) is used as-is
        return model

    def is_vision_enabled(self) -> bool:
        """True if a vision-capable model is configured for image extraction."""
        return bool(settings.LLM_VISION_MODEL)
    
    def _prepare_api_key(self, provider: str) -> Optional[str]:
        """Get API key for the specified provider"""
        if provider == LLMProvider.OLLAMA:
            return None  # Ollama doesn't require API key
        return settings.LLM_API_KEY
    
    def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        json_mode: bool = False,
        provider: Optional[str] = None,
        max_retries: int = 2
    ) -> str:
        """
        Call LLM with the given prompt.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
            json_mode: Whether to request JSON output
            provider: Specific provider to use (defaults to configured provider)
            max_retries: Number of retries on failure
            
        Returns:
            LLM response text
            
        Raises:
            Exception: If LLM call fails after retries
        """
        try:
            import litellm
            from litellm import completion
            
            # Suppress litellm verbose logging
            litellm.suppress_debug_info = True
            
        except ImportError:
            raise ConfigurationError("litellm not installed. Please install litellm.")
        
        provider = provider or settings.LLM_PROVIDER.lower()
        model_name = self._get_model_name(provider)
        api_key = self._prepare_api_key(provider)
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare kwargs
        kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if api_key:
            kwargs["api_key"] = api_key
        
        # Add base URL for Ollama
        if provider == LLMProvider.OLLAMA:
            kwargs["api_base"] = settings.OLLAMA_BASE_URL
        
        # Try JSON mode if supported and requested
        if json_mode:
            try:
                kwargs["response_format"] = {"type": "json_object"}
            except:
                # Fallback: add JSON instruction to prompt
                messages[-1]["content"] += "\n\nRespond with valid JSON only."
        
        # Retry loop
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"LLM call attempt {attempt + 1}/{max_retries + 1}")
                
                response = completion(**kwargs)
                
                # Extract content
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    logger.info(
                        f"LLM call SUCCESS [{provider}/{model_name}]: "
                        f"{len(content)} chars returned (attempt {attempt + 1})"
                    )
                    return content
                else:
                    raise Exception("Empty response from LLM")
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM call REJECTED/FAILED [{provider}/{model_name}] "
                    f"attempt {attempt + 1}: {e}"
                )
                
                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"LLM call FAILED after {max_retries + 1} attempts "
                        f"[{provider}/{model_name}]. Reason: {last_error}"
                    )
                    raise last_error
        
        raise Exception("LLM call failed")

    def call_llm_vision(
        self,
        images: list,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        json_mode: bool = True,
        max_retries: int = 2,
    ) -> str:
        """
        Call a vision-capable LLM with one or more page images (for handwritten /
        messy documents, including multi-page PDFs).

        Args:
            images: list of raw image byte strings (PNG/JPEG), one per page.

        Requires LLM_VISION_MODEL to be configured.

        Returns:
            The model's text response.

        Raises:
            ConfigurationError: if no vision model is configured.
            Exception: if the call fails after retries.
        """
        if not settings.LLM_VISION_MODEL:
            raise ConfigurationError("LLM_VISION_MODEL is not configured")

        if not images:
            raise OCRExtractionError("No page images provided for vision extraction")

        try:
            import litellm
            from litellm import completion
            litellm.suppress_debug_info = True
        except ImportError:
            raise ConfigurationError("litellm not installed. Please install litellm.")

        import base64

        # Build one image_url content entry per page (all rendered as PNG)
        image_contents = []
        for img_bytes in images:
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            data_url = f"data:image/png;base64,{b64}"
            image_contents.append({"type": "image_url", "image_url": {"url": data_url}})

        provider = settings.LLM_PROVIDER.lower()
        model_name = self._apply_provider_prefix(settings.LLM_VISION_MODEL, provider)
        api_key = self._prepare_api_key(provider)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": prompt}] + image_contents,
        })

        kwargs: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if provider == LLMProvider.OLLAMA:
            kwargs["api_base"] = settings.OLLAMA_BASE_URL
        if json_mode:
            try:
                kwargs["response_format"] = {"type": "json_object"}
            except Exception:
                pass

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = completion(**kwargs)
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    logger.info(
                        f"Vision LLM call SUCCESS [{provider}/{model_name}]: "
                        f"{len(content)} chars from {len(images)} page(s) (attempt {attempt + 1})"
                    )
                    return content
                raise Exception("Empty response from vision LLM")
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Vision LLM call FAILED [{provider}/{model_name}] "
                    f"attempt {attempt + 1}: {e}"
                )
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Vision LLM call failed after {max_retries + 1} attempts")
                    raise last_error

        raise Exception("Vision LLM call failed")
    
    def extract_structured_data(
        self,
        text: str,
        document_type: str,
        schema_description: str,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from text using LLM.
        
        Args:
            text: Raw text to extract from
            document_type: Type of document (PRESCRIPTION, HOSPITAL_BILL, etc.)
            schema_description: Description of expected output schema
            provider: Specific provider to use
            
        Returns:
            Extracted data as dictionary
        """
        system_prompt = f"""You are an expert at extracting structured data from medical documents.
Extract information accurately from the provided text and return it in JSON format.

Document Type: {document_type}
Expected Schema: {schema_description}

Rules:
- Only extract information that is clearly present in the text
- Use null for missing fields
- For amounts, extract numeric values only (no currency symbols)
- For dates, use YYYY-MM-DD format when possible
- Be precise and accurate"""

        user_prompt = f"""Extract structured data from this {document_type}:

{text}

Return the data as a valid JSON object matching the expected schema."""

        try:
            response = self.call_llm(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                json_mode=True,
                provider=provider
            )
            
            # Parse JSON
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Structured extraction failed: {e}")
            return {}
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling various formats.
        
        Args:
            response: LLM response text
            
        Returns:
            Parsed JSON dict or empty dict on failure
        """
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            
            # Try markdown JSON block
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try any code block
            json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            logger.error(f"Failed to parse JSON from LLM response: {response[:200]}")
            return {}
    
    def classify_document(self, text: str, provider: Optional[str] = None) -> str:
        """
        Classify document type from text.
        
        Args:
            text: Raw OCR text
            provider: Specific provider to use
            
        Returns:
            Document type string (e.g., "PRESCRIPTION", "HOSPITAL_BILL")
        """
        from .llm_prompts import (
            DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT,
            get_document_classification_prompt
        )
        
        try:
            response = self.call_llm(
                prompt=get_document_classification_prompt(text),
                system_prompt=DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=50,
                provider=provider
            )
            
            # Extract document type from response
            doc_type = response.strip().upper()
            
            # Validate against known types
            valid_types = [
                "PRESCRIPTION", "HOSPITAL_BILL", "PHARMACY_BILL",
                "LAB_REPORT", "DIAGNOSTIC_REPORT", "DISCHARGE_SUMMARY",
                "DENTAL_REPORT", "UNKNOWN"
            ]
            
            if doc_type in valid_types:
                return doc_type
            
            # Try to find type in response
            for valid_type in valid_types:
                if valid_type in doc_type:
                    return valid_type
            
            return "UNKNOWN"
            
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return "UNKNOWN"

    def classify_document_vision(self, images: list) -> str:
        """
        Classify a document type directly from page image(s) using a vision model.
        Used as a fallback when text OCR yields UNKNOWN (e.g. handwritten docs).

        Returns a document type string, or "UNKNOWN" on failure / if vision is off.
        """
        if not settings.LLM_VISION_MODEL or not images:
            return "UNKNOWN"

        from .llm_prompts import DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT

        try:
            response = self.call_llm_vision(
                images=images,
                prompt="Classify this medical document. Return ONLY the document type name.",
                system_prompt=DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=50,
                json_mode=False,
            )
            doc_type = response.strip().upper()
            valid_types = [
                "PRESCRIPTION", "HOSPITAL_BILL", "PHARMACY_BILL",
                "LAB_REPORT", "DIAGNOSTIC_REPORT", "DISCHARGE_SUMMARY",
                "DENTAL_REPORT", "UNKNOWN"
            ]
            if doc_type in valid_types:
                return doc_type
            for valid_type in valid_types:
                if valid_type in doc_type:
                    return valid_type
            return "UNKNOWN"
        except Exception as e:
            logger.error(f"Vision document classification failed: {e}")
            return "UNKNOWN"
    
    def check_patient_name_consistency(
        self,
        names: List[str],
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if patient names from different documents refer to the same person.
        
        Args:
            names: List of patient names from different documents
            provider: Specific provider to use
            
        Returns:
            Dict with same_person (bool), confidence (float), explanation (str)
        """
        from .llm_prompts import (
            PATIENT_NAME_CHECK_SYSTEM_PROMPT,
            get_patient_name_check_prompt
        )
        
        try:
            response = self.call_llm(
                prompt=get_patient_name_check_prompt(names),
                system_prompt=PATIENT_NAME_CHECK_SYSTEM_PROMPT,
                temperature=0.0,
                json_mode=True,
                provider=provider
            )
            
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Patient name consistency check failed: {e}")
            return {
                "same_person": True,  # Default to True to avoid false rejections
                "confidence": 0.5,
                "explanation": f"Check failed: {str(e)}"
            }


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLMService singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
