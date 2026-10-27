pragma SPARK_Mode (On);

package body Ash_Sweeper_Scheduler is

   procedure Check_And_Trigger_Purge (
      Current_Clock : in     Day_Time;
      Vault         : in out System_Vault_State;
      Triggered     :    out Boolean
   ) is
   begin
      if Current_Clock.Hour = Purge_Hour and then
         Current_Clock.Minute = Purge_Minute
      then
         if Vault.Status /= Memory_Zeroed then
            Vault.Status       := Memory_Zeroed;
            Vault.Last_Purge   := Current_Clock;
            Vault.Active_Pages := 0;
            Vault.Is_Sanitized := True;
            Triggered          := True;
         else
            Triggered          := False;
         end if;
      else
         Triggered := False;
      end if;
   end Check_And_Trigger_Purge;

   procedure Rearm_Sweeper (
      Vault : in out System_Vault_State
   ) is
   begin
      Vault.Status := Idle;
   end Rearm_Sweeper;

end Ash_Sweeper_Scheduler;
