"""
Text Interceptor — Universal Translation Layer (UTL)

Zachycení veškerého textového vstupu/výstupu na úrovni OS
prostřednictvím accessibility API.

- Windows: UIAutomationInterceptor (COM-based UI Automation via comtypes)
- Linux: ATSPIInterceptor (AT-SPI2 via python-dbus)

Modul poskytuje:
- TextInterceptor base class s on_text_output / on_text_input callbacky
- TextEvent dataclass pro přenos zachycených událostí
- Obousměrný provoz (input + output překlad současně)
- Native language pass-through (bypass pokud text odpovídá jazyku uživatele)
- Prometheus metriky: utl_text_intercept_events_total, utl_text_intercept_latency_seconds

Autor: Pan Jeskyně
Asistent: Kiro
"""

import sys
import time
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, List, NamedTuple

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[TEXT_INTERCEPT]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Histogram

    utl_text_intercept_events_total = Counter(
        'utl_text_intercept_events_total',
        'Total number of text interception events',
        ['direction', 'action']  # direction: input/output, action: translated/passthrough/error
    )

    utl_text_intercept_latency_seconds = Histogram(
        'utl_text_intercept_latency_seconds',
        'Latency of text interception processing in seconds',
        ['direction'],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]
    )
except ImportError:
    utl_text_intercept_events_total = None
    utl_text_intercept_latency_seconds = None

# === PLATFORM-SPECIFIC IMPORTS ===

# Windows: comtypes + UIAutomation COM
try:
    import comtypes
    import comtypes.client
    _COMTYPES_AVAILABLE = True
except ImportError:
    _COMTYPES_AVAILABLE = False

# Linux: python-dbus (AT-SPI2)
try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    _DBUS_AVAILABLE = True
except ImportError:
    _DBUS_AVAILABLE = False


# === CONSTANTS ===

# Maximum text length to process in a single event
MAX_TEXT_EVENT_LENGTH = 10000

# Polling interval for accessibility event checks (seconds)
POLL_INTERVAL_SECONDS = 0.05  # 50ms

# AT-SPI2 D-Bus constants
ATSPI_BUS_NAME = "org.a11y.Bus"
ATSPI_REGISTRY_PATH = "/org/a11y/atspi/accessible/root"
ATSPI_EVENT_INTERFACE = "org.a11y.atspi.Event.Object"


# === DATA MODELS ===

class Direction(Enum):
    """Direction of text flow relative to the user."""
    INPUT = "input"    # User is typing (sending text)
    OUTPUT = "output"  # Text is being displayed to the user


class Rect(NamedTuple):
    """Screen rectangle for text element positioning."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class AccessibilityElement:
    """Represents an accessibility element in the UI tree."""
    element_id: str
    app_name: str
    role: str = ""
    name: str = ""
    value: str = ""
    rect: Rect = Rect(0, 0, 0, 0)


@dataclass
class TextEvent:
    """Event representing captured text I/O.

    Attributes:
        source_app: Name of the application generating the event
        element_id: Accessibility element identifier
        text: Captured text content
        position: Screen position of the text element
        timestamp: Capture timestamp (Unix time)
        direction: INPUT (user typing) or OUTPUT (text displayed to user)
    """
    source_app: str
    element_id: str
    text: str
    position: Rect
    timestamp: float
    direction: Direction

    def __post_init__(self):
        # Truncate overly long text to prevent resource exhaustion
        if len(self.text) > MAX_TEXT_EVENT_LENGTH:
            self.text = self.text[:MAX_TEXT_EVENT_LENGTH]


# === TEXT INTERCEPTOR BASE CLASS ===

class TextInterceptor(ABC):
    """Captures all text I/O at OS level via accessibility APIs.

    This is the abstract base class. Platform-specific implementations:
    - UIAutomationInterceptor (Windows)
    - ATSPIInterceptor (Linux)

    Supports bidirectional operation: input + output translation simultaneously.
    Implements native language pass-through (bypass when text matches user's language).
    """

    def __init__(self, user_language: str = "cs"):
        """Initialize the Text Interceptor.

        Args:
            user_language: User's native language (ISO 639-1 code).
                           Text in this language is passed through unchanged.
        """
        self._user_language = user_language.lower().strip()
        self._output_callbacks: List[Callable[[TextEvent], None]] = []
        self._input_callbacks: List[Callable[[TextEvent], None]] = []
        self._running = False
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None

        # Language detector for pass-through logic
        self._language_detector = None
        try:
            from language_detector import LanguageDetector
            self._language_detector = LanguageDetector()
        except ImportError:
            logger.warning(
                f"{LOG_PREFIX} LanguageDetector not available. "
                "Native language pass-through disabled."
            )

    # === PUBLIC API ===

    def start(self) -> None:
        """Start intercepting text events.

        Begins listening for accessibility events in a background thread.
        Both input and output callbacks will fire when events are detected.
        """
        with self._lock:
            if self._running:
                logger.warning(f"{LOG_PREFIX} Already running, ignoring start()")
                return
            self._running = True

        logger.info(f"{LOG_PREFIX} Starting text interception (user_lang={self._user_language})")
        self._start_platform()

        self._worker_thread = threading.Thread(
            target=self._event_loop,
            name="TextInterceptor-Worker",
            daemon=True
        )
        self._worker_thread.start()
        logger.info(f"{LOG_PREFIX} Text interception active")

    def stop(self) -> None:
        """Stop intercepting text events.

        Cleanly shuts down the event loop and releases platform resources.
        """
        with self._lock:
            if not self._running:
                logger.warning(f"{LOG_PREFIX} Not running, ignoring stop()")
                return
            self._running = False

        logger.info(f"{LOG_PREFIX} Stopping text interception")
        self._stop_platform()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        self._worker_thread = None
        logger.info(f"{LOG_PREFIX} Text interception stopped")

    def on_text_output(self, callback: Callable[[TextEvent], None]) -> None:
        """Register a callback for text output events (text displayed to user).

        Args:
            callback: Function called with TextEvent when output text is detected.
        """
        with self._lock:
            self._output_callbacks.append(callback)
        logger.debug(f"{LOG_PREFIX} Registered output callback: {callback.__name__}")

    def on_text_input(self, callback: Callable[[TextEvent], None]) -> None:
        """Register a callback for text input events (user typing).

        Args:
            callback: Function called with TextEvent when input text is detected.
        """
        with self._lock:
            self._input_callbacks.append(callback)
        logger.debug(f"{LOG_PREFIX} Registered input callback: {callback.__name__}")

    def inject_text(self, target: AccessibilityElement, text: str) -> bool:
        """Inject translated text into a target accessibility element.

        Args:
            target: The accessibility element to inject text into.
            text: The translated text to inject.

        Returns:
            True if injection succeeded, False otherwise.
        """
        logger.info(
            f"{LOG_PREFIX} Injecting text into element "
            f"'{target.element_id}' in app '{target.app_name}': "
            f"'{text[:50]}...'" if len(text) > 50 else
            f"{LOG_PREFIX} Injecting text into element "
            f"'{target.element_id}' in app '{target.app_name}': '{text}'"
        )
        return self._inject_text_platform(target, text)

    @property
    def is_running(self) -> bool:
        """Whether the interceptor is currently active."""
        return self._running

    @property
    def user_language(self) -> str:
        """The configured user native language."""
        return self._user_language

    @user_language.setter
    def user_language(self, lang: str) -> None:
        """Update the user's native language setting."""
        self._user_language = lang.lower().strip()
        logger.info(f"{LOG_PREFIX} User language updated to: {self._user_language}")

    # === NATIVE LANGUAGE PASS-THROUGH ===

    def _is_native_language(self, text: str) -> bool:
        """Check if text is already in the user's native language.

        If so, the text should be passed through unchanged (Requirement 1.7).

        Args:
            text: Text to check.

        Returns:
            True if text is in user's native language (bypass translation).
        """
        if self._language_detector is None:
            # Without detector, cannot determine language — don't bypass
            return False

        # Very short text is unreliable to detect — don't bypass
        if len(text.strip()) < 10:
            return False

        result = self._language_detector.detect_text(text)

        if result.language == self._user_language and result.confidence >= 0.90:
            return True

        return False

    # === EVENT DISPATCH ===

    def _dispatch_event(self, event: TextEvent) -> None:
        """Dispatch a text event to registered callbacks.

        Implements:
        - Native language pass-through (bypass when text matches user's lang)
        - Bidirectional operation (handles both INPUT and OUTPUT)
        - Prometheus metrics tracking
        """
        start_time = time.perf_counter()
        direction_label = event.direction.value

        # Native language pass-through check
        if self._is_native_language(event.text):
            logger.debug(
                f"{LOG_PREFIX} Pass-through: text in native language "
                f"({self._user_language}), app={event.source_app}"
            )
            if utl_text_intercept_events_total is not None:
                utl_text_intercept_events_total.labels(
                    direction=direction_label, action="passthrough"
                ).inc()
            # Still observe latency for pass-through
            elapsed = time.perf_counter() - start_time
            if utl_text_intercept_latency_seconds is not None:
                utl_text_intercept_latency_seconds.labels(
                    direction=direction_label
                ).observe(elapsed)
            return

        # Dispatch to appropriate callbacks based on direction
        with self._lock:
            if event.direction == Direction.OUTPUT:
                callbacks = list(self._output_callbacks)
            else:
                callbacks = list(self._input_callbacks)

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Callback error ({callback.__name__}): {e}"
                )
                if utl_text_intercept_events_total is not None:
                    utl_text_intercept_events_total.labels(
                        direction=direction_label, action="error"
                    ).inc()

        # Metrics
        if utl_text_intercept_events_total is not None:
            utl_text_intercept_events_total.labels(
                direction=direction_label, action="translated"
            ).inc()

        elapsed = time.perf_counter() - start_time
        if utl_text_intercept_latency_seconds is not None:
            utl_text_intercept_latency_seconds.labels(
                direction=direction_label
            ).observe(elapsed)

    # === ABSTRACT PLATFORM METHODS ===

    @abstractmethod
    def _start_platform(self) -> None:
        """Platform-specific initialization (start listening for events)."""
        ...

    @abstractmethod
    def _stop_platform(self) -> None:
        """Platform-specific cleanup (release resources)."""
        ...

    @abstractmethod
    def _poll_events(self) -> List[TextEvent]:
        """Platform-specific event polling.

        Returns:
            List of TextEvent objects detected since last poll.
        """
        ...

    @abstractmethod
    def _inject_text_platform(self, target: AccessibilityElement, text: str) -> bool:
        """Platform-specific text injection.

        Args:
            target: Target accessibility element.
            text: Text to inject.

        Returns:
            True on success, False on failure.
        """
        ...

    # === EVENT LOOP ===

    def _event_loop(self) -> None:
        """Background event loop polling for accessibility events."""
        logger.info(f"{LOG_PREFIX} Event loop started")
        while self._running:
            try:
                events = self._poll_events()
                for event in events:
                    self._dispatch_event(event)
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Event loop error: {e}")
            time.sleep(POLL_INTERVAL_SECONDS)
        logger.info(f"{LOG_PREFIX} Event loop exited")


# === WINDOWS BACKEND: UI Automation ===

class UIAutomationInterceptor(TextInterceptor):
    """Windows text interceptor using COM-based UI Automation.

    Uses comtypes to interact with the Windows UI Automation API,
    capturing text change events from all accessible UI elements.

    NOTE: This is a stub-level implementation providing the architecture
    and basic event handling. Deep COM event hooking requires a running
    Windows UI Automation event subscription which is complex to implement
    fully in a cross-platform codebase.
    """

    def __init__(self, user_language: str = "cs"):
        super().__init__(user_language)
        self._uia_client = None
        self._event_handler = None
        self._focused_element = None

    def _start_platform(self) -> None:
        """Initialize Windows UI Automation COM client."""
        if not _COMTYPES_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} comtypes not available — "
                "UIAutomationInterceptor will operate in stub mode. "
                "Install with: pip install comtypes"
            )
            return

        try:
            # Initialize COM for this thread
            comtypes.CoInitialize()

            # Create UI Automation client
            # CUIAutomation CLSID: {FF48DBA4-60EF-4201-AA87-54103EEF594E}
            logger.info(
                f"{LOG_PREFIX} Initializing Windows UI Automation COM client"
            )
            # In real implementation, this would create IUIAutomation interface:
            # self._uia_client = comtypes.client.CreateObject(
            #     "{FF48DBA4-60EF-4201-AA87-54103EEF594E}",
            #     interface=IUIAutomation
            # )
            logger.info(
                f"{LOG_PREFIX} Windows UI Automation initialized (stub mode - "
                "would subscribe to TextChanged and ValueChanged events)"
            )
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to initialize UI Automation: {e}")

    def _stop_platform(self) -> None:
        """Release Windows UI Automation resources."""
        if not _COMTYPES_AVAILABLE:
            return

        try:
            if self._event_handler is not None:
                # Would unsubscribe from events here
                self._event_handler = None

            if self._uia_client is not None:
                self._uia_client = None

            comtypes.CoUninitialize()
            logger.info(f"{LOG_PREFIX} Windows UI Automation resources released")
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Error during UI Automation cleanup: {e}")

    def _poll_events(self) -> List[TextEvent]:
        """Poll for text change events from UI Automation.

        In a full implementation, this would:
        1. Check the UI Automation event queue for TextChanged events
        2. Query the focused element's value/text pattern
        3. Compare with previous state to detect changes
        4. Generate TextEvent for new text

        Current stub: logs that polling would occur.
        """
        if not _COMTYPES_AVAILABLE:
            return []

        # Stub: In real implementation, would query automation events
        # Example of what would happen:
        # - Subscribe to AutomationEvent for TextChanged pattern
        # - On TextChanged: get element name, value, bounding rect
        # - Create TextEvent with direction based on focus state
        #   (focused element changes = OUTPUT, typing in focused = INPUT)
        return []

    def _inject_text_platform(self, target: AccessibilityElement, text: str) -> bool:
        """Inject text using UI Automation ValuePattern or TextPattern.

        In a full implementation, this would:
        1. Find the automation element by element_id
        2. Get the ValuePattern or TextPattern interface
        3. Call SetValue() or InsertText()

        Current stub: logs the injection attempt.
        """
        if not _COMTYPES_AVAILABLE:
            logger.info(
                f"{LOG_PREFIX} [STUB] Would inject text via UI Automation "
                f"ValuePattern into '{target.element_id}'"
            )
            return False

        logger.info(
            f"{LOG_PREFIX} [STUB] UI Automation inject_text: "
            f"element='{target.element_id}', text='{text[:30]}...'"
        )
        # In real implementation:
        # element = self._uia_client.FindFirst(scope, condition)
        # value_pattern = element.GetCurrentPattern(ValuePattern.Pattern)
        # value_pattern.SetValue(text)
        return True


# === LINUX BACKEND: AT-SPI2 via D-Bus ===

class ATSPIInterceptor(TextInterceptor):
    """Linux text interceptor using AT-SPI2 via D-Bus.

    Uses python-dbus to connect to the AT-SPI2 accessibility bus,
    capturing text events from all accessible applications.

    NOTE: This is a stub-level implementation providing the architecture
    and basic event handling. Full AT-SPI2 event subscription requires
    a running D-Bus session and AT-SPI2 registry service.
    """

    def __init__(self, user_language: str = "cs"):
        super().__init__(user_language)
        self._bus = None
        self._registry = None
        self._event_listeners = []

    def _start_platform(self) -> None:
        """Initialize AT-SPI2 D-Bus connection and event listeners."""
        if not _DBUS_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} python-dbus not available — "
                "ATSPIInterceptor will operate in stub mode. "
                "Install with: pip install dbus-python"
            )
            return

        try:
            # Set up D-Bus main loop integration
            DBusGMainLoop(set_as_default=True)

            # Connect to the AT-SPI2 accessibility bus
            logger.info(f"{LOG_PREFIX} Connecting to AT-SPI2 bus")

            # Get the accessibility bus address
            # In real implementation:
            # session_bus = dbus.SessionBus()
            # a11y_bus_obj = session_bus.get_object(ATSPI_BUS_NAME, '/org/a11y/bus')
            # address = a11y_bus_obj.GetAddress(dbus_interface='org.a11y.Bus')
            # self._bus = dbus.connection.Connection(address)

            logger.info(
                f"{LOG_PREFIX} AT-SPI2 initialized (stub mode - "
                "would register for object:text-changed and "
                "object:text-caret-moved events)"
            )

            # In real implementation, would register event listeners:
            # self._registry = self._bus.get_object(
            #     'org.a11y.atspi.Registry',
            #     '/org/a11y/atspi/registry'
            # )
            # registry_iface = dbus.Interface(self._registry,
            #     'org.a11y.atspi.Registry')
            # registry_iface.RegisterEvent('object:text-changed:insert')
            # registry_iface.RegisterEvent('object:text-changed:delete')
            # registry_iface.RegisterEvent('object:text-caret-moved')

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to initialize AT-SPI2: {e}")

    def _stop_platform(self) -> None:
        """Release AT-SPI2 D-Bus resources."""
        if not _DBUS_AVAILABLE:
            return

        try:
            # Deregister event listeners
            for listener in self._event_listeners:
                # Would call DeregisterEvent here
                pass
            self._event_listeners.clear()

            if self._bus is not None:
                self._bus = None

            logger.info(f"{LOG_PREFIX} AT-SPI2 resources released")
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Error during AT-SPI2 cleanup: {e}")

    def _poll_events(self) -> List[TextEvent]:
        """Poll for text change events from AT-SPI2.

        In a full implementation, this would:
        1. Process pending D-Bus messages for text-changed signals
        2. For each signal: get accessible element, app name, text content
        3. Determine direction based on event type:
           - text-changed:insert on focused editable = INPUT
           - text-changed:insert on non-editable = OUTPUT
        4. Get element bounding box via GetExtents()

        Current stub: logs that polling would occur.
        """
        if not _DBUS_AVAILABLE:
            return []

        # Stub: In real implementation, would process D-Bus signals
        # from AT-SPI2 text-changed events.
        # Example signal handler:
        # def _on_text_changed(event):
        #     app_name = event.source.get_application().name
        #     element_id = event.source.get_unique_id()
        #     text = event.source.get_text(0, -1)
        #     extents = event.source.get_extents(CoordType.SCREEN)
        #     direction = Direction.INPUT if event.source.is_editable else Direction.OUTPUT
        return []

    def _inject_text_platform(self, target: AccessibilityElement, text: str) -> bool:
        """Inject text using AT-SPI2 EditableText interface.

        In a full implementation, this would:
        1. Get the accessible object by element_id
        2. Get the EditableText interface
        3. Call insertText() or setTextContents()

        Current stub: logs the injection attempt.
        """
        if not _DBUS_AVAILABLE:
            logger.info(
                f"{LOG_PREFIX} [STUB] Would inject text via AT-SPI2 "
                f"EditableText into '{target.element_id}'"
            )
            return False

        logger.info(
            f"{LOG_PREFIX} [STUB] AT-SPI2 inject_text: "
            f"element='{target.element_id}', text='{text[:30]}...'"
        )
        # In real implementation:
        # accessible = self._get_accessible_by_id(target.element_id)
        # editable_iface = dbus.Interface(accessible,
        #     'org.a11y.atspi.EditableText')
        # editable_iface.SetTextContents(text)
        return True


# === FACTORY FUNCTION ===

def create_interceptor(user_language: str = "cs") -> TextInterceptor:
    """Create the appropriate TextInterceptor for the current platform.

    Args:
        user_language: User's native language code (ISO 639-1).

    Returns:
        Platform-specific TextInterceptor instance.
    """
    if sys.platform == "win32":
        logger.info(f"{LOG_PREFIX} Creating UIAutomationInterceptor (Windows)")
        return UIAutomationInterceptor(user_language=user_language)
    elif sys.platform.startswith("linux"):
        logger.info(f"{LOG_PREFIX} Creating ATSPIInterceptor (Linux)")
        return ATSPIInterceptor(user_language=user_language)
    else:
        logger.warning(
            f"{LOG_PREFIX} Unsupported platform: {sys.platform}. "
            "Falling back to UIAutomationInterceptor (stub mode)."
        )
        return UIAutomationInterceptor(user_language=user_language)


# === MAIN GUARD ===

def main():
    """Self-test entry point for Text Interceptor module."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print(f"{LOG_PREFIX} Text Interceptor self-test")
    print(f"{LOG_PREFIX} Platform: {sys.platform}")
    print(f"{LOG_PREFIX} comtypes available: {_COMTYPES_AVAILABLE}")
    print(f"{LOG_PREFIX} dbus available: {_DBUS_AVAILABLE}")

    # Create interceptor for current platform
    interceptor = create_interceptor(user_language="cs")

    # Register callbacks
    output_events = []
    input_events = []

    def on_output(event: TextEvent):
        output_events.append(event)
        print(f"{LOG_PREFIX} OUTPUT: app={event.source_app}, text='{event.text[:50]}'")

    def on_input(event: TextEvent):
        input_events.append(event)
        print(f"{LOG_PREFIX} INPUT: app={event.source_app}, text='{event.text[:50]}'")

    interceptor.on_text_output(on_output)
    interceptor.on_text_input(on_input)

    # Test TextEvent creation
    test_event = TextEvent(
        source_app="TestApp",
        element_id="btn_1",
        text="Hello world — this is a test",
        position=Rect(100, 200, 300, 50),
        timestamp=time.time(),
        direction=Direction.OUTPUT
    )
    print(f"{LOG_PREFIX} Test event: {test_event}")

    # Test native language pass-through
    native_text = "Toto je text v českém jazyce, který by měl projít bez překladu"
    is_native = interceptor._is_native_language(native_text)
    print(f"{LOG_PREFIX} Native language check (cs text): {is_native}")

    foreign_text = "This is English text that should be translated"
    is_foreign_native = interceptor._is_native_language(foreign_text)
    print(f"{LOG_PREFIX} Native language check (en text): {is_foreign_native}")

    # Test dispatch with native pass-through
    interceptor._dispatch_event(test_event)

    # Test start/stop lifecycle
    print(f"{LOG_PREFIX} Starting interceptor...")
    interceptor.start()
    assert interceptor.is_running
    print(f"{LOG_PREFIX} Running: {interceptor.is_running}")

    # Let it run briefly
    time.sleep(0.2)

    print(f"{LOG_PREFIX} Stopping interceptor...")
    interceptor.stop()
    assert not interceptor.is_running
    print(f"{LOG_PREFIX} Running: {interceptor.is_running}")

    # Test inject_text
    target = AccessibilityElement(
        element_id="edit_1",
        app_name="Notepad",
        role="editable_text",
        name="Document",
        value="",
        rect=Rect(10, 10, 400, 300)
    )
    result = interceptor.inject_text(target, "Přeložený text")
    print(f"{LOG_PREFIX} inject_text result: {result}")

    # Test user_language property
    interceptor.user_language = "en"
    assert interceptor.user_language == "en"
    interceptor.user_language = "cs"
    assert interceptor.user_language == "cs"
    print(f"{LOG_PREFIX} User language property: OK")

    # Test TextEvent truncation
    long_text = "A" * (MAX_TEXT_EVENT_LENGTH + 100)
    long_event = TextEvent(
        source_app="TestApp",
        element_id="text_1",
        text=long_text,
        position=Rect(0, 0, 100, 20),
        timestamp=time.time(),
        direction=Direction.OUTPUT
    )
    assert len(long_event.text) == MAX_TEXT_EVENT_LENGTH
    print(f"{LOG_PREFIX} Text truncation: OK")

    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
