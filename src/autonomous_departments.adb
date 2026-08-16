pragma SPARK_Mode (On);

-- ============================================================
--  Autonomous_Departments — Body
-- ============================================================

package body Autonomous_Departments is

   procedure Initialize is
   begin
      for ID in Department_ID loop
         Departments (ID) := (Status          => Active,
                              Actions_Today   => 0,
                              Total_Actions   => 0,
                              Last_Action_Min => 0);
      end loop;
   end Initialize;

   procedure Reset_Daily is
   begin
      for ID in Department_ID loop
         Departments (ID).Actions_Today := 0;
      end loop;
   end Reset_Daily;

   function Can_Act (Dept        : Department_ID;
                     Now_Minutes : Minute_Of_Day) return Boolean is
      D : Department_State renames Departments (Dept);
   begin
      if D.Status = Suspended then
         return False;
      end if;

      if D.Actions_Today >= Max_Daily_Actions then
         return False;
      end if;

      -- Cooldown: min 30 minut mezi akcemi
      -- Bezpečné: Last_Action_Min max 1440, Cooldown 30, součet max 1470
      if Now_Minutes < D.Last_Action_Min + Cooldown_Minutes
         and D.Last_Action_Min + Cooldown_Minutes <= Max_Minutes_In_Day
      then
         return False;
      end if;

      return True;
   end Can_Act;

   procedure Execute_Action (Dept        : in     Department_ID;
                             Now_Minutes : in     Minute_Of_Day;
                             Result      :    out Action_Result) is
      D : Department_State renames Departments (Dept);
   begin
      if D.Status = Suspended then
         Result := Denied;
         return;
      end if;

      if D.Actions_Today >= Max_Daily_Actions then
         Result := Denied;
         return;
      end if;

      if D.Total_Actions >= Max_Total_Actions then
         Result := Denied;
         return;
      end if;

      -- Cooldown check
      if Now_Minutes < D.Last_Action_Min + Cooldown_Minutes
         and D.Last_Action_Min + Cooldown_Minutes <= Max_Minutes_In_Day
      then
         Result := Denied;
         return;
      end if;

      -- Vše OK — proved akci (Actions_Today < Max, tak +1 je bezpečné)
      D.Actions_Today   := D.Actions_Today + 1;
      D.Total_Actions   := D.Total_Actions + 1;
      D.Last_Action_Min := Now_Minutes;
      D.Status          := Active;
      Result            := Granted;
   end Execute_Action;

   procedure Suspend (Dept : in Department_ID) is
   begin
      Departments (Dept).Status := Suspended;
   end Suspend;

   procedure Resume (Dept : in Department_ID) is
   begin
      Departments (Dept).Status := Active;
   end Resume;

   function All_Active return Boolean is
   begin
      for ID in Department_ID loop
         if Departments (ID).Status /= Active then
            return False;
         end if;
      end loop;
      return True;
   end All_Active;

end Autonomous_Departments;
