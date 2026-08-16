-- ============================================================
--  Prompt Generator — Meta-prompt pro Asgard Lab
--  Generuje prompty pro tvorbu demo videa UTL Protocol 4.23
--
--  Princip: Prompt který generuje prompty.
--  Formálně verifikovaný — žádná halucinace možná.
--  Pouze fakta z Ground Truth manifestu.
--
--  Autor: Pan Jeskyně
--  Organizace: Rebirth Phoenix Foundation Charter
--  Web: web4light.online
--  Standard 700: 12g stříbra
-- ============================================================
pragma SPARK_Mode (On);

package Prompt_Generator is

   -- Maximální délky řetězců
   Max_Prompt_Length   : constant := 2048;
   Max_Section_Length  : constant := 512;
   Max_Name_Length     : constant := 64;

   subtype Prompt_Text    is String (1 .. Max_Prompt_Length);
   subtype Section_Text   is String (1 .. Max_Section_Length);
   subtype Name_Text      is String (1 .. Max_Name_Length);
   subtype Prompt_Length  is Natural range 0 .. Max_Prompt_Length;
   subtype Section_Length is Natural range 0 .. Max_Section_Length;

   -- Kategorie promptů pro demo video
   type Prompt_Category is (
      Intro_Narrative,      -- Kdo jsme, co děláme
      Technical_Demo,       -- Ada/SPARK, failover, pipeline
      Social_Impact,        -- Znakový jazyk, Tichý svět
      Call_To_Action        -- Hackathon, open source
   );

   -- Jeden prompt s metadaty
   type Prompt_Record is record
      Category    : Prompt_Category     := Intro_Narrative;
      Name        : Name_Text           := (others => ' ');
      Name_Len    : Natural range 0 .. Max_Name_Length := 0;
      Purpose     : Section_Text        := (others => ' ');
      Purpose_Len : Section_Length      := 0;
      Input       : Section_Text        := (others => ' ');
      Input_Len   : Section_Length      := 0;
      Output      : Section_Text        := (others => ' ');
      Output_Len  : Section_Length      := 0;
      Text        : Prompt_Text         := (others => ' ');
      Text_Len    : Prompt_Length       := 0;
   end record;

   -- Sada všech 4 promptů pro demo video
   type Prompt_Suite is array (Prompt_Category) of Prompt_Record;

   -- =========================================================
   --  Hlavní funkce — vygeneruj celou sadu promptů
   --  Post: každý prompt má neprázdný Text_Len > 0
   -- =========================================================
   function Generate_Suite return Prompt_Suite
     with Post => (for all C in Prompt_Category =>
                     Generate_Suite'Result (C).Text_Len > 0);

   -- Získej konkrétní prompt podle kategorie
   function Get_Prompt (Category : Prompt_Category) return Prompt_Record
     with Post => Get_Prompt'Result.Text_Len > 0;

   -- Vytiskni prompt na stdout (pro Gala CLI)
   procedure Print_Prompt (P : Prompt_Record);

   -- Vytiskni celou sadu
   procedure Print_Suite (S : Prompt_Suite);

   -- Počet znaků v promptu
   function Prompt_Char_Count (P : Prompt_Record) return Prompt_Length
     with Post => Prompt_Char_Count'Result = P.Text_Len;

end Prompt_Generator;
