pragma SPARK_Mode (On);

-- ============================================================
--  Gemini Types — Implementation
--  "SPARK se uci cesky pres Gemini."
-- ============================================================

package body Gemini_Types is

   function Is_Valid_Request (Req : Gemini_Request) return Boolean is
   begin
      if Req.Prompt_Len = 0 then
         return False;
      end if;

      if not Req.Has_Key then
         return False;
      end if;

      return True;
   end Is_Valid_Request;

   function Is_Usable (Resp : Gemini_Response) return Boolean is
   begin
      return Resp.Status = OK and Resp.Response_Len > 0;
   end Is_Usable;

end Gemini_Types;
