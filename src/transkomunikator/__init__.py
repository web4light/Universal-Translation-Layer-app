"""
Transkomunikátor — Real-time AI Translation Service
====================================================

Background service integrating:
- Ada/SPARK audio validation (subprocess)
- Whisper STT (speech-to-text)
- Geall/Gemini translation engine
- Coqui TTS (text-to-speech with voice cloning)
- P2P Mesh offloading
- Privacy Purge 423
- Prometheus monitoring

Standard 700: 12g stříbra = 1 mince
Autor: Pan Jeskyně
"""

__version__ = "0.1.0"

# Core modules
from .ethics_oath import EthicsOath, OathDecision, DataAccessReason
from .n8n_client import N8nWebhookClient, SystemStartup
from .pipeline_messages import (
    PipelineSerializer, PipelineMessage, ValidationResult,
    TranslationRequest, TranslationResponse, PipelineStage
)
from .autonomous_mode import AutonomousMode
