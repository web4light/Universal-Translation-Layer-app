package Gemini.Http is

   -- No SPARK mode here as we rely on external OS calls

   type Response is record
      Status_Code   : Natural;
      Response_Body : String (1 .. 16384);
      Body_Length   : Natural := 0;
      Success       : Boolean := False;
   end record;

   -- Make a POST request to the given URL with the JSON payload
   function Post
     (URL          : String;
      API_Key      : String;
      Payload_JSON : String) return Response;

end Gemini.Http;
