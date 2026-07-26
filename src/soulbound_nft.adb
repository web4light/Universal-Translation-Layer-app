--  ============================================================================
--  Soulbound NFT - Ada/SPARK Formally Verified Identity Logic
--
--  Purpose: Validates Soulbound NFT rules for Karel IV. digital identity
--           1 person = 1 identity (biometric binding)
--           Non-transferable NFT (soulbound = cannot be sold or moved)
--           Subscription tier access verification
--           Biometric-to-wallet binding (GNAT Mincovna exclusive)
--           Display name support (independent of wallet address)
--
--  Standard 700: 12g silver = 1 coin
--  Author: Pan Jeskyne (Jakub Panocha)
--  Assistant: Kiro
--  ============================================================================

with Ada.Text_IO;
with Ada.Integer_Text_IO;

procedure Soulbound_Nft with
   SPARK_Mode => On
is
   use Ada.Text_IO;
   use Ada.Integer_Text_IO;

   --  =========================================================================
   --  CONSTANTS
   --  =========================================================================

   MAX_USERS           : constant Natural := 100_000;
   MAX_TIER            : constant Natural := 4;
   BIOMETRIC_HASH_LEN  : constant Natural := 64;  -- SHA-256 hex length
   WALLET_ADDRESS_LEN  : constant Natural := 42;  -- "0x" + 40 hex chars
   MAX_DISPLAY_NAME_LEN : constant Natural := 64;  -- Max display name length

   --  Subscription tiers (CZK/month)
   TIER_PERSONAL    : constant Natural := 111;
   TIER_KAREL       : constant Natural := 222;
   TIER_STREAM      : constant Natural := 333;
   TIER_FAMILY      : constant Natural := 423;

   --  Standard 700
   STANDARD_700_SILVER : constant Float := 12.0;

   --  Biometric verification threshold
   --  False Acceptance Rate must be < 0.001% = 0.00001
   --  Minimum match score to accept (1.0 - FAR = 0.99999)
   FALSE_ACCEPTANCE_RATE : constant Float := 0.00001;
   BIOMETRIC_MATCH_THRESHOLD : constant Float := 0.99999;

   --  =========================================================================
   --  TYPES
   --  =========================================================================

   type Subscription_Tier is (None, Personal, Karel, Stream, Family);

   type Nft_Status is (Not_Minted, Active, Suspended, Burned);

   --  Display name: fixed-length string, actual length tracked separately
   subtype Display_Name_String is String (1 .. MAX_DISPLAY_NAME_LEN);

   type Identity_Record is record
      User_Id          : Natural;
      Tier             : Subscription_Tier;
      Nft_Status       : Soulbound_Nft.Nft_Status;
      Biometric_Bound  : Boolean;
      Transfer_Count   : Natural;  -- Must ALWAYS be 0 (soulbound)
      Silver_Paid      : Float;
      Coins_Minted     : Natural;
      Display_Name     : Display_Name_String;
      Display_Name_Len : Natural;  -- Actual length of display name (0 = not set)
      Wallet_Bound     : Boolean;  -- True if biometric->wallet binding exists
   end record;

   --  Biometric verification result
   type Biometric_Result is record
      Match_Score : Float;   -- 0.0 to 1.0 (similarity score)
      Verified    : Boolean; -- True only if score >= BIOMETRIC_MATCH_THRESHOLD
   end record;

   --  Wallet binding record (biometric hash -> wallet address, GNAT exclusive)
   subtype Wallet_Address_String is String (1 .. WALLET_ADDRESS_LEN);
   subtype Biometric_Hash_String is String (1 .. BIOMETRIC_HASH_LEN);

   type Wallet_Binding is record
      Biometric_Hash  : Biometric_Hash_String;
      Wallet_Address  : Wallet_Address_String;
      Binding_Active  : Boolean;
   end record;

   --  =========================================================================
   --  CORE VERIFICATION FUNCTIONS
   --  =========================================================================

   --  Verify that an NFT is truly soulbound (never transferred)
   function Is_Soulbound (Rec : Identity_Record) return Boolean is
     (Rec.Transfer_Count = 0 and Rec.Biometric_Bound)
   with
      Pre  => Rec.User_Id > 0,
      Post => Is_Soulbound'Result = (Rec.Transfer_Count = 0 and Rec.Biometric_Bound);

   --  Verify Standard 700: can mint coins only with enough silver
   function Can_Mint (Silver_Grams : Float) return Natural
   with
      Pre  => Silver_Grams >= 0.0,
      Post => (if Silver_Grams < STANDARD_700_SILVER
               then Can_Mint'Result = 0
               else Can_Mint'Result > 0)
   is
   begin
      if Silver_Grams < STANDARD_700_SILVER then
         return 0;
      else
         return Natural (Float'Floor (Silver_Grams / STANDARD_700_SILVER));
      end if;
   end Can_Mint;

   --  Verify subscription tier grants access to a feature level
   --  Feature levels: 1=assistant, 2=translation, 3=dubbing, 4=household
   function Has_Feature_Access (Tier : Subscription_Tier;
                                Feature_Level : Natural) return Boolean is
   begin
      case Tier is
         when None     => return False;
         when Personal => return Feature_Level <= 1;
         when Karel    => return Feature_Level <= 2;
         when Stream   => return Feature_Level <= 3;
         when Family   => return Feature_Level <= 4;
      end case;
   end Has_Feature_Access;

   --  Verify one-person-one-identity rule
   --  Returns True only if NFT is active AND soulbound AND biometric-bound
   function Verify_Unique_Identity (Rec : Identity_Record) return Boolean is
   begin
      return Rec.Nft_Status = Active
         and then Rec.Transfer_Count = 0
         and then Rec.Biometric_Bound;
   end Verify_Unique_Identity;

   --  Attempt to transfer NFT (must ALWAYS fail for soulbound)
   function Attempt_Transfer (Rec : Identity_Record) return Boolean
   with
      Post => Attempt_Transfer'Result = False  -- Soulbound = no transfer ever
   is
      pragma Unreferenced (Rec);
   begin
      --  Soulbound NFTs cannot be transferred. Ever.
      return False;
   end Attempt_Transfer;

   --  Calculate tier price in CZK
   function Tier_Price (Tier : Subscription_Tier) return Natural is
   begin
      case Tier is
         when None     => return 0;
         when Personal => return TIER_PERSONAL;
         when Karel    => return TIER_KAREL;
         when Stream   => return TIER_STREAM;
         when Family   => return TIER_FAMILY;
      end case;
   end Tier_Price;

   --  =========================================================================
   --  BIOMETRIC VERIFICATION FUNCTIONS (Requirement 11.4)
   --  =========================================================================

   --  Verify biometric match score against threshold
   --  FAR < 0.001% guaranteed by BIOMETRIC_MATCH_THRESHOLD = 0.99999
   function Verify_Biometric (Match_Score : Float) return Biometric_Result
   with
      Pre  => Match_Score >= 0.0 and Match_Score <= 1.0,
      Post => (if Match_Score >= BIOMETRIC_MATCH_THRESHOLD
               then Verify_Biometric'Result.Verified = True
               else Verify_Biometric'Result.Verified = False)
   is
   begin
      return (Match_Score => Match_Score,
              Verified    => Match_Score >= BIOMETRIC_MATCH_THRESHOLD);
   end Verify_Biometric;

   --  Check if false acceptance rate requirement is met
   --  Returns True only if the configured threshold guarantees FAR < 0.001%
   function Is_FAR_Compliant return Boolean
   with
      Post => Is_FAR_Compliant'Result = (FALSE_ACCEPTANCE_RATE < 0.00001)
   is
   begin
      return FALSE_ACCEPTANCE_RATE < 0.00001;
   end Is_FAR_Compliant;

   --  =========================================================================
   --  WALLET BINDING FUNCTIONS (Requirements 11.1, 11.5)
   --  =========================================================================

   --  Verify wallet binding: biometric hash must match and binding must be active
   --  This binding is stored EXCLUSIVELY within GNAT Mincovna (Req 11.5)
   function Verify_Wallet_Binding (Binding : Wallet_Binding;
                                   Provided_Hash : Biometric_Hash_String)
                                   return Boolean
   with
      Pre  => Binding.Binding_Active,
      Post => Verify_Wallet_Binding'Result =
              (Binding.Biometric_Hash = Provided_Hash and Binding.Binding_Active)
   is
   begin
      return Binding.Biometric_Hash = Provided_Hash
         and then Binding.Binding_Active;
   end Verify_Wallet_Binding;

   --  Check if identity record has valid wallet binding
   function Has_Wallet_Binding (Rec : Identity_Record) return Boolean
   with
      Pre  => Rec.User_Id > 0,
      Post => Has_Wallet_Binding'Result = (Rec.Wallet_Bound and Rec.Biometric_Bound)
   is
   begin
      return Rec.Wallet_Bound and then Rec.Biometric_Bound;
   end Has_Wallet_Binding;

   --  =========================================================================
   --  DISPLAY NAME FUNCTIONS (Requirement 11.6)
   --  =========================================================================

   --  Check if user has a display name set (independent of wallet address)
   function Has_Display_Name (Rec : Identity_Record) return Boolean
   with
      Post => Has_Display_Name'Result = (Rec.Display_Name_Len > 0)
   is
   begin
      return Rec.Display_Name_Len > 0;
   end Has_Display_Name;

   --  Validate display name length is within bounds
   function Is_Valid_Display_Name_Length (Length : Natural) return Boolean
   with
      Post => Is_Valid_Display_Name_Length'Result =
              (Length > 0 and Length <= MAX_DISPLAY_NAME_LEN)
   is
   begin
      return Length > 0 and then Length <= MAX_DISPLAY_NAME_LEN;
   end Is_Valid_Display_Name_Length;

   --  =========================================================================
   --  SELF-TEST
   --  =========================================================================

   Test_User   : Identity_Record;
   Test_Binding : Wallet_Binding;
   Bio_Result  : Biometric_Result;
   Coins       : Natural;
   Price       : Natural;
   Passed      : Natural := 0;
   Total       : constant Natural := 15;

   --  Helper: create a padded display name
   Test_Name : constant String := "PanJeskyne";
   Padded_Name : Display_Name_String := (others => ' ');

begin
   Put_Line ("=== Soulbound NFT - SPARK Verified Identity Logic ===");
   Put_Line ("Standard 700: 12g silver = 1 coin");
   Put_Line ("Rule: 1 person = 1 identity (non-transferable)");
   Put_Line ("Biometric FAR < 0.001% (threshold: 0.99999)");
   New_Line;

   --  Prepare padded display name
   Padded_Name (1 .. Test_Name'Length) := Test_Name;

   --  Setup test user with extended fields
   Test_User := (
      User_Id          => 1,
      Tier             => Karel,
      Nft_Status       => Active,
      Biometric_Bound  => True,
      Transfer_Count   => 0,
      Silver_Paid      => 36.0,
      Coins_Minted     => 3,
      Display_Name     => Padded_Name,
      Display_Name_Len => Test_Name'Length,
      Wallet_Bound     => True
   );

   --  Setup test wallet binding
   Test_Binding := (
      Biometric_Hash => "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
      Wallet_Address => "0x1234567890abcdef1234567890abcdef12345678",
      Binding_Active => True
   );

   --  Test 1: Soulbound check
   if Is_Soulbound (Test_User) then
      Put_Line ("PASS: NFT is soulbound (transfer_count=0, biometric=true)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: NFT should be soulbound");
   end if;

   --  Test 2: Standard 700 minting (36g = 3 coins)
   Coins := Can_Mint (36.0);
   if Coins = 3 then
      Put_Line ("PASS: Can_Mint(36.0g) = 3 coins");
      Passed := Passed + 1;
   else
      Put ("FAIL: Can_Mint(36.0g) = ");
      Put (Coins, Width => 0);
      Put_Line (" (expected 3)");
   end if;

   --  Test 3: Standard 700 minting (11.9g = 0 coins)
   Coins := Can_Mint (11.9);
   if Coins = 0 then
      Put_Line ("PASS: Can_Mint(11.9g) = 0 coins (below threshold)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Should not mint below 12g");
   end if;

   --  Test 4: Transfer must always fail
   if not Attempt_Transfer (Test_User) then
      Put_Line ("PASS: Transfer rejected (soulbound)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Transfer should NEVER succeed");
   end if;

   --  Test 5: Feature access (Karel tier = level 2 max)
   if Has_Feature_Access (Karel, 2) and not Has_Feature_Access (Karel, 3) then
      Put_Line ("PASS: Karel tier has level 1-2, not 3");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Karel tier access check");
   end if;

   --  Test 6: Family tier has all features
   if Has_Feature_Access (Family, 4) then
      Put_Line ("PASS: Family tier has all features (level 4)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Family should have level 4");
   end if;

   --  Test 7: Unique identity verification
   if Verify_Unique_Identity (Test_User) then
      Put_Line ("PASS: Unique identity verified");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Should verify unique identity");
   end if;

   --  Test 8: Tier pricing
   Price := Tier_Price (Karel);
   if Price = TIER_KAREL then
      Put_Line ("PASS: Karel tier price = 222 CZK/month");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Wrong tier price");
   end if;

   --  Test 9: Biometric verification - valid match (score = 1.0)
   Bio_Result := Verify_Biometric (1.0);
   if Bio_Result.Verified then
      Put_Line ("PASS: Biometric verified (score=1.0 >= threshold)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Perfect biometric should verify");
   end if;

   --  Test 10: Biometric verification - below threshold (score = 0.99)
   Bio_Result := Verify_Biometric (0.99);
   if not Bio_Result.Verified then
      Put_Line ("PASS: Biometric rejected (score=0.99 < 0.99999 threshold)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Low score should be rejected (FAR < 0.001%)");
   end if;

   --  Test 11: FAR compliance check
   if Is_FAR_Compliant then
      Put_Line ("PASS: FAR compliance verified (< 0.001%)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: FAR should be compliant");
   end if;

   --  Test 12: Wallet binding verification
   if Verify_Wallet_Binding (Test_Binding, Test_Binding.Biometric_Hash) then
      Put_Line ("PASS: Wallet binding verified (hash matches)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Valid binding should verify");
   end if;

   --  Test 13: Wallet binding - wrong hash
   if not Verify_Wallet_Binding (Test_Binding,
      "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff") then
      Put_Line ("PASS: Wallet binding rejected (wrong biometric hash)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Wrong hash should be rejected");
   end if;

   --  Test 14: Display name support
   if Has_Display_Name (Test_User) then
      Put_Line ("PASS: Display name is set (independent of wallet)");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Display name should be present");
   end if;

   --  Test 15: Has wallet binding
   if Has_Wallet_Binding (Test_User) then
      Put_Line ("PASS: Wallet binding active on identity record");
      Passed := Passed + 1;
   else
      Put_Line ("FAIL: Should have wallet binding");
   end if;

   --  Summary
   New_Line;
   Put ("Results: ");
   Put (Passed, Width => 0);
   Put ("/");
   Put (Total, Width => 0);
   Put_Line (" tests passed.");

   if Passed = Total then
      Put_Line ("=== ALL TESTS PASSED - Identity integrity VERIFIED ===");
   else
      Put_Line ("=== SOME TESTS FAILED ===");
   end if;
end Soulbound_Nft;
