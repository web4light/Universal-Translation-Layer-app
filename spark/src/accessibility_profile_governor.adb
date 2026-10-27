--  SPARK 2022 Implementation: Accessibility_Profile_Governor
package body Accessibility_Profile_Governor with
  SPARK_Mode => On
is

   procedure Initialize_Governor (State : out Governor_State) is
   begin
      State := (Initialized => True,
                Profile     =>
                  (Active                       => True,
                   Is_Disabled_User             => True,
                   Deaf_Mode_Enabled            => True,
                   Blind_Mode_Enabled           => False,
                   Avatar_Detail                => 3,
                   Target_FPS                   => 60,
                   Audio_Channels               => 2,
                   Commercial_Billing_Permitted => False));
   end Initialize_Governor;

   procedure Enable_Deaf_Mode
     (State   : in out Governor_State;
      Detail  : Avatar_Detail_Level;
      Success : out Boolean)
   is
   begin
      if not State.Profile.Active then
         Success := False;
         return;
      end if;

      State.Profile.Deaf_Mode_Enabled := True;
      State.Profile.Avatar_Detail     := Detail;
      State.Profile.Target_FPS        := 60;

      if State.Profile.Is_Disabled_User then
         State.Profile.Commercial_Billing_Permitted := False;
      end if;

      Success := True;
   end Enable_Deaf_Mode;

   procedure Set_User_Accessibility_Tier
     (State       : in out Governor_State;
      Is_Disabled : Boolean;
      Success     : out Boolean)
   is
   begin
      if not State.Profile.Active then
         Success := False;
         return;
      end if;

      State.Profile.Is_Disabled_User := Is_Disabled;
      if Is_Disabled then
         State.Profile.Commercial_Billing_Permitted := False;
      end if;

      Success := True;
   end Set_User_Accessibility_Tier;

end Accessibility_Profile_Governor;
