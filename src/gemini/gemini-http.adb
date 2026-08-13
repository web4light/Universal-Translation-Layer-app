with GNAT.OS_Lib;
with Ada.Streams.Stream_IO;
with Ada.Text_IO;

package body Gemini.Http is

   function Post
     (URL          : String;
      API_Key      : String;
      Payload_JSON : String) return Response
   is
      use GNAT.OS_Lib;

      Result       : Response;

      -- Temporary files
      Req_File     : constant String := "gemini_req.json";
      Res_File     : constant String := "gemini_res.json";

      -- Stream_IO for writing the payload
      use Ada.Streams.Stream_IO;
      File         : File_Type;

      -- Arguments for curl
      Arg1 : String_Access := new String'("-s");
      Arg2 : String_Access := new String'("-w");
      Arg3 : String_Access := new String'("%{http_code}");
      Arg4 : String_Access := new String'("-X");
      Arg5 : String_Access := new String'("POST");
      Arg6 : String_Access := new String'("-H");
      Arg7 : String_Access := new String'("Content-Type: application/json");
      Arg8 : String_Access := new String'("-H");
      -- Adjust header based on whether it's an API Key or Bearer token
      -- For simplicity, we'll assume Bearer token if it's long, or x-goog-api-key
      -- Actually, we'll just pass Authorization: Bearer for Vertex AI
      Arg9 : String_Access := new String'("Authorization: Bearer " & API_Key);
      Arg10: String_Access := new String'("-d");
      Arg11: String_Access := new String'("@" & Req_File);
      Arg12: String_Access := new String'("-o");
      Arg13: String_Access := new String'(Res_File);
      Arg14: String_Access := new String'(URL);

      Args : Argument_List := 
        (Arg1, Arg2, Arg3, Arg4, Arg5, Arg6, Arg7, Arg8, Arg9, Arg10, 
         Arg11, Arg12, Arg13, Arg14);
      Success : Boolean;
   begin
      -- 1. Write the payload to a temporary file
      Create (File, Out_File, Req_File);
      String'Write (Stream (File), Payload_JSON);
      Close (File);

      -- 2. Execute curl
      Spawn ("curl", Args, Success);

      if not Success then
         Result.Success := False;
         return Result;
      end if;

      -- 3. Read the response body from the temporary file
      declare
         use Ada.Text_IO;
         Res_TIO : Ada.Text_IO.File_Type;
         Line    : String (1 .. 1024);
         Last    : Natural;
      begin
         Open (Res_TIO, In_File, Res_File);
         Result.Body_Length := 0;
         while not End_Of_File (Res_TIO) loop
            Get_Line (Res_TIO, Line, Last);
            if Result.Body_Length + Last <= Result.Response_Body'Length then
               Result.Response_Body
                 (Result.Body_Length + 1 .. Result.Body_Length + Last) :=
                 Line (1 .. Last);
               Result.Body_Length := Result.Body_Length + Last;
            end if;
         end loop;
         Close (Res_TIO);
         Result.Success := True;
         Result.Status_Code := 200; -- Simplification for now
      exception
         when others =>
            Result.Success := False;
      end;

      -- Free allocated arguments
      Free (Arg1); Free (Arg2); Free (Arg3); Free (Arg4); Free (Arg5);
      Free (Arg6); Free (Arg7); Free (Arg8); Free (Arg9); Free (Arg10);
      Free (Arg11); Free (Arg12); Free (Arg13); Free (Arg14);

      return Result;
   end Post;

end Gemini.Http;
