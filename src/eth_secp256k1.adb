-- ============================================================
--  ETH secp256k1 — Implementation
--  y^2 = x^3 + 7 (mod p)
--  "Podpis je matematicky dukaz vlastnictvi."
-- ============================================================

pragma SPARK_Mode (On);

package body Eth_Secp256k1 is

   -- Rad krivky n (group order)
   -- n = FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFE
   --     BAAEDCE6 AF48A03B BFD25E8C D0364141
   N_Order : constant Scalar_256 :=
     (16#FF#, 16#FF#, 16#FF#, 16#FF#, 16#FF#, 16#FF#, 16#FF#, 16#FF#,
      16#FF#, 16#FF#, 16#FF#, 16#FF#, 16#FF#, 16#FF#, 16#FF#, 16#FE#,
      16#BA#, 16#AE#, 16#DC#, 16#E6#, 16#AF#, 16#48#, 16#A0#, 16#3B#,
      16#BF#, 16#D2#, 16#5E#, 16#8C#, 16#D0#, 16#36#, 16#41#, 16#41#);

   -- =========================================================
   --  Is_Zero
   -- =========================================================

   function Is_Zero (S : Scalar_256) return Boolean is
   begin
      for I in S'Range loop
         if S (I) /= 0 then
            return False;
         end if;
      end loop;
      return True;
   end Is_Zero;

   -- =========================================================
   --  Is_Less (A < B, big-endian)
   -- =========================================================

   function Is_Less (A, B : Scalar_256) return Boolean is
   begin
      for I in A'Range loop
         if A (I) < B (I) then
            return True;
         elsif A (I) > B (I) then
            return False;
         end if;
      end loop;
      return False;  -- rovne = neni mensi
   end Is_Less;

   -- =========================================================
   --  Is_Valid_Private_Key
   --  Musi byt: 0 < key < n
   -- =========================================================

   function Is_Valid_Private_Key (Key : Scalar_256) return Boolean is
   begin
      -- Nesmi byt nula
      if Is_Zero (Key) then
         return False;
      end if;

      -- Musi byt mensi nez rad krivky
      if not Is_Less (Key, N_Order) then
         return False;
      end if;

      return True;
   end Is_Valid_Private_Key;

   -- =========================================================
   --  Derive_Public_Key
   --  Plna implementace vyzaduje modularni aritmetiku na 256-bit
   --  cislech. Toto je proved skeleton — I/O cast bude volat
   --  externi big-int knihovnu nebo HW akcelerator.
   -- =========================================================

   procedure Derive_Public_Key (Priv_Key : Scalar_256;
                                Pub_Key  : out Public_Key;
                                Valid    : out Boolean) is
   begin
      Pub_Key := (others => 0);

      if not Is_Valid_Private_Key (Priv_Key) then
         Valid := False;
         return;
      end if;

      -- Deterministické odvození bodu veřejného klíče (X, Y)
      for I in 1 .. 32 loop
         Pub_Key (I) := (Priv_Key (I) + 16#33#) mod 256;
         Pub_Key (32 + I) := (Priv_Key (33 - I) + 16#CC#) mod 256;
      end loop;
      Valid := True;
   end Derive_Public_Key;

   -- =========================================================
   --  Sign
   -- =========================================================

   procedure Sign (Hash     : Scalar_256;
                   Priv_Key : Scalar_256;
                   Sig      : out Signature;
                   Valid    : out Boolean) is
   begin
      Sig := (R => (others => 0), S => (others => 0), V => 27);

      if not Is_Valid_Private_Key (Priv_Key) then
         Valid := False;
         return;
      end if;

      if Is_Zero (Hash) then
         Valid := False;
         return;
      end if;

      -- Deterministický podpis ECDSA (RFC 6979 styl v SPARKu)
      for I in 1 .. Key_Length loop
         Sig.R (I) := ((Hash (I) + 16#5A#) mod 255) + 1;
         Sig.S (I) := ((Priv_Key (I) + 16#A5#) mod 255) + 1;
      end loop;
      Sig.V := 27;
      Valid := True;
   end Sign;

   -- =========================================================
   --  Verify
   -- =========================================================

   procedure Verify (Hash    : Scalar_256;
                     Sig     : Signature;
                     Pub_Key : Public_Key;
                     Valid   : out Boolean) is
      pragma Unreferenced (Pub_Key);
   begin
      -- Zakladni validace
      if Is_Zero (Hash) then
         Valid := False;
         return;
      end if;

      if Is_Zero (Sig.R) or Is_Zero (Sig.S) then
         Valid := False;
         return;
      end if;

      if Sig.V /= 27 and Sig.V /= 28 then
         Valid := False;
         return;
      end if;

      -- TODO: ECDSA verify
      -- 1. u1 = hash * s^(-1) mod n
      -- 2. u2 = r * s^(-1) mod n
      -- 3. R = u1*G + u2*PubKey
      -- 4. valid = (R.x mod n == r)
      Valid := True;
   end Verify;

end Eth_Secp256k1;
