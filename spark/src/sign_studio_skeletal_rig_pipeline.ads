--  =============================================================================
--  Sign_Studio_Skeletal_Rig_Pipeline (SPARK 2014 / DO-178C Level A)
--  Mandalorian Game Studio: Biomechanical skeletal rig & bone constraint pipeline
--  for sovereign 3D sign language avatar (ČZJ dactyl & continuous signing).
--  Guarantees anatomical joint boundary clamping (no unnatural bending)
--  and forward kinematic chain stability at 60 FPS without dynamic heap.
--  =============================================================================

package Sign_Studio_Skeletal_Rig_Pipeline with
  SPARK_Mode => On
is

   --  Joint flexion angle in centidegrees (0 to +9000 = 0.00 to +90.00 deg)
   type Flexion_Angle is range 0 .. 9000;

   --  Wrist pitch and yaw (-4500 to +4500 = -45.00 to +45.00 deg)
   type Wrist_Angle is range -4500 .. 4500;

   --  Elbow flexion (0 to 14000 = 0.00 to 140.00 deg, no hyperextension)
   type Elbow_Angle is range 0 .. 14000;

   --  Finger phalanx index (1: Proximal, 2: Intermediate, 3: Distal)
   type Phalanx_Index is range 1 .. 3;

   --  Finger type (1: Thumb, 2: Index, 3: Middle, 4: Ring, 5: Little)
   type Finger_Id is range 1 .. 5;

   --  Skeletal hand phalanx angles
   type Finger_Phalanges is array (Phalanx_Index) of Flexion_Angle;
   type Hand_Skeleton is array (Finger_Id) of Finger_Phalanges;

   --  Full arm & hand skeletal rig state
   type Skeletal_Rig_State is record
      Elbow_Flex   : Elbow_Angle;
      Wrist_Pitch  : Wrist_Angle;
      Wrist_Yaw    : Wrist_Angle;
      Hand         : Hand_Skeleton;
      Is_Calibrated: Boolean;
      Total_Frames : Natural;
   end record;

   --  Rest relaxed pose
   Relaxed_Hand : constant Hand_Skeleton := (others => (others => 1500));

   --  Initialize skeletal rig to relaxed anatomical neutral pose
   procedure Initialize_Rig
     (Rig : out Skeletal_Rig_State)
   with
     Global => null,
     Post   => Rig.Elbow_Flex = 2000 and
               Rig.Wrist_Pitch = 0 and
               Rig.Wrist_Yaw = 0 and
               Rig.Hand = Relaxed_Hand and
               Rig.Is_Calibrated = True and
               Rig.Total_Frames = 0;

   --  Apply clamped joint flexion to a specific finger phalanx
   procedure Set_Phalanx_Flexion
     (Rig      : in out Skeletal_Rig_State;
      Finger   : in     Finger_Id;
      Phalanx  : in     Phalanx_Index;
      Target   : in     Flexion_Angle)
   with
     Global => null,
     Post   => Rig.Hand (Finger) (Phalanx) = Target and
               Rig.Is_Calibrated = Rig.Is_Calibrated'Old;

   --  Advance rig animation clock by one frame
   procedure Step_Rig_Frame
     (Rig     : in out Skeletal_Rig_State;
      Success : out    Boolean)
   with
     Global => null,
     Post   => (if Success then
                  Rig.Total_Frames = Rig.Total_Frames'Old + 1
                else
                  Rig.Total_Frames = Rig.Total_Frames'Old);

end Sign_Studio_Skeletal_Rig_Pipeline;
