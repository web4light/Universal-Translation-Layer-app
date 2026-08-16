-- ============================================================
--  Agent Komenský — Implementace Dozorce Úkolů
--  Ada/SPARK 2022 — Formálně verifikované jádro
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (On);

package body Agent_Komensky is

   -- ==========================================================
   -- INICIALIZACE
   -- ==========================================================

   procedure Initialize (K : out Komensky_Orchestrator) is
   begin
      K.Count        := 0;
      K.Active_ID    := 0;
      K.Total_Solved := 0;

      for I in 1 .. Max_Tasks loop
         K.Tasks (I) := (ID           => 0,
                         Phase        => Labyrinth_Analysis,
                         Progress_Pct => 0,
                         Completed    => False);
      end loop;
   end Initialize;

   -- ==========================================================
   -- ZAPSÁNÍ ÚLOHY
   -- ==========================================================

   procedure Register_Task (K       : in out Komensky_Orchestrator;
                            Success : out Boolean) is
   begin
      if K.Count < Max_Tasks then
         K.Count := K.Count + 1;
         K.Tasks (K.Count) := (ID           => K.Count,
                               Phase        => Labyrinth_Analysis,
                               Progress_Pct => 10,
                               Completed    => False);
         K.Active_ID := K.Count;
         Success := True;
      else
         Success := False;
      end if;
   end Register_Task;

   -- ==========================================================
   -- POSUNUTÍ FÁZE
   -- ==========================================================

   procedure Advance_Phase (K       : in out Komensky_Orchestrator;
                            Task_ID : Task_Index;
                            Success : out Boolean) is
   begin
      if Task_ID >= 1 and then Task_ID <= K.Count then
         case K.Tasks (Task_ID).Phase is
            when Labyrinth_Analysis =>
               K.Tasks (Task_ID).Phase := Janua_Translation;
               K.Tasks (Task_ID).Progress_Pct := 35;
               Success := True;

            when Janua_Translation =>
               K.Tasks (Task_ID).Phase := Orbis_Sensory_Sync;
               K.Tasks (Task_ID).Progress_Pct := 65;
               Success := True;

            when Orbis_Sensory_Sync =>
               K.Tasks (Task_ID).Phase := Spark_Verification;
               K.Tasks (Task_ID).Progress_Pct := 90;
               Success := True;

            when Spark_Verification =>
               K.Tasks (Task_ID).Phase := Mastered_Delivery;
               K.Tasks (Task_ID).Progress_Pct := 100;
               K.Tasks (Task_ID).Completed := True;
               K.Total_Solved := K.Total_Solved + 1;
               Success := True;

            when Mastered_Delivery =>
               -- Již dokončeno
               Success := False;
         end case;
      else
         Success := False;
      end if;
   end Advance_Phase;

end Agent_Komensky;
