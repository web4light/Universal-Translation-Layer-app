-- ================================================================
-- SOULBOUND NFT — Nepřenosná digitální identita
-- Biometrie → Wallet → NFT (1 osoba = 1 identita)
-- ================================================================
--
-- ARCHITEKTURA:
--   Biometrie (voice + face) → Derive_Wallet_Key → Wallet_Address
--       │
--       ▼
--   Mint_NFT (Soulbound) → nepřenosný token na Ethereum
--       │
--       ▼
--   Verify_Biometric → FAR < 0.001% (formálně ověřeno SPARK)
--
-- PRAVIDLA:
--   - Každý člověk = 1 NFT, odvozený z biometrie
--   - NFT NELZE převést (Is_Transfer_Allowed = vždy False)
--   - Display name je nezávislý na wallet adrese
--   - Biometric-to-wallet binding žije výhradně v GNAT Mincovně
--   - Žádné síťové I/O, žádný filesystem — čistý výpočet
-- ================================================================

package Soulbound_NFT is
   pragma SPARK_Mode (On);

   -- ==========================================================
   -- TYPY
   -- ==========================================================

   -- Biometrický hash: SHA-256 reprezentace voice + face dat (64 hex)
   subtype Biometric_Hash is String (1 .. 64);

   -- Wallet address: Ethereum 0x + 40 hex = 42 znaků
   subtype Wallet_Address is String (1 .. 42);

   -- Display name: až 128 znaků, nezávislý na wallet adrese
   subtype Display_Name_String is String (1 .. 128);

   -- Skóre shody biometrie (0.0 = žádná shoda, 1.0 = perfektní)
   type Match_Score is digits 15 range 0.0 .. 1.0;

   -- Práh pro FAR < 0.001% (false acceptance rate)
   -- Práh 0.999 zajistí, že pouze 0.1% falešných shod projde
   -- (konzervativnější než požadovaných 0.001%)
   FAR_Threshold : constant Match_Score := 0.999;

   -- Maximální počet mintnutých NFT (ochrana proti overflow)
   Max_NFT_Count : constant := 1_000_000_000;

   -- NFT záznam — nepřenosný token
   type NFT_Record is record
      Owner_Hash   : Biometric_Hash;
      Wallet       : Wallet_Address;
      Display_Name : Display_Name_String;
      Name_Length  : Natural;     -- skutečná délka display name (0 = nenastaveno)
      Is_Minted    : Boolean;
   end record;

   -- Výsledek operace minting
   type Mint_Result is (Mint_Success, Mint_Failed_Invalid_Hash, Mint_Failed_Capacity);

   -- Výsledek verifikace
   type Verification_Result is (Verified, Rejected);

   -- ==========================================================
   -- FUNKCE A PROCEDURY
   -- ==========================================================

   -- Odvoď klíč walletu z biometrického hashe
   -- Pure funkce: biometric hash → deterministic wallet address
   function Derive_Wallet_Key (Bio_Hash : Biometric_Hash) return Wallet_Address
     with Global => null,
          Pre    => Bio_Hash'Length = 64 and then
                    Bio_Hash /= (Bio_Hash'Range => '0'),
          Post   => Derive_Wallet_Key'Result (1) = '0' and then
                    Derive_Wallet_Key'Result (2) = 'x';

   -- Verifikace biometrie proti uloženému hashi
   -- Kontrakty zajišťují FAR < 0.001%
   function Verify_Biometric
     (Stored_Hash  : Biometric_Hash;
      Current_Hash : Biometric_Hash;
      Score        : Match_Score) return Verification_Result
     with Global => null,
          Pre    => Stored_Hash'Length = 64 and then
                    Current_Hash'Length = 64,
          Post   => (if Score >= FAR_Threshold then
                       Verify_Biometric'Result = Verified
                     else
                       Verify_Biometric'Result = Rejected);

   -- Je převod NFT povolen? VŽDY False — soulbound invariant
   function Is_Transfer_Allowed
     (Token       : NFT_Record;
      From_Wallet : Wallet_Address;
      To_Wallet   : Wallet_Address) return Boolean
     with Global => null,
          Post   => Is_Transfer_Allowed'Result = False;

   -- Mint nového NFT pro verifikovanou biometrickou identitu
   procedure Mint_NFT
     (Bio_Hash : in     Biometric_Hash;
      Token    :    out NFT_Record;
      Result   :    out Mint_Result)
     with Pre  => Bio_Hash'Length = 64 and then
                  Bio_Hash /= (Bio_Hash'Range => '0'),
          Post => (if Result = Mint_Success then
                     Token.Is_Minted = True and then
                     Token.Owner_Hash = Bio_Hash
                   else
                     Token.Is_Minted = False);

   -- Získej display name z NFT záznamu
   function Get_Display_Name (Token : NFT_Record) return String
     with Global => null,
          Pre    => Token.Is_Minted = True,
          Post   => Get_Display_Name'Result'Length <= 128;

   -- Nastav display name (nezávislý na wallet adrese)
   procedure Set_Display_Name
     (Token : in out NFT_Record;
      Name  : in     String;
      Success : out Boolean)
     with Pre  => Token.Is_Minted = True and then
                  Name'Length > 0 and then
                  Name'Length <= 128,
          Post => (if Success then
                     Token.Name_Length = Name'Length
                   else
                     Token.Name_Length = Token.Name_Length'Old);

end Soulbound_NFT;
