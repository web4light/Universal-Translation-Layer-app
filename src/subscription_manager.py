#!/usr/bin/env python3
"""
Subscription Manager — Tier Access Control
UTL Subscription and Payment Logic

Manages subscription tiers, access control, and graceful degradation.
No per-token billing. Pay month, use unlimited.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
Author: Pan Jeskyne
"""

import time
import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set
from prometheus_client import Gauge, Counter

# === PROMETHEUS METRICS ===

utl_subscription_active_users = Gauge(
    'utl_subscription_active_users',
    'Number of active subscribers'
)
utl_subscription_tier_distribution = Gauge(
    'utl_subscription_tier_distribution',
    'Users per subscription tier',
    ['tier']
)

# === SUBSCRIPTION TIERS ===


class SubscriptionTier(Enum):
    """Available subscription plans."""
    NONE = "none"             # No subscription — offline only
    GEALL_111 = "geall_111"  # 111 CZK/month: AI assistant, 1 device
    KAREL_222 = "karel_222"  # 222 CZK/month: Real-time translation + voice clone
    DUBBING_333 = "dubbing_333"  # 333 CZK/month: Stream dubbing
    FAMILY_423 = "family_423"    # 423 CZK/month: Everything, whole household


# Features available per tier
TIER_FEATURES: dict = {
    SubscriptionTier.NONE: {"offline_translation"},
    SubscriptionTier.GEALL_111: {
        "offline_translation", "geall_assistant", "text_interception",
        "overlay_rendering"
    },
    SubscriptionTier.KAREL_222: {
        "offline_translation", "geall_assistant", "text_interception",
        "overlay_rendering", "voice_translation", "voice_clone",
        "realtime_mode", "quality_mode"
    },
    SubscriptionTier.DUBBING_333: {
        "offline_translation", "geall_assistant", "text_interception",
        "overlay_rendering", "voice_translation", "voice_clone",
        "realtime_mode", "quality_mode", "stream_dubbing",
        "speaker_separation", "smart_tv"
    },
    SubscriptionTier.FAMILY_423: {
        "offline_translation", "geall_assistant", "text_interception",
        "overlay_rendering", "voice_translation", "voice_clone",
        "realtime_mode", "quality_mode", "stream_dubbing",
        "speaker_separation", "smart_tv", "unlimited_devices",
        "family_sharing", "mesh_priority"
    },
}

# Prices in CZK
TIER_PRICES: dict = {
    SubscriptionTier.NONE: 0,
    SubscriptionTier.GEALL_111: 111,
    SubscriptionTier.KAREL_222: 222,
    SubscriptionTier.DUBBING_333: 333,
    SubscriptionTier.FAMILY_423: 423,
}


# === SUBSCRIPTION STATE ===


@dataclass
class SubscriptionState:
    """Current subscription state for a user."""
    tier: SubscriptionTier
    wallet_address: str
    activated_at: int         # Unix timestamp
    expires_at: int           # Unix timestamp
    devices_count: int = 1
    is_active: bool = True


# === SUBSCRIPTION MANAGER ===

class SubscriptionManager:
    """
    Manages subscription tiers and feature access control.

    Principles:
    - No per-token, per-minute, or per-character billing
    - Unlimited usage within tier
    - Graceful degradation to offline-only when expired
    - MiniMe token payment via Soulbound NFT wallet
    - Automatic price reduction as mesh grows
    """

    def __init__(self):
        """Initialize subscription manager."""
        self._subscriptions: dict = {}  # wallet_address -> SubscriptionState
        print("[SUBSCRIPTION] Manager initialized")

    def register(self, wallet_address: str, tier: SubscriptionTier,
                 duration_days: int = 30) -> SubscriptionState:
        """
        Register or update a subscription.

        Args:
            wallet_address: User's Soulbound NFT wallet
            tier: Subscription tier
            duration_days: Subscription duration (default 30 days)

        Returns:
            SubscriptionState for the user
        """
        now = int(time.time())
        state = SubscriptionState(
            tier=tier,
            wallet_address=wallet_address,
            activated_at=now,
            expires_at=now + (duration_days * 86400),
            is_active=True
        )
        self._subscriptions[wallet_address] = state

        utl_subscription_active_users.set(len(self._subscriptions))
        utl_subscription_tier_distribution.labels(tier=tier.value).inc()

        print(f"[SUBSCRIPTION] Registered: {wallet_address[:10]}... "
              f"tier={tier.value} for {duration_days} days")
        return state

    def check_access(self, wallet_address: str, feature: str) -> bool:
        """
        Check if user has access to a specific feature.

        Args:
            wallet_address: User's wallet
            feature: Feature name to check

        Returns:
            True if access granted, False otherwise
        """
        state = self._subscriptions.get(wallet_address)

        if state is None:
            # No subscription — only offline translation
            return feature in TIER_FEATURES[SubscriptionTier.NONE]

        # Check expiration
        if time.time() > state.expires_at:
            state.is_active = False
            print(f"[SUBSCRIPTION] Expired: {wallet_address[:10]}...")
            return feature in TIER_FEATURES[SubscriptionTier.NONE]

        # Check feature availability in tier
        allowed_features = TIER_FEATURES.get(state.tier, set())
        return feature in allowed_features

    def get_tier(self, wallet_address: str) -> SubscriptionTier:
        """Get current tier for a wallet address."""
        state = self._subscriptions.get(wallet_address)
        if state is None or not state.is_active:
            return SubscriptionTier.NONE
        if time.time() > state.expires_at:
            return SubscriptionTier.NONE
        return state.tier

    def get_available_features(self, wallet_address: str) -> Set[str]:
        """Get all features available to a user."""
        tier = self.get_tier(wallet_address)
        return TIER_FEATURES.get(tier, set())

    def is_family_plan(self, wallet_address: str) -> bool:
        """Check if user is on family plan (unlimited devices)."""
        return self.get_tier(wallet_address) == SubscriptionTier.FAMILY_423

    def degrade_gracefully(self, wallet_address: str):
        """
        Degrade to offline-only mode when subscription expires.

        User keeps basic offline translation but loses mesh,
        dubbing, voice clone, and AI assistant features.
        """
        state = self._subscriptions.get(wallet_address)
        if state:
            state.is_active = False
            print(f"[SUBSCRIPTION] Degraded to offline: {wallet_address[:10]}...")
            print("[SUBSCRIPTION] Restore subscription to regain full access")

    def calculate_mesh_discount(self, total_mesh_nodes: int) -> float:
        """
        Calculate price reduction based on mesh size.

        More users = more mesh capacity = lower operational costs = discount.

        Args:
            total_mesh_nodes: Total active nodes in mesh

        Returns:
            Discount multiplier (0.0 to 1.0, where 0.8 = 20% discount)
        """
        if total_mesh_nodes < 100:
            return 1.0  # No discount
        elif total_mesh_nodes < 1000:
            return 0.9  # 10% discount
        elif total_mesh_nodes < 10000:
            return 0.8  # 20% discount
        else:
            return 0.7  # 30% max discount

    @property
    def active_count(self) -> int:
        """Number of active subscriptions."""
        return sum(1 for s in self._subscriptions.values()
                   if s.is_active and time.time() < s.expires_at)


# === ENTRY POINT ===

def main():
    """Test subscription manager."""
    print("[SUBSCRIPTION] Testing subscription manager...\n")

    mgr = SubscriptionManager()

    # Register test users
    user1 = "0x7B7AC386f34d853df35a94d5CeCaEb3609E7d2e2"
    user2 = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"

    mgr.register(user1, SubscriptionTier.FAMILY_423)
    mgr.register(user2, SubscriptionTier.KAREL_222)

    # Check access
    print(f"\n  User1 (Family 423):")
    print(f"    voice_translation: {mgr.check_access(user1, 'voice_translation')}")
    print(f"    stream_dubbing:    {mgr.check_access(user1, 'stream_dubbing')}")
    print(f"    unlimited_devices: {mgr.check_access(user1, 'unlimited_devices')}")

    print(f"\n  User2 (Karel 222):")
    print(f"    voice_translation: {mgr.check_access(user2, 'voice_translation')}")
    print(f"    stream_dubbing:    {mgr.check_access(user2, 'stream_dubbing')}")
    print(f"    unlimited_devices: {mgr.check_access(user2, 'unlimited_devices')}")

    # Mesh discount
    print(f"\n  Mesh discount (50 nodes):    {mgr.calculate_mesh_discount(50)}")
    print(f"  Mesh discount (500 nodes):   {mgr.calculate_mesh_discount(500)}")
    print(f"  Mesh discount (5000 nodes):  {mgr.calculate_mesh_discount(5000)}")
    print(f"  Mesh discount (50000 nodes): {mgr.calculate_mesh_discount(50000)}")

    print(f"\n  Active subscriptions: {mgr.active_count}")
    print("\n[SUBSCRIPTION] Test complete")


if __name__ == '__main__':
    main()
