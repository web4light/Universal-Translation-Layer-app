--  =============================================================================
--  WebXR_Spatial_Anchor_Enclave Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body WebXR_Spatial_Anchor_Enclave with
  SPARK_Mode => On
is

   procedure Initialize_Anchor
     (State : out Spatial_Anchor_State)
   is
   begin
      State.Current_Pose.X     := 0.000;
      State.Current_Pose.Y     := 0.000;
      State.Current_Pose.Z     := 0.000;
      State.Current_Pose.Pitch := 0;
      State.Current_Pose.Yaw   := 0;
      State.Current_Pose.Roll  := 0;
      State.Status             := Anchor_Unset;
      State.Frame_Count        := 0;
      State.Is_Zeroized        := True;
   end Initialize_Anchor;

   procedure Update_Spatial_Pose
     (State    : in out Spatial_Anchor_State;
      Target   : in     Pose_6DOF;
      Accepted : out    Boolean)
   is
      Delta_Pitch : Angular_Difference;
      Delta_Yaw   : Angular_Difference;
      Delta_Roll  : Angular_Difference;
   begin
      if State.Status = Anchor_Tracking then
         -- Check angular velocity bounds using Integer difference
         if Integer (Target.Pitch) >= Integer (State.Current_Pose.Pitch) then
            Delta_Pitch := Integer (Target.Pitch) - Integer (State.Current_Pose.Pitch);
         else
            Delta_Pitch := Integer (State.Current_Pose.Pitch) - Integer (Target.Pitch);
         end if;

         if Integer (Target.Yaw) >= Integer (State.Current_Pose.Yaw) then
            Delta_Yaw := Integer (Target.Yaw) - Integer (State.Current_Pose.Yaw);
         else
            Delta_Yaw := Integer (State.Current_Pose.Yaw) - Integer (Target.Yaw);
         end if;

         if Integer (Target.Roll) >= Integer (State.Current_Pose.Roll) then
            Delta_Roll := Integer (Target.Roll) - Integer (State.Current_Pose.Roll);
         else
            Delta_Roll := Integer (State.Current_Pose.Roll) - Integer (Target.Roll);
         end if;

         if Delta_Pitch <= Max_Angular_Step and then
            Delta_Yaw   <= Max_Angular_Step and then
            Delta_Roll  <= Max_Angular_Step and then
            State.Frame_Count < Natural'Last
         then
            State.Current_Pose := Target;
            State.Frame_Count  := State.Frame_Count + 1;
            State.Status       := Anchor_Tracking;
            State.Is_Zeroized  := False;
            Accepted           := True;
         else
            State.Status := Anchor_Lost;
            Accepted     := False;
         end if;
      else
         -- Initial lock-on
         if State.Frame_Count < Natural'Last then
            State.Current_Pose := Target;
            State.Frame_Count  := State.Frame_Count + 1;
            State.Status       := Anchor_Tracking;
            State.Is_Zeroized  := False;
            Accepted           := True;
         else
            State.Status := Anchor_Lost;
            Accepted     := False;
         end if;
      end if;
   end Update_Spatial_Pose;

   procedure Purge_Spatial_Anchor
     (State   : in out Spatial_Anchor_State;
      Success : out    Boolean)
   is
   begin
      State.Current_Pose.X     := 0.000;
      State.Current_Pose.Y     := 0.000;
      State.Current_Pose.Z     := 0.000;
      State.Current_Pose.Pitch := 0;
      State.Current_Pose.Yaw   := 0;
      State.Current_Pose.Roll  := 0;
      State.Status             := Anchor_Unset;
      State.Is_Zeroized        := True;
      Success                  := True;
   end Purge_Spatial_Anchor;

end WebXR_Spatial_Anchor_Enclave;
