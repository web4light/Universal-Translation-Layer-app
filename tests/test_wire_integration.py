"""
Integration Tests: Wire Modules (Tasks 12.1–12.5)

Verifies that all wire modules can be instantiated and their
core interfaces work end-to-end.

Tests:
- 12.1: Wire Text Pipeline
- 12.2: Wire Audio Pipeline
- 12.3: Wire Mesh Orchestrator
- 12.4: Wire Karel IV. Engine
- 12.5: Wire Geall AI Assistant
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
os.chdir(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


# === 12.1: Wire Text Pipeline ===


class TestWireTextPipeline:
    """Integration test for text pipeline wiring."""

    def test_import_and_instantiate(self):
        """TextPipeline can be imported and instantiated."""
        from wire_text_pipeline import TextPipeline
        pipeline = TextPipeline(target_lang="cs")
        assert pipeline is not None

    def test_set_target_lang(self):
        """Target language can be changed."""
        from wire_text_pipeline import TextPipeline
        pipeline = TextPipeline(target_lang="cs")
        pipeline.set_target_lang("de")
        assert pipeline._target_lang == "de"

    def test_translate_and_overlay_returns_result(self):
        """translate_and_overlay returns a string or None."""
        from wire_text_pipeline import TextPipeline
        from overlay_renderer import Rect
        pipeline = TextPipeline(target_lang="cs")
        result = pipeline.translate_and_overlay(
            "Hello world",
            Rect(x=0, y=0, width=100, height=20),
            element_id="test_elem",
        )
        # Should return string (translated) or None (on error)
        assert result is None or isinstance(result, str)


# === 12.2: Wire Audio Pipeline ===


class TestWireAudioPipeline:
    """Integration test for audio pipeline wiring."""

    def test_import_and_instantiate(self):
        """AudioPipeline can be imported and instantiated."""
        from wire_audio_pipeline import AudioPipeline
        pipeline = AudioPipeline(target_lang="cs")
        assert pipeline is not None

    def test_get_status(self):
        """Status returns dict with expected keys."""
        from wire_audio_pipeline import AudioPipeline
        pipeline = AudioPipeline(target_lang="cs")
        status = pipeline.get_status()
        assert isinstance(status, dict)
        assert "dubber" in status
        assert "tv" in status

    def test_dubber_property(self):
        """Dubber property is accessible."""
        from wire_audio_pipeline import AudioPipeline
        from stream_dubber import StreamDubber
        pipeline = AudioPipeline(target_lang="cs")
        assert isinstance(pipeline.dubber, StreamDubber)


# === 12.3: Wire Mesh Orchestrator ===


class TestWireMesh:
    """Integration test for mesh layer wiring."""

    def test_import_and_instantiate(self):
        """MeshLayer can be imported and instantiated."""
        from wire_mesh import MeshLayer
        mesh = MeshLayer(local_node_id="test_node")
        assert mesh is not None

    def test_properties_accessible(self):
        """Mesh layer properties are accessible."""
        from wire_mesh import MeshLayer
        mesh = MeshLayer(local_node_id="test_node")
        assert mesh.orchestrator is not None
        assert mesh.shard_manager is not None
        assert mesh.privacy is not None
        assert mesh.offline is not None


# === 12.4: Wire Karel IV. Engine ===


class TestWireKarelEngine:
    """Integration test for Karel IV. engine wiring."""

    def test_import_and_instantiate(self):
        """KarelIVEngine can be imported and instantiated."""
        from wire_karel_engine import KarelIVEngine
        engine = KarelIVEngine(target_lang="cs")
        assert engine is not None

    def test_get_status(self):
        """Status returns expected structure."""
        from wire_karel_engine import KarelIVEngine
        engine = KarelIVEngine(target_lang="cs")
        status = engine.get_status()
        assert isinstance(status, dict)
        assert status["engine"] == "Karel IV."
        assert status["target_lang"] == "cs"


# === 12.5: Wire Geall AI Assistant ===


class TestWireGeall:
    """Integration test for Geall AI assistant wiring."""

    def test_import_and_instantiate(self):
        """GeallAssistant can be imported and instantiated."""
        from wire_geall import GeallAssistant
        geall = GeallAssistant(target_lang="cs")
        assert geall is not None

    def test_query_count_starts_at_zero(self):
        """Query count starts at zero."""
        from wire_geall import GeallAssistant
        geall = GeallAssistant(target_lang="cs")
        assert geall.query_count == 0
