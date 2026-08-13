with Gemini.Types;
with Gemini.Http;

package Gemini.Api is

   type Generation_Config is record
      Temperature : Float range 0.0 .. 2.0 := 1.0;
      Max_Tokens  : Natural range 1 .. 8192 := 2048;
   end record;

   -- Generates content from the model based on the provided prompt and configuration
   -- This calls the external HTTP service, so it is not in SPARK_Mode (On)
   function Generate_Content
     (Project_ID : String;
      Location   : String;
      API_Key    : String;
      Prompt     : String) return String;

end Gemini.Api;
