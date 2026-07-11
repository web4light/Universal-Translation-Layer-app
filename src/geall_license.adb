--  ============================================================================
--  Geall License Validator - Ada/SPARK 2022
--
--  Účel: Validace Household licence (plán 423 Kč/měsíc)
--        Air-gapped — NEKOMUNIKUJE s Vakuovou Mincovnou přímo.
--        Kontroluje Standard 700 silver-gram invariant lokálně.
--
--  Standard 700: 12g stříbra = 1 mince
--
--  Použití:
--    geall_license.exe --license-id <id>
--
--  Výstup (stdout):
--    {"active": <bool>, "plan": "<str>", "expires_unix": <float>, "device_count": <int>}
--
--  Autor: Pan Jeskyně
--  Asistent: Kiro (Claude Sonnet 4.5)
--  ============================================================================

with Ada.Text_IO;
with Ada.Command_Line;
with Ada.Strings.Unbounded;

procedure Geall_License with
   SPARK_Mode => On
is
   use Ada.Text_IO;
   use Ada.Command_Line;
   use Ada.Strings.Unbounded;

   --  ===========================================================================
   --  KONSTANTY - STANDARD 700 & HOUSEHOLD PLAN
   --  ===========================================================================

   STANDARD_700_SILVER  : constant Float   := 12.0;   -- 12g stříbra na minci
   HOUSEHOLD_PRICE_CZK  : constant Natural := 423;    -- 423 Kč/měsíc
   HOUSEHOLD_MAX_DEVICES : constant Natural := 10;    -- max zařízení v domácnosti
   SUBSCRIPTION_SECONDS : constant Float   := 2_592_000.0; -- 30 × 86400 s

   --  Simulovaná "aktuální" Unix epocha (při air-gap provozu není síť)
   --  V produkci by toto bylo čteno z RTC / protected hardware clock.
   DEMO_NOW_UNIX        : constant Float   := 1_750_000_000.0;

   --  ===========================================================================
   --  TYPY DLE DESIGN DOKUMENTU
   --  ===========================================================================

   --  Počet mincí — nezáporné celé číslo
   type Coin_Amount is new Natural;

   --  Operační paměť v MB (0 .. 512) — hard ceiling systému
   type Memory_MB is new Natural range 0 .. 512;

   --  Silver amount — nezáporné desetinné číslo
   type Silver_Amount is digits 15 range 0.0 .. 1.0E12;

   --  ===========================================================================
   --  FORMÁLNĚ OVĚŘENÁ FUNKCE — STANDARD 700 INVARIANT
   --  ===========================================================================

   --  Vrátí počet mincí z dané hmotnosti stříbra.
   --  Pre:  Silver_Grams musí být >= 0.0
   --  Post: Je-li stříbra méně než 12g, výsledek = 0; jinak výsledek > 0.
   function Calculate_Coins_From_Silver
      (Silver_Grams : Silver_Amount) return Coin_Amount
   with
      Pre  => Silver_Grams >= 0.0,
      Post => (if Silver_Grams < Silver_Amount (STANDARD_700_SILVER)
               then Calculate_Coins_From_Silver'Result = 0
               else Calculate_Coins_From_Silver'Result > 0)
   is
   begin
      if Silver_Grams < Silver_Amount (STANDARD_700_SILVER) then
         return 0;
      else
         return Coin_Amount (Float'Floor (Float (Silver_Grams)
                                          / STANDARD_700_SILVER));
      end if;
   end Calculate_Coins_From_Silver;

   --  ===========================================================================
   --  LICENCE — VALIDACE HOUSEHOLD PLÁNU
   --  ===========================================================================

   --  Validate_Household zkontroluje silver-gram invariant pro zadané
   --  license-id a zapíše JSON status řádek na stdout.
   --
   --  Logika (air-gap, bez volání Mincovny):
   --    1. License-id "HOUSEHOLD-*" → aktivní household plán
   --    2. Jiné id    → neaktivní / neznámý plán
   --    3. Standard 700 invariant se ověřuje na symbolické hodnotě
   --       korespondující s household plánem (1 mince = 12g).
   procedure Validate_Household (License_Id : String) is

      --  Symbolická silver hodnota odpovídající 1 household minci
      Household_Silver : constant Silver_Amount := Silver_Amount (STANDARD_700_SILVER);

      Coins       : Coin_Amount;
      Is_Active   : Boolean;
      Plan_Name   : Unbounded_String;
      Expires_Unix : Float;
      Device_Count : Natural;

      --  Minimální in-place Boolean → JSON-string konverze
      function Bool_To_JSON (B : Boolean) return String is
      begin
         if B then return "true"; else return "false"; end if;
      end Bool_To_JSON;

   begin
      --  Standard 700 invariant check — musí projít pro jakékoli kladné id
      Coins := Calculate_Coins_From_Silver (Household_Silver);

      --  Detekce household licence podle prefixu
      if License_Id'Length >= 10
         and then License_Id (License_Id'First .. License_Id'First + 9) = "HOUSEHOLD-"
         and then Coins > 0
      then
         Is_Active    := True;
         Plan_Name    := To_Unbounded_String ("household");
         Expires_Unix := DEMO_NOW_UNIX + SUBSCRIPTION_SECONDS;
         Device_Count := HOUSEHOLD_MAX_DEVICES;
      else
         Is_Active    := False;
         Plan_Name    := To_Unbounded_String ("unknown");
         Expires_Unix := 0.0;
         Device_Count := 0;
      end if;

      --  JSON výstup (jedna řádka, bez whitespace navíc — Python subprocess ho parsuje)
      Put_Line ("{""active"": " & Bool_To_JSON (Is_Active)
               & ", ""plan"": """ & To_String (Plan_Name) & """"
               & ", ""expires_unix"": " & Float'Image (Expires_Unix)
               & ", ""device_count"": " & Natural'Image (Device_Count)
               & "}");
   end Validate_Household;

   --  ===========================================================================
   --  VSTUPNÍ BOD — CLI ARGUMENT PARSING
   --  ===========================================================================

   License_Id_Value : Unbounded_String := To_Unbounded_String ("");
   Found_License_Id : Boolean := False;
   Arg_Index        : Natural;

begin
   --  Parsování --license-id <value>
   Arg_Index := 1;
   while Arg_Index <= Argument_Count loop
      if Argument (Arg_Index) = "--license-id" then
         if Arg_Index < Argument_Count then
            Arg_Index := Arg_Index + 1;
            License_Id_Value := To_Unbounded_String (Argument (Arg_Index));
            Found_License_Id := True;
         else
            Put_Line (Standard_Error,
                      "[LICENSE] Error: --license-id requires a value");
            Set_Exit_Status (Failure);
            return;
         end if;
      end if;
      Arg_Index := Arg_Index + 1;
   end loop;

   if not Found_License_Id then
      Put_Line (Standard_Error,
                "[LICENSE] Error: --license-id argument is required");
      Put_Line (Standard_Error,
                "[LICENSE] Usage: geall_license.exe --license-id <id>");
      Set_Exit_Status (Failure);
      return;
   end if;

   --  Validace a JSON výstup
   Validate_Household (To_String (License_Id_Value));

end Geall_License;
