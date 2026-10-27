--  =============================================================================
--  Sign_Studio_Kinematics (SPARK 2014 / DO-178C Level A) - Implementation
--  =============================================================================

package body Sign_Studio_Kinematics with
  SPARK_Mode => On
is

   function Interpolate_Angle
     (From, To : Angle_Centideg;
      T_Pct    : Percentage) return Angle_Centideg
   is
      Diff   : constant Long_Integer := Long_Integer (To) - Long_Integer (From);
      Scaled : constant Long_Integer := (Diff * Long_Integer (T_Pct)) / 100;
      Res    : constant Long_Integer := Long_Integer (From) + Scaled;
   begin
      if Res > 18000 then
         return 18000;
      elsif Res < -18000 then
         return -18000;
      else
         return Angle_Centideg (Res);
      end if;
   end Interpolate_Angle;

   function Interpolate_Finger
     (From, To : Percentage;
      T_Pct    : Percentage) return Percentage
   is
      Diff   : constant Integer := Integer (To) - Integer (From);
      Scaled : constant Integer := (Diff * Integer (T_Pct)) / 100;
      Res    : constant Integer := Integer (From) + Scaled;
   begin
      if Res > 100 then
         return 100;
      elsif Res < 0 then
         return 0;
      else
         return Percentage (Res);
      end if;
   end Interpolate_Finger;

   procedure Initialize_Studio
     (State : out Studio_Engine_State)
   is
   begin
      State := (Current_Pose   => Neutral_Pose,
                Target_Pose    => Neutral_Pose,
                Interpolation  => 100,
                Is_Posing_Done => True);
   end Initialize_Studio;

   procedure Set_Target_Gesture
     (State  : in out Studio_Engine_State;
      Target : in     Skeletal_Pose)
   is
   begin
      State.Target_Pose    := Target;
      State.Interpolation  := 0;
      State.Is_Posing_Done := False;
   end Set_Target_Gesture;

   procedure Step_Kinematic_Frame
     (State      : in out Studio_Engine_State;
      Step_Delta : in     Percentage)
   is
      New_Pct : Percentage;
   begin
      if 100 - State.Interpolation <= Step_Delta then
         New_Pct := 100;
      else
         New_Pct := State.Interpolation + Step_Delta;
      end if;

      State.Interpolation := New_Pct;

      --  Interpolate joint angles
      State.Current_Pose.Shoulder_Pitch := Interpolate_Angle
        (State.Current_Pose.Shoulder_Pitch, State.Target_Pose.Shoulder_Pitch, New_Pct);

      State.Current_Pose.Shoulder_Yaw := Interpolate_Angle
        (State.Current_Pose.Shoulder_Yaw, State.Target_Pose.Shoulder_Yaw, New_Pct);

      State.Current_Pose.Elbow_Flexion := Interpolate_Angle
        (State.Current_Pose.Elbow_Flexion, State.Target_Pose.Elbow_Flexion, New_Pct);

      State.Current_Pose.Wrist_Pitch := Interpolate_Angle
        (State.Current_Pose.Wrist_Pitch, State.Target_Pose.Wrist_Pitch, New_Pct);

      State.Current_Pose.Wrist_Roll := Interpolate_Angle
        (State.Current_Pose.Wrist_Roll, State.Target_Pose.Wrist_Roll, New_Pct);

      for I in 1 .. 5 loop
         State.Current_Pose.Fingers (I) := Interpolate_Finger
           (State.Current_Pose.Fingers (I), State.Target_Pose.Fingers (I), New_Pct);
      end loop;

      if New_Pct = 100 then
         State.Is_Posing_Done := True;
      else
         State.Is_Posing_Done := False;
      end if;
   end Step_Kinematic_Frame;

end Sign_Studio_Kinematics;
