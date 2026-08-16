-- ============================================================
--  Karls Berg — Implementation
--  Most na NVIDIA Riva (curl subprocess)
-- ============================================================

pragma SPARK_Mode (On);

package body Karls_Berg is

   -- =========================================================
   procedure Initialize (B       : out Bridge;
                         API_Key : String) is
   begin
      B.State := Ready;
      B.API_Key_Len := API_Key'Length;
      B.API_Key := (others => ' ');
      B.API_Key (1 .. API_Key'Length) := API_Key;
   end Initialize;

   -- =========================================================
   function Is_Clean_Text (Text : String) return Boolean is
   begin
      for I in Text'Range loop
         -- Žádné >> (speaker markers)
         if I < Text'Last and then
           Text (I) = '>' and then Text (I + 1) = '>'
         then
            return False;
         end if;
         -- Žádné [ ] (sound effects)
         if Text (I) = '[' or Text (I) = ']' then
            return False;
         end if;
      end loop;
      return True;
   end Is_Clean_Text;

   -- =========================================================
   procedure Clean_Text (Input  : String;
                         Output : out String;
                         Length : out Text_Length) is
      pragma SPARK_Mode (Off);  -- Dynamic string indexing
      J : Natural := 0;
   begin
      Output := (others => ' ');

      for I in Input'Range loop
         if Input (I) /= '>'
           and Input (I) /= '['
           and Input (I) /= ']'
           and J < Max_Text_Length
         then
            J := J + 1;
            Output (J) := Input (I);
         end if;
      end loop;

      Length := J;
   end Clean_Text;

   -- =========================================================
   procedure Translate (B        : in out Bridge;
                        Request  : Translate_Request;
                        Response : out Translate_Response) is
      pragma SPARK_Mode (Off);  -- subprocess volání není SPARK
      --
      --  Zde volá: curl -s -X POST
      --    https://integrate.api.nvidia.com/v1/chat/completions
      --    -H "Authorization: Bearer <API_KEY>"
      --    -H "Content-Type: application/json"
      --    -d '{"model":"nvidia/riva-translate-4b-instruct-v2",
      --         "messages":[{"role":"user","content":"Translate to <lang>: <text>"}]}'
      --
      --  SPARK ověřuje vstup (precondition) a výstup (postcondition)
      --  Samotné volání curl je mimo SPARK mode (I/O)
      --
   begin
      --  Stub: v produkci zde bude GNAT.Expect + curl
      Response.Success := True;
      Response.Text_Len := Request.Text_Len;
      Response.Text (1 .. Request.Text_Len) :=
        Request.Text (1 .. Request.Text_Len);
   end Translate;

end Karls_Berg;
