-- ============================================================
--  PJAY Generator — AST → Ada/SPARK kód
--
--  Vstup: AST z pjay_parser
--  Výstup: Ada source code (bounded string)
--
--  procedura X est → procedure X is
--  incipit → begin
--  Hoc est via: → deklarace
--  Locutus sum: → sekvence volání
--  Ego sum Groot: → if ... then SIC else NON
--  Latratus! → Put_Line (alert)
--  finis X → end X;
--
--  SPARK proved — výstup nikdy nepřeteče buffer.
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (On);

with PJAY_Parser; use PJAY_Parser;

package PJAY_Generator is

   Max_Output : constant := 65_536;
   subtype Output_Length is Natural range 0 .. Max_Output;

   type Generated_Code is record
      Length  : Output_Length := 0;
      Success : Boolean := False;
   end record;

   -- Generuj Ada kód z AST
   procedure Generate (Tree   : AST;
                       Code   : out Generated_Code)
     with Pre  => Is_Valid (Tree),
          Post => Code.Success;

   -- Kolik řádků vygenerováno?
   function Lines_Generated (Code : Generated_Code) return Natural;

end PJAY_Generator;
