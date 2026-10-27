--  =============================================================================
--  Asterisk Gateway — Prometheus Telemetry Packer Implementation
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  Zero heap, static bounded memory, mathematical overflow protection.
--  =============================================================================

package body Prometheus_Telemetry_Packer with
  SPARK_Mode => On
is

   procedure Validate_Metric_Name
     (Name     : in  Metric_String;
      Len      : in  Natural;
      Is_Valid : out Boolean)
   is
   begin
      if Len = 0 then
         Is_Valid := False;
         return;
      end if;

      if not (Name (1) in 'a' .. 'z' or else
              Name (1) in 'A' .. 'Z' or else
              Name (1) = '_')
      then
         Is_Valid := False;
         return;
      end if;

      Is_Valid := True;
      for I in 2 .. Len loop
         if not (Name (I) in 'a' .. 'z' or else
                 Name (I) in 'A' .. 'Z' or else
                 Name (I) in '0' .. '9' or else
                 Name (I) = '_')
         then
            Is_Valid := False;
            exit;
         end if;
         pragma Loop_Invariant (I in 2 .. Len);
      end loop;
   end Validate_Metric_Name;

   procedure Pack_Metric
     (Name       : in  Metric_String;
      Name_Len   : in  Natural;
      Value      : in  Natural;
      Buffer     : out Output_Buffer;
      Buffer_Len : out Natural;
      Success    : out Boolean)
   is
      Valid_Name : Boolean;
      Pos        : Natural;
      D6, D5, D4, D3, D2, D1 : Natural;
   begin
      Buffer := (others => ' ');
      Buffer_Len := 0;

      Validate_Metric_Name (Name, Name_Len, Valid_Name);
      if not Valid_Name then
         Success := False;
         return;
      end if;

      for I in 1 .. Name_Len loop
         Buffer (I) := Name (I);
         pragma Loop_Invariant (I in 1 .. Name_Len);
      end loop;
      Pos := Name_Len;

      Pos := Pos + 1;
      Buffer (Pos) := ' ';

      D6 := (Value / 100_000) mod 10;
      D5 := (Value / 10_000) mod 10;
      D4 := (Value / 1_000) mod 10;
      D3 := (Value / 100) mod 10;
      D2 := (Value / 10) mod 10;
      D1 := Value mod 10;

      if Value >= 100_000 then
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D6);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D5);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D4);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D3);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D2);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D1);
      elsif Value >= 10_000 then
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D5);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D4);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D3);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D2);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D1);
      elsif Value >= 1_000 then
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D4);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D3);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D2);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D1);
      elsif Value >= 100 then
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D3);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D2);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D1);
      elsif Value >= 10 then
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D2);
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D1);
      else
         Pos := Pos + 1;
         Buffer (Pos) := Character'Val (Character'Pos ('0') + D1);
      end if;

      Pos := Pos + 1;
      Buffer (Pos) := ASCII.LF;

      Buffer_Len := Pos;
      Success := True;
   end Pack_Metric;

end Prometheus_Telemetry_Packer;
