"""
Property-Based Tests: Pipeline Message Serialization Round-Trip
Feature: universal-translation-layer

Property 17: Pipeline message serialization round-trip
Validates: Requirements 13.3, 13.5
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from utl_pipeline_models import (
    TextInterceptionMessage,
    DubbingSegment,
    MeshNodeRegistration,
    SubscriptionState,
    SubscriptionTier,
    NodeCapabilities,
    MAX_FIELD_LENGTH,
)


# === Strategies ===

safe_text = st.text(
    alphabet=st.characters(blacklist_categories=('Cs',)),
    min_size=0,
    max_size=200,
)

lang_code = st.sampled_from(["en", "cs", "de", "fr", "es", "it", "pl", "sk", "ja", "zh"])

confidence = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

position = st.tuples(
    st.integers(min_value=0, max_value=10000),
    st.integers(min_value=0, max_value=10000),
    st.integers(min_value=1, max_value=5000),
    st.integers(min_value=1, max_value=5000),
)

timestamp = st.integers(min_value=1, max_value=2000000000)

node_capabilities = st.builds(
    NodeCapabilities,
    cpu_cores=st.integers(min_value=1, max_value=128),
    gpu_vram_mb=st.integers(min_value=0, max_value=65536),
    ram_mb=st.integers(min_value=512, max_value=131072),
    bandwidth_mbps=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    available_models=st.lists(st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_"), max_size=5),
)

subscription_tier = st.sampled_from(list(SubscriptionTier))


# === Property 17: Serialization round-trip ===


class TestProperty17SerializationRoundTrip:
    """Property 17: Pipeline message serialization round-trip.

    For any valid message object, from_json(to_json(obj)) == obj.
    """

    @given(
        source_app=safe_text,
        element_id=safe_text,
        original_text=safe_text,
        translated_text=safe_text,
        source_lang=lang_code,
        target_lang=lang_code,
        conf=confidence,
        pos=position,
        ts=timestamp,
    )
    @settings(max_examples=100)
    def test_text_interception_message_roundtrip(
        self, source_app, element_id, original_text, translated_text,
        source_lang, target_lang, conf, pos, ts
    ):
        """TextInterceptionMessage serializes and deserializes losslessly."""
        # Feature: universal-translation-layer, Property 17
        msg = TextInterceptionMessage(
            source_app=source_app,
            element_id=element_id,
            original_text=original_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            confidence=conf,
            position=pos,
            timestamp=ts,
        )
        restored = TextInterceptionMessage.from_json(msg.to_json())
        assert restored == msg

    @given(
        speaker_id=safe_text.filter(lambda x: len(x) > 0),
        original_text=safe_text,
        translated_text=safe_text,
        source_lang=lang_code,
        target_lang=lang_code,
        start_time_ms=st.integers(min_value=0, max_value=10000000),
        duration_ms=st.integers(min_value=0, max_value=60000),
        voice_profile_id=safe_text.filter(lambda x: len(x) > 0),
    )
    @settings(max_examples=100)
    def test_dubbing_segment_roundtrip(
        self, speaker_id, original_text, translated_text,
        source_lang, target_lang, start_time_ms, duration_ms, voice_profile_id
    ):
        """DubbingSegment serializes and deserializes losslessly."""
        # Feature: universal-translation-layer, Property 17
        seg = DubbingSegment(
            speaker_id=speaker_id,
            original_text=original_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            start_time_ms=start_time_ms,
            duration_ms=duration_ms,
            voice_profile_id=voice_profile_id,
        )
        restored = DubbingSegment.from_json(seg.to_json())
        assert restored == seg

    @given(
        node_id=safe_text.filter(lambda x: len(x) > 0),
        ip_address=st.from_regex(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", fullmatch=True),
        port=st.integers(min_value=1, max_value=65535),
        capabilities=node_capabilities,
        model_shards=st.lists(st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_"), max_size=5),
        ts=timestamp,
        signature=st.binary(min_size=0, max_size=64),
    )
    @settings(max_examples=100)
    def test_mesh_node_registration_roundtrip(
        self, node_id, ip_address, port, capabilities, model_shards, ts, signature
    ):
        """MeshNodeRegistration serializes and deserializes losslessly."""
        # Feature: universal-translation-layer, Property 17
        node = MeshNodeRegistration(
            node_id=node_id,
            ip_address=ip_address,
            port=port,
            capabilities=capabilities,
            model_shards=model_shards,
            timestamp=ts,
            signature=signature,
        )
        restored = MeshNodeRegistration.from_json(node.to_json())
        assert restored == node

    @given(
        wallet_address=safe_text.filter(lambda x: len(x) > 0),
        tier=subscription_tier,
        active=st.booleans(),
        expires_at=st.integers(min_value=0, max_value=2000000000),
        devices=st.lists(st.text(min_size=1, max_size=20), max_size=10),
        payment_token=safe_text,
    )
    @settings(max_examples=100)
    def test_subscription_state_roundtrip(
        self, wallet_address, tier, active, expires_at, devices, payment_token
    ):
        """SubscriptionState serializes and deserializes losslessly."""
        # Feature: universal-translation-layer, Property 17
        sub = SubscriptionState(
            wallet_address=wallet_address,
            tier=tier,
            active=active,
            expires_at=expires_at,
            devices=devices,
            payment_token=payment_token,
        )
        restored = SubscriptionState.from_json(sub.to_json())
        assert restored == sub

    @given(
        source_app=safe_text,
        element_id=safe_text,
        original_text=safe_text,
        translated_text=safe_text,
        source_lang=lang_code,
        target_lang=lang_code,
        conf=confidence,
        pos=position,
        ts=timestamp,
    )
    @settings(max_examples=100)
    def test_legacy_aliases_work(
        self, source_app, element_id, original_text, translated_text,
        source_lang, target_lang, conf, pos, ts
    ):
        """Legacy serialize/deserialize aliases produce same result."""
        # Feature: universal-translation-layer, Property 17
        msg = TextInterceptionMessage(
            source_app=source_app,
            element_id=element_id,
            original_text=original_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            confidence=conf,
            position=pos,
            timestamp=ts,
        )
        # serialize = to_json, deserialize = from_json
        restored = TextInterceptionMessage.deserialize(msg.serialize())
        assert restored == msg
