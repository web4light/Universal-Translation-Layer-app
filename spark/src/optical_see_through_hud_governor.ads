--  =============================================================================
--  Optical_See_Through_HUD_Governor (SPARK 2022 / DO-178C DAL-A)
--  Sovereign Web 4.23 & SPECS AR Glasses: Optical See-Through Safety.
--  Formal invariant enforcement for optical luminance clamping (<= 1000 nits),
--  real-time depth occlusion safety (clear field of view),
--  and ephemeral HUD buffer zeroization at 04:23 UTC.
--  =============================================================================

package Optical_See_Through_HUD_Governor with
  SPARK_Mode => On
is

   subtype Nits_Luminance is Natural range 0 .. 2000;
   subtype Depth_Millimeters is Natural range 100 .. 100_000;
   subtype FOV_Degrees is Positive range 1 .. 120;

   Max_Safe_Luminance : constant Nits_Luminance := 1000;
   Min_Obstacle_Clearance_MM : constant Depth_Millimeters := 300;

   type HUD_Overlay_Record is record
      Target_Nits     : Nits_Luminance;
      Estimated_Depth : Depth_Millimeters;
      Overlay_FOV     : FOV_Degrees;
      Obstructs_View  : Boolean;
   end record;

   type HUD_Supervisor_State is record
      Active_Luminance  : Nits_Luminance;
      Rendered_Frames   : Natural;
      Is_Eye_Safe       : Boolean;
      Is_Sanitized      : Boolean;
   end record;

   --  Initialize pristine optical HUD governor state
   procedure Initialize_HUD
     (State : out HUD_Supervisor_State)
   with
     Global => null,
     Post   => State.Active_Luminance = 0 and
               State.Rendered_Frames = 0 and
               State.Is_Eye_Safe = True and
               State.Is_Sanitized = True;

   --  Render AR caption overlay with optical safety & occlusion clamping
   procedure Render_Overlay_Frame
     (State    : in out HUD_Supervisor_State;
      Overlay  : in     HUD_Overlay_Record;
      Accepted : out    Boolean)
   with
     Global => null,
     Pre    => State.Rendered_Frames < Natural'Last,
     Post   => (if Accepted then
                  State.Active_Luminance <= Max_Safe_Luminance and
                  State.Rendered_Frames = State.Rendered_Frames'Old + 1 and
                  State.Is_Eye_Safe = True and
                  State.Is_Sanitized = False
                else
                  State.Rendered_Frames = State.Rendered_Frames'Old);

   --  Deterministic 04:23 UTC RAM scrub (clean slate non-binary zero)
   procedure Purge_HUD_Session
     (State   : in out HUD_Supervisor_State;
      Success : out    Boolean)
   with
     Global => null,
     Post   => State.Active_Luminance = 0 and
               State.Is_Eye_Safe = True and
               State.Is_Sanitized = True and
               Success = True;

end Optical_See_Through_HUD_Governor;
