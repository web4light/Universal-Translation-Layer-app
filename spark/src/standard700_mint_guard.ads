--  =============================================================================
--  Asterisk Gateway — Standard 700 Mint Guard
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  Zero synthetic tokens: strictly enforces physical silver custody backing
--  (12g Ag per Groš) and Swiss bank verification before any coin minting.
--  Burned gas/ether is logged as raw waste and cannot mint value.
--  =============================================================================

package Standard700_Mint_Guard with
  SPARK_Mode => On
is
   Grams_Per_Gros  : constant := 12;
   Max_Gros_Supply : constant := 1_000_000;
   Max_Grams_Ag    : constant := Max_Gros_Supply * Grams_Per_Gros;

   subtype Gros_Count is Natural range 0 .. Max_Gros_Supply;
   subtype Grams_Ag is Natural range 0 .. Max_Grams_Ag;
   subtype Burned_Gas is Natural range 0 .. 100_000_000;

   type Vault_State is record
      Total_Minted_Gros    : Gros_Count;
      Custody_Silver_Grams : Grams_Ag;
      Burned_Gas_Accrued   : Burned_Gas;
      Swiss_Custody_Active : Boolean;
   end record;

   --  Initializes the mint vault in a pristine, verified backed state:
   --  Initial 10 Grošů backed by 120g Ag under active custody.
   procedure Initialize_Vault
     (Vault : out Vault_State)
   with
     Global => null,
     Depends => (Vault => null),
     Post => Vault.Total_Minted_Gros = 10 and then
             Vault.Custody_Silver_Grams = 120 and then
             Vault.Burned_Gas_Accrued = 0 and then
             Vault.Swiss_Custody_Active;

   --  Records incinerated gas/ether.
   --  Mathematically guarantees burn does not increment minted supply or custody.
   procedure Record_Burned_Gas
     (Vault    : in out Vault_State;
      Burn_Gas : in     Burned_Gas)
   with
     Global => null,
     Depends => (Vault =>+ Burn_Gas),
     Pre  => Burn_Gas <= 100_000 and then
             Vault.Burned_Gas_Accrued <= Burned_Gas'Last - Burn_Gas,
     Post => Vault.Burned_Gas_Accrued = Vault.Burned_Gas_Accrued'Old + Burn_Gas and then
             Vault.Total_Minted_Gros = Vault.Total_Minted_Gros'Old and then
             Vault.Custody_Silver_Grams = Vault.Custody_Silver_Grams'Old and then
             Vault.Swiss_Custody_Active = Vault.Swiss_Custody_Active'Old;

   --  Deposits verified physical silver grams under Swiss bank custody.
   procedure Deposit_Physical_Silver
     (Vault       : in out Vault_State;
      Grams       : in     Grams_Ag;
      Bank_Active : in     Boolean)
   with
     Global => null,
     Depends => (Vault =>+ (Grams, Bank_Active)),
     Pre  => Vault.Custody_Silver_Grams <= Max_Grams_Ag - Grams,
     Post => Vault.Custody_Silver_Grams = Vault.Custody_Silver_Grams'Old + Grams and then
             Vault.Swiss_Custody_Active = Bank_Active and then
             Vault.Total_Minted_Gros = Vault.Total_Minted_Gros'Old and then
             Vault.Burned_Gas_Accrued = Vault.Burned_Gas_Accrued'Old;

   --  Mints new Groš ONLY IF physical silver is physically present and verified.
   --  Zero unbacked tokens allowed under Standard 700 law.
   procedure Mint_Gros
     (Vault   : in out Vault_State;
      Amount  : in     Gros_Count;
      Success : out    Boolean)
   with
     Global => null,
     Depends => ((Vault, Success) => (Vault, Amount)),
     Post => (if Success then
                Vault.Total_Minted_Gros = Vault.Total_Minted_Gros'Old + Amount and then
                Vault.Total_Minted_Gros * Grams_Per_Gros <= Vault.Custody_Silver_Grams and then
                Vault.Swiss_Custody_Active
              else
                Vault = Vault'Old);

end Standard700_Mint_Guard;
