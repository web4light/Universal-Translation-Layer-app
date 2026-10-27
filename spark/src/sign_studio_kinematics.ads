--  =============================================================================
--  Sign_Studio_Kinematics (SPARK 2014 / DO-178C Level A)
--  Mandalorian Game Studio: Formally verified skeletal kinematic engine for
--  real-time sign language gestures, dactyl alphabets, and joint rotations.
--  Operates deterministically at 60 FPS without dynamic allocation.
--  =============================================================================

package Sign_Studio_Kinematics with
  SPARK_Mode => On
is

   --  Angular representation in centidegrees (-18000 to +18000 = -180.00 to +180.00 deg)
   type Angle_Centideg is range -18000 .. 18000;

   --  Normalized joint extension percentage (0 .. 100%)
   type Percentage is range 0 .. 100;

   --  Five finger joints configuration
   type Finger_Array is array (1 .. 5) of Percentage;

   --  Upper body skeletal kinematic pose for 3D Sign Avatar
   type Skeletal_Pose is record
      Shoulder_Pitch : Angle_Centideg;
      Shoulder_Yaw   : Angle_Centideg;
      Elbow_Flexion  : Angle_Centideg;
      Wrist_Pitch    : Angle_Centideg;
      Wrist_Roll     : Angle_Centideg;
      Fingers        : Finger_Array;
   end record;

   --  Kinematic engine state
   type Studio_Engine_State is record
      Current_Pose   : Skeletal_Pose;
      Target_Pose    : Skeletal_Pose;
      Interpolation  : Percentage;  --  0 = at current, 100 = arrived at target
      Is_Posing_Done : Boolean;
   end record;

   --  Initial neutral rest pose
   Neutral_Pose : constant Skeletal_Pose :=
     (Shoulder_Pitch => 0,
      Shoulder_Yaw   => 0,
      Elbow_Flexion  => 0,
      Wrist_Pitch    => 0,
      Wrist_Roll     => 0,
      Fingers        => (others => 0));

   --  Initialize the game studio kinematic engine
   procedure Initialize_Studio
     (State : out Studio_Engine_State)
   with
     Global => null,
     Post   => State.Current_Pose = Neutral_Pose and
               State.Target_Pose = Neutral_Pose and
               State.Interpolation = 100 and
               State.Is_Posing_Done = True;

   --  Set target sign gesture pose
   procedure Set_Target_Gesture
     (State  : in out Studio_Engine_State;
      Target : in     Skeletal_Pose)
   with
     Global => null,
     Post   => State.Target_Pose = Target and
               State.Interpolation = 0 and
               State.Is_Posing_Done = False;

   --  Deterministic 60 FPS kinematic step interpolation
   --  Step_Delta advances interpolation towards 100%
   procedure Step_Kinematic_Frame
     (State      : in out Studio_Engine_State;
      Step_Delta : in     Percentage)
   with
     Global => null,
     Post   => (if State.Interpolation = 100 then State.Is_Posing_Done);

   --  Linear interpolation between two angles in centidegrees
   function Interpolate_Angle
     (From, To : Angle_Centideg;
      T_Pct    : Percentage) return Angle_Centideg
   with
     Global => null;

end Sign_Studio_Kinematics;
