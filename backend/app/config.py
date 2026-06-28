"""
MediClaim Configuration

Centralized configuration management using Pydantic Settings.
All environment variables are validated and type-checked.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional
from pathlib import Path
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # === Application ===
    APP_NAME: str = "MediClaim AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # === API ===
    API_V1_PREFIX: str = "/api/v1"

    # Allowed CORS origins. Set CORS_ORIGINS as a comma-separated string (or a
    # JSON array) in your environment, e.g. on Railway:
    #   CORS_ORIGINS="https://my-frontend.up.railway.app,http://localhost:5173"
    # It is parsed into BACKEND_CORS_ORIGINS below. Kept as a separate plain
    # string field so pydantic-settings does not try to JSON-decode it.
    CORS_ORIGINS: Optional[str] = None
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @model_validator(mode="after")
    def _apply_cors_origins(self):
        """Build BACKEND_CORS_ORIGINS from the CORS_ORIGINS env string if provided."""
        if self.CORS_ORIGINS:
            raw = self.CORS_ORIGINS.strip()
            if raw.startswith("["):
                self.BACKEND_CORS_ORIGINS = json.loads(raw)
            else:
                self.BACKEND_CORS_ORIGINS = [
                    origin.strip() for origin in raw.split(",") if origin.strip()
                ]
        return self
    
    # === Supabase ===
    SUPABASE_URL: str
    SUPABASE_KEY: str  # Service role key for backend
    SUPABASE_ANON_KEY: Optional[str] = None  # For frontend (optional)
    SUPABASE_STORAGE_BUCKET: str = "claim-documents"
    
    # === LLM Configuration ===
    # Primary provider selection
    LLM_PROVIDER: str = "openrouter"  # Options: openrouter, openai, anthropic, gemini, ollama
    
    # Universal LLM credentials
    LLM_API_KEY: Optional[str] = None  # API key for the selected provider (not needed for Ollama)
    LLM_MODEL: str = "openai/gpt-4o-mini"  # Model name (format depends on provider)

    # Optional vision-capable model for handwritten / messy document extraction.
    # When set, the OCRExtractor sends the document image directly to this model
    # (better for handwriting) instead of relying solely on PaddleOCR text.
    # Examples: "openai/gpt-4o", "openai/gpt-4o-mini" (OpenRouter), "gpt-4o" (OpenAI),
    # "gemini-1.5-pro" (Gemini). Leave empty to use the text-only OCR path.
    LLM_VISION_MODEL: Optional[str] = None
    
    # Ollama specific (only if LLM_PROVIDER="ollama")
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # === OCR ===
    PADDLEOCR_LANG: str = "en"  # Options: en, ch, etc.
    PADDLEOCR_USE_ANGLE_CLS: bool = True
    PADDLEOCR_USE_GPU: bool = False
    OCR_CONFIDENCE_THRESHOLD: float = 0.5

    # Memory-tuning knobs (important for small cloud instances such as Railway).
    # PaddlePaddle/OpenCV can spike RAM and get OOM-killed during inference.
    # - CPU_THREADS=1 keeps Paddle's thread pool (and its buffers) small.
    # - ENABLE_MKLDNN=False avoids large MKLDNN scratch allocations.
    # - DET_LIMIT_SIDE_LEN caps the detector's internal image size.
    # - MAX_IMAGE_DIM downsizes very large source images before processing.
    PADDLEOCR_CPU_THREADS: int = 1
    PADDLEOCR_ENABLE_MKLDNN: bool = False
    PADDLEOCR_DET_LIMIT_SIDE_LEN: int = 736
    OCR_MAX_IMAGE_DIM: int = 1600
    
    # === Policy ===
    POLICY_FILE_PATH: str = "policy_terms.json"
    
    # === Processing ===
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_DOCUMENT_TYPES: list[str] = ["image/jpeg", "image/jpg", "image/png", "application/pdf"]
    
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Singleton instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance"""
    return settings


# Helper function to get policy file path
def get_policy_file_path() -> Path:
    """Get absolute path to policy_terms.json"""
    # Try backend/data first, then root directory
    backend_path = Path(__file__).parent.parent / "data" / settings.POLICY_FILE_PATH
    if backend_path.exists():
        return backend_path
    
    root_path = Path(__file__).parent.parent.parent.parent / settings.POLICY_FILE_PATH
    if root_path.exists():
        return root_path
    
    raise FileNotFoundError(f"Policy file not found: {settings.POLICY_FILE_PATH}")
