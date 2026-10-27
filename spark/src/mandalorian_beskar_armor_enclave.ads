--  =============================================================================
--  Mandalorian_Beskar_Armor_Enclave (SPARK 2014 / DO-178C Level A)
--  Sovereign Soulbound Armor Enclave (SB-NFT: Štít i Meč).
--  Guards personal agent life-binding, wallet drain immunity, and Beskar shield.
--  No version numbers; immutable bond to sovereign hardware identity.
--  =============================================================================

package Mandalorian_Beskar_Armor_Enclave with
  SPARK_Mode => On
is

   type Identity_Hash is mod 2**32;
   type Armor_Integrity_Score is range 0 .. 1000;
   type Coin_Gros_Count is range 0 .. 100_000;
   type Attack_Counter is range 0 .. 1_000_000;

   type Armor_Enclave_State is record
      Owner_Identity    : Identity_Hash;
      Is_Bound          : Boolean;
      Integrity         : Armor_Integrity_Score;
      Spend_Limit       : Coin_Gros_Count;
      Total_Spent       : Coin_Gros_Count;
      Attacks_Deflected : Attack_Counter;
   end record;

   --  Initial unbound state
   procedure Initialize_Enclave
     (State : out Armor_Enclave_State)
   with
     Global => null,
     Post   => not State.Is_Bound and
               State.Integrity = 0 and
               State.Spend_Limit = 0 and
               State.Total_Spent = 0 and
               State.Attacks_Deflected = 0;

   --  Soulbound binding: forged once in the Mandalorian Forge for life
   procedure Bind_Soulbound_Armor
     (State       : in out Armor_Enclave_State;
      Identity    : in     Identity_Hash;
      Initial_Lim : in     Coin_Gros_Count)
   with
     Global => null,
     Pre    => not State.Is_Bound and Identity /= 0 and Initial_Lim > 0,
     Post   => State.Is_Bound and
               State.Owner_Identity = Identity and
               State.Integrity = 1000 and
               State.Spend_Limit = Initial_Lim and
               State.Total_Spent = 0 and
               State.Attacks_Deflected = 0;

   --  Shield check: verify and authorize outbound wallet spend
   procedure Authorize_Spend
     (State     : in out Armor_Enclave_State;
      Requester : in     Identity_Hash;
      Amount    : in     Coin_Gros_Count;
      Allowed   : out    Boolean)
   with
     Global => null,
     Pre    => State.Is_Bound and State.Attacks_Deflected < Attack_Counter'Last,
     Post   => (if Allowed then
                  Requester = State.Owner_Identity and
                  State.Total_Spent = State.Total_Spent'Old + Amount and
                  State.Total_Spent <= State.Spend_Limit and
                  State.Attacks_Deflected = State.Attacks_Deflected'Old and
                  State.Owner_Identity = State.Owner_Identity'Old and
                  State.Is_Bound = State.Is_Bound'Old and
                  State.Integrity = State.Integrity'Old and
                  State.Spend_Limit = State.Spend_Limit'Old
                else
                  State.Total_Spent = State.Total_Spent'Old and
                  State.Owner_Identity = State.Owner_Identity'Old and
                  State.Is_Bound = State.Is_Bound'Old and
                  State.Integrity = State.Integrity'Old and
                  State.Spend_Limit = State.Spend_Limit'Old and
                  (if Requester /= State.Owner_Identity then
                     State.Attacks_Deflected = State.Attacks_Deflected'Old + 1
                   else
                     State.Attacks_Deflected = State.Attacks_Deflected'Old));

   --  Beskar reforging in the Great Forge
   procedure Reforge_Beskar_Shield
     (State      : in out Armor_Enclave_State;
      New_Limit  : in     Coin_Gros_Count)
   with
     Global => null,
     Pre    => State.Is_Bound and New_Limit >= State.Total_Spent,
     Post   => State.Is_Bound and
               State.Integrity = 1000 and
               State.Spend_Limit = New_Limit and
               State.Total_Spent = State.Total_Spent'Old and
               State.Owner_Identity = State.Owner_Identity'Old and
               State.Attacks_Deflected = State.Attacks_Deflected'Old;

end Mandalorian_Beskar_Armor_Enclave;
