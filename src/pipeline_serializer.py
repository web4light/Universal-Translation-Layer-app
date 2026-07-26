"""
Pipeline Message Serialization — Karel IV.

Round-trip serialize/deserialize for pipeline messages flowing
between Ada/SPARK validators and Python bridge layer.

All messages are JSON with bounded field lengths (MAX_FIELD_LENGTH = 4096).

Provides two APIs:
  1. Class-based (PipelineMessage, ValidationResult, etc.) — OOP style
  2. PipelineSerializer — static methods operating on plain dicts (design spec)

Autor: Pan Jeskyně
Asistent: Kiro
"""

import json
import time
import logging

# === CONSTANTS ===

MAX_FIELD_LENGTH = 4096
MAX_PROMPT_LENGTH = 8192
MAX_RESPONSE_LENGTH = 32768


# === PIPELINE MESSAGE ===

class PipelineMessage:
    """Base pipeline message with stage, content, timestamp."""

    def __init__(self, stage, content, timestamp=None):
        self.stage = stage
        self.content = content[:MAX_FIELD_LENGTH] if content else ""
        self.timestamp = timestamp or int(time.time())

    def serialize(self):
        """Serialize to JSON string."""
        return json.dumps({
            "stage": self.stage,
            "content": self.content,
            "timestamp": self.timestamp
        })

    @classmethod
    def deserialize(cls, data):
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            stage=obj["stage"],
            content=obj["content"],
            timestamp=obj["timestamp"]
        )

    def __eq__(self, other):
        if not isinstance(other, PipelineMessage):
            return False
        return (self.stage == other.stage and
                self.content == other.content and
                self.timestamp == other.timestamp)


# === VALIDATION RESULT ===

class ValidationResult:
    """Result from SPARK validator (pipeline_validator / transkomunikator_validator)."""

    def __init__(self, valid, reason, stage, byte_offset=0, timestamp=None):
        self.valid = valid
        self.reason = reason[:MAX_FIELD_LENGTH] if reason else ""
        self.stage = stage
        self.byte_offset = byte_offset
        self.timestamp = timestamp or int(time.time())

    def serialize(self):
        """Serialize to JSON string."""
        return json.dumps({
            "valid": self.valid,
            "reason": self.reason,
            "stage": self.stage,
            "byte_offset": self.byte_offset,
            "timestamp": self.timestamp
        })

    @classmethod
    def deserialize(cls, data):
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            valid=obj["valid"],
            reason=obj["reason"],
            stage=obj["stage"],
            byte_offset=obj.get("byte_offset", 0),
            timestamp=obj["timestamp"]
        )

    def __eq__(self, other):
        if not isinstance(other, ValidationResult):
            return False
        return (self.valid == other.valid and
                self.reason == other.reason and
                self.stage == other.stage and
                self.byte_offset == other.byte_offset and
                self.timestamp == other.timestamp)


# === TRANSLATION REQUEST ===

class TranslationRequest:
    """Translation request to Bifrost/Gemini."""

    def __init__(self, text, source_lang, target_lang, timestamp=None):
        self.text = text[:MAX_PROMPT_LENGTH] if text else ""
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.timestamp = timestamp or int(time.time())

    def serialize(self):
        """Serialize to JSON string."""
        return json.dumps({
            "text": self.text,
            "source": self.source_lang,
            "target": self.target_lang,
            "timestamp": self.timestamp
        })

    @classmethod
    def deserialize(cls, data):
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            text=obj["text"],
            source_lang=obj["source"],
            target_lang=obj["target"],
            timestamp=obj["timestamp"]
        )

    def __eq__(self, other):
        if not isinstance(other, TranslationRequest):
            return False
        return (self.text == other.text and
                self.source_lang == other.source_lang and
                self.target_lang == other.target_lang and
                self.timestamp == other.timestamp)


# === TRANSLATION RESPONSE ===

class TranslationResponse:
    """Translation response from Bifrost/Gemini."""

    def __init__(self, translated, quality_score, source_lang, target_lang, timestamp=None):
        self.translated = translated[:MAX_RESPONSE_LENGTH] if translated else ""
        self.quality_score = quality_score
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.timestamp = timestamp or int(time.time())

    def serialize(self):
        """Serialize to JSON string."""
        return json.dumps({
            "translated": self.translated,
            "quality_score": self.quality_score,
            "source": self.source_lang,
            "target": self.target_lang,
            "timestamp": self.timestamp
        })

    @classmethod
    def deserialize(cls, data):
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            translated=obj["translated"],
            quality_score=obj["quality_score"],
            source_lang=obj["source"],
            target_lang=obj["target"],
            timestamp=obj["timestamp"]
        )

    def __eq__(self, other):
        if not isinstance(other, TranslationResponse):
            return False
        return (self.translated == other.translated and
                self.quality_score == other.quality_score and
                self.source_lang == other.source_lang and
                self.target_lang == other.target_lang and
                self.timestamp == other.timestamp)


# === COMPONENT REGISTRATION ===

class ComponentRegistration:
    """Component registration message for n8n."""

    def __init__(self, name, version, port, health_url, timestamp=None):
        self.name = name
        self.version = version
        self.port = port
        self.health_url = health_url
        self.timestamp = timestamp or int(time.time())

    def serialize(self):
        """Serialize to JSON string."""
        return json.dumps({
            "name": self.name,
            "version": self.version,
            "port": self.port,
            "health_url": self.health_url,
            "timestamp": self.timestamp
        })

    @classmethod
    def deserialize(cls, data):
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            name=obj["name"],
            version=obj["version"],
            port=obj["port"],
            health_url=obj["health_url"],
            timestamp=obj["timestamp"]
        )

    def __eq__(self, other):
        if not isinstance(other, ComponentRegistration):
            return False
        return (self.name == other.name and
                self.version == other.version and
                self.port == other.port and
                self.health_url == other.health_url and
                self.timestamp == other.timestamp)


# ============================================================================
# PIPELINE SERIALIZER — DICT-BASED STATIC METHODS
# ============================================================================

# Valid pipeline stages per design spec
VALID_STAGES = {"stt", "translate", "response", "audio_validate"}

# Logger
logger = logging.getLogger(__name__)


class PipelineSerializer:
    """
    Pipeline message serialization/deserialization with round-trip guarantee.

    Operates on plain dict objects matching the design data models:
    - Pipeline_Message: {stage, timestamp, valid, data, error}
    - Validation_Result: {valid, reason, timestamp, stage}
    - Translation_Request: {text, source, target}
    - Translation_Response: {translated, quality_score}

    All methods raise ValueError on invalid/missing required fields.
    Log prefix: [SERIALIZER]
    """

    # === PIPELINE MESSAGE ===

    @staticmethod
    def serialize_pipeline_message(msg: dict) -> str:
        """
        Serialize pipeline message to JSON string.

        Required fields: stage, timestamp, valid, data
        Optional fields: error (defaults to None)

        Args:
            msg: dict with pipeline message fields

        Returns:
            str: JSON string representation

        Raises:
            ValueError: if required fields are missing or invalid
        """
        PipelineSerializer._validate_pipeline_message(msg)
        logger.debug("[SERIALIZER] Serializing pipeline message: stage=%s", msg["stage"])
        return json.dumps(msg, ensure_ascii=False)

    @staticmethod
    def deserialize_pipeline_message(json_str: str) -> dict:
        """
        Deserialize JSON string to pipeline message dict.

        Validates all required fields are present after parsing.

        Args:
            json_str: JSON string to parse

        Returns:
            dict: pipeline message with all required fields

        Raises:
            ValueError: if JSON is malformed or required fields missing
        """
        try:
            msg = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("[SERIALIZER] Pipeline message parse error: %s", e)
            raise ValueError(f"[SERIALIZER] Invalid JSON: {e}") from e

        PipelineSerializer._validate_pipeline_message(msg)
        logger.debug("[SERIALIZER] Deserialized pipeline message: stage=%s", msg["stage"])
        return msg

    @staticmethod
    def _validate_pipeline_message(msg: dict):
        """Validate pipeline message has all required fields."""
        if not isinstance(msg, dict):
            raise ValueError("[SERIALIZER] Pipeline message must be a dict")

        required = ["stage", "timestamp", "valid", "data"]
        for field in required:
            if field not in msg:
                raise ValueError(
                    f"[SERIALIZER] Pipeline message missing required field: '{field}'"
                )

        if msg["stage"] not in VALID_STAGES:
            raise ValueError(
                f"[SERIALIZER] Invalid stage '{msg['stage']}'. "
                f"Must be one of: {sorted(VALID_STAGES)}"
            )

        if not isinstance(msg["timestamp"], (int, float)):
            raise ValueError("[SERIALIZER] 'timestamp' must be a number")

        if not isinstance(msg["valid"], bool):
            raise ValueError("[SERIALIZER] 'valid' must be a boolean")

        if not isinstance(msg["data"], dict):
            raise ValueError("[SERIALIZER] 'data' must be a dict")

        # Ensure 'error' field exists (defaults to None)
        if "error" not in msg:
            msg["error"] = None

    # === VALIDATION RESULT ===

    @staticmethod
    def serialize_validation_result(result: dict) -> str:
        """
        Serialize validation result to JSON string.

        Required fields: valid (bool), reason (str), timestamp (int), stage (str)

        Args:
            result: dict with validation result fields

        Returns:
            str: JSON string representation

        Raises:
            ValueError: if required fields are missing or invalid
        """
        PipelineSerializer._validate_validation_result(result)
        logger.debug("[SERIALIZER] Serializing validation result: stage=%s, valid=%s",
                     result["stage"], result["valid"])
        return json.dumps(result, ensure_ascii=False)

    @staticmethod
    def deserialize_validation_result(json_str: str) -> dict:
        """
        Deserialize JSON string to validation result dict.

        Args:
            json_str: JSON string to parse

        Returns:
            dict: validation result with all required fields

        Raises:
            ValueError: if JSON is malformed or required fields missing
        """
        try:
            result = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("[SERIALIZER] Validation result parse error: %s", e)
            raise ValueError(f"[SERIALIZER] Invalid JSON: {e}") from e

        PipelineSerializer._validate_validation_result(result)
        logger.debug("[SERIALIZER] Deserialized validation result: stage=%s", result["stage"])
        return result

    @staticmethod
    def _validate_validation_result(result: dict):
        """Validate validation result has all required fields."""
        if not isinstance(result, dict):
            raise ValueError("[SERIALIZER] Validation result must be a dict")

        required = ["valid", "reason", "timestamp", "stage"]
        for field in required:
            if field not in result:
                raise ValueError(
                    f"[SERIALIZER] Validation result missing required field: '{field}'"
                )

        if not isinstance(result["valid"], bool):
            raise ValueError("[SERIALIZER] 'valid' must be a boolean")

        if not isinstance(result["reason"], str):
            raise ValueError("[SERIALIZER] 'reason' must be a string")

        if not isinstance(result["timestamp"], (int, float)):
            raise ValueError("[SERIALIZER] 'timestamp' must be a number")

        if not isinstance(result["stage"], str):
            raise ValueError("[SERIALIZER] 'stage' must be a string")

    # === TRANSLATION REQUEST ===

    @staticmethod
    def serialize_translation_request(request: dict) -> str:
        """
        Serialize translation request to JSON string.

        Required fields: text (str), source (str), target (str)

        Args:
            request: dict with translation request fields

        Returns:
            str: JSON string representation

        Raises:
            ValueError: if required fields are missing or invalid
        """
        PipelineSerializer._validate_translation_request(request)
        logger.debug("[SERIALIZER] Serializing translation request: %s->%s",
                     request["source"], request["target"])
        return json.dumps(request, ensure_ascii=False)

    @staticmethod
    def deserialize_translation_request(json_str: str) -> dict:
        """
        Deserialize JSON string to translation request dict.

        Args:
            json_str: JSON string to parse

        Returns:
            dict: translation request with all required fields

        Raises:
            ValueError: if JSON is malformed or required fields missing
        """
        try:
            request = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("[SERIALIZER] Translation request parse error: %s", e)
            raise ValueError(f"[SERIALIZER] Invalid JSON: {e}") from e

        PipelineSerializer._validate_translation_request(request)
        logger.debug("[SERIALIZER] Deserialized translation request: %s->%s",
                     request["source"], request["target"])
        return request

    @staticmethod
    def _validate_translation_request(request: dict):
        """Validate translation request has all required fields."""
        if not isinstance(request, dict):
            raise ValueError("[SERIALIZER] Translation request must be a dict")

        required = ["text", "source", "target"]
        for field in required:
            if field not in request:
                raise ValueError(
                    f"[SERIALIZER] Translation request missing required field: '{field}'"
                )

        if not isinstance(request["text"], str):
            raise ValueError("[SERIALIZER] 'text' must be a string")

        if not request["text"]:
            raise ValueError("[SERIALIZER] 'text' must be non-empty")

        if not isinstance(request["source"], str):
            raise ValueError("[SERIALIZER] 'source' must be a string")

        if not request["source"]:
            raise ValueError("[SERIALIZER] 'source' must be non-empty")

        if not isinstance(request["target"], str):
            raise ValueError("[SERIALIZER] 'target' must be a string")

        if not request["target"]:
            raise ValueError("[SERIALIZER] 'target' must be non-empty")

    # === TRANSLATION RESPONSE ===

    @staticmethod
    def serialize_translation_response(response: dict) -> str:
        """
        Serialize translation response to JSON string.

        Required fields: translated (str), quality_score (float)

        Args:
            response: dict with translation response fields

        Returns:
            str: JSON string representation

        Raises:
            ValueError: if required fields are missing or invalid
        """
        PipelineSerializer._validate_translation_response(response)
        logger.debug("[SERIALIZER] Serializing translation response: score=%.2f",
                     response["quality_score"])
        return json.dumps(response, ensure_ascii=False)

    @staticmethod
    def deserialize_translation_response(json_str: str) -> dict:
        """
        Deserialize JSON string to translation response dict.

        Args:
            json_str: JSON string to parse

        Returns:
            dict: translation response with all required fields

        Raises:
            ValueError: if JSON is malformed or required fields missing
        """
        try:
            response = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("[SERIALIZER] Translation response parse error: %s", e)
            raise ValueError(f"[SERIALIZER] Invalid JSON: {e}") from e

        PipelineSerializer._validate_translation_response(response)
        logger.debug("[SERIALIZER] Deserialized translation response: score=%.2f",
                     response["quality_score"])
        return response

    @staticmethod
    def _validate_translation_response(response: dict):
        """Validate translation response has all required fields."""
        if not isinstance(response, dict):
            raise ValueError("[SERIALIZER] Translation response must be a dict")

        required = ["translated", "quality_score"]
        for field in required:
            if field not in response:
                raise ValueError(
                    f"[SERIALIZER] Translation response missing required field: '{field}'"
                )

        if not isinstance(response["translated"], str):
            raise ValueError("[SERIALIZER] 'translated' must be a string")

        if not response["translated"]:
            raise ValueError("[SERIALIZER] 'translated' must be non-empty")

        if not isinstance(response["quality_score"], (int, float)):
            raise ValueError("[SERIALIZER] 'quality_score' must be a number")
