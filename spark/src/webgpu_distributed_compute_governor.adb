--  =============================================================================
--  WebGPU_Distributed_Compute_Governor Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body WebGPU_Distributed_Compute_Governor with
  SPARK_Mode => On
is

   procedure Initialize_Governor
     (State : out WebGPU_Governor_State)
   is
   begin
      State.Duty_Cycle_Cap   := 2;
      State.Active_Kernels   := 0;
      State.Total_Frames_Run := 0;
      State.Is_Sanitized     := True;
   end Initialize_Governor;

   procedure Dispatch_Community_Kernel
     (State    : in out WebGPU_Governor_State;
      Kernel   : in     Compute_Kernel_Record;
      Accepted : out    Boolean)
   is
   begin
      if (not Kernel.Access_DOM_Leaks) and then
         Kernel.Airgap_Isolated and then
         State.Active_Kernels < Natural'Last and then
         State.Total_Frames_Run < Natural'Last
      then
         State.Duty_Cycle_Cap   := 2;
         State.Active_Kernels   := State.Active_Kernels + 1;
         State.Total_Frames_Run := State.Total_Frames_Run + 1;
         State.Is_Sanitized     := False;
         Accepted               := True;
      else
         Accepted := False;
      end if;
   end Dispatch_Community_Kernel;

   procedure Purge_Compute_Session
     (State   : in out WebGPU_Governor_State;
      Cleaned : out    Boolean)
   is
   begin
      State.Duty_Cycle_Cap := 2;
      State.Active_Kernels := 0;
      State.Is_Sanitized   := True;
      Cleaned              := True;
   end Purge_Compute_Session;

end WebGPU_Distributed_Compute_Governor;
