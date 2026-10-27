pragma SPARK_Mode (On);

package Mandalorian_Forge_Ingot_Guard is

   type Ingot_ID_Type is range 1 .. 100_000;
   type Recipient_ID_Type is range 1 .. 10_000;
   type Grams_Type is range 1 .. 1_000;
   type Purity_Permille is range 990 .. 1_000;
   type Slot_Index is range 1 .. 16;

   type Forge_Status_Type is (Status_Idle, Status_Smelting, Status_Forged_To_Armor, Status_Quenched);

   type Ingot_Record is record
      Active      : Boolean;
      Ingot_ID    : Ingot_ID_Type;
      Mass_Grams  : Grams_Type;
      Purity      : Purity_Permille;
      Bound_Owner : Recipient_ID_Type;
      Status      : Forge_Status_Type;
   end record;

   type Ingot_Vault_Array is array (Slot_Index) of Ingot_Record;

   type Forge_Vault is record
      Vault_Active : Boolean;
      Slot_Count   : Natural range 0 .. 16;
      Total_Mass   : Natural range 0 .. 16_000;
      Slots        : Ingot_Vault_Array;
   end record;

   procedure Initialize_Forge_Vault
     (Vault : out Forge_Vault)
   with
     Global => null,
     Depends => (Vault => null),
     Post =>
       Vault.Vault_Active and then
       Vault.Slot_Count = 0 and then
       Vault.Total_Mass = 0 and then
       (for all S in Slot_Index => not Vault.Slots (S).Active);

   procedure Smelt_Ingot
     (Vault   : in out Forge_Vault;
      Slot    : in     Slot_Index;
      ID      : in     Ingot_ID_Type;
      Mass    : in     Grams_Type;
      Purity  : in     Purity_Permille;
      Owner   : in     Recipient_ID_Type;
      Success : out    Boolean)
   with
     Global => null,
     Depends =>
       (Vault   =>+ (Slot, ID, Mass, Purity, Owner),
        Success => (Vault, Slot, Mass)),
     Pre => Vault.Vault_Active,
     Post =>
       (if Success then
          Vault.Slots (Slot).Active and then
          Vault.Slots (Slot).Ingot_ID = ID and then
          Vault.Slots (Slot).Mass_Grams = Mass and then
          Vault.Slots (Slot).Purity = Purity and then
          Vault.Slots (Slot).Bound_Owner = Owner and then
          Vault.Slots (Slot).Status = Status_Smelting and then
          Vault.Slot_Count = Vault'Old.Slot_Count + 1 and then
          Vault.Total_Mass = Vault'Old.Total_Mass + Natural (Mass) and then
          (for all S in Slot_Index =>
             (if S /= Slot then Vault.Slots (S) = Vault'Old.Slots (S)))
        else
          Vault = Vault'Old);

   procedure Forge_To_Soulbound_Armor
     (Vault   : in out Forge_Vault;
      Slot    : in     Slot_Index;
      Success : out    Boolean)
   with
     Global => null,
     Depends =>
       (Vault   =>+ Slot,
        Success => (Vault, Slot)),
     Pre => Vault.Vault_Active,
     Post =>
       (if Success then
          Vault.Slots (Slot).Active and then
          Vault.Slots (Slot).Status = Status_Forged_To_Armor and then
          Vault.Slots (Slot).Ingot_ID = Vault'Old.Slots (Slot).Ingot_ID and then
          Vault.Slots (Slot).Mass_Grams = Vault'Old.Slots (Slot).Mass_Grams and then
          Vault.Slots (Slot).Purity = Vault'Old.Slots (Slot).Purity and then
          Vault.Slots (Slot).Bound_Owner = Vault'Old.Slots (Slot).Bound_Owner and then
          Vault.Slot_Count = Vault'Old.Slot_Count and then
          Vault.Total_Mass = Vault'Old.Total_Mass and then
          (for all S in Slot_Index =>
             (if S /= Slot then Vault.Slots (S) = Vault'Old.Slots (S)))
        else
          Vault = Vault'Old);

end Mandalorian_Forge_Ingot_Guard;
