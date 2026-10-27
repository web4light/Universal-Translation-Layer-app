--  =============================================================================
--  Asterisk Gateway — Prometheus Telemetry Packer
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  Zero heap, static bounded memory, mathematical overflow protection.
--  Standard 700: Real-time Prometheus metrics exporter (ports 9302 / 9091).
--  =============================================================================

package Prometheus_Telemetry_Packer with
  SPARK_Mode => On
is
   Max_Name_Len   : constant := 32;
   Max_Buffer_Len : constant := 128;
   Max_Value      : constant := 999_999;

   subtype Metric_String is String (1 .. Max_Name_Len);
   subtype Output_Buffer is String (1 .. Max_Buffer_Len);

   --  Validates that a metric identifier strictly conforms to Prometheus grammar:
   --  [a-zA-Z_][a-zA-Z0-9_]* up to 32 characters.
   procedure Validate_Metric_Name
     (Name     : in  Metric_String;
      Len      : in  Natural;
      Is_Valid : out Boolean)
   with
     Global => null,
     Depends => (Is_Valid => (Name, Len)),
     Pre  => Len <= Max_Name_Len,
     Post => (if Len = 0 then not Is_Valid);

   --  Packs a metric into Prometheus text exposition format:
   --  "<metric_name> <value>\n"
   --  Guarantees zero heap, bounded indices, and complete buffer initialization.
   procedure Pack_Metric
     (Name       : in  Metric_String;
      Name_Len   : in  Natural;
      Value      : in  Natural;
      Buffer     : out Output_Buffer;
      Buffer_Len : out Natural;
      Success    : out Boolean)
   with
     Global => null,
     Depends => ((Buffer, Buffer_Len) => (Name, Name_Len, Value),
                 Success              => (Name, Name_Len)),
     Pre  => Name_Len <= Max_Name_Len and then Value <= Max_Value,
     Post => (if Success then
                Buffer_Len in 4 .. 40 and then
                Buffer_Len <= Max_Buffer_Len
              else
                Buffer_Len = 0);

end Prometheus_Telemetry_Packer;
