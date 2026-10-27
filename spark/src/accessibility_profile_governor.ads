--  SPARK 2022 Formal Specification: Accessibility_Profile_Governor
--  Hippocratic Oath & barrier-free accessibility governor for Asterisk Gateway.
--  Level 4 Gold: 100% Flow analysis and SMT formal verification.

package Accessibility_Profile_Governor with
  SPARK_Mode => On
is

   type Avatar_Detail_Level is range 1 .. 4;
   type Frame_Rate_Type is range 15 .. 120;
   type Audio_Channels_Type is range 1 .. 8;

   type Profile_Record is record
      Active                        : Boolean;
      Is_Disabled_User              : Boolean;
      Deaf_Mode_Enabled             : Boolean;
      Blind_Mode_Enabled            : Boolean;
      Avatar_Detail                 : Avatar_Detail_Level;
      Target_FPS                    : Frame_Rate_Type;
      Audio_Channels                : Audio_Channels_Type;
      Commercial_Billing_Permitted  : Boolean; -- Hippocratic Oath Guard
   end record;

   type Governor_State is record
      Initialized : Boolean;
      Profile     : Profile_Record;
   end record;

   --  Deterministic initialization (Hippocratic Oath default: Free barrier-free access)
   procedure Initialize_Governor (State : out Governor_State) with
     Global => null,
     Depends => (State => null),
     Post => State.Initialized and then
             State.Profile.Active and then
             State.Profile.Is_Disabled_User and then
             State.Profile.Deaf_Mode_Enabled and then
             not State.Profile.Commercial_Billing_Permitted and then
             State.Profile.Target_FPS >= 30 and then
             State.Profile.Avatar_Detail = 3;

   --  Enable deaf mode (3D sign language avatar) with minimum 30 FPS guarantee
   procedure Enable_Deaf_Mode
     (State   : in out Governor_State;
      Detail  : Avatar_Detail_Level;
      Success : out Boolean) with
     Global => null,
     Depends => (State => (State, Detail),
                 Success => State),
     Pre => State.Initialized,
     Post => (if Success then
                State.Profile.Deaf_Mode_Enabled and then
                State.Profile.Avatar_Detail = Detail and then
                State.Profile.Target_FPS >= 30 and then
                (if State.Profile.Is_Disabled_User then
                   not State.Profile.Commercial_Billing_Permitted)
              else
                State = State'Old);

   --  Set user tier: If user is disabled, commercial billing is mathematically FORBIDDEN
   procedure Set_User_Accessibility_Tier
     (State       : in out Governor_State;
      Is_Disabled : Boolean;
      Success     : out Boolean) with
     Global => null,
     Depends => (State => (State, Is_Disabled),
                 Success => State),
     Pre => State.Initialized,
     Post => (if Success then
                State.Profile.Is_Disabled_User = Is_Disabled and then
                (if Is_Disabled then not State.Profile.Commercial_Billing_Permitted)
              else
                State = State'Old);

end Accessibility_Profile_Governor;
