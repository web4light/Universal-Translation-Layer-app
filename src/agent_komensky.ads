-- ============================================================
--  Agent Komenský — Nejvyšší Dozorce Úkolů (Taskmaster)
--  Ada/SPARK 2022 — Formálně verifikovaný orchestrátor úloh
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Inspirován Janem Amosem Komenským (Janua Linguarum, Didactica Magna):
--  Systematicky rozkládá složité překladové a dabingové úlohy,
--  garantuje posloupnost kroků a matematickou neprůstřelnost.
--
--  Autor: Pan Jeskyně
--  Standard: 700 / Protokol 4.23
-- ============================================================

pragma SPARK_Mode (On);

package Agent_Komensky is

   -- ==========================================================
   -- KONSTANTY
   -- ==========================================================

   Max_Tasks      : constant := 50;
   Max_Text_Len   : constant := 1_000;
   Max_Steps      : constant := 5;

   -- ==========================================================
   -- TYPY A ROZSAHY
   -- ==========================================================

   subtype Task_Index is Natural range 0 .. Max_Tasks;
   subtype Task_Count is Natural range 0 .. Max_Tasks;
   subtype Step_Count is Natural range 0 .. Max_Steps;
   subtype Text_Len is Natural range 0 .. Max_Text_Len;

   -- Fáze vzdělávání / zpracování úlohy (Didaktika Komenského)
   type Task_Phase is (
      Labyrinth_Analysis,  -- Analýza vstupu a struktury (Labyrint světa)
      Janua_Translation,   -- Jazykový překlad přes Gemini (Brána jazyků otevřená)
      Orbis_Sensory_Sync,  -- Časová a audio synchronizace (Svět v obrazech)
      Spark_Verification,  -- Formální matematický důkaz v Ada/SPARK
      Mastered_Delivery    -- Dokončený a odevzdaný úkol (Ráj srdce)
   );

   -- Stav jedné úlohy
   type Task_Record is record
      ID           : Task_Index := 0;
      Phase        : Task_Phase := Labyrinth_Analysis;
      Progress_Pct : Natural range 0 .. 100 := 0;
      Completed    : Boolean    := False;
   end record;

   type Task_Array is array (1 .. Max_Tasks) of Task_Record;

   -- Celkový stav Dozorce Komenského
   type Komensky_Orchestrator is record
      Tasks        : Task_Array;
      Count        : Task_Count := 0;
      Active_ID    : Task_Index := 0;
      Total_Solved : Natural    := 0;
   end record;

   -- ==========================================================
   -- KONTRAKTY A OPERACE
   -- ==========================================================

   -- Inicializace Dozorce Komenského
   procedure Initialize (K : out Komensky_Orchestrator)
     with Post => K.Count = 0
                  and K.Active_ID = 0
                  and K.Total_Solved = 0;

   -- Zapsání nové úlohy do fronty
   procedure Register_Task (K       : in out Komensky_Orchestrator;
                            Success : out Boolean)
     with Pre  => K.Count < Max_Tasks,
          Post => (if Success then K.Count = K.Count'Old + 1
                   else K.Count = K.Count'Old);

   -- Posunutí úlohy do další didaktické fáze
   procedure Advance_Phase (K       : in out Komensky_Orchestrator;
                            Task_ID : Task_Index;
                            Success : out Boolean)
     with Pre  => Task_ID >= 1 and Task_ID <= K.Count,
          Post => (if Success and K.Tasks (Task_ID).Completed
                   then K.Total_Solved = K.Total_Solved'Old + 1
                   else K.Total_Solved = K.Total_Solved'Old);

end Agent_Komensky;
