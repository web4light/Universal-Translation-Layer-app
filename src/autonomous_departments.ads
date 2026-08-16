pragma SPARK_Mode (On);

-- ============================================================
--  Autonomous_Departments — Autonomní oddělení Web4
--
--  4 oddělení. Každé dělá JEDNU věc. Žádné překryvy.
--
--    1. Engineering  — staví, kóduje, verifikuje
--    2. Marketing    — propagace + ohlasy + oslovení (vše v jednom)
--    3. Operations   — provoz, monitoring, údržba
--    4. Legal        — Justýna Lab: matematická verifikace práv a smluv
--
--  Autor: Pan Jeskyně
-- ============================================================

package Autonomous_Departments is

   -- ==========================================================
   -- KONSTANTY
   -- ==========================================================

   Max_Daily_Actions    : constant := 100;
   Cooldown_Minutes     : constant := 30;
   Max_Minutes_In_Day   : constant := 1_440;
   Max_Total_Actions    : constant := 999_999;

   -- ==========================================================
   -- TYPY
   -- ==========================================================

   type Department_ID is (Engineering, Marketing, Operations, Legal);

   type Department_Status is (Active, Cooldown, Suspended);

   subtype Action_Count is Natural range 0 .. Max_Daily_Actions;
   subtype Total_Count is Natural range 0 .. Max_Total_Actions;
   subtype Minute_Of_Day is Natural range 0 .. Max_Minutes_In_Day;

   -- Stav jednoho oddělení
   type Department_State is record
      Status          : Department_Status := Active;
      Actions_Today   : Action_Count      := 0;
      Total_Actions   : Total_Count       := 0;
      Last_Action_Min : Minute_Of_Day     := 0;
   end record;

   -- Pole všech oddělení
   type All_Departments is array (Department_ID) of Department_State;

   -- Výsledek akce — jistič: prošlo nebo ne
   type Action_Result is (Granted, Denied);

   -- ==========================================================
   -- GLOBÁLNÍ STAV
   -- ==========================================================

   Departments : All_Departments;

   -- ==========================================================
   -- OPERACE
   -- ==========================================================

   -- Inicializovat
   procedure Initialize
     with Global => (Output => Departments),
          Post   => (for all D of Departments =>
                       D.Status = Active
                       and D.Actions_Today = 0
                       and D.Total_Actions = 0);

   -- Reset denních čítačů (o půlnoci)
   procedure Reset_Daily
     with Global => (In_Out => Departments),
          Post   => (for all D of Departments =>
                       D.Actions_Today = 0);

   -- Může oddělení jednat?
   function Can_Act (Dept        : Department_ID;
                     Now_Minutes : Minute_Of_Day) return Boolean
     with Global => (Input => Departments);

   -- Provést akci
   procedure Execute_Action (Dept        : in     Department_ID;
                             Now_Minutes : in     Minute_Of_Day;
                             Result      :    out Action_Result)
     with Global => (In_Out => Departments),
          Pre    => Departments (Dept).Total_Actions < Max_Total_Actions;

   -- Pozastavit oddělení
   procedure Suspend (Dept : in Department_ID)
     with Global => (In_Out => Departments),
          Post   => Departments (Dept).Status = Suspended;

   -- Obnovit oddělení
   procedure Resume (Dept : in Department_ID)
     with Global => (In_Out => Departments),
          Post   => Departments (Dept).Status = Active;

   -- Všechna oddělení aktivní?
   function All_Active return Boolean
     with Global => (Input => Departments),
          Post   => All_Active'Result =
                    (for all D of Departments => D.Status = Active);

end Autonomous_Departments;
