pragma SPARK_Mode (On);

package body Gemini.Types is

   function To_Text_Part (S : String) return Text_Part is
      Result : Text_Part;
   begin
      Result.Length := S'Length;
      Result.Text (1 .. S'Length) := S;
      return Result;
   end To_Text_Part;

   function To_Content (Role : Role_Kind; Text : String) return Content is
      Result : Content;
   begin
      Result.Role := Role;
      Result.Num_Parts := 1;
      Result.Parts (1) := To_Text_Part (Text);
      return Result;
   end To_Content;

end Gemini.Types;
