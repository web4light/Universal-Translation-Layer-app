-- ============================================================
--  ETH secp256k1 — Elipticka krivka pro Ethereum podpisy
--
--  Kazda transakce na Ethereu je podepsana secp256k1.
--  Privatni klic → verejny klic → adresa.
--  sign(tx_hash, privkey) → (r, s, v)
--
--  SPARK proved. GPL-free. Zadna libsecp256k1 (C).
--  Zadna OpenSSL. Cista Ada.
--
--  PRIBALOVY LETAK:
--    Ucinna latka: secp256k1 nad GF(p)
--    Indikace: Ethereum transakce, Sepolia testnet
--    Kontraindikace: nesmí se michat s neverifikovanym kodem
--    Nezadouci ucinky: matematicka jistota
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0 (Rebirth Phoenix Foundation Charter)
-- ============================================================

pragma SPARK_Mode (On);

package Eth_Secp256k1 is

   -- =========================================================
   --  Typy — 256-bit cisla jako pole 32 bytu (big-endian)
   -- =========================================================

   subtype Byte is Natural range 0 .. 255;
   type Byte_Array is array (Positive range <>) of Byte;

   -- 256-bit scalar (privatni klic, hash, r, s)
   Key_Length : constant := 32;
   subtype Scalar_256 is Byte_Array (1 .. Key_Length);

   -- Verejny klic (uncompressed: 64 bytu, bez 0x04 prefixu)
   Pub_Key_Length : constant := 64;
   subtype Public_Key is Byte_Array (1 .. Pub_Key_Length);

   -- Ethereum adresa (20 bytu)
   Addr_Length : constant := 20;
   subtype Eth_Address is Byte_Array (1 .. Addr_Length);

   -- Podpis (r + s + v)
   type Signature is record
      R : Scalar_256 := (others => 0);
      S : Scalar_256 := (others => 0);
      V : Byte := 27;  -- recovery ID (27 nebo 28)
   end record;

   -- =========================================================
   --  Krivka secp256k1 parametry
   --  y^2 = x^3 + 7 (mod p)
   --  p = FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF
   --      FFFFFFFF FFFFFFFF FFFFFFFE FFFFFC2F
   -- =========================================================

   -- Bod na krivce (afinni souradnice, 32+32 bytu)
   type Curve_Point is record
      X : Scalar_256 := (others => 0);
      Y : Scalar_256 := (others => 0);
      Is_Infinity : Boolean := False;
   end record;

   -- =========================================================
   --  API
   -- =========================================================

   -- Validace privatniho klice (musi byt 1 < key < n)
   function Is_Valid_Private_Key (Key : Scalar_256) return Boolean;

   -- Privatni klic → verejny klic (nasobeni generatorem G)
   procedure Derive_Public_Key (Priv_Key : Scalar_256;
                                Pub_Key  : out Public_Key;
                                Valid    : out Boolean)
     with Post => (if not Is_Valid_Private_Key (Priv_Key) then Valid = False);

   -- Podepis hash privatnim klicem
   procedure Sign (Hash     : Scalar_256;
                   Priv_Key : Scalar_256;
                   Sig      : out Signature;
                   Valid    : out Boolean)
     with Post => (if not Is_Valid_Private_Key (Priv_Key) then Valid = False);

   -- Over podpis (pro verifikaci)
   procedure Verify (Hash    : Scalar_256;
                     Sig     : Signature;
                     Pub_Key : Public_Key;
                     Valid   : out Boolean);

   -- =========================================================
   --  Pomocne (interni, pro SPARK)
   -- =========================================================

   -- Je scalar nulovy?
   function Is_Zero (S : Scalar_256) return Boolean;

   -- Porovnani dvou scalaru
   function Is_Less (A, B : Scalar_256) return Boolean;

end Eth_Secp256k1;
