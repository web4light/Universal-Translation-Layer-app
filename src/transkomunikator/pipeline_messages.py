"""
Pipeline Message Serialization — Karel IV. n8n System
=====================================================

Serialization/deserialization for all pipeline messages between:
- Ada/SPARK validators (subprocess JSON I/O)
- n8n webhooks
- Python bridge components

Round-trip property: serialize(deserialize(msg)) == msg

Standard: Karel IV. n8n System Requirement 13
"""

import json
import time
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[PIPELINE_MSG]"

# === CONSTANTS ===

MAX_FIELD_LENGTH = 4096
MAX_PROMPT_LENGTH = 8192
MAX_RESPONSE_LENGTH = 32768


# === ENUMS ===

class PipelineStage(Enum):
    CAPTURE = "capture"
    BIOMETRIC = "biometric"
    STT = "stt"
    VALIDATE_TEXT = "validate_text"
    TRANSLATE = "translate"
    VALIDATE_RESPONSE = "validate_response"
    TTS = "tts"
    OUTPUT = "output"


class ValidationStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"


# === DATA MODELS ===

@dataclass
class ValidationResult:
    """Result from Ada/SPARK validator."""
    valid: bool
    reason: str = ""
    timestamp: int = 0
    stage: str = ""
    byte_offset: Optional[int] = None

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time())


@dataclass
class TranslationRequest:
    """Request sent to Bifrost/Gemini translator."""
    text: str
    source: str
    target: str
    request_id: str = ""
    timestamp: int = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time())


@dataclass
class TranslationResponse:
    """Response from Bifrost/Gemini translator."""
    translated: str = ""
    quality_score: float = 0.0
    error: str = ""
    request_id: str = ""
    timestamp: int = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time())


@dataclass
class PipelineMessage:
    """Generic pipeline message between stages."""
    stage: str
    status: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = 0
    error: str = ""

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time())


@dataclass
class ComponentRegistration:
    """Component registration message for n8n."""
    name: str
    version: str
    port: int
    health: str = "ok"
    timestamp: int = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time())


# === SERIALIZER ===

class PipelineSerializer:
    """Serializes/deserializes pipeline messages to/from JSON.

    Enforces field length limits per Standard.
    Round-trip guarantee: deserialize(serialize(msg)) == msg
    """

    @staticmethod
    def serialize_validation_result(result: ValidationResult) -> str:
        """Serialize ValidationResult to JSON string."""
        return json.dumps(asdict(result), ensure_ascii=False)

    @staticmethod
    def deserialize_validation_result(data: str) -> ValidationResult:
        """Deserialize JSON string to ValidationResult."""
        d = json.loads(data)
        return ValidationResult(**d)

    @staticmethod
    def serialize_translation_request(req: TranslationRequest) -> str:
        """Serialize TranslationRequest. Validates field lengths."""
        if len(req.text) > MAX_PROMPT_LENGTH:
            raise ValueError(f"text exceeds MAX_PROMPT_LENGTH ({len(req.text)} > {MAX_PROMPT_LENGTH})")
        if len(req.source) > MAX_FIELD_LENGTH:
            raise ValueError(f"source exceeds MAX_FIELD_LENGTH")
        if len(req.target) > MAX_FIELD_LENGTH:
            raise ValueError(f"target exceeds MAX_FIELD_LENGTH")
        return json.dumps(asdict(req), ensure_ascii=False)

    @staticmethod
    def deserialize_translation_request(data: str) -> TranslationRequest:
        """Deserialize JSON to TranslationRequest."""
        d = json.loads(data)
        return TranslationRequest(**d)

    @staticmethod
    def serialize_translation_response(resp: TranslationResponse) -> str:
        """Serialize TranslationResponse. Validates field lengths."""
        if len(resp.translated) > MAX_RESPONSE_LENGTH:
            raise ValueError(f"translated exceeds MAX_RESPONSE_LENGTH ({len(resp.translated)} > {MAX_RESPONSE_LENGTH})")
        return json.dumps(asdict(resp), ensure_ascii=False)

    @staticmethod
    def deserialize_translation_response(data: str) -> TranslationResponse:
        """Deserialize JSON to TranslationResponse."""
        d = json.loads(data)
        return TranslationResponse(**d)

    @staticmethod
    def serialize_pipeline_message(msg: PipelineMessage) -> str:
        """Serialize PipelineMessage."""
        return json.dumps(asdict(msg), ensure_ascii=False)

    @staticmethod
    def deserialize_pipeline_message(data: str) -> PipelineMessage:
        """Deserialize JSON to PipelineMessage."""
        d = json.loads(data)
        return PipelineMessage(**d)

    @staticmethod
    def serialize_component_registration(reg: ComponentRegistration) -> str:
        """Serialize ComponentRegistration."""
        return json.dumps(asdict(reg), ensure_ascii=False)

    @staticmethod
    def deserialize_component_registration(data: str) -> ComponentRegistration:
        """Deserialize JSON to ComponentRegistration."""
        d = json.loads(data)
        return ComponentRegistration(**d)


# === MAIN ===

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"{LOG_PREFIX} Pipeline Messages self-test")

    s = PipelineSerializer()

    # Round-trip: ValidationResult
    vr = ValidationResult(valid=True, reason="ok", stage="stt")
    assert s.deserialize_validation_result(s.serialize_validation_result(vr)) == vr
    print("  PASS: ValidationResult round-trip")

    # Round-trip: TranslationRequest
    tr = TranslationRequest(text="Hello world", source="en", target="cs")
    assert s.deserialize_translation_request(s.serialize_translation_request(tr)) == tr
    print("  PASS: TranslationRequest round-trip")

    # Round-trip: TranslationResponse
    resp = TranslationResponse(translated="Ahoj svete", quality_score=0.95)
    assert s.deserialize_translation_response(s.serialize_translation_response(resp)) == resp
    print("  PASS: TranslationResponse round-trip")

    # Field length validation
    try:
        big = TranslationRequest(text="x" * (MAX_PROMPT_LENGTH + 1), source="en", target="cs")
        s.serialize_translation_request(big)
        assert False, "Should have raised"
    except ValueError:
        print("  PASS: MAX_PROMPT_LENGTH enforcement")

    # Round-trip: PipelineMessage
    pm = PipelineMessage(stage="stt", status="completed", data={"text": "hello"})
    assert s.deserialize_pipeline_message(s.serialize_pipeline_message(pm)) == pm
    print("  PASS: PipelineMessage round-trip")

    print(f"{LOG_PREFIX} All tests PASSED.")


if __name__ == '__main__':
    main()
