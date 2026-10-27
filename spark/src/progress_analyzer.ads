pragma SPARK_Mode (On);

package Progress_Analyzer is

   type Verification_Status is (Success, Failure, Warning);
   
   -- Maximální délka zprávy pro n8n
   Max_Msg_Len : constant := 128;
   subtype Msg_String is String (1 .. Max_Msg_Len);

   -- Struktura výsledku pro n8n
   type Analysis_Result is record
      Status  : Verification_Status;
      Summary : Msg_String := [others => ' '];
   end record;

   -- Procedura, která analyzuje log z gnatprove
   -- Vstup: Log (převedený z textu)
   -- Výstup: Result (strukturovaný fakt)
   procedure Analyze_Log (
      Log_Line : in String; 
      Result   : out Analysis_Result
   )
   with Post => 
     (if Result.Status = Success then 
         Result.Summary /= Msg_String'[others => ' '] 
      else 
         True);

end Progress_Analyzer;
