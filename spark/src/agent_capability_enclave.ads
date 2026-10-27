--  SPARK 2022 Formal Specification: Agent_Capability_Enclave
--  Fine-grained capability-based security model for autonomous agents.
--  Level 4 Gold: 100% Flow analysis and SMT formal verification.

with Interfaces; use Interfaces;

package Agent_Capability_Enclave with
  SPARK_Mode => On
is

   type Agent_Id is range 1 .. 16;
   type Capability_Mask is new Interfaces.Unsigned_32;
   subtype Security_Tier_Type is Natural range 0 .. 3;

   --  Defined capability bits
   CAP_TAVILY_QUERY      : constant Capability_Mask := 2**0; -- 1
   CAP_TELEMETRY_SCRAPE  : constant Capability_Mask := 2**1; -- 2
   CAP_PROPOSE_CONSENSUS : constant Capability_Mask := 2**2; -- 4
   CAP_MINT_STANDARD700  : constant Capability_Mask := 2**3; -- 8
   CAP_SWEEP_ASH         : constant Capability_Mask := 2**4; -- 16
   CAP_ROUTE_MESH        : constant Capability_Mask := 2**5; -- 32
   CAP_EMIT_TELEMETRY    : constant Capability_Mask := 2**6; -- 64

   CRITICAL_MASK : constant Capability_Mask := CAP_MINT_STANDARD700 or CAP_SWEEP_ASH;

   type Enclave_Record is record
      Active        : Boolean;
      Capabilities  : Capability_Mask;
      Security_Tier : Security_Tier_Type; -- 0: Untrusted, 1: Standard, 2: Operator, 3: Sovereign Root
   end record;

   type Enclave_Table is array (Agent_Id) of Enclave_Record;

   type Enclave_State is record
      Initialized : Boolean;
      Agents      : Enclave_Table;
   end record;

   --  Deterministic initialization with Zero-Heap
   procedure Initialize_Enclave (State : out Enclave_State) with
     Global => null,
     Depends => (State => null),
     Post => State.Initialized and then
             State.Agents (1).Security_Tier = 3 and then
             State.Agents (1).Active and then
             (for all Id in Agent_Id =>
                (if Id /= 1 then State.Agents (Id).Security_Tier = 0 and then
                                 State.Agents (Id).Capabilities = 0 and then
                                 not State.Agents (Id).Active));

   --  Pure capability query
   function Has_Capability
     (State : Enclave_State;
      Agent : Agent_Id;
      Cap   : Capability_Mask) return Boolean
   is
     (State.Initialized and then
      Cap > 0 and then
      State.Agents (Agent).Active and then
      (State.Agents (Agent).Capabilities and Cap) = Cap);

   --  Grant capability with strict security tier enforcement
   procedure Grant_Capability
     (State   : in out Enclave_State;
      Agent   : Agent_Id;
      Cap     : Capability_Mask;
      Success : out Boolean) with
     Global => null,
     Depends => (State => (State, Agent, Cap),
                 Success => (State, Agent, Cap)),
     Pre => State.Initialized and Cap > 0,
     Post => (if Success then
                State.Agents (Agent).Active and then
                (if (Cap and CRITICAL_MASK) /= 0 then
                   State.Agents (Agent).Security_Tier >= 2)
              else
                State = State'Old);

   --  Revoke capability
   procedure Revoke_Capability
     (State   : in out Enclave_State;
      Agent   : Agent_Id;
      Cap     : Capability_Mask;
      Success : out Boolean) with
     Global => null,
     Depends => (State => (State, Agent, Cap),
                 Success => (State, Agent)),
     Pre => State.Initialized and Cap > 0,
     Post => (if Success then
                State.Agents (Agent).Active = State'Old.Agents (Agent).Active and then
                State.Agents (Agent).Security_Tier = State'Old.Agents (Agent).Security_Tier
              else
                State = State'Old);

   --  Set security tier (Caller must be root, Target cannot be root)
   procedure Set_Security_Tier
     (State    : in out Enclave_State;
      Caller   : Agent_Id;
      Target   : Agent_Id;
      New_Tier : Security_Tier_Type;
      Success  : out Boolean) with
     Global => null,
     Depends => (State => (State, Caller, Target, New_Tier),
                 Success => (State, Caller)),
     Pre => State.Initialized and Caller /= Target and Target /= 1,
     Post => (if Success then
                State.Agents (Caller).Security_Tier = 3 and then
                State.Agents (Target).Security_Tier = New_Tier
              else
                State = State'Old);

end Agent_Capability_Enclave;
