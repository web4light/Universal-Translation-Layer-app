"""
Wire Geall AI Assistant — Universal Translation Layer (UTL)

Integration module: connects Geall AI assistant functionality
with mesh network, translation, and privacy layers.

Geall = AI asistent integrovaný v Karel IV. platformě
Komunikuje přes Bifrost (Ada/SPARK) bridge s Gemini API.

Autor: Pan Jeskyně
Asistent: Kiro
"""

import logging
import time
from typing import Optional, Dict

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[GEALL]"

# === LOCAL IMPORTS ===

from translation_engine import TranslationEngine
from privacy_protocol import PrivacyProtocol
from subscription_manager import SubscriptionManager, SubscriptionTier

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Histogram

    utl_geall_queries_total = Counter(
        'utl_geall_queries_total',
        'Total Geall AI assistant queries',
        ['status']
    )

    utl_geall_latency_seconds = Histogram(
        'utl_geall_latency_seconds',
        'Geall query processing latency',
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    )
except ImportError:
    utl_geall_queries_total = None
    utl_geall_latency_seconds = None


# === GEALL ASSISTANT CLASS ===

class GeallAssistant:
    """Geall AI Assistant — integrated in Karel IV. platform.

    Provides multilingual AI assistant capabilities:
    - Query processing with privacy protection
    - Translation of responses to user's language
    - Subscription-gated access (PERSONAL tier and above)
    - Zero persistence for all queries (privacy protocol)
    """

    def __init__(self, target_lang: str = "cs"):
        self._target_lang = target_lang
        self._translator = TranslationEngine()
        self._privacy = PrivacyProtocol()
        self._subscriptions = SubscriptionManager()
        self._query_count = 0

        logger.info(f"{LOG_PREFIX} Geall Assistant wired (lang={target_lang})")

    def query(self, user_id: str, question: str,
              response_lang: str = None) -> Optional[str]:
        """Process a Geall AI query.

        Args:
            user_id: User identifier (for access check)
            question: User's question text
            response_lang: Language for response (default: target_lang)

        Returns:
            AI response text, or None if access denied
        """
        start = time.perf_counter()

        # Check subscription access
        if not self._subscriptions.check_access(user_id, "assistant"):
            logger.info(f"{LOG_PREFIX} Access denied for {user_id}")
            if utl_geall_queries_total:
                utl_geall_queries_total.labels(status="denied").inc()
            return None

        try:
            # Process query (in production: calls Bifrost → Gemini)
            # For now: echo with translation
            lang = response_lang or self._target_lang

            # Translate if needed
            result = self._translator.translate(
                text=question,
                source_lang="auto",
                target_lang=lang,
            )

            self._query_count += 1
            response = f"[Geall] {result.translated_text}"

            elapsed = time.perf_counter() - start
            if utl_geall_latency_seconds:
                utl_geall_latency_seconds.observe(elapsed)
            if utl_geall_queries_total:
                utl_geall_queries_total.labels(status="success").inc()

            # Privacy: don't persist the query
            self._privacy.execute_purge()

            return response

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Query error: {e}")
            if utl_geall_queries_total:
                utl_geall_queries_total.labels(status="error").inc()
            return None

    @property
    def query_count(self) -> int:
        return self._query_count

    def get_status(self) -> Dict:
        return {
            "target_lang": self._target_lang,
            "queries_processed": self._query_count,
            "privacy": self._privacy.get_status(),
        }


# === MAIN GUARD ===

def main():
    """Self-test."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"{LOG_PREFIX} Geall Assistant wiring self-test")

    geall = GeallAssistant(target_lang="cs")

    # Activate a test user
    geall._subscriptions.activate("test_user", SubscriptionTier.PERSONAL)

    # Query with access
    response = geall.query("test_user", "What is the weather?")
    print(f"{LOG_PREFIX} Response: {response}")
    assert response is not None

    # Query without access
    response = geall.query("nobody", "Hello")
    assert response is None
    print(f"{LOG_PREFIX} Access denied for unsubscribed user: OK")

    print(f"{LOG_PREFIX} Status: {geall.get_status()}")
    print(f"{LOG_PREFIX} Done.")


if __name__ == '__main__':
    main()
