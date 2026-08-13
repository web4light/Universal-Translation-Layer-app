-- ============================================================
--  Cave Lab Core — Implementation
--  "Prvni malby jsou z jeskyni."
-- ============================================================

pragma SPARK_Mode (On);

package body Cave_Lab_Core is

   -- =========================================================
   --  Is_Safe_Prompt
   -- =========================================================

   function Is_Safe_Prompt (Prompt_Len : Prompt_Length) return Boolean is
   begin
      -- Prazdny prompt = nebezpecny (nic nedelat)
      if Prompt_Len = 0 then
         return False;
      end if;

      -- Prilis dlouhy = podezrely
      if Prompt_Len > Max_Prompt_Length then
         return False;
      end if;

      -- Validni prompt
      return True;
   end Is_Safe_Prompt;

   -- =========================================================
   --  Validate_Project
   -- =========================================================

   procedure Validate_Project (Info : in out Project_Info) is
   begin
      if not Is_Safe_Prompt (Info.Prompt_Len) then
         Info.Status := Failed;
         return;
      end if;

      -- Detekce typu
      Info.Kind := Detect_Kind (Info.Prompt_Len);

      -- Defaultni schema podle typu
      case Info.Kind is
         when Web_Landing | Web_Portfolio | Graphics_Only =>
            Info.Scheme := Dark;
         when Web_Business | Web_Store | Web_Blog =>
            Info.Scheme := Light;
      end case;

      -- Responsive vzdy
      Info.Is_Responsive := True;

      -- Grafika pro vsechny typy krome Graphics_Only (tam je JEN grafika)
      Info.Has_Graphics := True;

      Info.Status := Validated;
   end Validate_Project;

   -- =========================================================
   --  Detect_Kind
   -- =========================================================

   function Detect_Kind (Prompt_Len : Prompt_Length) return Project_Kind is
   begin
      -- Jednoducha heuristika podle delky
      -- (plna verze bude porovnavat klicova slova)
      if Prompt_Len <= 30 then
         return Web_Landing;
      elsif Prompt_Len <= 80 then
         return Web_Business;
      elsif Prompt_Len <= 150 then
         return Web_Portfolio;
      else
         return Web_Store;
      end if;
   end Detect_Kind;

   -- =========================================================
   --  Increment
   -- =========================================================

   procedure Increment (Counter : in out Project_Counter) is
   begin
      Counter := Counter + 1;
   end Increment;

   -- =========================================================
   --  Is_Complete
   -- =========================================================

   function Is_Complete (Info : Project_Info) return Boolean is
   begin
      return Info.Status = Completed and Info.Filename_Len > 0;
   end Is_Complete;

end Cave_Lab_Core;
