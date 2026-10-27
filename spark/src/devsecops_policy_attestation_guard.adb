--  =============================================================================
--  DevSecOps_Policy_Attestation_Guard Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body DevSecOps_Policy_Attestation_Guard with
  SPARK_Mode => On
is

   procedure Initialize_Pipeline
     (State : out Pipeline_Attestation_Record)
   is
   begin
      State.Current_Stage   := Stage_Plan;
      State.Stages_Passed   := 0;
      State.Is_SBT_Signed   := True;
      State.Is_Deploy_Gated := True;
      State.Is_Sanitized    := True;
   end Initialize_Pipeline;

   procedure Advance_Lifecycle_Stage
     (State     : in out Pipeline_Attestation_Record;
      Next_Gate : in     DevSecOps_Stage;
      Approved  : out    Boolean)
   is
   begin
      if State.Stages_Passed < 9 and then
         State.Is_SBT_Signed
      then
         State.Current_Stage := Next_Gate;
         State.Stages_Passed := State.Stages_Passed + 1;
         State.Is_Sanitized  := False;
         Approved            := True;
      else
         Approved            := False;
      end if;
   end Advance_Lifecycle_Stage;

   procedure Purge_Pipeline_Tokens
     (State   : in out Pipeline_Attestation_Record;
      Success : out    Boolean)
   is
   begin
      State.Current_Stage   := Stage_Plan;
      State.Stages_Passed   := 0;
      State.Is_Deploy_Gated := True;
      State.Is_Sanitized    := True;
      Success               := True;
   end Purge_Pipeline_Tokens;

end DevSecOps_Policy_Attestation_Guard;
