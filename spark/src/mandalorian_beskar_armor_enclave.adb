--  =============================================================================
--  Mandalorian_Beskar_Armor_Enclave - Implementation
--  =============================================================================

package body Mandalorian_Beskar_Armor_Enclave with
  SPARK_Mode => On
is

   procedure Initialize_Enclave
     (State : out Armor_Enclave_State)
   is
   begin
      State := (Owner_Identity    => 0,
                Is_Bound          => False,
                Integrity         => 0,
                Spend_Limit       => 0,
                Total_Spent       => 0,
                Attacks_Deflected => 0);
   end Initialize_Enclave;

   procedure Bind_Soulbound_Armor
     (State       : in out Armor_Enclave_State;
      Identity    : in     Identity_Hash;
      Initial_Lim : in     Coin_Gros_Count)
   is
   begin
      State.Owner_Identity    := Identity;
      State.Is_Bound          := True;
      State.Integrity         := 1000;
      State.Spend_Limit       := Initial_Lim;
      State.Total_Spent       := 0;
      State.Attacks_Deflected := 0;
   end Bind_Soulbound_Armor;

   procedure Authorize_Spend
     (State     : in out Armor_Enclave_State;
      Requester : in     Identity_Hash;
      Amount    : in     Coin_Gros_Count;
      Allowed   : out    Boolean)
   is
   begin
      if Requester /= State.Owner_Identity then
         Allowed := False;
         State.Attacks_Deflected := State.Attacks_Deflected + 1;
         return;
      end if;

      if Amount <= State.Spend_Limit - State.Total_Spent then
         State.Total_Spent := State.Total_Spent + Amount;
         Allowed := True;
      else
         Allowed := False;
      end if;
   end Authorize_Spend;

   procedure Reforge_Beskar_Shield
     (State      : in out Armor_Enclave_State;
      New_Limit  : in     Coin_Gros_Count)
   is
   begin
      State.Integrity   := 1000;
      State.Spend_Limit := New_Limit;
   end Reforge_Beskar_Shield;

end Mandalorian_Beskar_Armor_Enclave;
