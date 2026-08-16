with Gemini.Json;
with Ada.Strings.Fixed;

package body Gemini.Api is

   function Generate_Content
     (Project_ID : String;
      Location   : String;
      API_Key    : String;
      Prompt     : String) return String
   is
      use Gemini.Types;
      use Gemini.Json;
      use Gemini.Http;

      URL : constant String :=
        "https://" & Location & "-aiplatform.googleapis.com/v1/projects/" &
        Project_ID & "/locations/" & Location &
        "/publishers/google/models/gemini-2.0-flash:generateContent";

      Req     : Request_Body;
      Content : Gemini.Types.Content;
      Buffer  : Json_Buffer;
      Res     : Response;

   begin
      -- 1. Build the SPARK types
      Content := To_Content (User, Prompt);
      Req.Num_Contents := 1;
      Req.Contents (1) := Content;

      -- 2. Serialize to JSON (formally proven bounds)
      Serialize (Req, Buffer);

      -- 3. Perform HTTP request
      Res := Post (URL, API_Key, Buffer.Data (1 .. Buffer.Length));

      if not Res.Success then
         return "Error: HTTP request failed.";
      end if;

      -- 4. Very rudimentary JSON parsing to extract the model's response
      declare
         Pattern : constant String := """text"": """;
         Idx     : Natural := Ada.Strings.Fixed.Index
           (Res.Response_Body (1 .. Res.Body_Length), Pattern);
      begin
         if Idx > 0 then
            declare
               Start_Idx : constant Natural := Idx + Pattern'Length;
               End_Idx   : Natural := Ada.Strings.Fixed.Index
                 (Res.Response_Body (Start_Idx .. Res.Body_Length), """");
            begin
               if End_Idx > Start_Idx then
                  declare
                     Raw : constant String :=
                       Res.Response_Body (Start_Idx .. End_Idx - 1);
                  begin
                     return Raw;
                  end;
               end if;
            end;
         end if;
      end;

      return "Error: Could not parse response. " &
        Res.Response_Body (1 .. Res.Body_Length);
   end Generate_Content;

end Gemini.Api;
