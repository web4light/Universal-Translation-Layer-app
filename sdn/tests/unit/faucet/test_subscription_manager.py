#!/usr/bin/env python3
"""Unit tests for the SubscriptionManager module.

Verifies tier access control logic, unlimited usage enforcement,
graceful degradation, and MiniMe payment integration.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import sys
import time
import unittest
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, "/home/pj/faucet/src")

from subscription_manager import (
    SubscriptionManager,
    SubscriptionState,
    SubscriptionTier,
    Feature,
    MiniMePaymentClient,
    PaymentError,
    TIER_FEATURES,
    TIER_MAX_DEVICES,
    DEGRADED_FEATURES,
)


class TestSubscriptionTier(unittest.TestCase):
    """Tests for SubscriptionTier enum."""

    def test_tier_values(self):
        """Each tier should have the correct CZK/month value."""
        self.assertEqual(SubscriptionTier.GEALL_111.value, 111)
        self.assertEqual(SubscriptionTier.KAREL_222.value, 222)
        self.assertEqual(SubscriptionTier.DUBBING_333.value, 333)
        self.assertEqual(SubscriptionTier.FAMILY_423.value, 423)

    def test_tier_count(self):
        """There should be exactly 4 tiers."""
        self.assertEqual(len(SubscriptionTier), 4)


class TestSubscriptionState(unittest.TestCase):
    """Tests for SubscriptionState dataclass."""

    def test_valid_creation(self):
        """SubscriptionState should accept valid parameters."""
        state = SubscriptionState(
            wallet_address="0xABC123",
            tier=SubscriptionTier.KAREL_222,
            active=True,
            expires_at=int(time.time()) + 86400,
            devices=["device_1"],
            payment_token="0xTOKEN",
        )
        self.assertEqual(state.wallet_address, "0xABC123")
        self.assertEqual(state.tier, SubscriptionTier.KAREL_222)
        self.assertTrue(state.active)
        self.assertEqual(state.devices, ["device_1"])

    def test_negative_expires_at_raises(self):
        """expires_at < 0 should raise ValueError."""
        with self.assertRaises(ValueError):
            SubscriptionState(
                wallet_address="0x123",
                tier=SubscriptionTier.GEALL_111,
                active=True,
                expires_at=-1,
            )

    def test_zero_expires_at_allowed(self):
        """expires_at == 0 is valid (means already expired at epoch)."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.GEALL_111,
            active=True,
            expires_at=0,
        )
        self.assertEqual(state.expires_at, 0)

    def test_default_devices_empty(self):
        """Default devices list should be empty."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.GEALL_111,
            active=True,
            expires_at=9999999999,
        )
        self.assertEqual(state.devices, [])


class TestTierFeatures(unittest.TestCase):
    """Tests for tier-to-feature mapping (Req 12.1)."""

    def test_geall_111_features(self):
        """GEALL_111 should include AI assistant and text translation."""
        features = TIER_FEATURES[SubscriptionTier.GEALL_111]
        self.assertIn(Feature.GEALL_AGENT, features)
        self.assertIn(Feature.TEXT_TRANSLATION, features)
        self.assertIn(Feature.OFFLINE_LOCAL_MODEL, features)
        # Should NOT include voice/dubbing features
        self.assertNotIn(Feature.VOICE_TRANSLATION, features)
        self.assertNotIn(Feature.VOICE_CLONE, features)
        self.assertNotIn(Feature.STREAM_DUBBING, features)

    def test_karel_222_features(self):
        """KAREL_222 should include voice translation and clone."""
        features = TIER_FEATURES[SubscriptionTier.KAREL_222]
        self.assertIn(Feature.VOICE_TRANSLATION, features)
        self.assertIn(Feature.VOICE_CLONE, features)
        self.assertIn(Feature.GEALL_AGENT, features)
        self.assertNotIn(Feature.STREAM_DUBBING, features)

    def test_dubbing_333_features(self):
        """DUBBING_333 should include stream dubbing and mesh."""
        features = TIER_FEATURES[SubscriptionTier.DUBBING_333]
        self.assertIn(Feature.STREAM_DUBBING, features)
        self.assertIn(Feature.MESH_PARTICIPATION, features)
        self.assertIn(Feature.VOICE_TRANSLATION, features)
        self.assertIn(Feature.VOICE_CLONE, features)

    def test_family_423_has_all_features(self):
        """FAMILY_423 should include ALL features."""
        family_features = TIER_FEATURES[SubscriptionTier.FAMILY_423]
        for feature in Feature:
            self.assertIn(feature, family_features)

    def test_higher_tier_is_superset(self):
        """Each higher tier should include all features of lower tiers."""
        geall = TIER_FEATURES[SubscriptionTier.GEALL_111]
        karel = TIER_FEATURES[SubscriptionTier.KAREL_222]
        dubbing = TIER_FEATURES[SubscriptionTier.DUBBING_333]
        family = TIER_FEATURES[SubscriptionTier.FAMILY_423]

        self.assertTrue(geall.issubset(karel))
        self.assertTrue(karel.issubset(dubbing))
        self.assertTrue(dubbing.issubset(family))


class TestCheckAccess(unittest.TestCase):
    """Tests for SubscriptionManager.check_access (Req 12.1, 12.2)."""

    def setUp(self):
        self.manager = SubscriptionManager()

    def test_active_subscription_grants_tier_features(self):
        """Active subscription should grant access to all tier features."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.KAREL_222,
            active=True,
            expires_at=int(time.time()) + 86400,
        )
        self.assertTrue(
            self.manager.check_access(state, Feature.VOICE_TRANSLATION)
        )
        self.assertTrue(
            self.manager.check_access(state, Feature.VOICE_CLONE)
        )
        self.assertTrue(
            self.manager.check_access(state, Feature.GEALL_AGENT)
        )

    def test_active_subscription_denies_higher_tier_features(self):
        """Active subscription should NOT grant features from higher tiers."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.GEALL_111,
            active=True,
            expires_at=int(time.time()) + 86400,
        )
        self.assertFalse(
            self.manager.check_access(state, Feature.VOICE_TRANSLATION)
        )
        self.assertFalse(
            self.manager.check_access(state, Feature.STREAM_DUBBING)
        )

    def test_unlimited_usage_no_counters(self):
        """Access should be granted unlimited times with no counters (Req 12.2)."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.DUBBING_333,
            active=True,
            expires_at=int(time.time()) + 86400,
        )
        # Call check_access many times — should always succeed
        for _ in range(1000):
            self.assertTrue(
                self.manager.check_access(state, Feature.STREAM_DUBBING)
            )

    def test_expired_subscription_degraded_mode(self):
        """Expired subscription should only allow offline local model (Req 12.5)."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.FAMILY_423,
            active=True,
            expires_at=int(time.time()) - 1,  # Already expired
        )
        # Offline model accessible in degraded mode
        self.assertTrue(
            self.manager.check_access(state, Feature.OFFLINE_LOCAL_MODEL)
        )
        # All other features denied
        self.assertFalse(
            self.manager.check_access(state, Feature.VOICE_TRANSLATION)
        )
        self.assertFalse(
            self.manager.check_access(state, Feature.STREAM_DUBBING)
        )
        self.assertFalse(
            self.manager.check_access(state, Feature.GEALL_AGENT)
        )

    def test_inactive_subscription_degraded_mode(self):
        """Inactive subscription (active=False) should degrade to offline-only."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.FAMILY_423,
            active=False,
            expires_at=int(time.time()) + 86400,
        )
        self.assertTrue(
            self.manager.check_access(state, Feature.OFFLINE_LOCAL_MODEL)
        )
        self.assertFalse(
            self.manager.check_access(state, Feature.VOICE_TRANSLATION)
        )


class TestGracefulDegradation(unittest.TestCase):
    """Tests for graceful degradation behavior (Req 12.5)."""

    def setUp(self):
        self.manager = SubscriptionManager()

    def test_is_degraded_on_expired(self):
        """is_degraded should return True when subscription is expired."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.KAREL_222,
            active=True,
            expires_at=int(time.time()) - 100,
        )
        self.assertTrue(self.manager.is_degraded(state))

    def test_is_degraded_on_inactive(self):
        """is_degraded should return True when active=False."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.KAREL_222,
            active=False,
            expires_at=int(time.time()) + 86400,
        )
        self.assertTrue(self.manager.is_degraded(state))

    def test_not_degraded_when_valid(self):
        """is_degraded should return False when subscription is valid."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.KAREL_222,
            active=True,
            expires_at=int(time.time()) + 86400,
        )
        self.assertFalse(self.manager.is_degraded(state))

    def test_degraded_features_only_offline(self):
        """Degraded mode should only expose OFFLINE_LOCAL_MODEL."""
        self.assertEqual(DEGRADED_FEATURES, {Feature.OFFLINE_LOCAL_MODEL})

    def test_get_available_features_degraded(self):
        """get_available_features should return only offline model when degraded."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.FAMILY_423,
            active=True,
            expires_at=0,  # Long expired
        )
        features = self.manager.get_available_features(state)
        self.assertEqual(features, {Feature.OFFLINE_LOCAL_MODEL})

    def test_get_available_features_active(self):
        """get_available_features should return full tier set when active."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.DUBBING_333,
            active=True,
            expires_at=int(time.time()) + 86400,
        )
        features = self.manager.get_available_features(state)
        self.assertEqual(features, TIER_FEATURES[SubscriptionTier.DUBBING_333])


class TestDeviceLimits(unittest.TestCase):
    """Tests for device limit enforcement per tier."""

    def setUp(self):
        self.manager = SubscriptionManager()

    def test_geall_one_device_limit(self):
        """GEALL_111 should allow only 1 device."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.GEALL_111,
            active=True,
            expires_at=int(time.time()) + 86400,
            devices=["device_1"],
        )
        self.assertFalse(self.manager.check_device_limit(state, "device_2"))

    def test_family_unlimited_devices(self):
        """FAMILY_423 should allow unlimited devices."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.FAMILY_423,
            active=True,
            expires_at=int(time.time()) + 86400,
            devices=[f"device_{i}" for i in range(100)],
        )
        self.assertTrue(self.manager.check_device_limit(state, "device_new"))

    def test_existing_device_always_allowed(self):
        """Already registered device should always be allowed."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.GEALL_111,
            active=True,
            expires_at=int(time.time()) + 86400,
            devices=["device_1"],
        )
        self.assertTrue(self.manager.check_device_limit(state, "device_1"))

    def test_register_device_success(self):
        """register_device should add device when within limit."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.KAREL_222,
            active=True,
            expires_at=int(time.time()) + 86400,
            devices=[],
        )
        result = self.manager.register_device(state, "new_device")
        self.assertTrue(result)
        self.assertIn("new_device", state.devices)

    def test_register_device_over_limit_fails(self):
        """register_device should fail when at limit."""
        state = SubscriptionState(
            wallet_address="0x123",
            tier=SubscriptionTier.GEALL_111,
            active=True,
            expires_at=int(time.time()) + 86400,
            devices=["device_1"],
        )
        result = self.manager.register_device(state, "device_2")
        self.assertFalse(result)
        self.assertNotIn("device_2", state.devices)


class TestMiniMePaymentClient(unittest.TestCase):
    """Tests for MiniMe token payment integration (Req 12.4)."""

    def test_verify_wallet_valid(self):
        """Valid wallet address should pass verification."""
        client = MiniMePaymentClient(contract_address="0xCONTRACT")
        self.assertTrue(client.verify_wallet("0xVALID_WALLET"))

    def test_verify_wallet_empty(self):
        """Empty wallet address should fail verification."""
        client = MiniMePaymentClient()
        self.assertFalse(client.verify_wallet(""))

    def test_process_payment_success(self):
        """Valid payment should succeed."""
        client = MiniMePaymentClient(contract_address="0xCONTRACT")
        result = client.process_payment("0xWALLET", SubscriptionTier.KAREL_222)
        self.assertTrue(result)

    def test_process_payment_invalid_wallet(self):
        """Payment with invalid wallet should raise PaymentError."""
        client = MiniMePaymentClient()
        with self.assertRaises(PaymentError):
            client.process_payment("", SubscriptionTier.GEALL_111)

    def test_check_balance(self):
        """check_balance should return a positive value for valid wallets."""
        client = MiniMePaymentClient()
        balance = client.check_balance("0xWALLET")
        self.assertGreater(balance, 0)

    def test_check_balance_empty_wallet(self):
        """check_balance should return 0 for empty wallet."""
        client = MiniMePaymentClient()
        self.assertEqual(client.check_balance(""), 0.0)


class TestActivateSubscription(unittest.TestCase):
    """Tests for subscription activation flow."""

    def setUp(self):
        self.manager = SubscriptionManager()

    def test_activate_creates_state(self):
        """activate_subscription should create a valid SubscriptionState."""
        state = self.manager.activate_subscription(
            wallet_address="0xWALLET",
            tier=SubscriptionTier.DUBBING_333,
            device_id="my_device",
        )
        self.assertEqual(state.wallet_address, "0xWALLET")
        self.assertEqual(state.tier, SubscriptionTier.DUBBING_333)
        self.assertTrue(state.active)
        self.assertIn("my_device", state.devices)
        self.assertGreater(state.expires_at, int(time.time()))

    def test_activate_stores_in_users(self):
        """Activated subscription should be retrievable by wallet."""
        self.manager.activate_subscription(
            wallet_address="0xUSER1",
            tier=SubscriptionTier.GEALL_111,
        )
        state = self.manager.get_subscription("0xUSER1")
        self.assertIsNotNone(state)
        self.assertEqual(state.tier, SubscriptionTier.GEALL_111)

    def test_activate_with_custom_duration(self):
        """Custom duration should set correct expiration."""
        before = int(time.time())
        state = self.manager.activate_subscription(
            wallet_address="0xW",
            tier=SubscriptionTier.FAMILY_423,
            duration_days=90,
        )
        expected_min = before + (90 * 86400)
        self.assertGreaterEqual(state.expires_at, expected_min)

    def test_get_subscription_unknown_wallet(self):
        """get_subscription for unknown wallet returns None."""
        result = self.manager.get_subscription("0xNONEXISTENT")
        self.assertIsNone(result)


class TestPrometheusMetrics(unittest.TestCase):
    """Tests for Prometheus metric exposure."""

    def test_metrics_update_on_activation(self):
        """Activating a subscription should update metrics."""
        from subscription_manager import (
            utl_subscription_active_users,
            utl_subscription_tier_distribution,
        )

        manager = SubscriptionManager()
        manager.activate_subscription("0xA", SubscriptionTier.GEALL_111)
        manager.activate_subscription("0xB", SubscriptionTier.KAREL_222)

        # Active users gauge should be 2
        active = utl_subscription_active_users._value.get()
        self.assertEqual(active, 2)

    def test_tier_distribution_metric(self):
        """Tier distribution should count users per tier."""
        from subscription_manager import utl_subscription_tier_distribution

        manager = SubscriptionManager()
        manager.activate_subscription("0x1", SubscriptionTier.FAMILY_423)
        manager.activate_subscription("0x2", SubscriptionTier.FAMILY_423)
        manager.activate_subscription("0x3", SubscriptionTier.GEALL_111)

        family_count = utl_subscription_tier_distribution.labels(
            tier="FAMILY_423"
        )._value.get()
        geall_count = utl_subscription_tier_distribution.labels(
            tier="GEALL_111"
        )._value.get()

        self.assertEqual(family_count, 2)
        self.assertEqual(geall_count, 1)


if __name__ == "__main__":
    unittest.main()
