--  SPARK 2022 Implementation: Agent_Capability_Enclave
package body Agent_Capability_Enclave with
  SPARK_Mode => On
is

   procedure Initialize_Enclave (State : out Enclave_State) is
   begin
      State := (Initialized => True,
                Agents      =>
                  (1      => (Active => True,
                              Capabilities => 0,
                              Security_Tier => 3),
                   others => (Active => False,
                              Capabilities => 0,
                              Security_Tier => 0)));
   end Initialize_Enclave;

   procedure Grant_Capability
     (State   : in out Enclave_State;
      Agent   : Agent_Id;
      Cap     : Capability_Mask;
      Success : out Boolean)
   is
   begin
      --  Security tier guard for critical capabilities
      if (Cap and CRITICAL_MASK) /= 0 and then State.Agents (Agent).Security_Tier < 2 then
         Success := False;
         return;
      end if;

      State.Agents (Agent).Active := True;
      State.Agents (Agent).Capabilities := State.Agents (Agent).Capabilities or Cap;
      Success := True;
   end Grant_Capability;

   procedure Revoke_Capability
     (State   : in out Enclave_State;
      Agent   : Agent_Id;
      Cap     : Capability_Mask;
      Success : out Boolean)
   is
   begin
      if not State.Agents (Agent).Active then
         Success := False;
         return;
      end if;

      State.Agents (Agent).Capabilities := State.Agents (Agent).Capabilities and (not Cap);
      Success := True;
   end Revoke_Capability;

   procedure Set_Security_Tier
     (State    : in out Enclave_State;
      Caller   : Agent_Id;
      Target   : Agent_Id;
      New_Tier : Security_Tier_Type;
      Success  : out Boolean)
   is
   begin
      --  Only caller with Security_Tier = 3 can change tiers
      if State.Agents (Caller).Security_Tier /= 3 or else not State.Agents (Caller).Active then
         Success := False;
         return;
      end if;

      State.Agents (Target).Security_Tier := New_Tier;
      if New_Tier < 2 then
         State.Agents (Target).Capabilities := State.Agents (Target).Capabilities and (not CRITICAL_MASK);
      end if;
      Success := True;
   end Set_Security_Tier;

end Agent_Capability_Enclave;
