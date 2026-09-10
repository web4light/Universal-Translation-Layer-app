pragma SPARK_Mode (On);

package body Asterisk_Sovereign_Webmcp_Core is

   procedure Process_Stream
     (State   : in out Core_State;
      Length  : in     Payload_Length;
      Success :    out Boolean)
   is
   begin
      if Length > 0 and then State.Processed_Count < Max_Buffer_Size then
         State.Processed_Count := State.Processed_Count + 1;
         Success := True;
      else
         Success := False;
      end if;
   end Process_Stream;

end Asterisk_Sovereign_Webmcp_Core;
