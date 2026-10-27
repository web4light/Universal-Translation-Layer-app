pragma SPARK_Mode (On);

package body Progress_Analyzer is

   procedure Analyze_Log (
      Log_Line : in String; 
      Result   : out Analysis_Result
   ) is
      Found_Success : Boolean := False;
      Found_Error   : Boolean := False;
      Temp_Msg      : Msg_String := [others => ' '];
   begin
      -- Jednoduchá, ale formálně ověřitelná logika analýzy
      -- Bezpečné indexování s ohledem na Log_Line'First a délku
      if Log_Line'Length >= 6 then
         if Log_Line (Log_Line'First .. Log_Line'First + 5) = "PASSED" then
            Found_Success := True;
         elsif Log_Line (Log_Line'First .. Log_Line'First + 4) = "ERROR" then
            Found_Error := True;
         end if;
      elsif Log_Line'Length >= 5 then
         if Log_Line (Log_Line'First .. Log_Line'First + 4) = "ERROR" then
            Found_Error := True;
         end if;
      end if;

      -- Rozhodovací logika pokrývající všechny větve (SPARK inicializace OUT parametru)
      if Found_Success then
         Result.Status := Success;
         Temp_Msg (1 .. 15) := "Formal Proof OK";
         Result.Summary := Temp_Msg;
      elsif Found_Error then
         Result.Status := Failure;
         Temp_Msg (1 .. 10) := "Build Fail";
         Result.Summary := Temp_Msg;
      else
         Result.Status := Warning;
         Temp_Msg (1 .. 9) := "No Change";
         Result.Summary := Temp_Msg;
      end if;
   end Analyze_Log;

end Progress_Analyzer;
