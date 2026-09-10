pragma SPARK_Mode (On);

package Asterisk_Sovereign_WebMCP_Core is

   -- Konstanty (žádná magická čísla)
   Max_Buffer_Size : constant := 1_000;
   Max_Payload_Len : constant := 512;

   -- Typy s rozsahem
   subtype Buffer_Index is Natural range 0 .. Max_Buffer_Size;
   subtype Payload_Length is Natural range 0 .. Max_Payload_Len;

   -- Datové struktury s výchozími hodnotami
   type Core_State is record
      Processed_Count : Buffer_Index := 0;
      Is_Active       : Boolean := True;
      Zero_Trace_RAM  : Boolean := True;
   end record;

   -- Procedury s formálními Pre / Post kontrakty
   procedure Process_Stream
     (State   : in out Core_State;
      Length  : in     Payload_Length;
      Success :    out Boolean)
   with
      Pre  => Length > 0 and then State.Processed_Count < Max_Buffer_Size,
      Post => (if Success then State.Processed_Count = State.Processed_Count'Old + 1
               else State.Processed_Count = State.Processed_Count'Old);

end Asterisk_Sovereign_WebMCP_Core;
