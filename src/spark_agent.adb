-- ============================================================
--  SPARK Agent — Implementace Formálně Verifikovaného Agenta
--  Ada/SPARK 2022 — Nativní tělo
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (On);

package body SPARK_Agent is

   -- ==========================================================
   -- INICIALIZACE
   -- ==========================================================

   procedure Initialize (Ctx : out Agent_Context) is
   begin
      Ctx.State           := Idle;
      Ctx.Steps_Executed  := 0;
      Ctx.Tools_Used      := 0;
      Ctx.Goal_Achieved   := False;
      Ctx.Contract_Passed := True;

      for I in 1 .. Max_Tool_Calls loop
         Ctx.Active_Tools (I) := (Tool        => Tool_Code_Execution,
                                  Is_Executed => False,
                                  Succeeded   => False);
      end loop;
   end Initialize;

   -- ==========================================================
   -- REASONING KROK
   -- ==========================================================

   procedure Step_Reasoning (Ctx     : in out Agent_Context;
                             Success : out Boolean) is
   begin
      if Ctx.Steps_Executed < Max_Reasoning_Steps then
         Ctx.Steps_Executed := Ctx.Steps_Executed + 1;
         Ctx.State := Reasoning;
         Success := True;
      else
         Ctx.State := Error_State;
         Success := False;
      end if;
   end Step_Reasoning;

   -- ==========================================================
   -- VOLÁNÍ NÁSTROJE
   -- ==========================================================

   procedure Invoke_Tool (Ctx       : in out Agent_Context;
                          Tool      : Tool_Type;
                          Executed  : out Boolean) is
   begin
      if Ctx.Tools_Used < Max_Tool_Calls then
         Ctx.Tools_Used := Ctx.Tools_Used + 1;
         Ctx.Active_Tools (Ctx.Tools_Used) := (Tool        => Tool,
                                               Is_Executed => True,
                                               Succeeded   => True);
         Ctx.State := Verifying;
         Executed := True;
      else
         Executed := False;
      end if;
   end Invoke_Tool;

   -- ==========================================================
   -- ZÁVĚREČNÁ VERIFIKACE A CÍL
   -- ==========================================================

   procedure Finalize_Goal (Ctx     : in out Agent_Context;
                            Success : out Boolean) is
   begin
      if Ctx.Contract_Passed and then Ctx.Steps_Executed > 0 then
         Ctx.State := Finished;
         Ctx.Goal_Achieved := True;
         Success := True;
      else
         Ctx.State := Error_State;
         Ctx.Goal_Achieved := False;
         Success := False;
      end if;
   end Finalize_Goal;

end SPARK_Agent;
