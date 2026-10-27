--  =============================================================================
--  Cross_Domain_Taste_Synergy_Governor Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body Cross_Domain_Taste_Synergy_Governor with
  SPARK_Mode => On
is

   procedure Initialize_Synergy_Engine
     (State : out Synergy_Supervisor_State)
   is
   begin
      State.Primary_Domain_Id   := 1;
      State.Secondary_Domain_Id := 1;
      State.Calculated_Synergy  := 0;
      State.Synergy_Queries     := 0;
      State.Is_Privacy_Sealed   := True;
      State.Is_Sanitized        := True;
   end Initialize_Synergy_Engine;

   procedure Compute_Synergy
     (State     : in out Synergy_Supervisor_State;
      Domain_A  : in     Positive;
      Domain_B  : in     Positive;
      Raw_Score : in     Affinity_Score;
      Accepted  : out    Boolean)
   is
   begin
      if Domain_A in 1 .. 16 and then
         Domain_B in 1 .. 16 and then
         State.Synergy_Queries < Natural'Last
      then
         State.Primary_Domain_Id   := Domain_A;
         State.Secondary_Domain_Id := Domain_B;
         State.Calculated_Synergy  := Raw_Score;
         State.Synergy_Queries     := State.Synergy_Queries + 1;
         State.Is_Privacy_Sealed   := True;
         State.Is_Sanitized        := False;
         Accepted                  := True;
      else
         Accepted                  := False;
      end if;
   end Compute_Synergy;

   procedure Purge_Synergy_Session
     (State   : in out Synergy_Supervisor_State;
      Success : out    Boolean)
   is
   begin
      State.Calculated_Synergy := 0;
      State.Is_Privacy_Sealed  := True;
      State.Is_Sanitized       := True;
      Success                  := True;
   end Purge_Synergy_Session;

end Cross_Domain_Taste_Synergy_Governor;
