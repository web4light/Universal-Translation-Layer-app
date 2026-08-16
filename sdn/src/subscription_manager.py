"""Subscription Manager for the Universal Translation Layer.

Implements tier-based access control, unlimited usage enforcement,
graceful degradation to offline-only mode on expiration, and MiniMe
token payment integration via Soulbound NFT wallet.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from prometheus_client import Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
utl_subscription_active_users = Gauge(
    "utl_subscription_active_users",
    "Number of users with active subscriptions",
)
utl_subscription_tier_distribution = Gauge(
    "utl_subscription_tier_distribution",
    "Number of users per subscription tier",
    ["tier"],
)


class SubscriptionTier(Enum):
    """Subscription tier pricing and feature grouping.

    Each tier unlocks a specific set of features at a fixed CZK/month price.
    """

    GEALL_111 = 111  # Geall AI assistant, 1 device
    KAREL_222 = 222  # Voice translation + voice clone
    DUBBING_333 = 333  # Stream dubbing (all streaming services)
    FAMILY_423 = 423  # All features, unlimited devices


class Feature(Enum):
    """Features gated by subscription tiers."""

    GEALL_AGENT = "geall_agent"
    TEXT_TRANSLATION = "text_translation"
    VOICE_TRANSLATION = "voice_translation"
    VOICE_CLONE = "voice_clone"
    STREAM_DUBBING = "stream_dubbing"
    MESH_PARTICIPATION = "mesh_participation"
    OFFLINE_LOCAL_MODEL = "offline_local_model"


# Feature sets per tier (Requirement 12.1)
TIER_FEATURES: dict[SubscriptionTier, set[Feature]] = {
    SubscriptionTier.GEALL_111: {
        Feature.GEALL_AGENT,
        Feature.TEXT_TRANSLATION,
        Feature.OFFLINE_LOCAL_MODEL,
    },
    SubscriptionTier.KAREL_222: {
        Feature.GEALL_AGENT,
        Feature.TEXT_TRANSLATION,
        Feature.VOICE_TRANSLATION,
        Feature.VOICE_CLONE,
        Feature.OFFLINE_LOCAL_MODEL,
    },
    SubscriptionTier.DUBBING_333: {
        Feature.GEALL_AGENT,
        Feature.TEXT_TRANSLATION,
        Feature.VOICE_TRANSLATION,
        Feature.VOICE_CLONE,
        Feature.STREAM_DUBBING,
        Feature.MESH_PARTICIPATION,
        Feature.OFFLINE_LOCAL_MODEL,
    },
    SubscriptionTier.FAMILY_423: {
        Feature.GEALL_AGENT,
        Feature.TEXT_TRANSLATION,
        Feature.VOICE_TRANSLATION,
        Feature.VOICE_CLONE,
        Feature.STREAM_DUBBING,
        Feature.MESH_PARTICIPATION,
        Feature.OFFLINE_LOCAL_MODEL,
    },
}

# Maximum devices per tier
TIER_MAX_DEVICES: dict[SubscriptionTier, Optional[int]] = {
    SubscriptionTier.GEALL_111: 1,
    SubscriptionTier.KAREL_222: 1,
    SubscriptionTier.DUBBING_333: 1,
    SubscriptionTier.FAMILY_423: None,  # Unlimited
}

# Features available in degraded (offline-only) mode after expiration
DEGRADED_FEATURES: set[Feature] = {Feature.OFFLINE_LOCAL_MODEL}


@dataclass
class SubscriptionState:
    """User subscription state managed via Soulbound NFT wallet."""

    wallet_address: str
    tier: SubscriptionTier
    active: bool
    expires_at: int
    devices: list[str] = field(default_factory=list)
    payment_token: str = ""

    def __post_init__(self):
        if self.expires_at < 0:
            raise ValueError("expires_at must be >= 0")


class PaymentError(Exception):
    """Raised when a MiniMe token payment operation fails."""


class MiniMePaymentClient:
    """MiniMe token payment integration via Soulbound NFT wallet.

    Provides the interface for subscription payment processing using
    blockchain-based MiniMe tokens bound to the user's Soulbound NFT
    identity.

    This is a stub/interface for the blockchain interaction layer.
    Actual implementation connects to the Soulbound NFT smart contract.
    """

    def __init__(self, contract_address: str = ""):
        self._contract_address = contract_address

    def verify_wallet(self, wallet_address: str) -> bool:
        """Verify that the wallet address is bound to a valid Soulbound NFT.

        Args:
            wallet_address: Ethereum wallet address derived from biometrics.

        Returns:
            True if the wallet holds a valid, non-transferable Soulbound NFT.
        """
        if not wallet_address:
            return False
        # Stub: in production, queries the NFT smart contract
        return True

    def process_payment(
        self, wallet_address: str, tier: SubscriptionTier
    ) -> bool:
        """Process a MiniMe token payment for a subscription tier.

        Args:
            wallet_address: Payer's Soulbound NFT wallet.
            tier: Subscription tier to pay for.

        Returns:
            True if payment was successful.

        Raises:
            PaymentError: If the payment transaction fails.
        """
        if not self.verify_wallet(wallet_address):
            raise PaymentError(
                f"Invalid wallet address: {wallet_address}"
            )
        # Stub: in production, initiates MiniMe token transfer
        logger.info(
            "Payment processed: wallet=%s, tier=%s, amount=%d CZK",
            wallet_address,
            tier.name,
            tier.value,
        )
        return True

    def check_balance(self, wallet_address: str) -> float:
        """Check the MiniMe token balance of a wallet.

        Args:
            wallet_address: Wallet to check.

        Returns:
            Current MiniMe token balance.
        """
        if not wallet_address:
            return 0.0
        # Stub: in production, queries token contract
        return float("inf")


class SubscriptionManager:
    """Manages subscription tiers, access control, and payment.

    Enforces unlimited usage while active (Req 12.2), graceful degradation
    to offline-only Local_Model on expiration (Req 12.5), and MiniMe token
    payment via Soulbound NFT wallet (Req 12.4).

    Usage:
        manager = SubscriptionManager()
        state = manager.activate_subscription(wallet, SubscriptionTier.KAREL_222)
        if manager.check_access(state, Feature.VOICE_TRANSLATION):
            # proceed with voice translation
            ...
    """

    def __init__(self, payment_client: Optional[MiniMePaymentClient] = None):
        self._payment_client = payment_client or MiniMePaymentClient()
        self._users: dict[str, SubscriptionState] = {}
        self._update_metrics()

    def activate_subscription(
        self,
        wallet_address: str,
        tier: SubscriptionTier,
        duration_days: int = 30,
        device_id: str = "",
    ) -> SubscriptionState:
        """Activate or renew a subscription for a user.

        Args:
            wallet_address: User's Soulbound NFT wallet address.
            tier: Desired subscription tier.
            duration_days: Subscription duration in days (default 30).
            device_id: Device identifier to register.

        Returns:
            Activated SubscriptionState.

        Raises:
            PaymentError: If payment fails.
        """
        self._payment_client.process_payment(wallet_address, tier)

        expires_at = int(time.time()) + (duration_days * 86400)
        devices = [device_id] if device_id else []

        state = SubscriptionState(
            wallet_address=wallet_address,
            tier=tier,
            active=True,
            expires_at=expires_at,
            devices=devices,
            payment_token=self._payment_client._contract_address,
        )

        self._users[wallet_address] = state
        self._update_metrics()
        logger.info(
            "Subscription activated: wallet=%s, tier=%s, expires=%d",
            wallet_address,
            tier.name,
            expires_at,
        )
        return state

    def check_access(self, state: SubscriptionState, feature: Feature) -> bool:
        """Check if a user has access to a specific feature.

        Access logic:
        - If subscription is active and not expired: grant iff feature in tier's set
        - If subscription is expired: only OFFLINE_LOCAL_MODEL is accessible
        - No per-token/minute/character billing — unlimited usage while active

        Args:
            state: User's current subscription state.
            feature: Feature being accessed.

        Returns:
            True if access is granted.
        """
        if not self._is_subscription_valid(state):
            # Graceful degradation: offline-only Local_Model (Req 12.5)
            return feature in DEGRADED_FEATURES

        # Unlimited usage while subscription active (Req 12.2)
        tier_features = TIER_FEATURES.get(state.tier, set())
        return feature in tier_features

    def check_device_limit(self, state: SubscriptionState, device_id: str) -> bool:
        """Check if a device can be added to the subscription.

        FAMILY_423 allows unlimited devices. Other tiers have limits.

        Args:
            state: User's subscription state.
            device_id: Device attempting to register.

        Returns:
            True if the device is allowed (already registered or within limit).
        """
        if device_id in state.devices:
            return True

        max_devices = TIER_MAX_DEVICES.get(state.tier, 1)
        if max_devices is None:
            # Unlimited devices (FAMILY_423)
            return True

        return len(state.devices) < max_devices

    def register_device(self, state: SubscriptionState, device_id: str) -> bool:
        """Register a device to the subscription.

        Args:
            state: User's subscription state.
            device_id: Device to register.

        Returns:
            True if device was registered successfully.
        """
        if device_id in state.devices:
            return True

        if not self.check_device_limit(state, device_id):
            logger.warning(
                "Device limit reached: wallet=%s, tier=%s, devices=%d",
                state.wallet_address,
                state.tier.name,
                len(state.devices),
            )
            return False

        state.devices.append(device_id)
        return True

    def get_subscription(self, wallet_address: str) -> Optional[SubscriptionState]:
        """Get current subscription state for a wallet.

        Args:
            wallet_address: User's wallet address.

        Returns:
            SubscriptionState or None if not found.
        """
        return self._users.get(wallet_address)

    def get_available_features(self, state: SubscriptionState) -> set[Feature]:
        """Get all features available to a user given their subscription state.

        Args:
            state: User's subscription state.

        Returns:
            Set of accessible features.
        """
        if not self._is_subscription_valid(state):
            return DEGRADED_FEATURES.copy()

        return TIER_FEATURES.get(state.tier, set()).copy()

    def is_degraded(self, state: SubscriptionState) -> bool:
        """Check if the user is in degraded (offline-only) mode.

        Degraded mode activates when subscription expires.

        Args:
            state: User's subscription state.

        Returns:
            True if user is in degraded mode.
        """
        return not self._is_subscription_valid(state)

    def _is_subscription_valid(self, state: SubscriptionState) -> bool:
        """Check if subscription is both active and not expired.

        Args:
            state: User's subscription state.

        Returns:
            True if subscription is currently valid.
        """
        if not state.active:
            return False
        return state.expires_at > int(time.time())

    def _update_metrics(self) -> None:
        """Update Prometheus metrics for subscription state."""
        active_count = sum(
            1 for s in self._users.values() if self._is_subscription_valid(s)
        )
        utl_subscription_active_users.set(active_count)

        # Reset all tier distribution to zero first
        for tier in SubscriptionTier:
            utl_subscription_tier_distribution.labels(tier=tier.name).set(0)

        # Count active users per tier
        for state in self._users.values():
            if self._is_subscription_valid(state):
                utl_subscription_tier_distribution.labels(
                    tier=state.tier.name
                ).inc()
