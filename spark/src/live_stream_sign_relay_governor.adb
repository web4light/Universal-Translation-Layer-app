--  =============================================================================
--  Live_Stream_Sign_Relay_Governor Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body Live_Stream_Sign_Relay_Governor with
  SPARK_Mode => On
is

   procedure Initialize_Relay
     (State : out Relay_State)
   is
   begin
      State.Current_FPS    := 0;
      State.Measured_Delay := 0;
      State.Queued_Frames  := 0;
      State.Status         := Stream_Idle;
      State.Frames_Emitted := 0;
      State.Is_Sanitized   := True;
   end Initialize_Relay;

   procedure Ingest_Sign_Frame
     (State    : in out Relay_State;
      Delay_Ms : in     Latency_Ms;
      Accepted : out    Boolean)
   is
   begin
      if State.Queued_Frames < 64 then
         State.Measured_Delay := Delay_Ms;
         State.Queued_Frames  := State.Queued_Frames + 1;
         if Delay_Ms <= Max_Broadcast_Latency then
            State.Status := Stream_Active;
         else
            State.Status := Stream_Degraded;
         end if;
         State.Is_Sanitized := False;
         Accepted           := True;
      else
         Accepted := False;
      end if;
   end Ingest_Sign_Frame;

   procedure Emit_Broadcast_Frame
     (State    : in out Relay_State;
      Emitted  : out    Boolean)
   is
   begin
      if State.Queued_Frames > 0 and then State.Frames_Emitted < Natural'Last then
         State.Queued_Frames  := State.Queued_Frames - 1;
         State.Frames_Emitted := State.Frames_Emitted + 1;
         State.Current_FPS    := 60;
         Emitted              := True;
      else
         Emitted := False;
      end if;
   end Emit_Broadcast_Frame;

   procedure Purge_Stream_Session
     (State   : in out Relay_State;
      Success : out    Boolean)
   is
   begin
      State.Current_FPS    := 0;
      State.Measured_Delay := 0;
      State.Queued_Frames  := 0;
      State.Status         := Stream_Idle;
      State.Is_Sanitized   := True;
      Success              := True;
   end Purge_Stream_Session;

end Live_Stream_Sign_Relay_Governor;
