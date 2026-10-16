import re
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

class SecretMaskingFilter(logging.Filter):
    """
    خفیہ چابیاں (API Keys)، ٹوکنز اور کوکیز کو لاگز میں ظاہر ہونے سے روکنے والا سیکیورٹی فلٹر
    """
    SECRET_PATTERNS = [
        re.compile(r'(AIzaSy[A-Za-z0-9_-]{33})', re.IGNORECASE),  # Google API Keys
        re.compile(r'(sk-[A-Za-z0-9_-]{30,})', re.IGNORECASE),     # OpenAI API Keys
        re.compile(r'("?(?:key|token|secret|password|cookie|storage_state)"?\s*[:=]\s*"?)([^"\'\s,;]+)("?)', re.IGNORECASE),
        re.compile(r'([A-Za-z0-9+/=]{40,})', re.IGNORECASE),       # Long Base64/hashes/tokens
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.mask_secrets(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.mask_secrets(str(arg)) for arg in record.args)
        return True

    @classmethod
    def mask_secrets(cls, text: str) -> str:
        masked = text
        for pat in cls.SECRET_PATTERNS:
            def replace_match(m):
                if len(m.groups()) == 3:
                    # Key-value pair like key="secret"
                    prefix, secret, suffix = m.group(1), m.group(2), m.group(3)
                    if len(secret) > 6:
                        masked_secret = secret[:2] + "****" + secret[-2:]
                    else:
                        masked_secret = "****"
                    return f"{prefix}{masked_secret}{suffix}"
                else:
                    matched_str = m.group(0)
                    if len(matched_str) > 6:
                        return matched_str[:2] + "****" + matched_str[-2:]
                    return "****"
            masked = pat.sub(replace_match, masked)
        return masked

class StructuredLogger:
    """
    منظم اور محفوظ اسٹرکچرڈ لاگر برائے ایجنٹ اے ایم
    ہر جاب اور ٹاسک کے تفصیلی مراحل کو باوقار انداز میں ریکارڈ کرتا ہے۔
    """
    def __init__(self, logger_name: str = "agent_am.structured"):
        self.logger = logging.getLogger(logger_name)
        if not any(isinstance(f, SecretMaskingFilter) for f in self.logger.filters):
            self.logger.addFilter(SecretMaskingFilter())

    def log_event(
        self,
        event_type: str,
        task_name: str,
        status: str,
        details_urdu: str,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """منظم ایونٹ لاگ بناتا اور محفوظ کرتا ہے"""
        now_pkt = datetime.now(ZoneInfo("Asia/Karachi"))
        clean_error = SecretMaskingFilter.mask_secrets(str(error)) if error else None
        
        event = {
            "timestamp_pkt": now_pkt.isoformat(),
            "event_type": event_type,
            "task_name": task_name,
            "status": status,
            "details_urdu": SecretMaskingFilter.mask_secrets(details_urdu),
            "duration_ms": duration_ms or 0,
            "error": clean_error,
            "extra": extra_data or {}
        }

        log_msg = f"[{status}] {task_name} | {event['details_urdu']}"
        if duration_ms:
            log_msg += f" ({duration_ms}ms)"
        if clean_error:
            log_msg += f" | ERROR: {clean_error}"

        if status in ["FAILED", "PERMANENT_FAILURE"]:
            self.logger.error(log_msg)
        elif status in ["WARNING", "TEMPORARY_FAILURE", "RETRYING"]:
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)

        return event

structured_logger = StructuredLogger()
