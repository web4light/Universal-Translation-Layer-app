pragma SPARK_Mode (On);

package Ash_Sweeper_Scheduler is

   -- Konstanty pro Ash Sweeper okno (04:23 UTC)
   Purge_Hour   : constant := 4;
   Purge_Minute : constant := 23;

   subtype Hour_Range   is Natural range 0 .. 23;
   subtype Minute_Range is Natural range 0 .. 59;
   subtype Second_Range is Natural range 0 .. 59;

   type Day_Time is record
      Hour   : Hour_Range;
      Minute : Minute_Range;
      Second : Second_Range;
   end record;

   type Sweeper_State is (Idle, Purge_Armed, Purge_Executed, Memory_Zeroed);

   type System_Vault_State is record
      Status       : Sweeper_State;
      Last_Purge   : Day_Time;
      Active_Pages : Natural;
      Is_Sanitized : Boolean;
   end record;

   -- Kontrola času a spuštění hermetického výmazu RAM
   procedure Check_And_Trigger_Purge (
      Current_Clock : in     Day_Time;
      Vault         : in out System_Vault_State;
      Triggered     :    out Boolean
   )
   with
      Global  => null,
      Depends => (
         Vault     =>+ Current_Clock,
         Triggered => (Current_Clock, Vault)
      ),
      Post    => (if Triggered then
                     Current_Clock.Hour = Purge_Hour and then
                     Current_Clock.Minute = Purge_Minute and then
                     Vault.Status = Memory_Zeroed and then
                     Vault.Active_Pages = 0 and then
                     Vault.Is_Sanitized
                  else
                     Vault.Status = Vault.Status'Old);

   -- Reset stavu po uplynutí intervalu 04:23
   procedure Rearm_Sweeper (
      Vault : in out System_Vault_State
   )
   with
      Global  => null,
      Depends => (Vault =>+ null),
      Post    => Vault.Status = Idle;

end Ash_Sweeper_Scheduler;
