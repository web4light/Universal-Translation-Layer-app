-- ============================================================
--  PJAY Parser — Syntakticky analyzator jazyka PJAY
--  Vstup: tokeny z pjay_lexer → Vystup: AST
--  SPARK proved.
--  Autor: Pan Jeskyne
-- ============================================================

pragma SPARK_Mode (On);

with PJAY_Lexer; use PJAY_Lexer;

package PJAY_Parser is

   Max_Procedures  : constant := 50;
   Max_Statements  : constant := 200;

   subtype Proc_Index is Natural range 0 .. Max_Procedures;
   subtype Stmt_Index is Natural range 0 .. Max_Statements;

   type Node_Kind is (Node_Procedure, Node_Hoc_Est_Via,
                      Node_Locutus_Sum, Node_Ego_Sum_Groot,
                      Node_Latratus, Node_Assignment, Node_Call);

   type Statement is record
      Kind     : Node_Kind := Node_Assignment;
      Name_Len : Token_Length := 0;
      Line     : Positive := 1;
   end record;

   type Procedure_Node is record
      Name_Len     : Token_Length := 0;
      Has_Hoc      : Boolean := False;
      Has_Locutus  : Boolean := False;
      Has_Groot    : Boolean := False;
      Has_Latratus : Boolean := False;
   end record;

   type Procedure_Array is array (1 .. Max_Procedures) of Procedure_Node;
   type Statement_Array is array (1 .. Max_Statements) of Statement;

   type AST is record
      Procs      : Procedure_Array;
      Num_Procs  : Proc_Index := 0;
      Stmts      : Statement_Array;
      Num_Stmts  : Stmt_Index := 0;
      Has_Error  : Boolean := False;
      Error_Line : Positive := 1;
   end record;

   type Parse_Result is (Parse_OK, Parse_Error);

   procedure Parse (Tree   : out AST;
                    Result : out Parse_Result)
     with Post => (if Result = Parse_OK then not Tree.Has_Error);

   function Is_Valid (Tree : AST) return Boolean
     with Post => Is_Valid'Result = (Tree.Num_Procs > 0 and not Tree.Has_Error);

end PJAY_Parser;
