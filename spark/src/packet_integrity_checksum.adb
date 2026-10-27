--  =============================================================================
--  Asterisk Gateway — Packet Integrity Checksum Implementation
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  =============================================================================

package body Packet_Integrity_Checksum with
  SPARK_Mode => On
is

   function Compute_CRC32 (Buffer : Byte_Buffer) return Checksum_32 is
      CRC : Checksum_32 := 16#FFFF_FFFF#;
      B   : Checksum_32;
   begin
      for I in Buffer'Range loop
         B := Checksum_32 (Buffer (I));
         CRC := CRC xor B;
         for Bit in 1 .. 8 loop
            if (CRC and 1) /= 0 then
               CRC := (CRC / 2) xor CRC32_Polynomial;
            else
               CRC := CRC / 2;
            end if;
         end loop;
      end loop;
      return CRC xor 16#FFFF_FFFF#;
   end Compute_CRC32;

   procedure Verify_Packet
     (Buffer         : in  Byte_Buffer;
      Expected_CRC32 : in  Checksum_32;
      Is_Valid       : out Boolean)
   is
   begin
      Is_Valid := (Compute_CRC32 (Buffer) = Expected_CRC32);
   end Verify_Packet;

   procedure Serialize_CRC32
     (Value : in  Checksum_32;
      B0    : out Byte_Val;
      B1    : out Byte_Val;
      B2    : out Byte_Val;
      B3    : out Byte_Val)
   is
   begin
      B0 := Byte_Val ((Value / 16#100_0000#) and 16#FF#);
      B1 := Byte_Val ((Value / 16#1_0000#) and 16#FF#);
      B2 := Byte_Val ((Value / 16#100#) and 16#FF#);
      B3 := Byte_Val (Value and 16#FF#);
   end Serialize_CRC32;

end Packet_Integrity_Checksum;
