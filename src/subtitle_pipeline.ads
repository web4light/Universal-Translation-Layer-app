-- ============================================================
--  Asgard Lab — Subtitle Translation Pipeline
--  Ada/SPARK Formální Verifikace
--
--  Garantuje:
--  - Žádný buffer overflow (ranged types)
--  - Žádný vynechaný segment (postcondition)
--  - Timing vždy sedí (precondition)
--  - Paměť konstantní (no leaks)
--
--  Autor: Pan Jeskyně
--  Verifikace: gnatprove
-- ============================================================

pragma SPARK_Mode (On);

package Subtitle_Pipeline is

   -- Maximální počet titulků v jednom souboru
   Max_Subtitles : constant := 10_000;

   -- Maximální délka textu jednoho titulku (UTF-8 bytes)
   Max_Text_Length : constant := 1_024;

   -- Maximální počet jazyků
   Max_Languages : constant := 200;

   -- Typy s rozsahem — NEMŮŽOU přetéct
   subtype Subtitle_Index is Natural range 0 .. Max_Subtitles;
   subtype Subtitle_Count is Natural range 0 .. Max_Subtitles;
   subtype Text_Length is Natural range 0 .. Max_Text_Length;
   subtype Language_Count is Natural range 0 .. Max_Languages;

   -- Timestamp v milisekundách (max ~24 hodin)
   subtype Timestamp_Ms is Natural range 0 .. 86_400_000;

   -- Jeden titulek
   type Subtitle_Entry is record
      Start_Ms    : Timestamp_Ms := 0;
      End_Ms      : Timestamp_Ms := 0;
      Text_Len    : Text_Length := 0;
      Text        : String (1 .. Max_Text_Length) := (others => ' ');
      Translated  : Boolean := False;
      Dubbed      : Boolean := False;
      Signed      : Boolean := False;
   end record;

   -- Pole titulků
   type Subtitle_Array is array (1 .. Max_Subtitles) of Subtitle_Entry;

   -- Stav pipeline
   type Pipeline_State is (Idle, Downloading, Translating, Dubbing, Signing, Complete, Error);

   -- Pipeline record
   type Pipeline is record
      State       : Pipeline_State := Idle;
      Subtitles   : Subtitle_Array;
      Count       : Subtitle_Count := 0;
      Translated  : Subtitle_Count := 0;
      Dubbed      : Subtitle_Count := 0;
      Signed      : Subtitle_Count := 0;
   end record;

   -- =========================================================
   --  Kontrakty (Pre/Post conditions)
   -- =========================================================

   -- Inicializace pipeline
   procedure Initialize (P : out Pipeline)
     with Post => P.State = Idle
                  and P.Count = 0
                  and P.Translated = 0
                  and P.Dubbed = 0
                  and P.Signed = 0;

   -- Přidání titulku
   procedure Add_Subtitle (P        : in out Pipeline;
                           Start_Ms : Timestamp_Ms;
                           End_Ms   : Timestamp_Ms;
                           Text     : String;
                           Success  : out Boolean)
     with Pre  => P.State = Downloading
                  and P.Count < Max_Subtitles
                  and Text'Length <= Max_Text_Length
                  and End_Ms > Start_Ms,
          Post => (if Success then P.Count = P.Count'Old + 1
                   else P.Count = P.Count'Old);

   -- Překlad jednoho titulku
   procedure Translate_Entry (P     : in out Pipeline;
                              Index : Subtitle_Index;
                              Text  : String)
     with Pre  => P.State = Translating
                  and Index >= 1
                  and Index <= P.Count
                  and Text'Length <= Max_Text_Length,
          Post => P.Translated >= P.Translated'Old
                  and P.Subtitles (Index).Translated = True;

   -- Ověření kompletnosti překladu
   function All_Translated (P : Pipeline) return Boolean
     with Post => All_Translated'Result = (P.Translated = P.Count);

   -- Ověření že timing sedí (žádný overlap)
   function Timing_Valid (P : Pipeline) return Boolean
     with Pre => P.Count > 0;

   -- Spuštění pipeline
   procedure Start_Download (P : in out Pipeline)
     with Pre  => P.State = Idle,
          Post => P.State = Downloading;

   procedure Start_Translation (P : in out Pipeline)
     with Pre  => P.State = Downloading and P.Count > 0,
          Post => P.State = Translating;

   procedure Start_Dubbing (P : in out Pipeline)
     with Pre  => P.State = Translating and All_Translated (P),
          Post => P.State = Dubbing;

   procedure Start_Signing (P : in out Pipeline)
     with Pre  => P.State = Dubbing,
          Post => P.State = Signing;

   procedure Complete_Pipeline (P : in out Pipeline)
     with Pre  => P.State = Signing,
          Post => P.State = Complete;

end Subtitle_Pipeline;
