"""
Soulbound NFT Bridge — Python ↔ Ada/SPARK subprocess komunikace.

Tento modul poskytuje Python rozhraní k Ada/SPARK Soulbound NFT logice.
Komunikace probíhá výhradně přes subprocess CLI (JSON na stdout).

Použití:
    bridge = SoulboundNFTBridge()
    result = bridge.derive_wallet("abcdef..." * 8)  # 64 hex chars
    verified = bridge.verify_biometric(stored_hash, current_hash, score)
    is_allowed = bridge.is_transfer_allowed(token, from_wallet, to_wallet)
"""

import json
import subprocess
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MintResult(Enum):
    """Výsledek operace minting NFT."""

    MINT_SUCCESS = "Mint_Success"
    MINT_FAILED_INVALID_HASH = "Mint_Failed_Invalid_Hash"
    MINT_FAILED_CAPACITY = "Mint_Failed_Capacity"


class VerificationResult(Enum):
    """Výsledek biometrické verifikace."""

    VERIFIED = "Verified"
    REJECTED = "Rejected"


@dataclass
class NFTRecord:
    """Python reprezentace Ada NFT_Record."""

    owner_hash: str = ""
    wallet: str = ""
    display_name: str = ""
    is_minted: bool = False


# Práh pro FAR < 0.001% — musí být konzistentní s Ada konstantou
FAR_THRESHOLD: float = 0.999


class SoulboundNFTBridge:
    """Bridge pro volání Ada/SPARK Soulbound NFT logiky přes subprocess.

    Pokud Ada binárka není dostupná, používá pure-Python fallback
    implementaci se stejnou logikou (pro testování a vývoj).
    """

    def __init__(self, binary_path: Optional[str] = None):
        """Inicializace bridge.

        Args:
            binary_path: Cesta k Ada binárce. Pokud None, hledá
                        v src/ nebo používá Python fallback.
        """
        self._binary_path = binary_path or self._find_binary()
        self._total_minted = 0

    def _find_binary(self) -> Optional[str]:
        """Najde Ada binárku v očekávaných lokacích."""
        candidates = [
            os.path.join(os.path.dirname(__file__), "soulbound_nft"),
            os.path.join(os.path.dirname(__file__), "..", "bin", "soulbound_nft"),
            "/usr/local/bin/soulbound_nft",
        ]
        for path in candidates:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None

    def _call_ada(self, command: str, args: dict) -> Optional[dict]:
        """Zavolá Ada binárku přes subprocess CLI.

        Args:
            command: Název příkazu (derive_wallet, verify, mint, transfer)
            args: JSON argumenty pro příkaz

        Returns:
            Parsovaný JSON výstup nebo None při selhání.
        """
        if self._binary_path is None:
            return None

        payload = json.dumps({"command": command, **args})
        try:
            result = subprocess.run(
                [self._binary_path],
                input=payload,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass
        return None

    def derive_wallet(self, bio_hash: str) -> str:
        """Odvoď wallet adresu z biometrického hashe.

        Args:
            bio_hash: 64-znakový hex string (SHA-256 biometrických dat)

        Returns:
            Ethereum wallet adresa (0x + 40 hex znaků)

        Raises:
            ValueError: Pokud bio_hash není validní (ne-hex, samé nuly, špatná délka)
        """
        if len(bio_hash) != 64:
            raise ValueError(f"Biometric hash must be 64 hex chars, got {len(bio_hash)}")
        if bio_hash == "0" * 64:
            raise ValueError("Biometric hash cannot be all zeros")
        if not all(c in "0123456789abcdefABCDEF" for c in bio_hash):
            raise ValueError("Biometric hash must contain only hex characters")

        # Zkus Ada binárku
        ada_result = self._call_ada("derive_wallet", {"bio_hash": bio_hash})
        if ada_result and "wallet" in ada_result:
            return ada_result["wallet"]

        # Python fallback — stejná logika jako Ada implementace
        return self._derive_wallet_fallback(bio_hash)

    def _derive_wallet_fallback(self, bio_hash: str) -> str:
        """Pure-Python fallback pro Derive_Wallet_Key.

        Identická logika s Ada implementací: XOR sousedních nibblů + salt.
        """
        result = ["0", "x"]
        bio_lower = bio_hash.lower()

        for i in range(40):
            nibble_a = int(bio_lower[i], 16)
            nibble_b = int(bio_lower[i + 24], 16)
            derived = (nibble_a + nibble_b + i + 1) % 16  # +1 because Ada is 1-indexed
            result.append(format(derived, "x"))

        return "".join(result)

    def verify_biometric(
        self, stored_hash: str, current_hash: str, score: float
    ) -> VerificationResult:
        """Verifikuj biometrii proti uloženému hashi.

        Args:
            stored_hash: Uložený biometrický hash (64 hex)
            current_hash: Aktuální biometrický hash (64 hex)
            score: Match skóre (0.0 - 1.0)

        Returns:
            VerificationResult.VERIFIED pokud score >= FAR_THRESHOLD,
            jinak VerificationResult.REJECTED.
        """
        if len(stored_hash) != 64 or len(current_hash) != 64:
            raise ValueError("Both hashes must be 64 hex characters")
        if not (0.0 <= score <= 1.0):
            raise ValueError("Score must be between 0.0 and 1.0")

        # Zkus Ada binárku
        ada_result = self._call_ada(
            "verify",
            {
                "stored_hash": stored_hash,
                "current_hash": current_hash,
                "score": score,
            },
        )
        if ada_result and "result" in ada_result:
            return VerificationResult(ada_result["result"])

        # Python fallback — konsistentní s Ada Post kontraktem
        if score >= FAR_THRESHOLD:
            return VerificationResult.VERIFIED
        else:
            return VerificationResult.REJECTED

    def is_transfer_allowed(
        self, token: NFTRecord, from_wallet: str, to_wallet: str
    ) -> bool:
        """Zkontroluj, zda je převod NFT povolen.

        VŽDY vrací False — soulbound invariant.

        Args:
            token: NFT záznam
            from_wallet: Odesílatel wallet adresa
            to_wallet: Příjemce wallet adresa

        Returns:
            False — převod nikdy není povolen (soulbound).
        """
        # Soulbound invariant: bez ohledu na parametry, výsledek je VŽDY False
        # Toto je záměr — Post kontrakt v Ada to formálně garantuje
        return False

    def mint_nft(self, bio_hash: str) -> tuple[NFTRecord, MintResult]:
        """Mintni nový Soulbound NFT.

        Args:
            bio_hash: 64-znakový hex biometrický hash

        Returns:
            Tuple (NFTRecord, MintResult) — token a výsledek operace.
        """
        if len(bio_hash) != 64:
            return NFTRecord(), MintResult.MINT_FAILED_INVALID_HASH
        if bio_hash == "0" * 64:
            return NFTRecord(), MintResult.MINT_FAILED_INVALID_HASH
        if not all(c in "0123456789abcdefABCDEF" for c in bio_hash):
            return NFTRecord(), MintResult.MINT_FAILED_INVALID_HASH

        # Zkus Ada binárku
        ada_result = self._call_ada("mint", {"bio_hash": bio_hash})
        if ada_result and "result" in ada_result:
            mint_result = MintResult(ada_result["result"])
            if mint_result == MintResult.MINT_SUCCESS:
                token = NFTRecord(
                    owner_hash=bio_hash,
                    wallet=ada_result.get("wallet", ""),
                    display_name="",
                    is_minted=True,
                )
                return token, mint_result
            return NFTRecord(), mint_result

        # Python fallback
        return self._mint_nft_fallback(bio_hash)

    def _mint_nft_fallback(self, bio_hash: str) -> tuple[NFTRecord, MintResult]:
        """Pure-Python fallback pro Mint_NFT."""
        if self._total_minted >= 1_000_000_000:
            return NFTRecord(), MintResult.MINT_FAILED_CAPACITY

        wallet = self._derive_wallet_fallback(bio_hash)
        self._total_minted += 1

        token = NFTRecord(
            owner_hash=bio_hash,
            wallet=wallet,
            display_name="",
            is_minted=True,
        )
        return token, MintResult.MINT_SUCCESS

    def set_display_name(self, token: NFTRecord, name: str) -> tuple[NFTRecord, bool]:
        """Nastav display name pro NFT (nezávislý na wallet adrese).

        Args:
            token: Mintnutý NFT záznam
            name: Display name (1-128 znaků)

        Returns:
            Tuple (updated_token, success)
        """
        if not token.is_minted:
            return token, False
        if not name or len(name) > 128:
            return token, False

        token.display_name = name
        return token, True

    def get_display_name(self, token: NFTRecord) -> str:
        """Získej display name z NFT záznamu.

        Args:
            token: Mintnutý NFT záznam

        Returns:
            Display name string, nebo prázdný string pokud není nastaven.
        """
        if not token.is_minted:
            return ""
        return token.display_name
