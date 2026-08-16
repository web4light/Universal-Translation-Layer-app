-- ============================================================
--  Lada Agent — Implementation
--  "Svejk by to nakreslil lip, ale Lada to proved."
-- ============================================================

pragma SPARK_Mode (On);

package body Lada_Agent is

   -- =========================================================
   --  Is_Valid_Request
   -- =========================================================

   function Is_Valid_Request (Req : Lada_Request) return Boolean is
   begin
      -- Prazdny prompt = nevalidni
      if Req.Prompt_Len = 0 then
         return False;
      end if;

      -- NSFW check
      if not Req.Is_NSFW_Safe then
         return False;
      end if;

      -- Prilis kratky prompt (< 3 znaky = nesmysl)
      if Req.Prompt_Len < 3 then
         return False;
      end if;

      return True;
   end Is_Valid_Request;

   -- =========================================================
   --  Validate
   -- =========================================================

   procedure Validate (Req : in out Lada_Request) is
   begin
      if not Is_Valid_Request (Req) then
         Req.Status := Failed;
         return;
      end if;

      -- Default styl pro ruzne typy
      case Req.Kind is
         when Logo | Icon_Set =>
            Req.Style := Minimalist;
            Req.Size := Medium;
         when UI_Mockup =>
            Req.Style := Minimalist;
            Req.Size := Wide;
         when Asset_3D =>
            Req.Style := Realistic;
            Req.Size := Large;
         when Color_Palette =>
            Req.Style := Abstract_Art;
            Req.Size := Small;
         when Image_PNG | Image_SVG =>
            null;  -- ponech co uzivatel zvolil
      end case;

      Req.Status := Validated;
   end Validate;

   -- =========================================================
   --  Complete
   -- =========================================================

   procedure Complete (Req : in out Lada_Request) is
   begin
      Req.Status := Completed;
   end Complete;

   -- =========================================================
   --  Fail
   -- =========================================================

   procedure Fail (Req : in out Lada_Request) is
   begin
      Req.Status := Failed;
   end Fail;

   -- =========================================================
   --  Count_Generation
   -- =========================================================

   procedure Count_Generation (Counter : in out Generation_Counter) is
   begin
      Counter := Counter + 1;
   end Count_Generation;

   -- =========================================================
   --  Count_Failure
   -- =========================================================

   procedure Count_Failure (Counter : in out Generation_Counter) is
   begin
      Counter := Counter + 1;
   end Count_Failure;

end Lada_Agent;
