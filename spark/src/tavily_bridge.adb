pragma SPARK_Mode (On);

package body Tavily_Bridge is

   procedure Validate_Query (
      Raw_Input : in  String;
      Fact      : out Validation_Fact
   ) is
      Has_Forbidden : Boolean := False;
      Copy_Len      : Natural;
      Clean_Buffer  : Query_String := [others => ' '];
   begin
      -- Kontrola délky bufferu
      if Raw_Input'Length = 0 or else Raw_Input'Length > Max_Query_Len then
         Fact.Status       := Buffer_Exceeded;
         Fact.Sanitized    := [others => ' '];
         Fact.Query_Length := 0;
         return;
      end if;

      Copy_Len := Raw_Input'Length;

      -- Formální kontrola nebezpečných řídicích a injekčních znaků
      for I in Raw_Input'Range loop
         if Raw_Input (I) = ';' or else
            Raw_Input (I) = '|' or else
            Raw_Input (I) = '&' or else
            Raw_Input (I) = '`' or else
            Raw_Input (I) = '$'
         then
            Has_Forbidden := True;
         end if;
      end loop;

      if Has_Forbidden then
         Fact.Status       := Injection_Blocked;
         Fact.Sanitized    := [others => ' '];
         Fact.Query_Length := 0;
      else
         for J in 1 .. Copy_Len loop
            Clean_Buffer (J) := Raw_Input (Raw_Input'First + (J - 1));
         end loop;

         Fact.Status       := Secure_Ok;
         Fact.Sanitized    := Clean_Buffer;
         Fact.Query_Length := Copy_Len;
      end if;
   end Validate_Query;

end Tavily_Bridge;
