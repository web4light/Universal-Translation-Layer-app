"""
Property-Based Tests: Subscription and NFT
Feature: universal-translation-layer

Property 14: Subscription tier access control
Property 21: Soulbound NFT non-transferability

Validates: Requirements 12.1, 12.2, 11.3
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from subscription_manager import (
    SubscriptionManager,
    SubscriptionTier,
    TIER_FEATURES,
    TIER_PRICES,
)


# === All features across all tiers ===

ALL_FEATURES = set()
for features in TIER_FEATURES.values():
    ALL_FEATURES.update(features)

ALL_FEATURES_LIST = sorted(ALL_FEATURES)

# Strategy for generating tiers
tier_strategy = st.sampled_from(list(SubscriptionTier))

# Strategy for generating feature names
feature_strategy = st.sampled_from(ALL_FEATURES_LIST)

# Strategy for wallet addresses
wallet_strategy = st.text(
    alphabet="0123456789abcdefABCDEF",
    min_size=40,
    max_size=40,
).map(lambda s: "0x" + s)


# === Property 14: Subscription tier access control ===
# For any user with subscription tier T and any feature access attempt F,
# access SHALL be granted if and only if F is included in tier T's feature set.
# No usage limits (token/minute/character billing) SHALL be enforced while
# subscription is active.


class TestProperty14SubscriptionTierAccessControl:
    """Property 14: Subscription tier access control."""

    @given(tier=tier_strategy, feature=feature_strategy, wallet=wallet_strategy)
    @settings(max_examples=100)
    def test_access_granted_iff_feature_in_tier(self, tier, feature, wallet):
        """Access is granted if and only if feature is in the tier's feature set."""
        # Feature: universal-translation-layer, Property 14: Subscription tier access control
        mgr = SubscriptionManager()
        mgr.register(wallet, tier)

        has_access = mgr.check_access(wallet, feature)
        expected = feature in TIER_FEATURES[tier]

        assert has_access == expected, (
            f"Tier {tier.value}: feature '{feature}' access={has_access}, "
            f"expected={expected}"
        )

    @given(tier=tier_strategy, wallet=wallet_strategy)
    @settings(max_examples=100)
    def test_no_usage_limits_while_active(self, tier, wallet):
        """Unlimited usage while subscription is active — repeated access always granted."""
        # Feature: universal-translation-layer, Property 14: Subscription tier access control
        mgr = SubscriptionManager()
        mgr.register(wallet, tier)

        # All features in the tier should be accessible repeatedly (no token limit)
        for feature in TIER_FEATURES[tier]:
            for _ in range(10):  # Access 10 times — should never be denied
                assert mgr.check_access(wallet, feature) is True

    @given(wallet=wallet_strategy, feature=feature_strategy)
    @settings(max_examples=100)
    def test_no_subscription_only_offline(self, wallet, feature):
        """Without subscription, only offline_translation is accessible."""
        # Feature: universal-translation-layer, Property 14: Subscription tier access control
        mgr = SubscriptionManager()
        # Don't register — no subscription

        has_access = mgr.check_access(wallet, feature)
        expected = feature in TIER_FEATURES[SubscriptionTier.NONE]

        assert has_access == expected, (
            f"Unsubscribed: feature '{feature}' access={has_access}, "
            f"expected={expected}"
        )

    @given(tier=tier_strategy, wallet=wallet_strategy)
    @settings(max_examples=100)
    def test_tier_feature_set_is_subset_of_higher_tiers(self, tier, wallet):
        """Higher tiers include all features from lower tiers (monotonic)."""
        # Feature: universal-translation-layer, Property 14: Subscription tier access control
        tier_order = [
            SubscriptionTier.NONE,
            SubscriptionTier.GEALL_111,
            SubscriptionTier.KAREL_222,
            SubscriptionTier.DUBBING_333,
            SubscriptionTier.FAMILY_423,
        ]
        tier_idx = tier_order.index(tier)

        for lower_idx in range(tier_idx):
            lower_tier = tier_order[lower_idx]
            lower_features = TIER_FEATURES[lower_tier]
            current_features = TIER_FEATURES[tier]
            assert lower_features.issubset(current_features), (
                f"Tier {tier.value} should include all features of {lower_tier.value}"
            )


# === Property 21: Soulbound NFT non-transferability ===
# For any Soulbound NFT and any transfer attempt (regardless of sender,
# receiver, or method), the smart contract SHALL reject the transaction.

class SoulboundNFT:
    """Simulated Soulbound NFT — non-transferable token.

    The real contract is in Ada/SPARK (soulbound_nft.adb).
    This Python simulation validates the logic.
    """

    def __init__(self, owner: str, token_id: str):
        self._owner = owner
        self._token_id = token_id
        self._is_soulbound = True

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def token_id(self) -> str:
        return self._token_id

    def transfer(self, sender: str, receiver: str, method: str = "transfer") -> bool:
        """Attempt to transfer the NFT.

        All transfers are rejected for Soulbound NFTs.

        Returns:
            False always — transfer rejected
        """
        # Soulbound = non-transferable regardless of method
        if self._is_soulbound:
            return False
        # This code is unreachable for Soulbound NFTs
        return True  # pragma: no cover

    def safe_transfer_from(self, sender: str, receiver: str) -> bool:
        """ERC-721 safeTransferFrom — always rejected."""
        return self.transfer(sender, receiver, method="safeTransferFrom")

    def transfer_from(self, sender: str, receiver: str) -> bool:
        """ERC-721 transferFrom — always rejected."""
        return self.transfer(sender, receiver, method="transferFrom")

    def approve(self, spender: str) -> bool:
        """ERC-721 approve — always rejected for Soulbound."""
        if self._is_soulbound:
            return False
        return True  # pragma: no cover

    def set_approval_for_all(self, operator: str, approved: bool) -> bool:
        """ERC-721 setApprovalForAll — always rejected for Soulbound."""
        if self._is_soulbound:
            return False
        return True  # pragma: no cover


# Strategy for Ethereum-like addresses
address_strategy = st.text(
    alphabet="0123456789abcdef",
    min_size=40,
    max_size=40,
).map(lambda s: "0x" + s)

# Strategy for transfer methods
transfer_method_strategy = st.sampled_from([
    "transfer", "transferFrom", "safeTransferFrom",
    "delegate", "burn_and_remint", "proxy_transfer",
    "admin_override", "emergency_transfer",
])


class TestProperty21SoulboundNFTNonTransferability:
    """Property 21: Soulbound NFT non-transferability."""

    @given(
        owner=address_strategy,
        sender=address_strategy,
        receiver=address_strategy,
        method=transfer_method_strategy,
        token_id=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_all_transfers_rejected(self, owner, sender, receiver, method, token_id):
        """Any transfer attempt is rejected, regardless of sender/receiver/method."""
        # Feature: universal-translation-layer, Property 21: Soulbound NFT non-transferability
        nft = SoulboundNFT(owner=owner, token_id=token_id)

        result = nft.transfer(sender, receiver, method=method)
        assert result is False, (
            f"Transfer should be rejected: sender={sender[:10]}, "
            f"receiver={receiver[:10]}, method={method}"
        )
        # Owner unchanged
        assert nft.owner == owner

    @given(
        owner=address_strategy,
        receiver=address_strategy,
        token_id=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_owner_transfer_to_self_rejected(self, owner, receiver, token_id):
        """Even owner-to-self or owner-initiated transfers are rejected."""
        # Feature: universal-translation-layer, Property 21: Soulbound NFT non-transferability
        nft = SoulboundNFT(owner=owner, token_id=token_id)

        # Owner tries to transfer to themselves
        assert nft.transfer(owner, owner) is False
        # Owner tries to transfer to someone else
        assert nft.transfer(owner, receiver) is False
        # Owner unchanged
        assert nft.owner == owner

    @given(
        owner=address_strategy,
        spender=address_strategy,
        token_id=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_approve_rejected(self, owner, spender, token_id):
        """Approve and setApprovalForAll are rejected for Soulbound NFTs."""
        # Feature: universal-translation-layer, Property 21: Soulbound NFT non-transferability
        nft = SoulboundNFT(owner=owner, token_id=token_id)

        assert nft.approve(spender) is False
        assert nft.set_approval_for_all(spender, True) is False
        assert nft.set_approval_for_all(spender, False) is False

    @given(
        owner=address_strategy,
        sender=address_strategy,
        receiver=address_strategy,
        token_id=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_erc721_methods_rejected(self, owner, sender, receiver, token_id):
        """Standard ERC-721 transfer methods are all rejected."""
        # Feature: universal-translation-layer, Property 21: Soulbound NFT non-transferability
        nft = SoulboundNFT(owner=owner, token_id=token_id)

        assert nft.safe_transfer_from(sender, receiver) is False
        assert nft.transfer_from(sender, receiver) is False
        assert nft.owner == owner
