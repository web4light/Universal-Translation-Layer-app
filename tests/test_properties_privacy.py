"""
Property-Based Tests: Privacy Protocol
Feature: universal-translation-layer

Property 8: Zero disk persistence invariant
Property 9: Encryption round-trip and key exclusivity
Property 10: Audit log hash chain integrity

Validates: Requirements 8.1, 8.3, 8.5, 8.6, 5.5
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from privacy_protocol import PrivacyProtocol, AuditEntry


# === Property 8: Zero disk persistence invariant ===


class TestProperty8ZeroDiskPersistence:
    """Property 8: Zero disk persistence invariant.

    For any sequence of operations, zero bytes of user content
    SHALL be written to local disk.
    """

    def _cleanup_tmp(self):
        """Remove any pre-existing test artifacts from /tmp."""
        import glob
        patterns = ["/tmp/utl_*", "/tmp/privacy_*", "/tmp/translation_*",
                    "/tmp/dubbed_*", "/tmp/transcript_*", "/tmp/geall_*"]
        for pat in patterns:
            for f in glob.glob(pat):
                try:
                    os.remove(f)
                except OSError:
                    pass

    @given(
        data=st.binary(min_size=1, max_size=1024),
        metadata_keys=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    def test_no_disk_writes_after_operations(self, data, metadata_keys):
        """After encrypt/store/purge operations, no user content on disk."""
        # Feature: universal-translation-layer, Property 8
        self._cleanup_tmp()
        pp = PrivacyProtocol()

        # Perform operations
        key = pp.get_session_key()
        ct = pp.encrypt(data, key)
        pt = pp.decrypt(ct)

        # Store metadata (should be in RAM only)
        for k in metadata_keys:
            pp.store_metadata(k, data.hex())

        # Purge
        pp.execute_purge()

        # Verify no persistence
        result = pp.verify_no_persistence()
        assert result.clean, f"Artifacts found: {result.artifacts_found}"

    @given(
        operations=st.lists(
            st.binary(min_size=1, max_size=256),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_repeated_operations_clean(self, operations):
        """Multiple encryption operations leave no disk trace."""
        # Feature: universal-translation-layer, Property 8
        self._cleanup_tmp()
        pp = PrivacyProtocol()
        key = pp.get_session_key()

        for data in operations:
            ct = pp.encrypt(data, key)
            pp.decrypt(ct)

        result = pp.verify_no_persistence()
        assert result.clean


# === Property 9: Encryption round-trip and key exclusivity ===


class TestProperty9EncryptionRoundTrip:
    """Property 9: Encryption round-trip and key exclusivity.

    (a) decrypt(encrypt(x)) == x with correct key
    (b) decrypt with wrong key fails or produces garbage
    """

    @given(data=st.binary(min_size=1, max_size=4096))
    @settings(max_examples=100)
    def test_roundtrip_correct_key(self, data):
        """Encryption with correct key produces original plaintext."""
        # Feature: universal-translation-layer, Property 9
        pp = PrivacyProtocol()
        key = pp.get_session_key()

        ciphertext = pp.encrypt(data, key)
        plaintext = pp.decrypt(ciphertext)

        assert plaintext == data

    @given(data=st.binary(min_size=1, max_size=1024))
    @settings(max_examples=100)
    def test_wrong_key_fails(self, data):
        """Decryption with wrong key fails or produces different output."""
        # Feature: universal-translation-layer, Property 9
        pp1 = PrivacyProtocol()  # Has key A
        pp2 = PrivacyProtocol()  # Has key B (different)

        # Ensure keys are different
        assume(pp1.get_session_key() != pp2.get_session_key())

        key1 = pp1.get_session_key()
        ciphertext = pp1.encrypt(data, key1)

        # pp2 tries to decrypt with its own key — should fail
        try:
            result = pp2.decrypt(ciphertext)
            # If no exception, result should differ from original
            assert result != data, "Wrong key should not produce correct plaintext"
        except RuntimeError:
            # Expected: decryption failure with wrong key
            pass

    @given(data=st.binary(min_size=1, max_size=512))
    @settings(max_examples=100)
    def test_ciphertext_differs_from_plaintext(self, data):
        """Ciphertext is not equal to plaintext (encryption actually transforms)."""
        # Feature: universal-translation-layer, Property 9
        pp = PrivacyProtocol()
        key = pp.get_session_key()

        ciphertext = pp.encrypt(data, key)
        # Ciphertext includes nonce, so it's longer and different
        assert ciphertext != data


# === Property 10: Audit log hash chain integrity ===


class TestProperty10AuditLogHashChain:
    """Property 10: Audit log hash chain integrity.

    Each entry's hash includes the previous entry's hash.
    Modifying any entry invalidates subsequent hashes.
    """

    @given(
        actions=st.lists(
            st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz_"),
            min_size=2,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_chain_integrity_verified(self, actions):
        """Hash chain is verifiable for any sequence of entries."""
        # Feature: universal-translation-layer, Property 10
        pp = PrivacyProtocol()

        # Add entries
        for action in actions:
            pp._add_audit_entry(action)

        # Verify chain integrity
        assert pp.verify_audit_chain() is True

    @given(
        actions=st.lists(
            st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz_"),
            min_size=3,
            max_size=10,
        ),
        tamper_index=st.integers(min_value=0),
    )
    @settings(max_examples=100)
    def test_tamper_detection(self, actions, tamper_index):
        """Modifying any entry invalidates the chain."""
        # Feature: universal-translation-layer, Property 10
        pp = PrivacyProtocol()

        for action in actions:
            pp._add_audit_entry(action)

        log = pp.get_audit_log()
        assume(len(log) >= 3)

        # Tamper with an entry (not the initialization entries)
        idx = tamper_index % len(log)
        original_hash = log[idx].hash_chain
        log[idx] = AuditEntry(
            timestamp=log[idx].timestamp,
            action="TAMPERED_" + log[idx].action,
            hash_chain=original_hash,  # Keep old hash — now invalid
            verified=log[idx].verified,
        )

        # Replace audit log with tampered version
        pp._audit_log = log

        # Chain should now be invalid (tampered action won't match hash)
        assert pp.verify_audit_chain() is False

    @given(
        actions=st.lists(
            st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz"),
            min_size=1,
            max_size=15,
        )
    )
    @settings(max_examples=100)
    def test_chain_grows_monotonically(self, actions):
        """Each new entry extends the chain by exactly one."""
        # Feature: universal-translation-layer, Property 10
        pp = PrivacyProtocol()
        initial_len = len(pp.get_audit_log())

        for i, action in enumerate(actions):
            pp._add_audit_entry(action)
            assert len(pp.get_audit_log()) == initial_len + i + 1
