-- ============================================================
--  ETH RLP — Implementation
--  SPARK proved, GPL-free
-- ============================================================

pragma SPARK_Mode (On);

package body Eth_RLP is

   -- Pomocna: pocet bytu potrebnych pro big-endian representaci
   function Byte_Count (Value : Natural) return Natural
     with Post => Byte_Count'Result in 0 .. 4
   is
   begin
      if Value = 0 then
         return 0;
      elsif Value <= 255 then
         return 1;
      elsif Value <= 65_535 then
         return 2;
      elsif Value <= 16_777_215 then
         return 3;
      else
         return 4;
      end if;
   end Byte_Count;

   -- =========================================================
   --  Encode_Bytes
   -- =========================================================

   procedure Encode_Bytes (Input      : Byte_Array;
                           Output     : out RLP_Buffer;
                           Output_Len : out RLP_Length)
   is
      Len : constant Natural := Input'Length;
   begin
      Output := (others => 0);

      if Len = 0 then
         -- Prazdny string: 0x80
         Output (1) := 16#80#;
         Output_Len := 1;

      elsif Len = 1 and then Input (Input'First) <= 16#7F# then
         -- Single byte 0x00..0x7F: sam sobe
         Output (1) := Input (Input'First);
         Output_Len := 1;

      elsif Len <= 55 then
         -- Short string: 0x80 + len, pak data
         Output (1) := 16#80# + Len;
         for I in 0 .. Len - 1 loop
            Output (2 + I) := Input (Input'First + I);
         end loop;
         Output_Len := 1 + Len;

      else
         -- Long string: 0xB7 + byte_count(len), len bytes, data
         -- Len > 55, Len <= Max_Payload - 3 = 4093
         -- Takze Byte_Count(Len) je vzdy 2 (256..65535)
         declare
            Len_Bytes : constant Natural := 2;  -- Len in 56..4093 → vzdy 2 byty
            Remaining : Natural := Len;
         begin
            Output (1) := 16#B7# + Len_Bytes;

            -- Write length big-endian
            for I in reverse 1 .. Len_Bytes loop
               Output (1 + I) := Remaining mod 256;
               Remaining := Remaining / 256;
            end loop;

            -- Write data
            for I in 0 .. Len - 1 loop
               Output (2 + Len_Bytes + I) := Input (Input'First + I);
            end loop;

            Output_Len := 1 + Len_Bytes + Len;
         end;
      end if;
   end Encode_Bytes;

   -- =========================================================
   --  Encode_Empty
   -- =========================================================

   procedure Encode_Empty (Output     : out RLP_Buffer;
                           Output_Len : out RLP_Length) is
   begin
      Output := (others => 0);
      Output (1) := 16#80#;
      Output_Len := 1;
   end Encode_Empty;

   -- =========================================================
   --  Encode_Natural
   -- =========================================================

   procedure Encode_Natural (Value      : Natural;
                             Output     : out RLP_Buffer;
                             Output_Len : out RLP_Length)
   is
      Temp : Byte_Array (1 .. 4);
      Temp_Len : Natural := 0;
      Remaining : Natural := Value;
   begin
      Output := (others => 0);

      if Value = 0 then
         -- Zero encodes as empty byte string → 0x80
         Output (1) := 16#80#;
         Output_Len := 1;
         return;
      end if;

      -- Convert to big-endian bytes (bez leading zeros)
      Temp := (others => 0);
      Temp_Len := Byte_Count (Value);

      for I in reverse 1 .. Temp_Len loop
         Temp (I) := Remaining mod 256;
         Remaining := Remaining / 256;
      end loop;

      -- Encode as byte string
      Encode_Bytes (Temp (1 .. Temp_Len), Output, Output_Len);
   end Encode_Natural;

   -- =========================================================
   --  Encoded_Length
   -- =========================================================

   function Encoded_Length (Input_Len : Natural) return Natural is
   begin
      if Input_Len = 0 then
         return 1;
      elsif Input_Len = 1 then
         -- Muze byt 1 (single byte) nebo 2 (prefix + byte)
         -- Worst case: 2
         return 2;
      elsif Input_Len <= 55 then
         return 1 + Input_Len;
      else
         return 1 + Byte_Count (Input_Len) + Input_Len;
      end if;
   end Encoded_Length;

   -- =========================================================
   --  Decode_Header
   -- =========================================================

   function Decode_Header (Input : Byte_Array) return RLP_Decode_Result is
      First : constant Byte := Input (Input'First);
      Result : RLP_Decode_Result;
   begin
      Result := (Kind => Invalid, Data_Offset => 1,
                 Data_Length => 0, Total_Length => 0);

      if First <= 16#7F# then
         -- Single byte
         Result.Kind := Single_Byte;
         Result.Data_Offset := 1;
         Result.Data_Length := 1;
         Result.Total_Length := 1;

      elsif First <= 16#B7# then
         -- Short string (0-55 bytes)
         declare
            Len : constant Natural := First - 16#80#;
         begin
            Result.Kind := Short_String;
            Result.Data_Offset := 2;
            Result.Data_Length := Len;
            Result.Total_Length := 1 + Len;
         end;

      elsif First <= 16#BF# then
         -- Long string
         declare
            Len_Bytes : constant Natural := First - 16#B7#;
            Len : Natural := 0;
         begin
            if Input'Length < 1 + Len_Bytes then
               Result.Kind := Invalid;
               return Result;
            end if;

            for I in 1 .. Len_Bytes loop
               if Len > Max_Payload then
                  Result.Kind := Invalid;
                  return Result;
               end if;
               Len := Len * 256 + Input (Input'First + I);
            end loop;

            if Len > Max_Payload then
               Result.Kind := Invalid;
               return Result;
            end if;

            if 1 + Len_Bytes + Len > Max_Payload then
               Result.Kind := Invalid;
               return Result;
            end if;

            Result.Kind := Long_String;
            Result.Data_Offset := 1 + Len_Bytes + 1;
            Result.Data_Length := Len;
            Result.Total_Length := 1 + Len_Bytes + Len;
         end;

      elsif First <= 16#F7# then
         -- Short list (0-55 bytes total)
         declare
            Len : constant Natural := First - 16#C0#;
         begin
            Result.Kind := Short_List;
            Result.Data_Offset := 2;
            Result.Data_Length := Len;
            Result.Total_Length := 1 + Len;
         end;

      else
         -- Long list
         declare
            Len_Bytes : constant Natural := First - 16#F7#;
            Len : Natural := 0;
         begin
            if Input'Length < 1 + Len_Bytes then
               Result.Kind := Invalid;
               return Result;
            end if;

            for I in 1 .. Len_Bytes loop
               if Len > Max_Payload then
                  Result.Kind := Invalid;
                  return Result;
               end if;
               Len := Len * 256 + Input (Input'First + I);
            end loop;

            if Len > Max_Payload then
               Result.Kind := Invalid;
               return Result;
            end if;

            if 1 + Len_Bytes + Len > Max_Payload then
               Result.Kind := Invalid;
               return Result;
            end if;

            Result.Kind := Long_List;
            Result.Data_Offset := 1 + Len_Bytes + 1;
            Result.Data_Length := Len;
            Result.Total_Length := 1 + Len_Bytes + Len;
         end;
      end if;

      return Result;
   end Decode_Header;

end Eth_RLP;
