--  =============================================================================
--  Epoch_0423_Global_Scrub_Synchronizer Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body Epoch_0423_Global_Scrub_Synchronizer with
  SPARK_Mode => On
is

   procedure Initialize_Synchronizer
     (State : out Global_Scrub_State)
   is
   begin
      State.Purged_Enclaves  := 0;
      State.Status           := Scrub_Pending;
      State.Epochs_Completed := 0;
      State.Is_NonBinaryZero := True;
   end Initialize_Synchronizer;

   procedure Check_And_Trigger_0423
     (State    : in out Global_Scrub_State;
      Hour     : in     Hour_Type;
      Minute   : in     Minute_Type;
      Accepted : out    Boolean)
   is
   begin
      if Hour = 4 and Minute = 23 then
         State.Purged_Enclaves  := 0;
         State.Status           := Scrub_In_Progress;
         State.Is_NonBinaryZero := False;
         Accepted               := True;
      else
         Accepted               := False;
      end if;
   end Check_And_Trigger_0423;

   procedure Acknowledge_Enclave
     (State    : in out Global_Scrub_State;
      Accepted : out    Boolean)
   is
   begin
      if State.Status = Scrub_In_Progress and then State.Purged_Enclaves < Total_Enclaves then
         State.Purged_Enclaves := State.Purged_Enclaves + 1;
         Accepted              := True;
      else
         Accepted              := False;
      end if;
   end Acknowledge_Enclave;

   procedure Finalize_NonBinary_Zero
     (State    : in out Global_Scrub_State;
      Complete : out    Boolean)
   is
   begin
      if State.Status = Scrub_In_Progress and then
         State.Purged_Enclaves = Total_Enclaves and then
         State.Epochs_Completed < Natural'Last
      then
         State.Status           := Scrub_Achieved;
         State.Is_NonBinaryZero := True;
         State.Epochs_Completed := State.Epochs_Completed + 1;
         Complete               := True;
      else
         Complete               := False;
      end if;
   end Finalize_NonBinary_Zero;

end Epoch_0423_Global_Scrub_Synchronizer;
