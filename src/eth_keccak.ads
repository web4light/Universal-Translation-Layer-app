-- ============================================================
--  ETH Keccak-256 — SHA-3 hash pro Ethereum
--
--  Kazda adresa, kazdy TX hash, kazdy podpis v Ethereu
--  pouziva Keccak-256 (NE standardni SHA3-256, ale puvodni
--  Keccak pred NIST standardizaci).
--
--  SPARK proved. GPL-free. Zadna GNU.
--  Zadna zavislost na OpenSSL/libcrypto.
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0 (Rebirth Phoenix Foundation Charter)
-- ============================================================

pragma SPARK_Mode (On);

package Eth_Keccak is

   -- Keccak-256 vystup: 32 bytu (256 bitu)
   Hash_Length : constant := 32;

   -- Byte typy
   subtype Byte is Natural range 0 .. 255;
   type Byte_Array is array (Positive range <>) of Byte;
   subtype Hash_Value is Byte_Array (1 .. Hash_Length);

   -- Keccak state: 5x5 matice 64-bit slov = 1600 bitu
   type Unsigned_64 is mod 2**64;
   type State_Array is array (Natural range 0 .. 4,
                              Natural range 0 .. 4) of Unsigned_64;

   -- Rate pro Keccak-256: 1088 bitu = 136 bytu
   Rate_Bytes : constant := 136;
   subtype Rate_Index is Natural range 0 .. Rate_Bytes - 1;

   -- Maximalni vstup pro jednorazovy hash (dostatecne pro TX)
   Max_Input : constant := 4_096;
   subtype Input_Length is Natural range 0 .. Max_Input;

   -- =========================================================
   --  API
   -- =========================================================

   -- Jednorazovy hash: vstup → 32-byte Keccak-256
   procedure Hash (Input      : Byte_Array;
                   Output     : out Hash_Value)
     with Pre => Input'Length <= Max_Input;

   -- Ethereum adresa z public key (posledních 20 bytu Keccak hashe)
   Address_Length : constant := 20;
   subtype Eth_Address is Byte_Array (1 .. Address_Length);

   procedure Public_Key_To_Address (Pub_Key : Byte_Array;
                                    Addr    : out Eth_Address)
     with Pre => Pub_Key'Length = 64;  -- uncompressed, bez 0x04 prefixu

   -- =========================================================
   --  Interni (pro SPARK prove)
   -- =========================================================

   -- Keccak-f[1600] permutace (24 rund)
   procedure Keccak_F (State : in out State_Array);

   -- Theta step
   procedure Theta (State : in out State_Array);

   -- Rho + Pi steps
   procedure Rho_Pi (State : in out State_Array);

   -- Chi step
   procedure Chi (State : in out State_Array);

   -- Iota step (pridat round constant)
   procedure Iota (State : in out State_Array;
                   Round : Natural)
     with Pre => Round <= 23;

end Eth_Keccak;
