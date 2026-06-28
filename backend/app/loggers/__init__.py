"""
MediClaim Logger Module

Centralized logging configuration with support for:
- File and console logging
- Third-party library verbosity control
- Audit logging for claim processing events
"""

import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# === Log directory and file setup ===
try:
    _repo_root = Path(__file__).resolve().parents[3]  # Go up to MediClaim root
except Exception:
    _repo_root = Path(os.getcwd()).resolve()

LOG_DIR = str(_repo_root / "logs")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except Exception:
    # If the directory can't be created (permissions, etc.), fall back to console-only logging.
    LOG_DIR = ""

LOG_FILE = f"{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.log"
LOG_PATH = os.path.join(LOG_DIR, LOG_FILE) if LOG_DIR else ""

# === Logging Configuration ===
_log_level_name = (os.getenv("LOG_LEVEL") or "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
_log_format = "[%(asctime)s] %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"

try:
    if LOG_PATH:
        logging.basicConfig(filename=LOG_PATH, format=_log_format, level=_log_level)
    else:
        logging.basicConfig(format=_log_format, level=_log_level)
except Exception:
    # Never crash app startup due to logging issues.
    logging.basicConfig(format=_log_format, level=_log_level)

_root_logger = logging.getLogger()
_root_logger.setLevel(_log_level)


# === Configure third-party library log levels ===
def configure_logging():
    """
    Configure logging levels for the application.
    Reduces verbosity of third-party libraries like httpx, urllib3, etc.
    """
    # Set httpx to WARNING to reduce Supabase request logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Set other noisy libraries to WARNING
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Keep uvicorn/fastapi at INFO
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Quiet down the OCR stack (RapidOCR / ONNXRuntime)
    logging.getLogger("RapidOCR").setLevel(logging.WARNING)
    logging.getLogger("onnxruntime").setLevel(logging.WARNING)
    
    # Configure LangChain/LangGraph
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langgraph").setLevel(logging.INFO)
    
    # Configure LLM providers
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.INFO)


# === Optional: Stream logs to console as well ===
_has_console = any(
    isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
    for h in _root_logger.handlers
)

if not _has_console:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(_log_level)
    console_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s | %(message)s"))
    _root_logger.addHandler(console_handler)

# Auto-configure logging on module import
configure_logging()

# === Application logger ===
logger = logging.getLogger("mediclaim")
logger.setLevel(_log_level)
logger.propagate = True


# === Audit Logging ===
def log_claim_event(
    claim_id: str,
    event_type: str,
    agent_name: Optional[str] = None,
    details: Optional[dict] = None,
    member_id: Optional[str] = None
):
    """
    Log a claim processing event for audit purposes.
    
    Args:
        claim_id: The claim ID being processed
        event_type: Type of event (SUBMITTED, VERIFIED, EXTRACTED, VALIDATED, DECIDED, etc.)
        agent_name: Name of the agent that triggered the event
        details: Optional additional metadata
        member_id: Optional member ID for tracking
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "claim_id": claim_id,
        "event_type": event_type,
        "agent_name": agent_name,
        "member_id": member_id,
        "details": details or {}
    }
    
    # Log to console with structured format
    logger.info(f"[AUDIT] {json.dumps(log_entry)}")
    
    # TODO: Insert into audit_logs table when Supabase is fully integrated
    # supabase_admin.table("audit_logs").insert(log_entry).execute()
