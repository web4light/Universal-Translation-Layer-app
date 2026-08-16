-- ============================================================
--  PJAY Generator — Implementation
--  AST → Ada/SPARK
-- ============================================================

pragma SPARK_Mode (On);

package body PJAY_Generator is

   procedure Generate (Tree : AST;
                       Code : out Generated_Code) is
   begin
      -- Placeholder: skutečná implementace bude procházet AST
      -- a generovat Ada kód řádek po řádku
      Code.Length := 0;
      Code.Success := True;
   end Generate;

   function Lines_Generated (Code : Generated_Code) return Natural is
   begin
      -- Přibližný odhad: 1 řádek = ~40 znaků
      if Code.Length = 0 then
         return 0;
      end if;
      return Code.Length / 40 + 1;
   end Lines_Generated;

end PJAY_Generator;
