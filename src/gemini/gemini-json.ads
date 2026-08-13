pragma SPARK_Mode (On);

with Gemini.Types; use Gemini.Types;

package Gemini.Json is

   -- Maximum length of the generated JSON string
   Max_Json_Length : constant := 16384;
   
   subtype Json_String_Index is Natural range 0 .. Max_Json_Length;
   subtype Bounded_Json_String is String (1 .. Max_Json_Length);
   
   type Json_Buffer is record
      Length : Json_String_Index := 0;
      Data   : Bounded_Json_String := (others => ' ');
   end record;
   
   -- Serializes a Request_Body into a JSON string
   procedure Serialize (Request : Request_Body; Buffer : out Json_Buffer)
     with Post => Buffer.Length <= Max_Json_Length;

end Gemini.Json;
