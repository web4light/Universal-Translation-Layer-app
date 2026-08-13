-- ============================================================
--  ETH RLP — Recursive Length Prefix encoder/decoder
--
--  Zaklad Ethereum serializace. Kazda transakce, kazdy blok,
--  kazdy stav prochazi pres RLP.
--
--  SPARK proved — zadny buffer overflow, zadny off-by-one.
--  GPL-free. Zadna GNU zavislost.
--
--  Spec: https://ethereum.org/en/developers/docs/data-structures-and-encoding/rlp/
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0 (Rebirth Phoenix Foundation Charter)
-- ============================================================

pragma SPARK_Mode (On);

package Eth_RLP is

   -- Maximalni delka RLP payloadu (dostatecne pro transakce)
   Max_Payload : constant := 4_096;

   -- Byte typ
   subtype Byte is Natural range 0 .. 255;

   -- Byte array pro RLP data
   type Byte_Array is array (Positive range <>) of Byte;

   -- Bounded byte buffer
   subtype RLP_Buffer is Byte_Array (1 .. Max_Payload);
   subtype RLP_Length is Natural range 0 .. Max_Payload;

   -- =========================================================
   --  RLP Encoding Rules:
   --
   --  1. Single byte 0x00..0x7F → sám sobě
   --  2. String 0-55 bytes → 0x80 + len, pak data
   --  3. String >55 bytes → 0xB7 + len_of_len, len, data
   --  4. List 0-55 bytes → 0xC0 + len, pak concatenated items
   --  5. List >55 bytes → 0xF7 + len_of_len, len, items
   -- =========================================================

   -- Encode single byte string (prazdny az 55 bytu)
   procedure Encode_Bytes (Input      : Byte_Array;
                           Output     : out RLP_Buffer;
                           Output_Len : out RLP_Length)
     with Pre  => Input'Length <= Max_Payload - 3;

   -- Encode prazdny string
   procedure Encode_Empty (Output     : out RLP_Buffer;
                           Output_Len : out RLP_Length)
     with Post => Output_Len = 1;

   -- Encode jednoho Natural jako big-endian byty
   procedure Encode_Natural (Value      : Natural;
                             Output     : out RLP_Buffer;
                             Output_Len : out RLP_Length);

   -- Delka RLP encodingu pro byte array
   function Encoded_Length (Input_Len : Natural) return Natural
     with Pre  => Input_Len <= Max_Payload - 3;

   -- Decode: zjisti typ a delku prvniho RLP itemu
   type RLP_Item_Kind is (Single_Byte, Short_String, Long_String,
                          Short_List, Long_List, Invalid);

   type RLP_Decode_Result is record
      Kind        : RLP_Item_Kind := Invalid;
      Data_Offset : Positive := 1;       -- kde zacinaji data
      Data_Length : RLP_Length := 0;      -- delka dat
      Total_Length : RLP_Length := 0;     -- celkova delka itemu
   end record;

   -- Decode header prvniho RLP itemu
   function Decode_Header (Input : Byte_Array) return RLP_Decode_Result
     with Pre => Input'Length >= 1;

end Eth_RLP;
