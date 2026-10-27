--  =============================================================================
--  Optical_See_Through_HUD_Governor Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body Optical_See_Through_HUD_Governor with
  SPARK_Mode => On
is

   procedure Initialize_HUD
     (State : out HUD_Supervisor_State)
   is
   begin
      State.Active_Luminance := 0;
      State.Rendered_Frames  := 0;
      State.Is_Eye_Safe      := True;
      State.Is_Sanitized     := True;
   end Initialize_HUD;

   procedure Render_Overlay_Frame
     (State    : in out HUD_Supervisor_State;
      Overlay  : in     HUD_Overlay_Record;
      Accepted : out    Boolean)
   is
      Clamped_Nits : Nits_Luminance;
   begin
      if (not Overlay.Obstructs_View) and then
         Overlay.Estimated_Depth >= Min_Obstacle_Clearance_MM and then
         State.Rendered_Frames < Natural'Last
      then
         if Overlay.Target_Nits > Max_Safe_Luminance then
            Clamped_Nits := Max_Safe_Luminance;
         else
            Clamped_Nits := Overlay.Target_Nits;
         end if;

         State.Active_Luminance := Clamped_Nits;
         State.Rendered_Frames  := State.Rendered_Frames + 1;
         State.Is_Eye_Safe      := True;
         State.Is_Sanitized     := False;
         Accepted               := True;
      else
         Accepted := False;
      end if;
   end Render_Overlay_Frame;

   procedure Purge_HUD_Session
     (State   : in out HUD_Supervisor_State;
      Success : out    Boolean)
   is
   begin
      State.Active_Luminance := 0;
      State.Is_Eye_Safe      := True;
      State.Is_Sanitized     := True;
      Success                := True;
   end Purge_HUD_Session;

end Optical_See_Through_HUD_Governor;
