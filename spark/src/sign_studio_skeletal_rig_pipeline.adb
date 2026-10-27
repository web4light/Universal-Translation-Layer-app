--  =============================================================================
--  Sign_Studio_Skeletal_Rig_Pipeline - Implementation
--  =============================================================================

package body Sign_Studio_Skeletal_Rig_Pipeline with
  SPARK_Mode => On
is

   procedure Initialize_Rig
     (Rig : out Skeletal_Rig_State)
   is
   begin
      Rig := (Elbow_Flex    => 2000,
              Wrist_Pitch   => 0,
              Wrist_Yaw     => 0,
              Hand          => Relaxed_Hand,
              Is_Calibrated => True,
              Total_Frames  => 0);
   end Initialize_Rig;

   procedure Set_Phalanx_Flexion
     (Rig      : in out Skeletal_Rig_State;
      Finger   : in     Finger_Id;
      Phalanx  : in     Phalanx_Index;
      Target   : in     Flexion_Angle)
   is
   begin
      Rig.Hand (Finger) (Phalanx) := Target;
   end Set_Phalanx_Flexion;

   procedure Step_Rig_Frame
     (Rig     : in out Skeletal_Rig_State;
      Success : out    Boolean)
   is
   begin
      if Rig.Total_Frames < Natural'Last then
         Rig.Total_Frames := Rig.Total_Frames + 1;
         Success := True;
      else
         Success := False;
      end if;
   end Step_Rig_Frame;

end Sign_Studio_Skeletal_Rig_Pipeline;
