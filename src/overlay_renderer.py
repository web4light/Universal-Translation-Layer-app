"""
Overlay Renderer — Universal Translation Layer (UTL)

Vykreslení přeloženého textu přes originální obsah v libovolné aplikaci.

- Windows: DirectCompositionRenderer (hardware-accelerated layered window via ctypes/win32)
- Linux: X11OverlayRenderer (X11 override-redirect + Cairo rendering)

Modul poskytuje:
- OverlayRenderer base class s show_translation / update_position / hide / set_mode
- TextStyle dataclass pro definici vzhledu přeloženého textu
- OverlayMode enum: REPLACE, TOOLTIP, SIDE_BY_SIDE
- Sledování aktivních overlayů (element_id -> overlay state)
- Prometheus metriky: utl_overlay_render_latency_seconds, utl_overlay_gpu_usage_percent
- Target: <150ms display latency, <3% GPU usage

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
from typing import Dict, Optional, NamedTuple

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[OVERLAY]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Histogram, Gauge

    utl_overlay_render_latency_seconds = Histogram(
        'utl_overlay_render_latency_seconds',
        'Latency of overlay rendering in seconds',
        ['mode', 'action'],  # mode: replace/tooltip/side_by_side, action: show/update/hide
        buckets=[0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]
    )

    utl_overlay_gpu_usage_percent = Gauge(
        'utl_overlay_gpu_usage_percent',
        'Current GPU usage percentage by overlay renderer'
    )
except ImportError:
    utl_overlay_render_latency_seconds = None
    utl_overlay_gpu_usage_percent = None

# === PLATFORM-SPECIFIC IMPORTS ===

# Windows: ctypes + win32api for DirectComposition layered windows
try:
    import ctypes
    import ctypes.wintypes
    _CTYPES_AVAILABLE = True
except ImportError:
    _CTYPES_AVAILABLE = False

try:
    import win32api
    import win32gui
    import win32con
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False

# Linux: python-xlib for X11 + Cairo for rendering
try:
    from Xlib import X, display as xdisplay, Xatom
    _XLIB_AVAILABLE = True
except ImportError:
    _XLIB_AVAILABLE = False

try:
    import cairo
    _CAIRO_AVAILABLE = True
except ImportError:
    _CAIRO_AVAILABLE = False

# === CONSTANTS ===

# Maximum latency threshold for overlay display (milliseconds)
MAX_DISPLAY_LATENCY_MS = 150

# Maximum GPU usage target (percent)
MAX_GPU_USAGE_PERCENT = 3.0

# Default overlay dimensions
DEFAULT_OVERLAY_PADDING = 4  # pixels
DEFAULT_OVERLAY_MARGIN = 2   # pixels


# === DATA MODELS ===

class Rect(NamedTuple):
    """Screen rectangle for element positioning."""
    x: int
    y: int
    width: int
    height: int


class OverlayMode(Enum):
    """Display mode for translated text overlay."""
    REPLACE = "replace"           # Replace original text with translation
    TOOLTIP = "tooltip"           # Show translation in a tooltip near original
    SIDE_BY_SIDE = "side_by_side" # Show both original and translation


@dataclass
class TextStyle:
    """Style definition for rendered overlay text.

    Attributes:
        font_family: Font family name (e.g. 'Segoe UI', 'DejaVu Sans')
        font_size: Font size in points
        color: RGBA tuple (0-255 each channel)
        background: RGBA background color tuple (0-255 each channel)
    """
    font_family: str = "Segoe UI"
    font_size: int = 14
    color: tuple = (255, 255, 255, 255)       # RGBA — white, fully opaque
    background: tuple = (30, 30, 30, 220)     # RGBA — dark, mostly opaque

    def __post_init__(self):
        # Validate RGBA tuples
        for channel_name, value in [("color", self.color), ("background", self.background)]:
            if len(value) != 4:
                raise ValueError(
                    f"{channel_name} must be a 4-tuple (R, G, B, A), got {len(value)} elements"
                )
            for i, v in enumerate(value):
                if not (0 <= v <= 255):
                    raise ValueError(
                        f"{channel_name}[{i}] must be 0-255, got {v}"
                    )
        if self.font_size <= 0:
            raise ValueError(f"font_size must be > 0, got {self.font_size}")


@dataclass
class OverlayState:
    """Internal state of a single active overlay.

    Tracks position, content, and timing for each overlay element.
    """
    element_id: str
    rect: Rect
    translated_text: str
    style: TextStyle
    mode: OverlayMode
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    visible: bool = True


# === OVERLAY RENDERER BASE CLASS ===

class OverlayRenderer(ABC):
    """Renders translated text overlay on top of original content.

    This is the abstract base class. Platform-specific implementations:
    - DirectCompositionRenderer (Windows)
    - X11OverlayRenderer (Linux)

    Supports modes: REPLACE, TOOLTIP, SIDE_BY_SIDE.
    Tracks active overlays keyed by element_id.
    Logs latency warnings when display exceeds 150ms.
    """

    def __init__(self):
        self._mode: OverlayMode = OverlayMode.REPLACE
        self._overlays: Dict[str, OverlayState] = {}
        self._lock = threading.Lock()
        self._initialized = False

    # === PUBLIC API ===

    def show_translation(self, original_rect: Rect, translated: str,
                         style: TextStyle, element_id: Optional[str] = None) -> None:
        """Display translated text over the original text position.

        Args:
            original_rect: Screen rectangle of the original text element.
            translated: Translated text content to display.
            style: TextStyle defining font, color, background.
            element_id: Unique identifier for this overlay (auto-generated if None).

        Target: <150ms from call to visible overlay.
        """
        start_time = time.perf_counter()

        if element_id is None:
            element_id = f"overlay_{id(translated)}_{int(time.time() * 1000)}"

        overlay = OverlayState(
            element_id=element_id,
            rect=original_rect,
            translated_text=translated,
            style=style,
            mode=self._mode,
            created_at=time.time(),
            last_updated=time.time(),
            visible=True
        )

        with self._lock:
            self._overlays[element_id] = overlay

        # Platform-specific rendering
        self._render_overlay(overlay)

        # Measure and log latency
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        mode_label = self._mode.value

        if utl_overlay_render_latency_seconds is not None:
            utl_overlay_render_latency_seconds.labels(
                mode=mode_label, action="show"
            ).observe(elapsed_ms / 1000)

        if elapsed_ms > MAX_DISPLAY_LATENCY_MS:
            logger.warning(
                f"{LOG_PREFIX} show_translation latency {elapsed_ms:.1f}ms "
                f"exceeds target {MAX_DISPLAY_LATENCY_MS}ms "
                f"(element={element_id})"
            )
        else:
            logger.debug(
                f"{LOG_PREFIX} show_translation: {elapsed_ms:.1f}ms "
                f"(element={element_id}, mode={mode_label})"
            )

    def update_position(self, element_id: str, new_rect: Rect) -> None:
        """Reposition an active overlay to maintain alignment.

        Called when user scrolls or resizes a window.
        The overlay follows the original text element.

        Args:
            element_id: Identifier of the overlay to reposition.
            new_rect: New screen rectangle for the overlay.
        """
        start_time = time.perf_counter()

        with self._lock:
            if element_id not in self._overlays:
                logger.warning(
                    f"{LOG_PREFIX} update_position: unknown element '{element_id}'"
                )
                return
            overlay = self._overlays[element_id]
            overlay.rect = new_rect
            overlay.last_updated = time.time()

        # Platform-specific repositioning
        self._reposition_overlay(overlay)

        # Measure latency
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        mode_label = self._mode.value

        if utl_overlay_render_latency_seconds is not None:
            utl_overlay_render_latency_seconds.labels(
                mode=mode_label, action="update"
            ).observe(elapsed_ms / 1000)

        if elapsed_ms > MAX_DISPLAY_LATENCY_MS:
            logger.warning(
                f"{LOG_PREFIX} update_position latency {elapsed_ms:.1f}ms "
                f"exceeds target {MAX_DISPLAY_LATENCY_MS}ms "
                f"(element={element_id})"
            )

    def hide(self, element_id: str) -> None:
        """Hide and remove a specific overlay.

        Args:
            element_id: Identifier of the overlay to hide.
        """
        start_time = time.perf_counter()

        with self._lock:
            if element_id not in self._overlays:
                logger.debug(
                    f"{LOG_PREFIX} hide: element '{element_id}' not found (already hidden?)"
                )
                return
            overlay = self._overlays.pop(element_id)
            overlay.visible = False

        # Platform-specific hide
        self._hide_overlay(overlay)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        mode_label = self._mode.value

        if utl_overlay_render_latency_seconds is not None:
            utl_overlay_render_latency_seconds.labels(
                mode=mode_label, action="hide"
            ).observe(elapsed_ms / 1000)

        logger.debug(f"{LOG_PREFIX} hide: element '{element_id}' removed ({elapsed_ms:.1f}ms)")

    def set_mode(self, mode: OverlayMode) -> None:
        """Set the overlay display mode.

        Args:
            mode: OverlayMode — REPLACE, TOOLTIP, or SIDE_BY_SIDE.
        """
        old_mode = self._mode
        self._mode = mode
        logger.info(f"{LOG_PREFIX} Mode changed: {old_mode.value} -> {mode.value}")

        # Re-render all active overlays in the new mode
        with self._lock:
            for overlay in self._overlays.values():
                overlay.mode = mode

        self._apply_mode_change()

    @property
    def mode(self) -> OverlayMode:
        """Current overlay display mode."""
        return self._mode

    @property
    def active_overlay_count(self) -> int:
        """Number of currently active overlays."""
        with self._lock:
            return len(self._overlays)

    def get_overlay(self, element_id: str) -> Optional[OverlayState]:
        """Get the state of a specific overlay.

        Args:
            element_id: Overlay element identifier.

        Returns:
            OverlayState if found, None otherwise.
        """
        with self._lock:
            return self._overlays.get(element_id)

    def hide_all(self) -> None:
        """Hide and remove all active overlays."""
        with self._lock:
            overlay_ids = list(self._overlays.keys())

        for eid in overlay_ids:
            self.hide(eid)

        logger.info(f"{LOG_PREFIX} All overlays hidden ({len(overlay_ids)} removed)")

    # === ABSTRACT PLATFORM METHODS ===

    @abstractmethod
    def _render_overlay(self, overlay: OverlayState) -> None:
        """Platform-specific overlay rendering."""
        ...

    @abstractmethod
    def _reposition_overlay(self, overlay: OverlayState) -> None:
        """Platform-specific overlay repositioning."""
        ...

    @abstractmethod
    def _hide_overlay(self, overlay: OverlayState) -> None:
        """Platform-specific overlay hiding."""
        ...

    @abstractmethod
    def _apply_mode_change(self) -> None:
        """Platform-specific mode change handling (re-render all overlays)."""
        ...


# === WINDOWS BACKEND: DirectComposition ===

class DirectCompositionRenderer(OverlayRenderer):
    """Windows overlay renderer using DirectComposition + layered windows.

    Uses ctypes and win32api to create a hardware-accelerated transparent
    layered window (WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST)
    that renders translated text over target applications.

    DirectComposition provides GPU-accelerated compositing with minimal
    overhead (target: <3% GPU usage).

    NOTE: This is a stub-level implementation. Full DirectComposition
    integration requires a running Windows desktop and GDI+/Direct2D
    rendering pipeline.
    """

    def __init__(self):
        super().__init__()
        self._hwnd = None
        self._class_registered = False

    def initialize(self) -> bool:
        """Initialize the DirectComposition overlay window.

        Creates a transparent, click-through, always-on-top layered window.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        if not (_CTYPES_AVAILABLE and sys.platform == "win32"):
            logger.warning(
                f"{LOG_PREFIX} DirectCompositionRenderer requires Windows + ctypes. "
                "Operating in stub mode."
            )
            self._initialized = True
            return True

        if not _WIN32_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} win32api/win32gui not available. "
                "Install with: pip install pywin32. Operating in stub mode."
            )
            self._initialized = True
            return True

        try:
            logger.info(f"{LOG_PREFIX} Initializing DirectComposition renderer")

            # In full implementation:
            # 1. Register window class with CS_HREDRAW | CS_VREDRAW
            # 2. Create layered window:
            #    hwnd = CreateWindowEx(
            #        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE,
            #        class_name, "UTL_Overlay",
            #        WS_POPUP, 0, 0, screen_w, screen_h, None, None, hinstance, None
            #    )
            # 3. Set layered window alpha: SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
            # 4. Initialize DirectComposition device + visual tree
            # 5. Show window without activating: ShowWindow(hwnd, SW_SHOWNOACTIVATE)

            logger.info(
                f"{LOG_PREFIX} DirectComposition initialized (stub mode — "
                "would create WS_EX_LAYERED | WS_EX_TRANSPARENT overlay window)"
            )
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to initialize DirectComposition: {e}")
            return False

    def _render_overlay(self, overlay: OverlayState) -> None:
        """Render overlay using DirectComposition + GDI+ text drawing.

        In full implementation:
        1. Create/update DirectComposition visual for this element
        2. Use Direct2D or GDI+ to draw text with TextStyle parameters
        3. Position visual at overlay.rect coordinates
        4. For TOOLTIP mode: offset visual below/beside original rect
        5. For SIDE_BY_SIDE mode: place visual to the right of original
        6. Commit DirectComposition device to trigger GPU compositing
        """
        if not self._initialized:
            return

        mode_label = overlay.mode.value
        rect = overlay.rect

        logger.debug(
            f"{LOG_PREFIX} [DC] Render overlay '{overlay.element_id}' "
            f"at ({rect.x}, {rect.y}, {rect.width}x{rect.height}) "
            f"mode={mode_label}, text='{overlay.translated_text[:40]}...'"
            if len(overlay.translated_text) > 40 else
            f"{LOG_PREFIX} [DC] Render overlay '{overlay.element_id}' "
            f"at ({rect.x}, {rect.y}, {rect.width}x{rect.height}) "
            f"mode={mode_label}, text='{overlay.translated_text}'"
        )

        # Stub: In real implementation would call:
        # - IDCompositionDevice::CreateVisual()
        # - IDCompositionVisual::SetContent(surface)
        # - ID2D1RenderTarget::DrawText(translated, format, rect, brush)
        # - IDCompositionDevice::Commit()

        # Update GPU usage metric (stub: report near-zero)
        if utl_overlay_gpu_usage_percent is not None:
            utl_overlay_gpu_usage_percent.set(0.5)  # Stub value

    def _reposition_overlay(self, overlay: OverlayState) -> None:
        """Reposition overlay by updating DirectComposition visual offset.

        In full implementation:
        - IDCompositionVisual::SetOffsetX/Y(new_rect.x, new_rect.y)
        - IDCompositionDevice::Commit()
        """
        if not self._initialized:
            return

        rect = overlay.rect
        logger.debug(
            f"{LOG_PREFIX} [DC] Reposition '{overlay.element_id}' "
            f"to ({rect.x}, {rect.y})"
        )

    def _hide_overlay(self, overlay: OverlayState) -> None:
        """Hide overlay by removing DirectComposition visual.

        In full implementation:
        - IDCompositionVisual::SetContent(None)
        - Remove visual from tree
        - IDCompositionDevice::Commit()
        """
        if not self._initialized:
            return

        logger.debug(f"{LOG_PREFIX} [DC] Hide overlay '{overlay.element_id}'")

    def _apply_mode_change(self) -> None:
        """Re-render all overlays with new mode.

        In full implementation: re-layout all visuals based on new mode
        (REPLACE = same position, TOOLTIP = offset, SIDE_BY_SIDE = adjacent).
        """
        if not self._initialized:
            return

        with self._lock:
            for overlay in self._overlays.values():
                self._render_overlay(overlay)

        logger.debug(f"{LOG_PREFIX} [DC] Mode change applied to all overlays")

    def destroy(self) -> None:
        """Release DirectComposition resources and destroy overlay window.

        In full implementation:
        - Release IDCompositionDevice
        - DestroyWindow(hwnd)
        - UnregisterClass
        """
        if self._hwnd is not None and _WIN32_AVAILABLE:
            # win32gui.DestroyWindow(self._hwnd)
            self._hwnd = None

        self._initialized = False
        logger.info(f"{LOG_PREFIX} [DC] DirectComposition resources released")


# === LINUX BACKEND: X11 + Cairo ===

class X11OverlayRenderer(OverlayRenderer):
    """Linux overlay renderer using X11 override-redirect window + Cairo.

    Creates an X11 window with override_redirect=True (bypasses window manager)
    that is transparent and positioned on top of all windows. Cairo is used
    for hardware-accelerated text rendering.

    NOTE: This is a stub-level implementation. Full X11 overlay requires
    a running X server and compositing window manager for transparency.
    """

    def __init__(self):
        super().__init__()
        self._display = None
        self._window = None
        self._gc = None
        self._cairo_surface = None

    def initialize(self) -> bool:
        """Initialize X11 overlay window with override-redirect.

        Creates a transparent, unmanaged window that sits on top of all content.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        if not sys.platform.startswith("linux"):
            logger.warning(
                f"{LOG_PREFIX} X11OverlayRenderer requires Linux. "
                "Operating in stub mode."
            )
            self._initialized = True
            return True

        if not _XLIB_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} python-xlib not available. "
                "Install with: pip install python-xlib. Operating in stub mode."
            )
            self._initialized = True
            return True

        if not _CAIRO_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} pycairo not available. "
                "Install with: pip install pycairo. Operating in stub mode."
            )
            self._initialized = True
            return True

        try:
            logger.info(f"{LOG_PREFIX} Initializing X11 overlay renderer")

            # In full implementation:
            # 1. Open X11 display connection
            #    self._display = xdisplay.Display()
            #    screen = self._display.screen()
            #    root = screen.root
            #
            # 2. Find a 32-bit ARGB visual for transparency
            #    visual = find_argb_visual(screen)
            #
            # 3. Create override-redirect window (unmanaged, always on top)
            #    self._window = root.create_window(
            #        0, 0, screen.width_in_pixels, screen.height_in_pixels,
            #        0, 32, X.InputOutput, visual,
            #        override_redirect=True,
            #        event_mask=X.ExposureMask
            #    )
            #
            # 4. Set window type to _NET_WM_WINDOW_TYPE_DOCK (stays above all)
            #    self._window.change_property(
            #        _NET_WM_WINDOW_TYPE, Xatom.ATOM, 32, [_NET_WM_WINDOW_TYPE_DOCK]
            #    )
            #
            # 5. Make window input-transparent (pass clicks through)
            #    Set _NET_WM_STATE to _NET_WM_STATE_ABOVE
            #    Use XShape extension to make click-through
            #
            # 6. Create Cairo surface tied to X11 window
            #    self._cairo_surface = cairo.XlibSurface(
            #        display, window_id, visual, width, height
            #    )
            #
            # 7. Map (show) the window
            #    self._window.map()
            #    self._display.flush()

            logger.info(
                f"{LOG_PREFIX} X11 overlay initialized (stub mode — "
                "would create override-redirect ARGB window + Cairo surface)"
            )
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to initialize X11 overlay: {e}")
            return False

    def _render_overlay(self, overlay: OverlayState) -> None:
        """Render overlay using Cairo text drawing on X11 surface.

        In full implementation:
        1. Clear the region at overlay.rect on the Cairo surface
        2. Set font (overlay.style.font_family, font_size)
        3. Draw background rectangle with style.background RGBA
        4. Draw text with style.color RGBA
        5. For TOOLTIP mode: position below/beside original rect with arrow
        6. For SIDE_BY_SIDE mode: position to the right of original
        7. Flush X11 display to push changes to screen
        """
        if not self._initialized:
            return

        rect = overlay.rect
        mode_label = overlay.mode.value

        logger.debug(
            f"{LOG_PREFIX} [X11] Render overlay '{overlay.element_id}' "
            f"at ({rect.x}, {rect.y}, {rect.width}x{rect.height}) "
            f"mode={mode_label}"
        )

        # Stub: In real implementation would call:
        # ctx = cairo.Context(self._cairo_surface)
        # ctx.set_source_rgba(bg_r/255, bg_g/255, bg_b/255, bg_a/255)
        # ctx.rectangle(rect.x, rect.y, rect.width, rect.height)
        # ctx.fill()
        # ctx.select_font_face(style.font_family, cairo.FONT_SLANT_NORMAL, ...)
        # ctx.set_font_size(style.font_size)
        # ctx.set_source_rgba(fg_r/255, fg_g/255, fg_b/255, fg_a/255)
        # ctx.move_to(rect.x + padding, rect.y + font_size + padding)
        # ctx.show_text(overlay.translated_text)
        # self._display.flush()

        # Update GPU usage metric (stub: report near-zero)
        if utl_overlay_gpu_usage_percent is not None:
            utl_overlay_gpu_usage_percent.set(0.3)  # Stub value

    def _reposition_overlay(self, overlay: OverlayState) -> None:
        """Reposition overlay by redrawing at new coordinates.

        In full implementation:
        - Clear old region on Cairo surface
        - Redraw at new overlay.rect position
        - Flush X11 display
        """
        if not self._initialized:
            return

        rect = overlay.rect
        logger.debug(
            f"{LOG_PREFIX} [X11] Reposition '{overlay.element_id}' "
            f"to ({rect.x}, {rect.y})"
        )

    def _hide_overlay(self, overlay: OverlayState) -> None:
        """Hide overlay by clearing its region on the Cairo surface.

        In full implementation:
        - Clear the overlay region with transparent pixels
        - Flush X11 display
        """
        if not self._initialized:
            return

        logger.debug(f"{LOG_PREFIX} [X11] Hide overlay '{overlay.element_id}'")

    def _apply_mode_change(self) -> None:
        """Re-render all overlays with new mode.

        In full implementation: clear entire surface and re-render all
        overlays with updated layout (REPLACE/TOOLTIP/SIDE_BY_SIDE).
        """
        if not self._initialized:
            return

        with self._lock:
            for overlay in self._overlays.values():
                self._render_overlay(overlay)

        logger.debug(f"{LOG_PREFIX} [X11] Mode change applied to all overlays")

    def destroy(self) -> None:
        """Release X11 and Cairo resources.

        In full implementation:
        - Destroy Cairo surface
        - Unmap and destroy X11 window
        - Close X11 display connection
        """
        if self._cairo_surface is not None:
            # self._cairo_surface.finish()
            self._cairo_surface = None

        if self._window is not None:
            # self._window.unmap()
            # self._window.destroy()
            self._window = None

        if self._display is not None:
            # self._display.close()
            self._display = None

        self._initialized = False
        logger.info(f"{LOG_PREFIX} [X11] X11 + Cairo resources released")


# === FACTORY FUNCTION ===

def create_renderer() -> OverlayRenderer:
    """Create the appropriate OverlayRenderer for the current platform.

    Returns:
        Platform-specific OverlayRenderer instance (already initialized).
    """
    if sys.platform == "win32":
        logger.info(f"{LOG_PREFIX} Creating DirectCompositionRenderer (Windows)")
        renderer = DirectCompositionRenderer()
        renderer.initialize()
        return renderer
    elif sys.platform.startswith("linux"):
        logger.info(f"{LOG_PREFIX} Creating X11OverlayRenderer (Linux)")
        renderer = X11OverlayRenderer()
        renderer.initialize()
        return renderer
    else:
        logger.warning(
            f"{LOG_PREFIX} Unsupported platform: {sys.platform}. "
            "Falling back to DirectCompositionRenderer (stub mode)."
        )
        renderer = DirectCompositionRenderer()
        renderer.initialize()
        return renderer


# === MAIN GUARD ===

def main():
    """Self-test entry point for Overlay Renderer module."""
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    print(f"{LOG_PREFIX} Overlay Renderer self-test")
    print(f"{LOG_PREFIX} Platform: {sys.platform}")
    print(f"{LOG_PREFIX} ctypes available: {_CTYPES_AVAILABLE}")
    print(f"{LOG_PREFIX} win32 available: {_WIN32_AVAILABLE}")
    print(f"{LOG_PREFIX} Xlib available: {_XLIB_AVAILABLE}")
    print(f"{LOG_PREFIX} Cairo available: {_CAIRO_AVAILABLE}")
    print()

    # Create renderer for current platform
    renderer = create_renderer()
    print(f"{LOG_PREFIX} Renderer created: {type(renderer).__name__}")
    print(f"{LOG_PREFIX} Initial mode: {renderer.mode.value}")
    print(f"{LOG_PREFIX} Active overlays: {renderer.active_overlay_count}")
    print()

    # Test TextStyle creation and validation
    style = TextStyle(
        font_family="Segoe UI",
        font_size=16,
        color=(255, 255, 255, 255),
        background=(0, 0, 0, 200)
    )
    print(f"{LOG_PREFIX} TextStyle: font={style.font_family}, size={style.font_size}")

    # Test TextStyle validation errors
    try:
        bad_style = TextStyle(font_size=-1)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"{LOG_PREFIX} TextStyle validation (negative size): OK — {e}")

    try:
        bad_style = TextStyle(color=(256, 0, 0, 0))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"{LOG_PREFIX} TextStyle validation (bad RGBA): OK — {e}")
    print()

    # Test show_translation
    rect1 = Rect(100, 200, 300, 30)
    renderer.show_translation(rect1, "Přeložený text příklad", style, element_id="elem_1")
    print(f"{LOG_PREFIX} Active overlays after show: {renderer.active_overlay_count}")
    assert renderer.active_overlay_count == 1

    # Test update_position
    new_rect = Rect(100, 250, 300, 30)
    renderer.update_position("elem_1", new_rect)
    overlay_state = renderer.get_overlay("elem_1")
    assert overlay_state is not None
    assert overlay_state.rect == new_rect
    print(f"{LOG_PREFIX} update_position: OK (moved to y=250)")

    # Test set_mode
    renderer.set_mode(OverlayMode.TOOLTIP)
    assert renderer.mode == OverlayMode.TOOLTIP
    print(f"{LOG_PREFIX} set_mode(TOOLTIP): OK")

    renderer.set_mode(OverlayMode.SIDE_BY_SIDE)
    assert renderer.mode == OverlayMode.SIDE_BY_SIDE
    print(f"{LOG_PREFIX} set_mode(SIDE_BY_SIDE): OK")

    renderer.set_mode(OverlayMode.REPLACE)
    assert renderer.mode == OverlayMode.REPLACE
    print(f"{LOG_PREFIX} set_mode(REPLACE): OK")
    print()

    # Test multiple overlays
    rect2 = Rect(400, 100, 200, 25)
    renderer.show_translation(rect2, "Second overlay", style, element_id="elem_2")
    assert renderer.active_overlay_count == 2
    print(f"{LOG_PREFIX} Multiple overlays: {renderer.active_overlay_count}")

    # Test hide
    renderer.hide("elem_1")
    assert renderer.active_overlay_count == 1
    assert renderer.get_overlay("elem_1") is None
    print(f"{LOG_PREFIX} hide(elem_1): OK, remaining={renderer.active_overlay_count}")

    # Test hide_all
    renderer.show_translation(Rect(0, 0, 100, 20), "Third", style, element_id="elem_3")
    assert renderer.active_overlay_count == 2
    renderer.hide_all()
    assert renderer.active_overlay_count == 0
    print(f"{LOG_PREFIX} hide_all: OK")

    # Test hide unknown element (should not raise)
    renderer.hide("nonexistent_element")
    print(f"{LOG_PREFIX} hide(unknown): OK (no error)")

    # Test update_position unknown element (should not raise)
    renderer.update_position("nonexistent_element", Rect(0, 0, 10, 10))
    print(f"{LOG_PREFIX} update_position(unknown): OK (no error)")
    print()

    # Test OverlayMode enum values
    assert OverlayMode.REPLACE.value == "replace"
    assert OverlayMode.TOOLTIP.value == "tooltip"
    assert OverlayMode.SIDE_BY_SIDE.value == "side_by_side"
    print(f"{LOG_PREFIX} OverlayMode enum values: OK")

    # Test Rect NamedTuple
    r = Rect(10, 20, 30, 40)
    assert r.x == 10 and r.y == 20 and r.width == 30 and r.height == 40
    print(f"{LOG_PREFIX} Rect NamedTuple: OK")

    print()
    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
