--  =============================================================================
--  Mandalorian_Multi_Coin_Vault_Governor - Implementation
--  =============================================================================

package body Mandalorian_Multi_Coin_Vault_Governor with
  SPARK_Mode => On
is

   procedure Initialize_Vault
     (Vault : out Multi_Coin_Vault)
   is
   begin
      Vault := (Silver_Ag_Custody_Cg => 0,
                Gold_Au_Custody_Cg   => 0,
                Beskar_Custody_Cg    => 0,
                Minted_Gros_Count    => 0,
                Minted_Dukat_Count   => 0,
                Minted_Beskar_Count  => 0,
                Burned_Gas_Ash_Units => 0);
   end Initialize_Vault;

   procedure Deposit_Collateral
     (Vault      : in out Multi_Coin_Vault;
      Silver_Cg  : in     Centigrams_Type;
      Gold_Cg    : in     Centigrams_Type;
      Beskar_Cg  : in     Centigrams_Type)
   is
   begin
      Vault.Silver_Ag_Custody_Cg := Vault.Silver_Ag_Custody_Cg + Silver_Cg;
      Vault.Gold_Au_Custody_Cg   := Vault.Gold_Au_Custody_Cg + Gold_Cg;
      Vault.Beskar_Custody_Cg    := Vault.Beskar_Custody_Cg + Beskar_Cg;
   end Deposit_Collateral;

   procedure Mint_Silver_Gros
     (Vault    : in out Multi_Coin_Vault;
      Quantity : in     Coin_Count_Type;
      Success  : out    Boolean)
   is
   begin
      if Vault.Minted_Gros_Count <= Coin_Count_Type'Last - Quantity then
         declare
            New_Total   : constant Coin_Count_Type := Vault.Minted_Gros_Count + Quantity;
            Required_Cg : constant Long_Long_Integer :=
              Long_Long_Integer (New_Total) * Long_Long_Integer (Gros_Ag_Unit_Cg);
         begin
            if Required_Cg <= Long_Long_Integer (Vault.Silver_Ag_Custody_Cg) then
               Vault.Minted_Gros_Count := New_Total;
               Success := True;
            else
               Success := False;
            end if;
         end;
      else
         Success := False;
      end if;
   end Mint_Silver_Gros;

   procedure Mint_Gold_Dukat
     (Vault    : in out Multi_Coin_Vault;
      Quantity : in     Coin_Count_Type;
      Success  : out    Boolean)
   is
   begin
      if Vault.Minted_Dukat_Count <= Coin_Count_Type'Last - Quantity then
         declare
            New_Total   : constant Coin_Count_Type := Vault.Minted_Dukat_Count + Quantity;
            Required_Cg : constant Long_Long_Integer :=
              Long_Long_Integer (New_Total) * Long_Long_Integer (Dukat_Au_Unit_Cg);
         begin
            if Required_Cg <= Long_Long_Integer (Vault.Gold_Au_Custody_Cg) then
               Vault.Minted_Dukat_Count := New_Total;
               Success := True;
            else
               Success := False;
            end if;
         end;
      else
         Success := False;
      end if;
   end Mint_Gold_Dukat;

   procedure Forge_Beskar_Ingot
     (Vault    : in out Multi_Coin_Vault;
      Quantity : in     Coin_Count_Type;
      Success  : out    Boolean)
   is
   begin
      if Vault.Minted_Beskar_Count <= Coin_Count_Type'Last - Quantity then
         declare
            New_Total   : constant Coin_Count_Type := Vault.Minted_Beskar_Count + Quantity;
            Required_Cg : constant Long_Long_Integer :=
              Long_Long_Integer (New_Total) * Long_Long_Integer (Beskar_Unit_Cg);
         begin
            if Required_Cg <= Long_Long_Integer (Vault.Beskar_Custody_Cg) then
               Vault.Minted_Beskar_Count := New_Total;
               Success := True;
            else
               Success := False;
            end if;
         end;
      else
         Success := False;
      end if;
   end Forge_Beskar_Ingot;

end Mandalorian_Multi_Coin_Vault_Governor;
