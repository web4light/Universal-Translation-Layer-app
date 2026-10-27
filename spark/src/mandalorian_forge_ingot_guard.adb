pragma SPARK_Mode (On);

package body Mandalorian_Forge_Ingot_Guard is

   Default_Slot : constant Ingot_Record :=
     (Active      => False,
      Ingot_ID    => 1,
      Mass_Grams  => 1,
      Purity      => 990,
      Bound_Owner => 1,
      Status      => Status_Idle);

   procedure Initialize_Forge_Vault
     (Vault : out Forge_Vault)
   is
   begin
      Vault.Vault_Active := True;
      Vault.Slot_Count   := 0;
      Vault.Total_Mass   := 0;
      Vault.Slots        := (others => Default_Slot);
   end Initialize_Forge_Vault;

   procedure Smelt_Ingot
     (Vault   : in out Forge_Vault;
      Slot    : in     Slot_Index;
      ID      : in     Ingot_ID_Type;
      Mass    : in     Grams_Type;
      Purity  : in     Purity_Permille;
      Owner   : in     Recipient_ID_Type;
      Success : out    Boolean)
   is
   begin
      if not Vault.Slots (Slot).Active and then
         Vault.Slot_Count < 16 and then
         Vault.Total_Mass <= 16_000 - Natural (Mass)
      then
         Vault.Slots (Slot) :=
           (Active      => True,
            Ingot_ID    => ID,
            Mass_Grams  => Mass,
            Purity      => Purity,
            Bound_Owner => Owner,
            Status      => Status_Smelting);

         Vault.Slot_Count := Vault.Slot_Count + 1;
         Vault.Total_Mass := Vault.Total_Mass + Natural (Mass);
         Success          := True;
      else
         Success := False;
      end if;
   end Smelt_Ingot;

   procedure Forge_To_Soulbound_Armor
     (Vault   : in out Forge_Vault;
      Slot    : in     Slot_Index;
      Success : out    Boolean)
   is
   begin
      if Vault.Slots (Slot).Active and then
         Vault.Slots (Slot).Status = Status_Smelting
      then
         Vault.Slots (Slot).Status := Status_Forged_To_Armor;
         Success := True;
      else
         Success := False;
      end if;
   end Forge_To_Soulbound_Armor;

end Mandalorian_Forge_Ingot_Guard;
