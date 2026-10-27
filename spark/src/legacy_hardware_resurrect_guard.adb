--  =============================================================================
--  Legacy_Hardware_Resurrect_Guard Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body Legacy_Hardware_Resurrect_Guard with
  SPARK_Mode => On
is

   procedure Initialize_Supervisor
     (State : out Supervisor_State)
   is
   begin
      State.Channel.Dev_Id        := 1;
      State.Channel.Protocol      := Proto_Asterisk_SIP;
      State.Channel.Payload_Bytes := 0;
      State.Channel.Status        := Channel_Dormant;
      State.Channel.Is_Leak_Free  := True;
      State.Channel.Is_Sanitized  := True;
      State.Total_Reaped          := 0;
      State.Total_Frames          := 0;
   end Initialize_Supervisor;

   procedure Resurrect_Channel
     (State    : in out Supervisor_State;
      Dev      : in     Device_ID;
      Proto    : in     Legacy_Protocol;
      Accepted : out    Boolean)
   is
   begin
      if State.Channel.Status /= Channel_Resurrected then
         State.Channel.Dev_Id        := Dev;
         State.Channel.Protocol      := Proto;
         State.Channel.Payload_Bytes := 0;
         State.Channel.Status        := Channel_Resurrected;
         State.Channel.Is_Leak_Free  := True;
         State.Channel.Is_Sanitized  := False;
         Accepted                    := True;
      else
         Accepted := False;
      end if;
   end Resurrect_Channel;

   procedure Reap_Zombie_Channel
     (State   : in out Supervisor_State;
      Success : out    Boolean)
   is
   begin
      if State.Channel.Status = Channel_Resurrected and then
         State.Total_Reaped < Natural'Last
      then
         State.Channel.Payload_Bytes := 0;
         State.Channel.Status        := Channel_Zombie_Reaped;
         State.Channel.Is_Leak_Free  := True;
         State.Channel.Is_Sanitized  := True;
         State.Total_Reaped          := State.Total_Reaped + 1;
         Success                     := True;
      else
         Success := False;
      end if;
   end Reap_Zombie_Channel;

   procedure Purge_Resurrect_Session
     (State   : in out Supervisor_State;
      Cleaned : out    Boolean)
   is
   begin
      State.Channel.Payload_Bytes := 0;
      State.Channel.Status        := Channel_Dormant;
      State.Channel.Is_Leak_Free  := True;
      State.Channel.Is_Sanitized  := True;
      Cleaned                     := True;
   end Purge_Resurrect_Session;

end Legacy_Hardware_Resurrect_Guard;
