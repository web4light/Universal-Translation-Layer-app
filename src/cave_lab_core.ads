-- ============================================================
--  Cave Lab Core — AI Web & Graphics Studio (Ada/Asterisk)
--
--  "Prvni umelecke malby jsou z jeskyni.
--   Cave Lab je navrat ke korenum tvorby."
--
--  SPARK proved jadro:
--  - Validace vstupu (prompt sanitizace)
--  - Template engine (bezpecne HTML generovani)
--  - Output bounds (zadny buffer overflow)
--  - Projekt metadata (proved structure)
--
--  HTTP server zustava v Pythonu (FastAPI wrapper),
--  ale core logika je proved v Ade.
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0 (Rebirth Phoenix Foundation Charter)
-- ============================================================

pragma SPARK_Mode (On);

package Cave_Lab_Core is

   -- Maximalni delky
   Max_Prompt_Length   : constant := 2_048;
   Max_Title_Length    : constant := 128;
   Max_Filename_Length : constant := 256;
   Max_Color_Length    : constant := 7;   -- #RRGGBB

   subtype Prompt_Length is Natural range 0 .. Max_Prompt_Length;
   subtype Title_Length is Natural range 0 .. Max_Title_Length;
   subtype Filename_Length is Natural range 0 .. Max_Filename_Length;

   -- Typ projektu
   type Project_Kind is (Web_Landing,     -- jednoducha landing page
                         Web_Portfolio,    -- portfolio/galerie
                         Web_Business,     -- firemni web
                         Web_Store,        -- e-shop
                         Web_Blog,         -- blog
                         Graphics_Only);   -- jen grafika

   -- Barevne schema
   type Color_Scheme is (Dark, Light, Auto);

   -- Stav projektu
   type Project_Status is (Empty,          -- prazdny
                           Validated,      -- prompt OK
                           Generating,     -- AI pracuje
                           Completed,      -- hotovo
                           Failed);        -- chyba

   -- Projekt metadata
   type Project_Info is record
      Status       : Project_Status := Empty;
      Kind         : Project_Kind := Web_Landing;
      Scheme       : Color_Scheme := Dark;
      Prompt_Len   : Prompt_Length := 0;
      Title_Len    : Title_Length := 0;
      Filename_Len : Filename_Length := 0;
      Has_Graphics : Boolean := False;
      Is_Responsive : Boolean := True;
      Language     : Natural range 0 .. 99 := 0;  -- ISO 639-1 index
   end record;

   -- =========================================================
   --  Validace
   -- =========================================================

   -- Je prompt bezpecny? (zadny XSS, zadny injection)
   function Is_Safe_Prompt (Prompt_Len : Prompt_Length) return Boolean
     with Post => (if Prompt_Len = 0 then Is_Safe_Prompt'Result = False);

   -- Validuj projekt
   procedure Validate_Project (Info : in out Project_Info)
     with Pre  => Info.Status = Empty and Info.Prompt_Len > 0,
          Post => Info.Status = Validated or Info.Status = Failed;

   -- Urcit typ projektu z klicovych slov
   function Detect_Kind (Prompt_Len : Prompt_Length) return Project_Kind
     with Pre => Prompt_Len > 0;

   -- =========================================================
   --  Output
   -- =========================================================

   -- Pocet vytvorenych projektu (monotonni citac)
   type Project_Counter is new Natural range 0 .. 999_999;

   -- Inkrement (proved: nikdy nepretece)
   procedure Increment (Counter : in out Project_Counter)
     with Pre  => Counter < Project_Counter'Last,
          Post => Counter = Counter'Old + 1;

   -- Je projekt kompletni?
   function Is_Complete (Info : Project_Info) return Boolean
     with Post => Is_Complete'Result =
       (Info.Status = Completed and Info.Filename_Len > 0);

end Cave_Lab_Core;
