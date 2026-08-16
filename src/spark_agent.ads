-- ============================================================
--  SPARK Agent — Formálně Verifikovaný Autonomní Agent Jádra
--  Ada/SPARK 2022 — Nativní SPARK implementace agenta
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Účel:
--  Formálně verifikovaný agent pro autonomní řízení úloh,
--  generování a validaci kódu s matematickou jistotou (gnatprove Level 2).
--
--  Pravidla:
--  - Žádné alokace (new/Free)
--  - Žádné pointery (access)
--  - Žádné výjimky (raise)
--  - Žádné Unchecked konverze
--  - Striktní ranged types a Pre/Post kontrakty
-- ============================================================

pragma SPARK_Mode (On);

package SPARK_Agent is

   -- ==========================================================
   -- KONSTANTY
   -- ==========================================================

   Max_Agent_Memory_Bytes : constant := 65_536;
   Max_Reasoning_Steps    : constant := 100;
   Max_Tool_Calls         : constant := 16;
   Max_Text_Buffer        : constant := 256;

   -- ==========================================================
   -- TYPY A ROZSAHY
   -- ==========================================================

   subtype Memory_Index is Natural range 0 .. Max_Agent_Memory_Bytes;
   subtype Step_Index   is Natural range 0 .. Max_Reasoning_Steps;
   subtype Tool_Index   is Natural range 0 .. Max_Tool_Calls;
   subtype Text_Length  is Natural range 0 .. Max_Text_Buffer;

   type Agent_State is (Idle, Reasoning, Executing_Tool, Verifying, Finished, Error_State);
   type Tool_Type   is (Tool_Code_Execution, Tool_Filesystem, Tool_Gnatprove, Tool_Telemetry);

   type Bounded_String is record
      Length : Text_Length := 0;
      Data   : String (1 .. Max_Text_Buffer) := (others => ' ');
   end record;

   type Tool_Call_Record is record
      Tool        : Tool_Type := Tool_Code_Execution;
      Is_Executed : Boolean := False;
      Succeeded   : Boolean := False;
   end record;

   type Tool_Call_Array is array (1 .. Max_Tool_Calls) of Tool_Call_Record;

   type Agent_Context is record
      State           : Agent_State     := Idle;
      Steps_Executed  : Step_Index      := 0;
      Tools_Used      : Tool_Index      := 0;
      Active_Tools    : Tool_Call_Array := (others => (Tool => Tool_Code_Execution, Is_Executed => False, Succeeded => False));
      Goal_Achieved   : Boolean         := False;
      Contract_Passed : Boolean         := True;
   end record;

   -- ==========================================================
   -- OPERACE AGENTA
   -- ==========================================================

   -- Inicializace kontextu agenta
   procedure Initialize (Ctx : out Agent_Context)
     with Post => Ctx.State = Idle and then
                  Ctx.Steps_Executed = 0 and then
                  Ctx.Tools_Used = 0 and then
                  not Ctx.Goal_Achieved and then
                  Ctx.Contract_Passed;

   -- Krok uvažování (Reasoning cycle)
   procedure Step_Reasoning (Ctx     : in out Agent_Context;
                             Success : out Boolean)
     with Pre  => Ctx.State in Idle | Reasoning | Verifying and then
                  Ctx.Steps_Executed < Max_Reasoning_Steps,
          Post => (if Success then
                      Ctx.Steps_Executed = Ctx.Steps_Executed'Old + 1 and then
                      Ctx.State in Reasoning | Verifying | Finished
                   else
                      Ctx.State = Error_State);

   -- Naplánování a validace nástroje
   procedure Invoke_Tool (Ctx       : in out Agent_Context;
                          Tool      : Tool_Type;
                          Executed  : out Boolean)
     with Pre  => Ctx.State = Reasoning and then
                  Ctx.Tools_Used < Max_Tool_Calls,
          Post => (if Executed then
                      Ctx.Tools_Used = Ctx.Tools_Used'Old + 1 and then
                      Ctx.Active_Tools (Ctx.Tools_Used).Is_Executed
                   else
                      Ctx.Tools_Used = Ctx.Tools_Used'Old);

   -- Formální závěrečné ověření stavu
   procedure Finalize_Goal (Ctx     : in out Agent_Context;
                            Success : out Boolean)
     with Pre  => Ctx.State in Reasoning | Verifying,
          Post => (if Success then
                      Ctx.State = Finished and then
                      Ctx.Goal_Achieved and then
                      Ctx.Contract_Passed
                   else
                      Ctx.State = Error_State);

end SPARK_Agent;
