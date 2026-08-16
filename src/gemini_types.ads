pragma SPARK_Mode (On);

-- ============================================================
--  Gemini Types — SPARK proved typy pro Gemini API
--
--  Bounded strings, validated requests, proved responses.
--  Zadny Unbounded_String. Zadny heap.
--  Vsechno na stacku, vsechno proved.
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0
-- ============================================================

package Gemini_Types is

   -- =========================================================
   --  Konstanty
   -- =========================================================

   Max_Prompt_Length   : constant := 8_192;
   Max_Response_Length : constant := 32_768;
   Max_Model_Length    : constant := 64;
   Max_Key_Length      : constant := 128;

   subtype Prm_Len is Natural range 0 .. Max_Prompt_Length;
   subtype Resp_Len is Natural range 0 .. Max_Response_Length;
   subtype Model_Len is Natural range 0 .. Max_Model_Length;
   subtype Key_Len is Natural range 0 .. Max_Key_Length;

   -- =========================================================
   --  Jazyk
   -- =========================================================

   type Language is (CS, EN, DE, FR, ES, IT, RU, JA, ZH,
                     KO, PT, AR, HI, VI, PL, NL, SV, TR);

   -- =========================================================
   --  Typ ukolu
   -- =========================================================

   type Task_Kind is (Translation,       -- preklad
                      Dubbing_Script,     -- skript pro dabing
                      Subtitle_Clean,     -- cisteni titulku
                      Voice_Prompt,       -- prompt pro TTS
                      Code_Generation,    -- generovani kodu
                      Image_Prompt);      -- prompt pro Lada

   -- =========================================================
   --  Request
   -- =========================================================

   subtype Temperature_Value is Natural range 0 .. 200;
   -- 0 = 0.00, 100 = 1.00, 200 = 2.00 (celociselne, proved)

   type Gemini_Request is record
      Job         : Task_Kind := Translation;
      Source_Lang : Language := EN;
      Target_Lang : Language := CS;
      Prompt_Len  : Prm_Len := 0;
      Max_Tokens  : Natural range 1 .. Max_Response_Length := 4_096;
      Temperature : Temperature_Value := 30;  -- 30 = 0.30
      Has_Key     : Boolean := False;
   end record;

   -- =========================================================
   --  Response
   -- =========================================================

   type Response_Status is (OK,           -- uspesna odpoved
                            Error_Auth,    -- spatny API klic
                            Error_Quota,   -- prekrocen limit
                            Error_Network, -- sit nedostupna
                            Error_Parse,   -- nesmyslna odpoved
                            Empty);        -- zadna odpoved

   type Gemini_Response is record
      Status       : Response_Status := Empty;
      Response_Len : Resp_Len := 0;
      Tokens_Used  : Natural range 0 .. 999_999 := 0;
      Truncated    : Boolean := False;
   end record;

   -- =========================================================
   --  Validace
   -- =========================================================

   -- Je request validni?
   function Is_Valid_Request (Req : Gemini_Request) return Boolean
     with Post => (if Req.Prompt_Len = 0 then
                     Is_Valid_Request'Result = False);

   -- Je response pouzitelna?
   function Is_Usable (Resp : Gemini_Response) return Boolean
     with Post => Is_Usable'Result =
                  (Resp.Status = OK and Resp.Response_Len > 0);

end Gemini_Types;
