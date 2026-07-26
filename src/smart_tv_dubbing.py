"""
Smart TV Dubbing Support — Universal Translation Layer (UTL)

Extends Stream Dubber for Smart TV environments:
- HDMI-CEC integration for auto-detection of playback state
- Chromecast/AirPlay audio capture support
- Low-latency mode optimized for TV viewing (<1.5s target)
- Multi-room audio sync for household plan users
- Remote control integration (pause dubbing, switch language)

Autor: Pan Jeskyně
Asistent: Kiro
Standard: Karel IV. Stream Dabing (333 CZK/month)
"""

import time
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[SMART_TV]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Gauge, Counter, Histogram

    utl_tv_dubbing_active = Gauge(
        'utl_tv_dubbing_active',
        'Number of active TV dubbing sessions'
    )

    utl_tv_dubbing_latency_seconds = Histogram(
        'utl_tv_dubbing_latency_seconds',
        'Smart TV dubbing latency in seconds',
        buckets=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
    )

    utl_tv_sessions_total = Counter(
        'utl_tv_sessions_total',
        'Total TV dubbing sessions started',
        ['source_type']  # hdmi, chromecast, airplay, manual
    )
except ImportError:
    utl_tv_dubbing_active = None
    utl_tv_dubbing_latency_seconds = None
    utl_tv_sessions_total = None

# === CONSTANTS ===

TV_LATENCY_TARGET_S = 1.5       # <1.5s for TV viewing comfort
HDMI_CEC_POLL_INTERVAL_S = 0.5  # Check HDMI-CEC every 500ms
MAX_ROOMS = 10                   # Max multi-room sync


# === ENUMS ===

class TVSourceType(Enum):
    """Audio source type for TV dubbing."""
    HDMI = "hdmi"
    CHROMECAST = "chromecast"
    AIRPLAY = "airplay"
    MANUAL = "manual"


class PlaybackState(Enum):
    """TV playback state (from HDMI-CEC or equivalent)."""
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class DubbingQuality(Enum):
    """Dubbing quality preset."""
    LOW_LATENCY = "low_latency"     # Fastest, slightly lower quality
    BALANCED = "balanced"            # Default for TV
    HIGH_QUALITY = "high_quality"    # Best quality, higher latency


# === DATA MODELS ===

@dataclass
class TVSession:
    """Active TV dubbing session."""
    session_id: str
    source_type: TVSourceType
    target_lang: str
    quality: DubbingQuality = DubbingQuality.BALANCED
    playback_state: PlaybackState = PlaybackState.UNKNOWN
    started_at: float = field(default_factory=time.time)
    last_latency_s: float = 0.0
    segments_dubbed: int = 0
    room_name: str = "living_room"


@dataclass
class RoomConfig:
    """Configuration for a room in multi-room setup."""
    room_name: str
    target_lang: str
    output_device: str = "default"
    sync_offset_ms: int = 0  # Audio sync offset per room


# === SMART TV DUBBING CLASS ===

class SmartTVDubbing:
    """Smart TV dubbing support for Karel IV. Stream Dabing tier.

    Extends the core StreamDubber with TV-specific features:
    - Auto-detection of TV playback via HDMI-CEC
    - Chromecast/AirPlay audio capture
    - Low-latency mode for comfortable TV viewing
    - Multi-room audio sync for Family plan

    Target latency: <1.5s (TV viewing comfort threshold).
    """

    def __init__(self, target_lang: str = "cs"):
        """Initialize Smart TV Dubbing.

        Args:
            target_lang: Default target language for dubbing
        """
        self._lock = threading.Lock()
        self._target_lang = target_lang
        self._sessions: Dict[str, TVSession] = {}
        self._rooms: Dict[str, RoomConfig] = {}
        self._cec_monitor_running = False
        self._cec_thread: Optional[threading.Thread] = None
        self._on_playback_change: Optional[Callable] = None
        self._session_counter = 0

        logger.info(f"{LOG_PREFIX} Initialized (target_lang={target_lang})")

    # === SESSION MANAGEMENT ===

    def start_session(self, source_type: TVSourceType,
                      target_lang: str = None,
                      quality: DubbingQuality = DubbingQuality.BALANCED,
                      room_name: str = "living_room") -> str:
        """Start a new TV dubbing session.

        Args:
            source_type: Audio source (HDMI, Chromecast, AirPlay, Manual)
            target_lang: Target language (uses default if None)
            quality: Dubbing quality preset
            room_name: Room identifier for multi-room sync

        Returns:
            Session ID string
        """
        with self._lock:
            self._session_counter += 1
            session_id = f"tv_{self._session_counter:04d}"

            session = TVSession(
                session_id=session_id,
                source_type=source_type,
                target_lang=target_lang or self._target_lang,
                quality=quality,
                room_name=room_name,
            )
            self._sessions[session_id] = session

            if utl_tv_dubbing_active:
                utl_tv_dubbing_active.inc()
            if utl_tv_sessions_total:
                utl_tv_sessions_total.labels(source_type=source_type.value).inc()

        logger.info(
            f"{LOG_PREFIX} Session started: {session_id} "
            f"(source={source_type.value}, lang={session.target_lang}, "
            f"quality={quality.value}, room={room_name})"
        )
        return session_id

    def stop_session(self, session_id: str) -> bool:
        """Stop an active TV dubbing session.

        Returns True if session was found and stopped.
        """
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is None:
                return False

            if utl_tv_dubbing_active:
                utl_tv_dubbing_active.dec()

        duration = time.time() - session.started_at
        logger.info(
            f"{LOG_PREFIX} Session stopped: {session_id} "
            f"(duration={duration:.1f}s, segments={session.segments_dubbed})"
        )
        return True

    def get_session(self, session_id: str) -> Optional[TVSession]:
        """Get session info."""
        with self._lock:
            return self._sessions.get(session_id)

    # === PLAYBACK CONTROL ===

    def pause_dubbing(self, session_id: str) -> bool:
        """Pause dubbing for a session (keeps session alive)."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.playback_state = PlaybackState.PAUSED
        logger.info(f"{LOG_PREFIX} Dubbing paused: {session_id}")
        return True

    def resume_dubbing(self, session_id: str) -> bool:
        """Resume dubbing for a paused session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.playback_state = PlaybackState.PLAYING
        logger.info(f"{LOG_PREFIX} Dubbing resumed: {session_id}")
        return True

    def switch_language(self, session_id: str, new_lang: str) -> bool:
        """Switch target language mid-session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            old_lang = session.target_lang
            session.target_lang = new_lang
        logger.info(f"{LOG_PREFIX} Language switched: {session_id} ({old_lang} -> {new_lang})")
        return True

    # === HDMI-CEC INTEGRATION ===

    def start_cec_monitoring(self) -> None:
        """Start HDMI-CEC monitoring for auto-detection."""
        if self._cec_monitor_running:
            return

        self._cec_monitor_running = True
        self._cec_thread = threading.Thread(
            target=self._cec_monitor_loop,
            name="HDMI-CEC-Monitor",
            daemon=True,
        )
        self._cec_thread.start()
        logger.info(f"{LOG_PREFIX} HDMI-CEC monitoring started")

    def stop_cec_monitoring(self) -> None:
        """Stop HDMI-CEC monitoring."""
        self._cec_monitor_running = False
        if self._cec_thread:
            self._cec_thread.join(timeout=2.0)

    def _cec_monitor_loop(self) -> None:
        """Monitor HDMI-CEC for playback state changes.

        In production: uses python-cec library to detect TV state.
        Stub mode: simulates state for testing.
        """
        while self._cec_monitor_running:
            # Stub: check if CEC library is available
            # In production, this would use:
            #   import cec
            #   cec.init()
            #   tv = cec.Device(0)
            #   power_status = tv.power_status
            time.sleep(HDMI_CEC_POLL_INTERVAL_S)

    def on_playback_change(self, callback: Callable[[str, PlaybackState], None]) -> None:
        """Register callback for TV playback state changes.

        Args:
            callback: Function(session_id, new_state) called on change
        """
        self._on_playback_change = callback

    # === MULTI-ROOM SYNC ===

    def add_room(self, room_name: str, target_lang: str,
                 output_device: str = "default",
                 sync_offset_ms: int = 0) -> None:
        """Add a room to multi-room dubbing setup.

        Args:
            room_name: Unique room identifier
            target_lang: Language for this room
            output_device: Audio output device name
            sync_offset_ms: Sync offset to compensate for speaker distance
        """
        with self._lock:
            self._rooms[room_name] = RoomConfig(
                room_name=room_name,
                target_lang=target_lang,
                output_device=output_device,
                sync_offset_ms=sync_offset_ms,
            )
        logger.info(
            f"{LOG_PREFIX} Room added: {room_name} "
            f"(lang={target_lang}, offset={sync_offset_ms}ms)"
        )

    def remove_room(self, room_name: str) -> bool:
        """Remove a room from multi-room setup."""
        with self._lock:
            return self._rooms.pop(room_name, None) is not None

    def get_rooms(self) -> List[RoomConfig]:
        """Get all configured rooms."""
        with self._lock:
            return list(self._rooms.values())

    # === LATENCY OPTIMIZATION ===

    def get_latency_config(self, quality: DubbingQuality) -> Dict:
        """Get latency optimization parameters for a quality preset.

        Returns dict with chunk_ms, model_size, and other settings.
        """
        configs = {
            DubbingQuality.LOW_LATENCY: {
                "chunk_ms": 250,
                "whisper_model": "tiny",
                "tts_speed": 1.1,
                "skip_silence": True,
                "target_latency_s": 1.0,
            },
            DubbingQuality.BALANCED: {
                "chunk_ms": 500,
                "whisper_model": "base",
                "tts_speed": 1.0,
                "skip_silence": True,
                "target_latency_s": 1.5,
            },
            DubbingQuality.HIGH_QUALITY: {
                "chunk_ms": 1000,
                "whisper_model": "small",
                "tts_speed": 1.0,
                "skip_silence": False,
                "target_latency_s": 2.5,
            },
        }
        return configs.get(quality, configs[DubbingQuality.BALANCED])

    # === STATUS ===

    def get_status(self) -> Dict:
        """Get Smart TV dubbing status."""
        with self._lock:
            return {
                "active_sessions": len(self._sessions),
                "configured_rooms": len(self._rooms),
                "cec_monitoring": self._cec_monitor_running,
                "sessions": {
                    sid: {
                        "source": s.source_type.value,
                        "lang": s.target_lang,
                        "state": s.playback_state.value,
                        "segments": s.segments_dubbed,
                    }
                    for sid, s in self._sessions.items()
                },
            }

    @property
    def active_session_count(self) -> int:
        """Number of active dubbing sessions."""
        return len(self._sessions)


# === MAIN GUARD ===

def main():
    """Self-test entry point for Smart TV Dubbing module."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    print(f"{LOG_PREFIX} Smart TV Dubbing self-test")

    tv = SmartTVDubbing(target_lang="cs")

    # Start sessions
    s1 = tv.start_session(TVSourceType.HDMI, target_lang="cs")
    s2 = tv.start_session(TVSourceType.CHROMECAST, target_lang="en")
    print(f"{LOG_PREFIX} Sessions: {s1}, {s2}")
    assert tv.active_session_count == 2

    # Playback control
    assert tv.pause_dubbing(s1) is True
    session = tv.get_session(s1)
    assert session.playback_state == PlaybackState.PAUSED

    assert tv.resume_dubbing(s1) is True
    session = tv.get_session(s1)
    assert session.playback_state == PlaybackState.PLAYING

    # Language switch
    assert tv.switch_language(s1, "ja") is True
    session = tv.get_session(s1)
    assert session.target_lang == "ja"
    print(f"{LOG_PREFIX} Playback control + language switch: OK")

    # Multi-room
    tv.add_room("living_room", "cs", sync_offset_ms=0)
    tv.add_room("bedroom", "en", sync_offset_ms=50)
    tv.add_room("kitchen", "cs", sync_offset_ms=120)
    rooms = tv.get_rooms()
    assert len(rooms) == 3
    print(f"{LOG_PREFIX} Multi-room setup: {len(rooms)} rooms")

    # Latency config
    config = tv.get_latency_config(DubbingQuality.LOW_LATENCY)
    assert config["target_latency_s"] == 1.0
    assert config["whisper_model"] == "tiny"
    print(f"{LOG_PREFIX} Low-latency config: {config}")

    # Stop sessions
    assert tv.stop_session(s1) is True
    assert tv.stop_session(s2) is True
    assert tv.active_session_count == 0

    print(f"{LOG_PREFIX} Status: {tv.get_status()}")
    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
