--  =============================================================================
--  Asterisk Gateway — Standard 700 Mint Guard Implementation
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  =============================================================================

package body Standard700_Mint_Guard with
  SPARK_Mode => On
is

   procedure Initialize_Vault
     (Vault : out Vault_State)
   is
   begin
      Vault := (Total_Minted_Gros    => 10,
                Custody_Silver_Grams => 120,
                Burned_Gas_Accrued   => 0,
                Swiss_Custody_Active => True);
   end Initialize_Vault;

   procedure Record_Burned_Gas
     (Vault    : in out Vault_State;
      Burn_Gas : in     Burned_Gas)
   is
   begin
      Vault.Burned_Gas_Accrued := Vault.Burned_Gas_Accrued + Burn_Gas;
   end Record_Burned_Gas;

   procedure Deposit_Physical_Silver
     (Vault       : in out Vault_State;
      Grams       : in     Grams_Ag;
      Bank_Active : in     Boolean)
   is
   begin
      Vault.Custody_Silver_Grams := Vault.Custody_Silver_Grams + Grams;
      Vault.Swiss_Custody_Active := Bank_Active;
   end Deposit_Physical_Silver;

   procedure Mint_Gros
     (Vault   : in out Vault_State;
      Amount  : in     Gros_Count;
      Success : out    Boolean)
   is
   begin
      if Vault.Swiss_Custody_Active
        and then Amount <= Max_Gros_Supply - Vault.Total_Minted_Gros
        and then (Vault.Total_Minted_Gros + Amount) * Grams_Per_Gros <= Vault.Custody_Silver_Grams
      then
         Vault.Total_Minted_Gros := Vault.Total_Minted_Gros + Amount;
         Success := True;
      else
         Success := False;
      end if;
   end Mint_Gros;

end Standard700_Mint_Guard;
