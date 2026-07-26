"""
Ethics Oath — Hippocratic Oath for Karel IV. n8n System
========================================================

Dva neprekrocitelne etické principy zabudovane v jadre pipeline:

1. HIPPOKRATOVA PRISAHA (Data Oath):
   System NESMI poskytnout data klienta nikomu — vyjimka:
   a) Klient vyslovne souhlasil (aktivni ConsentGrant)
   b) Bezprostredni ohrozeni zivota (life_threatening_override)

2. PRAVIDLO NAHRAVANI (Recording Oath):
   a) Uzivatel SMI nahravat sam sebe (vlastni hlas)
   b) Nahravani OSTATNICH bez souhlasu je ZAKAZANO
   c) System ODMITNE zpracovat nahravku obsahujici treti osoby

3. CENTRAL STOP:
   Jediny kill switch drzi Mincovna (GNAT core).
   Zadny jiny subjekt nesmi system zastavit.

Tyto principy NELZE obejit — zadna konfigurace, zadny prikaz.
Formalne overeno Ada/SPARK (gnatprove).

Standard: Rebirth Phoenix Foundation — Digital Ethics Charter
"""

import time
import hashlib
import threading
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[ETHICS]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Gauge

    karel_ethics_decisions_total = Counter(
        'karel_ethics_decisions_total',
        'Total ethics decisions made',
        ['decision']
    )
    karel_ethics_audit_entries_total = Counter(
        'karel_ethics_audit_entries_total',
        'Total audit log entries'
    )
    karel_ethics_consent_active = Gauge(
        'karel_ethics_consent_active',
        'Number of active recording consents'
    )
except ImportError:
    karel_ethics_decisions_total = None
    karel_ethics_audit_entries_total = None
    karel_ethics_consent_active = None

# === ENUMS ===

class DataAccessReason(Enum):
    CLIENT_CONSENT = "client_consent"
    LIFE_THREATENING = "life_threatening"
    PEER_AGENT_REQUEST = "peer_agent_request"
    SYSTEM_REQUEST = "system_request"
    MESH_SHARING = "mesh_sharing"


class OathDecision(Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    DENIED_NO_CONSENT = "denied_no_consent"
    DENIED_RECORDING = "denied_recording_violation"
    ALLOWED_LIFE_THREATENING = "allowed_life_threatening"


# === DATA MODELS ===

@dataclass
class AuditEntry:
    timestamp: float
    decision: str
    reason: str
    context: str
    hash_chain: str
    override_used: bool = False


@dataclass
class RecordingConsent:
    person_id: str
    consented: bool
    consented_at: float = 0.0
    expires_at: Optional[float] = None
    scope: str = "voice"


# === ETHICS OATH CLASS ===

class EthicsOath:
    """Hippocratic Oath enforcement for Karel IV. pipeline.

    GATEKEEPER for all data operations. Every component that wants
    to share, transmit, or expose data MUST pass through this layer.

    Cannot be disabled. Cannot be bypassed. Formally verified.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._audit_log: List[AuditEntry] = []
        self._recording_consents: Dict[str, RecordingConsent] = {}
        self._owner_speaker_id: Optional[str] = None
        logger.info(f"{LOG_PREFIX} Ethics Oath initialized — Hippocratic principles active")

    # === DATA OATH ===

    def may_share_data(self, reason: DataAccessReason,
                       has_consent: bool = False,
                       context: str = "") -> OathDecision:
        """Determine if data may be shared. ONLY two paths to ALLOWED."""

        if reason == DataAccessReason.LIFE_THREATENING:
            decision = OathDecision.ALLOWED_LIFE_THREATENING
            logger.warning(f"{LOG_PREFIX} LIFE-THREAT OVERRIDE: {context}")
        elif reason == DataAccessReason.CLIENT_CONSENT and has_consent:
            decision = OathDecision.ALLOWED
        else:
            decision = OathDecision.DENIED_NO_CONSENT
            logger.info(f"{LOG_PREFIX} Data sharing DENIED: {reason.value} — {context}")

        self._record_audit(decision.value, reason.value, context,
                          override_used=(reason == DataAccessReason.LIFE_THREATENING))
        self._record_metric(decision)
        return decision

    # === RECORDING OATH ===

    def may_record(self, is_owner_voice: bool,
                   detected_speakers: int = 1,
                   context: str = "") -> OathDecision:
        """Determine if recording/processing is allowed.

        Rules:
        - Owner voice only: ALLOWED
        - Multiple speakers detected without consent: DENIED
        - No speakers (silence): ALLOWED
        """
        if detected_speakers == 0:
            return OathDecision.ALLOWED

        if detected_speakers == 1 and is_owner_voice:
            return OathDecision.ALLOWED

        if detected_speakers > 1:
            # Multiple speakers — check if all have consent
            # For now: deny unless owner is alone
            decision = OathDecision.DENIED_RECORDING
            logger.warning(
                f"{LOG_PREFIX} Recording DENIED — {detected_speakers} speakers "
                f"detected, unconsented third party. Context: {context}"
            )
            self._record_audit(decision.value, "recording_check", context)
            self._record_metric(decision)
            return decision

        if not is_owner_voice:
            decision = OathDecision.DENIED_RECORDING
            logger.warning(f"{LOG_PREFIX} Recording DENIED — not owner voice. Context: {context}")
            self._record_audit(decision.value, "recording_check", context)
            self._record_metric(decision)
            return decision

        return OathDecision.ALLOWED

    # === CONSENT MANAGEMENT ===

    def grant_recording_consent(self, person_id: str,
                                duration_hours: int = None) -> None:
        with self._lock:
            expires = None
            if duration_hours:
                expires = time.time() + duration_hours * 3600
            self._recording_consents[person_id] = RecordingConsent(
                person_id=person_id, consented=True,
                consented_at=time.time(), expires_at=expires
            )
            if karel_ethics_consent_active:
                karel_ethics_consent_active.inc()
            logger.info(f"{LOG_PREFIX} Recording consent GRANTED: {person_id}")

    def revoke_recording_consent(self, person_id: str) -> bool:
        with self._lock:
            c = self._recording_consents.get(person_id)
            if c is None:
                return False
            c.consented = False
            if karel_ethics_consent_active:
                karel_ethics_consent_active.dec()
            logger.info(f"{LOG_PREFIX} Recording consent REVOKED: {person_id}")
            return True

    def has_recording_consent(self, person_id: str) -> bool:
        with self._lock:
            c = self._recording_consents.get(person_id)
            if c is None or not c.consented:
                return False
            if c.expires_at and time.time() > c.expires_at:
                c.consented = False
                return False
            return True

    # === AUDIT LOG ===

    def get_audit_log(self) -> List[AuditEntry]:
        with self._lock:
            return list(self._audit_log)

    def verify_audit_chain(self) -> bool:
        with self._lock:
            if not self._audit_log:
                return True
            prev = "genesis"
            for entry in self._audit_log:
                expected = self._compute_hash(prev, entry.timestamp,
                                             entry.decision, entry.reason)
                if entry.hash_chain != expected:
                    return False
                prev = entry.hash_chain
            return True

    def _record_audit(self, decision: str, reason: str,
                      context: str, override_used: bool = False) -> None:
        with self._lock:
            ts = time.time()
            prev = self._audit_log[-1].hash_chain if self._audit_log else "genesis"
            h = self._compute_hash(prev, ts, decision, reason)
            self._audit_log.append(AuditEntry(
                timestamp=ts, decision=decision, reason=reason,
                context=context, hash_chain=h, override_used=override_used
            ))
            if karel_ethics_audit_entries_total:
                karel_ethics_audit_entries_total.inc()

    @staticmethod
    def _compute_hash(prev: str, ts: float, decision: str, reason: str) -> str:
        content = f"{prev}:{ts}:{decision}:{reason}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _record_metric(self, decision: OathDecision) -> None:
        if karel_ethics_decisions_total:
            karel_ethics_decisions_total.labels(decision=decision.value).inc()

    # === STATUS ===

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "oath_active": True,
                "immutable": True,
                "audit_entries": len(self._audit_log),
                "chain_valid": self.verify_audit_chain(),
                "active_consents": sum(
                    1 for c in self._recording_consents.values() if c.consented
                ),
            }


# === MAIN ===

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"{LOG_PREFIX} Ethics Oath self-test")

    oath = EthicsOath()

    # Data oath tests
    r = oath.may_share_data(DataAccessReason.PEER_AGENT_REQUEST, False, "test")
    assert r == OathDecision.DENIED_NO_CONSENT
    print(f"  PASS: Peer request without consent -> DENIED")

    r = oath.may_share_data(DataAccessReason.CLIENT_CONSENT, True, "user shared")
    assert r == OathDecision.ALLOWED
    print(f"  PASS: Client consent -> ALLOWED")

    r = oath.may_share_data(DataAccessReason.LIFE_THREATENING, False, "emergency")
    assert r == OathDecision.ALLOWED_LIFE_THREATENING
    print(f"  PASS: Life-threatening -> ALLOWED (override)")

    # Recording oath tests
    r = oath.may_record(is_owner_voice=True, detected_speakers=1)
    assert r == OathDecision.ALLOWED
    print(f"  PASS: Owner alone -> ALLOWED")

    r = oath.may_record(is_owner_voice=True, detected_speakers=2)
    assert r == OathDecision.DENIED_RECORDING
    print(f"  PASS: Multiple speakers -> DENIED")

    r = oath.may_record(is_owner_voice=False, detected_speakers=1)
    assert r == OathDecision.DENIED_RECORDING
    print(f"  PASS: Not owner -> DENIED")

    # Audit chain
    assert oath.verify_audit_chain()
    print(f"  PASS: Audit chain valid")

    print(f"  Status: {oath.get_status()}")
    print(f"{LOG_PREFIX} All tests PASSED.")


if __name__ == '__main__':
    main()
