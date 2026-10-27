--  =============================================================================
--  WebXR_Spatial_Anchor_Enclave (SPARK 2022 / DO-178C DAL-A)
--  Sovereign Web 4.23: "Asterisk: Vltava Spatial Symphony & Sign Engine"
--  Formal invariant enforcement for 6-DOF WebXR head/hand spatial anchors,
--  vestibular sickness prevention (angular acceleration clamping),
--  and ephemeral volatile memory zeroization at 04:23 UTC.
--  =============================================================================

package WebXR_Spatial_Anchor_Enclave with
  SPARK_Mode => On
is

   --  Fixed-point metric coordinate: -10.000 to +10.000 meters, precision 1 mm
   type Metric_Coord is delta 0.001 range -10.000 .. 10.000;
   for Metric_Coord'Small use 0.001;

   --  Angular orientation in milliradians: -3142 .. 3142 (-pi .. +pi)
   type Milliradian_Angle is range -3142 .. 3142;

   --  Angular difference subtype for absolute velocity checks
   subtype Angular_Difference is Integer range 0 .. 6284;

   --  Max allowed angular delta per 60 FPS frame (prevents vestibular motion sickness)
   Max_Angular_Step : constant Angular_Difference := 250;

   type Pose_6DOF is record
      X     : Metric_Coord;
      Y     : Metric_Coord;
      Z     : Metric_Coord;
      Pitch : Milliradian_Angle;
      Yaw   : Milliradian_Angle;
      Roll  : Milliradian_Angle;
   end record;

   type Anchor_Status is (Anchor_Unset, Anchor_Tracking, Anchor_Lost);

   type Spatial_Anchor_State is record
      Current_Pose   : Pose_6DOF;
      Status         : Anchor_Status;
      Frame_Count    : Natural;
      Is_Zeroized    : Boolean;
   end record;

   --  Initialize pristine anchor state
   procedure Initialize_Anchor
     (State : out Spatial_Anchor_State)
   with
     Global => null,
     Post   => State.Status = Anchor_Unset and
               State.Frame_Count = 0 and
               State.Is_Zeroized = True and
               State.Current_Pose.X = 0.000 and
               State.Current_Pose.Y = 0.000 and
               State.Current_Pose.Z = 0.000 and
               State.Current_Pose.Pitch = 0 and
               State.Current_Pose.Yaw = 0 and
               State.Current_Pose.Roll = 0;

   --  Update spatial pose with vestibular angular clamping guard
   procedure Update_Spatial_Pose
     (State    : in out Spatial_Anchor_State;
      Target   : in     Pose_6DOF;
      Accepted : out    Boolean)
   with
     Global => null,
     Pre    => State.Frame_Count < Natural'Last,
     Post   => (if Accepted then
                  State.Status = Anchor_Tracking and
                  State.Frame_Count = State.Frame_Count'Old + 1 and
                  State.Is_Zeroized = False
                else
                  State.Status = Anchor_Lost and
                  State.Frame_Count = State.Frame_Count'Old);

   --  Deterministic 04:23 UTC memory scrub (RAM zeroization)
   procedure Purge_Spatial_Anchor
     (State   : in out Spatial_Anchor_State;
      Success : out    Boolean)
   with
     Global => null,
     Post   => State.Status = Anchor_Unset and
               State.Is_Zeroized = True and
               State.Current_Pose.X = 0.000 and
               State.Current_Pose.Y = 0.000 and
               State.Current_Pose.Z = 0.000 and
               State.Current_Pose.Pitch = 0 and
               State.Current_Pose.Yaw = 0 and
               State.Current_Pose.Roll = 0 and
               Success = True;

end WebXR_Spatial_Anchor_Enclave;
