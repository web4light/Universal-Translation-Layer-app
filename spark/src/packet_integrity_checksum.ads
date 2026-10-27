--  =============================================================================
--  Asterisk Gateway — Packet Integrity Checksum
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  Deterministic IEEE 802.3 CRC-32 checksum calculation, zero dynamic memory.
--  Standard 700: Bit-level packet tamper protection across mesh & WebMCP.
--  =============================================================================

package Packet_Integrity_Checksum with
  SPARK_Mode => On
is
   type Checksum_32 is mod 2**32;
   type Byte_Val is mod 256;

   CRC32_Polynomial : constant Checksum_32 := 16#EDB8_8320#;

   subtype Buffer_Index is Positive range 1 .. 512;
   type Byte_Buffer is array (Buffer_Index range <>) of Byte_Val;

   --  Computes deterministic IEEE 802.3 CRC-32 checksum.
   function Compute_CRC32
     (Buffer : Byte_Buffer) return Checksum_32
   with
     Global => null;

   --  Verifies packet integrity against expected checksum.
   procedure Verify_Packet
     (Buffer         : in  Byte_Buffer;
      Expected_CRC32 : in  Checksum_32;
      Is_Valid       : out Boolean)
   with
     Global => null,
     Depends => (Is_Valid => (Buffer, Expected_CRC32)),
     Post => Is_Valid = (Compute_CRC32 (Buffer) = Expected_CRC32);

   --  Serializes a 32-bit checksum into 4 big-endian bytes.
   procedure Serialize_CRC32
     (Value : in  Checksum_32;
      B0    : out Byte_Val;
      B1    : out Byte_Val;
      B2    : out Byte_Val;
      B3    : out Byte_Val)
   with
     Global => null,
     Depends => ((B0, B1, B2, B3) => Value);

end Packet_Integrity_Checksum;
