--  =============================================================================
--  Druid_Crucible_Ash_Collector Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body Druid_Crucible_Ash_Collector with
  SPARK_Mode => On
is

   procedure Initialize_Crucible
     (State : out Crucible_Record)
   is
   begin
      State.Temperature_C     := 1400;
      State.Accumulated_Ash_G := 0;
      State.Total_Gas_Burned  := 0;
      State.Is_Ash_Purified   := True;
      State.Is_Sanitized      := True;
   end Initialize_Crucible;

   procedure Capture_Burned_Gas_Ash
     (State     : in out Crucible_Record;
      Gas_Spent : in     Gas_Units;
      Ash_Added : in     Ash_Grams;
      Accepted  : out    Boolean)
   is
   begin
      if Ash_Added <= 1000 and then
         State.Accumulated_Ash_G <= Ash_Grams'Last - Ash_Added and then
         State.Total_Gas_Burned <= Natural'Last - Gas_Spent and then
         State.Temperature_C >= Melting_Point_Ag
      then
         State.Accumulated_Ash_G := State.Accumulated_Ash_G + Ash_Added;
         State.Total_Gas_Burned  := State.Total_Gas_Burned + Gas_Spent;
         State.Is_Sanitized      := False;
         Accepted                := True;
      else
         Accepted                := False;
      end if;
   end Capture_Burned_Gas_Ash;

   procedure Purge_Crucible_Session
     (State   : in out Crucible_Record;
      Success : out    Boolean)
   is
   begin
      State.Temperature_C   := 1400;
      State.Is_Ash_Purified := True;
      State.Is_Sanitized    := True;
      Success               := True;
   end Purge_Crucible_Session;

end Druid_Crucible_Ash_Collector;
