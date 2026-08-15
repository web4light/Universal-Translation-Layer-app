-- ============================================================
--  PJAY Parser — Implementation
-- ============================================================

pragma SPARK_Mode (On);

package body PJAY_Parser is

   procedure Parse (Tree   : out AST;
                    Result : out Parse_Result) is
   begin
      Tree := (Procs      => (others => <>),
               Num_Procs  => 0,
               Stmts      => (others => <>),
               Num_Stmts  => 0,
               Has_Error  => False,
               Error_Line => 1);
      Result := Parse_OK;
   end Parse;

   function Is_Valid (Tree : AST) return Boolean is
   begin
      return Tree.Num_Procs > 0 and not Tree.Has_Error;
   end Is_Valid;

end PJAY_Parser;
