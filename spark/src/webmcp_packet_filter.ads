pragma SPARK_Mode (On);

package WebMCP_Packet_Filter is

   Max_Method_Len : constant := 64;
   Max_Param_Len  : constant := 512;

   subtype Method_String is String (1 .. Max_Method_Len);
   subtype Param_String  is String (1 .. Max_Param_Len);

   type Filter_Verdict is (Packet_Accepted, Method_Too_Long, Payload_Overflow, Traversal_Detected);

   type Validated_Packet is record
      Verdict     : Filter_Verdict;
      Method_Name : Method_String := [others => ' '];
      Method_Len  : Natural range 0 .. Max_Method_Len := 0;
      Param_Len   : Natural range 0 .. Max_Param_Len  := 0;
   end record;

   -- Formálně verifikovaná kontrola a filtrace WebMCP packetu
   procedure Inspect_Packet (
      Raw_Method : in  String;
      Param_Size : in  Natural;
      Packet     : out Validated_Packet
   )
   with
      Global  => null,
      Depends => (Packet => (Raw_Method, Param_Size)),
      Post    => (if Packet.Verdict = Packet_Accepted then
                     Packet.Method_Len in 1 .. Max_Method_Len and then
                     Packet.Param_Len <= Max_Param_Len
                  else
                     Packet.Method_Len = 0);

end WebMCP_Packet_Filter;
