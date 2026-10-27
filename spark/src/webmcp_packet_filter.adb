pragma SPARK_Mode (On);

package body WebMCP_Packet_Filter is

   procedure Inspect_Packet (
      Raw_Method : in  String;
      Param_Size : in  Natural;
      Packet     : out Validated_Packet
   ) is
      Has_Traversal : Boolean := False;
      Clean_Name    : Method_String := [others => ' '];
      M_Len         : Natural;
   begin
      if Raw_Method'Length = 0 or else Raw_Method'Length > Max_Method_Len then
         Packet.Verdict     := Method_Too_Long;
         Packet.Method_Name := [others => ' '];
         Packet.Method_Len  := 0;
         Packet.Param_Len   := 0;
         return;
      end if;

      if Param_Size > Max_Param_Len then
         Packet.Verdict     := Payload_Overflow;
         Packet.Method_Name := [others => ' '];
         Packet.Method_Len  := 0;
         Packet.Param_Len   := 0;
         return;
      end if;

      M_Len := Raw_Method'Length;

      -- Detekce nebezpečných traversal a injection sekvencí
      for I in Raw_Method'Range loop
         if Raw_Method (I) = '.' or else
            Raw_Method (I) = '/' or else
            Raw_Method (I) = '\' or else
            Raw_Method (I) = Character'Val (0)
         then
            Has_Traversal := True;
         end if;
      end loop;

      if Has_Traversal then
         Packet.Verdict     := Traversal_Detected;
         Packet.Method_Name := [others => ' '];
         Packet.Method_Len  := 0;
         Packet.Param_Len   := 0;
      else
         for J in 1 .. M_Len loop
            Clean_Name (J) := Raw_Method (Raw_Method'First + (J - 1));
         end loop;

         Packet.Verdict     := Packet_Accepted;
         Packet.Method_Name := Clean_Name;
         Packet.Method_Len  := M_Len;
         Packet.Param_Len   := Param_Size;
      end if;
   end Inspect_Packet;

end WebMCP_Packet_Filter;
