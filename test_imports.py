#!/usr/bin/env python3
"""Quick import test for all wire modules."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.chdir(os.path.join(os.path.dirname(__file__), 'src'))

results = []

# Test each module
modules = [
    'utl_pipeline_models',
    'subscription_manager',
    'privacy_protocol',
    'mesh_orchestrator',
    'model_shard_manager',
    'language_detector',
    'text_interceptor',
    'translation_engine',
    'overlay_renderer',
    'stream_dubber',
    'speaker_mapper',
    'voice_separator',
    'audio_capture',
    'ocr_module',
    'offline_fallback',
    'wire_text_pipeline',
    'wire_audio_pipeline',
    'wire_mesh',
    'wire_karel_engine',
    'wire_geall',
]

for mod in modules:
    try:
        __import__(mod)
        results.append(f"OK: {mod}")
    except Exception as e:
        results.append(f"FAIL: {mod} -> {e}")

with open('/tmp/utl_imports.txt', 'w') as f:
    f.write('\n'.join(results))
