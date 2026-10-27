--  =============================================================================
--  Legacy_Hardware_Resurrect_Guard (SPARK 2022 / DO-178C DAL-A)
--  Sovereign Web 4.23 & Kiroween 2026: Resurrecting Dead Tech with Aerospace Safety.
--  Formal invariant enforcement for legacy hardware protocol bridges (SIP/RS-232/DTMF),
--  zombie process reaping with zero resource leaks, and 04:23 UTC volatile RAM purge.
--  =============================================================================

package Legacy_Hardware_Resurrect_Guard with
  SPARK_Mode => On
is

   subtype Device_ID is Positive range 1 .. 32;
   subtype Frame_Payload_Size is Natural range 0 .. 512;

   type Legacy_Protocol is
     (Proto_Serial_RS232,
      Proto_Asterisk_SIP,
      Proto_Teletext_Dactyl,
      Proto_Analog_DTMF);

   type Channel_Status is
     (Channel_Dormant,
      Channel_Resurrected,
      Channel_Zombie_Reaped);

   type Resurrected_Channel_Record is record
      Dev_Id         : Device_ID;
      Protocol       : Legacy_Protocol;
      Payload_Bytes  : Frame_Payload_Size;
      Status         : Channel_Status;
      Is_Leak_Free   : Boolean;
      Is_Sanitized   : Boolean;
   end record;

   type Supervisor_State is record
      Channel        : Resurrected_Channel_Record;
      Total_Reaped   : Natural;
      Total_Frames   : Natural;
   end record;

   --  Initialize pristine legacy resurrect supervisor state
   procedure Initialize_Supervisor
     (State : out Supervisor_State)
   with
     Global => null,
     Post   => State.Channel.Dev_Id = 1 and
               State.Channel.Protocol = Proto_Asterisk_SIP and
               State.Channel.Payload_Bytes = 0 and
               State.Channel.Status = Channel_Dormant and
               State.Channel.Is_Leak_Free = True and
               State.Channel.Is_Sanitized = True and
               State.Total_Reaped = 0 and
               State.Total_Frames = 0;

   --  Resurrect legacy hardware channel with bounded buffer invariant
   procedure Resurrect_Channel
     (State    : in out Supervisor_State;
      Dev      : in     Device_ID;
      Proto    : in     Legacy_Protocol;
      Accepted : out    Boolean)
   with
     Global => null,
     Post   => (if Accepted then
                  State.Channel.Dev_Id = Dev and
                  State.Channel.Protocol = Proto and
                  State.Channel.Payload_Bytes = 0 and
                  State.Channel.Status = Channel_Resurrected and
                  State.Channel.Is_Leak_Free = True and
                  State.Channel.Is_Sanitized = False
                else
                  State.Channel.Status = State.Channel.Status'Old);

   --  Reap zombie process and reclaim resources with zero-leak guarantee
   procedure Reap_Zombie_Channel
     (State   : in out Supervisor_State;
      Success : out    Boolean)
   with
     Global => null,
     Pre    => State.Total_Reaped < Natural'Last,
     Post   => (if Success then
                  State.Channel.Payload_Bytes = 0 and
                  State.Channel.Status = Channel_Zombie_Reaped and
                  State.Channel.Is_Leak_Free = True and
                  State.Channel.Is_Sanitized = True and
                  State.Total_Reaped = State.Total_Reaped'Old + 1
                else
                  State.Total_Reaped = State.Total_Reaped'Old);

   --  Deterministic 04:23 UTC RAM scrub (clean slate non-binary zero)
   procedure Purge_Resurrect_Session
     (State   : in out Supervisor_State;
      Cleaned : out    Boolean)
   with
     Global => null,
     Post   => State.Channel.Payload_Bytes = 0 and
               State.Channel.Status = Channel_Dormant and
               State.Channel.Is_Leak_Free = True and
               State.Channel.Is_Sanitized = True and
               Cleaned = True;

end Legacy_Hardware_Resurrect_Guard;
