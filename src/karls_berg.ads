-- ============================================================
--  Karls Berg — Ada/SPARK Most na NVIDIA AI
--
--  Karlův most spojoval dva břehy Vltavy (1357).
--  Karls Berg spojuje SPARK a NVIDIA (2026).
--
--  Funkce:
--  - Překlad přes NVIDIA Riva Translate
--  - Voice cloning přes Spark-TTS (RTX 3070)
--  - SPARK ověřuje vstup/výstup
--
--  Autor: Pan Jeskyně
--  Verifikace: gnatprove
-- ============================================================

pragma SPARK_Mode (On);

package Karls_Berg is

   -- Maximální délky
   Max_Text_Length    : constant := 4_096;
   Max_Response_Length : constant := 8_192;
   Max_API_Key_Length : constant := 128;
   Max_URL_Length     : constant := 256;

   -- Typy
   subtype Text_Length is Natural range 0 .. Max_Text_Length;
   subtype Response_Length is Natural range 0 .. Max_Response_Length;

   -- Podporované jazyky (40 jazyků NVIDIA Riva)
   type Language is (CS, EN, DE, FR, ES, IT, JA, KO, ZH, RU,
                     PL, SK, PT, NL, SV, DA, NO, FI, TR, AR,
                     HI, UK, EL, HU, RO, BG, HR, SR, SL, ET,
                     LV, LT, TH, VI, ID, MS, TL, HE, FA, UR);

   -- Stav mostu
   type Bridge_State is (Disconnected, Ready, Translating, Synthesizing, Error);

   -- Request na překlad
   type Translate_Request is record
      Source_Lang : Language := EN;
      Target_Lang : Language := CS;
      Text_Len    : Text_Length := 0;
      Text        : String (1 .. Max_Text_Length) := (others => ' ');
   end record;

   -- Response z překladu
   type Translate_Response is record
      Success     : Boolean := False;
      Text_Len    : Response_Length := 0;
      Text        : String (1 .. Max_Response_Length) := (others => ' ');
   end record;

   -- Most (state machine)
   type Bridge is record
      State    : Bridge_State := Disconnected;
      API_Key_Len : Natural range 0 .. Max_API_Key_Length := 0;
      API_Key  : String (1 .. Max_API_Key_Length) := (others => ' ');
   end record;

   -- =========================================================
   --  Kontrakty
   -- =========================================================

   -- Inicializace mostu
   procedure Initialize (B       : out Bridge;
                         API_Key : String)
     with Pre  => API_Key'Length > 0
                  and API_Key'Length <= Max_API_Key_Length,
          Post => B.State = Ready
                  and B.API_Key_Len = API_Key'Length;

   -- Překlad textu
   procedure Translate (B        : in out Bridge;
                        Request  : Translate_Request;
                        Response : out Translate_Response)
     with Pre  => B.State = Ready
                  and Request.Text_Len > 0
                  and Request.Source_Lang /= Request.Target_Lang,
          Post => B.State = Ready;

   -- Validace textu (žádné šipky, žádné artefakty)
   function Is_Clean_Text (Text : String) return Boolean;

   -- Vyčistit text před překladem
   procedure Clean_Text (Input  : String;
                         Output : out String;
                         Length : out Text_Length)
     with Pre  => Input'Length <= Max_Text_Length,
          Post => Length <= Input'Length;

end Karls_Berg;
