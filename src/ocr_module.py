"""
OCR Module — Universal Translation Layer (UTL)

EasyOCR-based text extraction for non-accessible applications.
Fallback modul pro aplikace, ktere neposkytuju text pres accessibility API.

- extract_text(region) -> list[OCRResult]: extrakce textu z oblasti obrazovky (<200ms target)
- detect_text_regions(screenshot) -> list[Rect]: nalezeni oblasti s textem
- Retry logika: zvetseni regionu pri selhani, preskoceni po 3 neuspesnych pokusech
- Prometheus metriky: utl_ocr_extraction_latency_seconds, utl_ocr_extraction_total

Autor: Pan Jeskyne
Asistent: Kiro
"""

import time
import logging
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[OCR]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Histogram, Counter

    utl_ocr_extraction_latency_seconds = Histogram(
        'utl_ocr_extraction_latency_seconds',
        'Latency of OCR text extraction in seconds',
        buckets=[0.025, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]
    )

    utl_ocr_extraction_total = Counter(
        'utl_ocr_extraction_total',
        'Total OCR extraction attempts',
        ['status']  # success, failure, skip
    )
except ImportError:
    utl_ocr_extraction_latency_seconds = None
    utl_ocr_extraction_total = None

# === EASYOCR BACKEND ===

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    easyocr = None
    _EASYOCR_AVAILABLE = False

# === CONSTANTS ===

LATENCY_TARGET_MS = 200       # Target extraction latency in milliseconds
MAX_RETRIES = 3               # Maximum retry attempts before skipping
REGION_EXPAND_FACTOR = 1.5    # Factor to expand region on retry
DEFAULT_LANGUAGES = ['en']    # Default OCR languages


# === DATA MODELS ===

@dataclass
class Rect:
    """Rectangle defined by position and size.

    Attributes:
        x: Left edge X coordinate
        y: Top edge Y coordinate
        width: Width of the rectangle
        height: Height of the rectangle
    """
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self):
        if self.width < 0:
            raise ValueError("width must be >= 0")
        if self.height < 0:
            raise ValueError("height must be >= 0")

    @property
    def area(self) -> int:
        """Area of the rectangle in pixels."""
        return self.width * self.height

    @property
    def right(self) -> int:
        """Right edge X coordinate."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Bottom edge Y coordinate."""
        return self.y + self.height

    def expanded(self, factor: float) -> 'Rect':
        """Return a new Rect expanded by the given factor, centered on the same midpoint."""
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        new_w = int(self.width * factor)
        new_h = int(self.height * factor)
        new_x = int(cx - new_w / 2)
        new_y = int(cy - new_h / 2)
        return Rect(x=new_x, y=new_y, width=max(0, new_w), height=max(0, new_h))

    def clamp(self, max_width: int, max_height: int) -> 'Rect':
        """Return a new Rect clamped to fit within given bounds."""
        x = max(0, self.x)
        y = max(0, self.y)
        w = min(self.width, max_width - x)
        h = min(self.height, max_height - y)
        return Rect(x=x, y=y, width=max(0, w), height=max(0, h))


@dataclass
class ScreenRegion:
    """A screen region defined by a rectangle and an associated screenshot.

    Attributes:
        rect: Bounding rectangle on screen
        image: Screenshot data as numpy array (H x W x C, uint8 BGR)
    """
    rect: Rect
    image: np.ndarray

    @property
    def height(self) -> int:
        """Height of the image data."""
        return self.image.shape[0]

    @property
    def width(self) -> int:
        """Width of the image data."""
        return self.image.shape[1]


@dataclass
class OCRResult:
    """Result of OCR text extraction.

    Attributes:
        text: Recognized text string
        confidence: Recognition confidence (0.0 - 1.0)
        bounding_box: Bounding rectangle of the text within the region
        language: Detected language of the text (ISO 639-1 code)
    """
    text: str
    confidence: float
    bounding_box: Rect
    language: str

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")


# === OCR MODULE CLASS ===

class OCRModule:
    """EasyOCR-based text extraction for non-accessible apps.

    Provides OCR fallback when applications do not expose text via
    accessibility APIs. Targets <200ms extraction latency per region.
    Implements retry logic: expands region by 1.5x on failure, skips
    after 3 consecutive failures.
    """

    def __init__(self, languages: Optional[List[str]] = None, gpu: bool = True):
        """Initialize OCR Module.

        Args:
            languages: List of language codes for OCR (default: ['en']).
            gpu: Whether to use GPU acceleration (default: True).
        """
        self._languages = languages or DEFAULT_LANGUAGES
        self._gpu = gpu
        self._reader: Optional[object] = None
        self._consecutive_failures: int = 0

        if not _EASYOCR_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} easyocr library not available. "
                "OCR extraction will return empty results. "
                "Install with: pip install easyocr"
            )
        else:
            self._init_reader()

    def _init_reader(self) -> None:
        """Initialize the EasyOCR reader (lazy load on first use if needed)."""
        try:
            self._reader = easyocr.Reader(self._languages, gpu=self._gpu)
            logger.info(
                f"{LOG_PREFIX} EasyOCR reader initialized "
                f"(languages={self._languages}, gpu={self._gpu})"
            )
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to initialize EasyOCR reader: {e}")
            self._reader = None

    # === TEXT EXTRACTION ===

    def extract_text(self, region: ScreenRegion) -> List[OCRResult]:
        """Extract text from a screen region using OCR.

        Implements retry logic:
        - On failure, retries with a 1.5x larger region
        - After 3 consecutive failures, skips (returns empty list)

        Target latency: <200ms per extraction.

        Args:
            region: ScreenRegion containing the image data and bounding rect.

        Returns:
            List of OCRResult objects with detected text, confidence, and positions.
            Returns empty list if OCR is unavailable or all retries fail.
        """
        # Skip if too many consecutive failures
        if self._consecutive_failures >= MAX_RETRIES:
            logger.warning(
                f"{LOG_PREFIX} Skipping extraction — "
                f"{MAX_RETRIES} consecutive failures reached"
            )
            self._record_metric('skip')
            return []

        start_time = time.perf_counter()
        results = self._try_extract(region)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if results is not None:
            # Success — reset failure counter
            self._consecutive_failures = 0
            self._record_metric('success')

            if elapsed_ms > LATENCY_TARGET_MS:
                logger.warning(
                    f"{LOG_PREFIX} Extraction exceeded target latency: "
                    f"{elapsed_ms:.1f}ms > {LATENCY_TARGET_MS}ms"
                )

            # Record latency
            if utl_ocr_extraction_latency_seconds is not None:
                utl_ocr_extraction_latency_seconds.observe(elapsed_ms / 1000.0)

            return results

        # First attempt failed — retry with expanded region
        for attempt in range(1, MAX_RETRIES):
            self._consecutive_failures += 1

            if self._consecutive_failures >= MAX_RETRIES:
                logger.warning(
                    f"{LOG_PREFIX} Max retries ({MAX_RETRIES}) reached — skipping"
                )
                self._record_metric('failure')
                return []

            expanded_rect = region.rect.expanded(REGION_EXPAND_FACTOR ** attempt)
            logger.info(
                f"{LOG_PREFIX} Retry {attempt}/{MAX_RETRIES - 1} with expanded region "
                f"({expanded_rect.width}x{expanded_rect.height})"
            )

            # Create expanded region from original image if possible
            expanded_region = self._expand_region(region, expanded_rect)
            retry_results = self._try_extract(expanded_region)

            if retry_results is not None:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                self._consecutive_failures = 0
                self._record_metric('success')

                if elapsed_ms > LATENCY_TARGET_MS:
                    logger.warning(
                        f"{LOG_PREFIX} Extraction (after retry) exceeded target: "
                        f"{elapsed_ms:.1f}ms > {LATENCY_TARGET_MS}ms"
                    )

                if utl_ocr_extraction_latency_seconds is not None:
                    utl_ocr_extraction_latency_seconds.observe(elapsed_ms / 1000.0)

                return retry_results

        # All retries failed
        self._consecutive_failures += 1
        self._record_metric('failure')
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if utl_ocr_extraction_latency_seconds is not None:
            utl_ocr_extraction_latency_seconds.observe(elapsed_ms / 1000.0)

        return []

    def _try_extract(self, region: ScreenRegion) -> Optional[List[OCRResult]]:
        """Attempt a single OCR extraction.

        Returns:
            List of OCRResult on success, None on failure.
        """
        if self._reader is None:
            return None

        try:
            # EasyOCR expects RGB numpy array or file path
            image = region.image
            if image is None or image.size == 0:
                return None

            # EasyOCR readtext returns list of (bbox, text, confidence)
            raw_results = self._reader.readtext(image)

            results: List[OCRResult] = []
            for bbox, text, confidence in raw_results:
                if not text.strip():
                    continue

                # Convert EasyOCR bbox (4 corner points) to Rect
                bounding_box = self._bbox_to_rect(bbox)

                results.append(OCRResult(
                    text=text.strip(),
                    confidence=float(confidence),
                    bounding_box=bounding_box,
                    language=self._languages[0] if self._languages else 'en'
                ))

            return results

        except Exception as e:
            logger.error(f"{LOG_PREFIX} OCR extraction failed: {e}")
            return None

    # === TEXT REGION DETECTION ===

    def detect_text_regions(self, screenshot: np.ndarray) -> List[Rect]:
        """Detect regions in a screenshot that contain text.

        Uses EasyOCR's text detection to find bounding boxes of text areas
        without performing full recognition (faster than extract_text).

        Args:
            screenshot: Full screenshot as numpy array (H x W x C, uint8).

        Returns:
            List of Rect objects indicating areas that contain text.
            Returns empty list if OCR is unavailable.
        """
        if self._reader is None:
            logger.warning(f"{LOG_PREFIX} Cannot detect text regions — reader unavailable")
            return []

        if screenshot is None or screenshot.size == 0:
            return []

        try:
            # Use EasyOCR detect method for region detection
            horizontal_list, free_list = self._reader.detect(screenshot)

            regions: List[Rect] = []

            # Process horizontal text regions
            if horizontal_list and len(horizontal_list) > 0:
                for box in horizontal_list[0]:
                    # horizontal_list boxes: [x_min, x_max, y_min, y_max]
                    if len(box) >= 4:
                        x_min, x_max, y_min, y_max = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                        regions.append(Rect(
                            x=x_min,
                            y=y_min,
                            width=max(0, x_max - x_min),
                            height=max(0, y_max - y_min)
                        ))

            # Process free-form text regions
            if free_list and len(free_list) > 0:
                for polygon in free_list[0]:
                    # Convert polygon to bounding rect
                    rect = self._polygon_to_rect(polygon)
                    if rect is not None:
                        regions.append(rect)

            return regions

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Text region detection failed: {e}")
            return []

    # === UTILITY METHODS ===

    def _bbox_to_rect(self, bbox) -> Rect:
        """Convert EasyOCR bbox (4 corner points) to Rect.

        EasyOCR returns bounding boxes as list of 4 [x, y] corner points:
        [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] (top-left, top-right, bottom-right, bottom-left)
        """
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        x_min = int(min(xs))
        y_min = int(min(ys))
        x_max = int(max(xs))
        y_max = int(max(ys))
        return Rect(x=x_min, y=y_min, width=max(0, x_max - x_min), height=max(0, y_max - y_min))

    def _polygon_to_rect(self, polygon) -> Optional[Rect]:
        """Convert a polygon (list of points) to its bounding Rect."""
        try:
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            x_min = int(min(xs))
            y_min = int(min(ys))
            x_max = int(max(xs))
            y_max = int(max(ys))
            return Rect(x=x_min, y=y_min, width=max(0, x_max - x_min), height=max(0, y_max - y_min))
        except (TypeError, ValueError, IndexError):
            return None

    def _expand_region(self, original: ScreenRegion, expanded_rect: Rect) -> ScreenRegion:
        """Create an expanded ScreenRegion from the original.

        If the expanded rect exceeds the original image bounds, clamps to available area.
        In production, this would capture a new screenshot of the expanded area.
        For now, returns the original region (caller should capture larger screenshot).
        """
        # Clamp expanded rect to image bounds
        clamped = expanded_rect.clamp(original.width, original.height)

        # If we can crop a larger area from the original image, do so
        try:
            y_start = max(0, clamped.y)
            y_end = min(original.height, clamped.y + clamped.height)
            x_start = max(0, clamped.x)
            x_end = min(original.width, clamped.x + clamped.width)

            if y_end > y_start and x_end > x_start:
                cropped_image = original.image[y_start:y_end, x_start:x_end]
                return ScreenRegion(rect=clamped, image=cropped_image)
        except (IndexError, ValueError):
            pass

        # Fallback: return original region
        return original

    def _record_metric(self, status: str) -> None:
        """Record extraction attempt metric."""
        if utl_ocr_extraction_total is not None:
            utl_ocr_extraction_total.labels(status=status).inc()

    # === STATUS ===

    @property
    def is_available(self) -> bool:
        """Whether the OCR backend is available and initialized."""
        return self._reader is not None

    @property
    def consecutive_failures(self) -> int:
        """Number of consecutive extraction failures."""
        return self._consecutive_failures

    def reset_failures(self) -> None:
        """Reset the consecutive failure counter (allows extraction to resume)."""
        self._consecutive_failures = 0
        logger.info(f"{LOG_PREFIX} Failure counter reset")


# === MAIN GUARD ===

def main():
    """Self-test entry point for OCR Module."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print(f"{LOG_PREFIX} OCR Module self-test")
    print(f"{LOG_PREFIX} EasyOCR available: {_EASYOCR_AVAILABLE}")

    # Test data model creation
    rect = Rect(x=10, y=20, width=100, height=50)
    print(f"{LOG_PREFIX} Rect: {rect}, area={rect.area}")

    expanded = rect.expanded(1.5)
    print(f"{LOG_PREFIX} Expanded 1.5x: {expanded}")

    clamped = Rect(x=-5, y=-5, width=200, height=200).clamp(150, 150)
    print(f"{LOG_PREFIX} Clamped: {clamped}")

    # Test OCRResult creation
    ocr_result = OCRResult(
        text="Hello World",
        confidence=0.95,
        bounding_box=rect,
        language="en"
    )
    print(f"{LOG_PREFIX} OCRResult: text='{ocr_result.text}', conf={ocr_result.confidence}")

    # Test ScreenRegion
    dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
    region = ScreenRegion(rect=rect, image=dummy_image)
    print(f"{LOG_PREFIX} ScreenRegion: {region.width}x{region.height}")

    # Test OCRModule instantiation (without EasyOCR reader if not installed)
    module = OCRModule(languages=['en'], gpu=False)
    print(f"{LOG_PREFIX} OCRModule available: {module.is_available}")

    # Test extract_text with dummy region (will return empty if no reader)
    results = module.extract_text(region)
    print(f"{LOG_PREFIX} extract_text result count: {len(results)}")

    # Test detect_text_regions with dummy screenshot
    regions = module.detect_text_regions(dummy_image)
    print(f"{LOG_PREFIX} detect_text_regions result count: {len(regions)}")

    # Test retry logic (force failures)
    module._consecutive_failures = 3
    results_skip = module.extract_text(region)
    assert results_skip == [], "Expected empty results after max failures"
    print(f"{LOG_PREFIX} Retry skip (after max failures): OK")

    # Reset and verify
    module.reset_failures()
    assert module.consecutive_failures == 0
    print(f"{LOG_PREFIX} Failure counter reset: OK")

    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
