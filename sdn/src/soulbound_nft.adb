-- ================================================================
-- SOULBOUND NFT — Implementace
-- Ada/SPARK 2024 — Formálně ověřitelný kód
-- Biometrická identita, nepřenosné NFT, display name
--
-- Komunikace s Python: stdout JSON (subprocess CLI)
-- ================================================================

with Ada.Text_IO; use Ada.Text_IO;

package body Soulbound_NFT is
   pragma SPARK_Mode (On);

   -- ==========================================================
   -- INTERNÍ STAV
   -- ==========================================================

   -- Počet mintnutých NFT (globální counter)
   Total_Minted : Natural := 0;

   -- ==========================================================
   -- INTERNÍ POMOCNÉ FUNKCE
   -- ==========================================================

   -- Validuje, že řetězec obsahuje pouze hex znaky
   function Is_Valid_Hex (S : String) return Boolean
     with Global => null
   is
   begin
      for I in S'Range loop
         case S (I) is
            when '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' =>
               null;
            when others =>
               return False;
         end case;
      end loop;
      return True;
   end Is_Valid_Hex;

   -- Jednoduchá XOR-based derivace (simulace KDF pro čistý výpočet)
   -- V produkci by šlo o HKDF-SHA256, ale tady jsme SPARK-pure
   function Hex_Char_To_Nibble (C : Character) return Natural
     with Global => null,
          Pre    => C in '0' .. '9' | 'a' .. 'f' | 'A' .. 'F',
          Post   => Hex_Char_To_Nibble'Result <= 15
   is
   begin
      case C is
         when '0' => return 0;
         when '1' => return 1;
         when '2' => return 2;
         when '3' => return 3;
         when '4' => return 4;
         when '5' => return 5;
         when '6' => return 6;
         when '7' => return 7;
         when '8' => return 8;
         when '9' => return 9;
         when 'a' | 'A' => return 10;
         when 'b' | 'B' => return 11;
         when 'c' | 'C' => return 12;
         when 'd' | 'D' => return 13;
         when 'e' | 'E' => return 14;
         when 'f' | 'F' => return 15;
         when others => return 0;  -- nikdy nenastane díky Pre
      end case;
   end Hex_Char_To_Nibble;

   function Nibble_To_Hex_Char (N : Natural) return Character
     with Global => null,
          Pre    => N <= 15
   is
      Hex_Chars : constant String := "0123456789abcdef";
   begin
      return Hex_Chars (Hex_Chars'First + N);
   end Nibble_To_Hex_Char;

   -- ==========================================================
   -- VEŘEJNÉ FUNKCE
   -- ==========================================================

   function Derive_Wallet_Key (Bio_Hash : Biometric_Hash) return Wallet_Address is
      Result : Wallet_Address := (others => '0');
      -- Derivace: XOR sousedních nibblů + salt rotace
      -- Produkuje deterministickou 40-hex adresu z 64-hex vstupu
      Nibble_A : Natural;
      Nibble_B : Natural;
      Derived  : Natural;
   begin
      -- Prefix "0x" pro Ethereum adresu
      Result (1) := '0';
      Result (2) := 'x';

      -- Derivace 40 hex znaků z 64 vstupních
      for I in 1 .. 40 loop
         -- XOR dvou nibblů ze vstupu pro jeden výstupní nibble
         if Is_Valid_Hex (Bio_Hash (I .. I)) and then
            Is_Valid_Hex (Bio_Hash (I + 24 .. I + 24))
         then
            Nibble_A := Hex_Char_To_Nibble (Bio_Hash (I));
            Nibble_B := Hex_Char_To_Nibble (Bio_Hash (I + 24));
            -- XOR + rotace pro lepší distribuci
            Derived := (Nibble_A + Nibble_B + I) mod 16;
            Result (I + 2) := Nibble_To_Hex_Char (Derived);
         else
            -- Fallback pro nevalidní hex (nemělo by nastat díky Pre)
            Result (I + 2) := '0';
         end if;
      end loop;

      return Result;
   end Derive_Wallet_Key;

   function Verify_Biometric
     (Stored_Hash  : Biometric_Hash;
      Current_Hash : Biometric_Hash;
      Score        : Match_Score) return Verification_Result
   is
   begin
      -- Hlavní rozhodovací logika:
      -- Score >= FAR_Threshold (0.999) → Verified
      -- Score < FAR_Threshold → Rejected
      -- Toto zajišťuje FAR < 0.001% (false acceptance rate)
      --
      -- Kontrakt Post garantuje konsistenci s touto logikou
      if Score >= FAR_Threshold then
         return Verified;
      else
         return Rejected;
      end if;
   end Verify_Biometric;

   function Is_Transfer_Allowed
     (Token       : NFT_Record;
      From_Wallet : Wallet_Address;
      To_Wallet   : Wallet_Address) return Boolean
   is
      pragma Unreferenced (Token);
      pragma Unreferenced (From_Wallet);
      pragma Unreferenced (To_Wallet);
   begin
      -- SOULBOUND INVARIANT: Převod NIKDY není povolen.
      -- Bez ohledu na odesílatele, příjemce nebo metodu.
      -- Post kontrakt formálně garantuje: Result = False
      return False;
   end Is_Transfer_Allowed;

   procedure Mint_NFT
     (Bio_Hash : in     Biometric_Hash;
      Token    :    out NFT_Record;
      Result   :    out Mint_Result)
   is
   begin
      -- Inicializace výstupního tokenu
      Token := NFT_Record'(
         Owner_Hash   => (others => '0'),
         Wallet       => (others => '0'),
         Display_Name => (others => ' '),
         Name_Length  => 0,
         Is_Minted    => False
      );

      -- Validace: hash nesmí být samé nuly (Pre kontrakt to zajistí,
      -- ale pro SPARK explicitní kontrola)
      if Bio_Hash = (Bio_Hash'Range => '0') then
         Result := Mint_Failed_Invalid_Hash;
         return;
      end if;

      -- Validace: hex znaky
      if not Is_Valid_Hex (Bio_Hash) then
         Result := Mint_Failed_Invalid_Hash;
         return;
      end if;

      -- Kapacitní kontrola
      if Total_Minted >= Max_NFT_Count then
         Result := Mint_Failed_Capacity;
         return;
      end if;

      -- Mint NFT — odvodit wallet, vytvořit token
      Token.Owner_Hash := Bio_Hash;
      Token.Wallet     := Derive_Wallet_Key (Bio_Hash);
      Token.Is_Minted  := True;
      Token.Name_Length := 0;  -- display name zatím nenastaveno

      -- Inkrementovat globální counter
      Total_Minted := Total_Minted + 1;

      -- Logování na stdout (Python bridge čte JSON)
      Put_Line ("{""event"":""nft_minted"","
                & """owner_hash"":""" & Bio_Hash & ""","
                & """wallet"":""" & Token.Wallet & ""","
                & """total_minted"":" & Natural'Image (Total_Minted) & "}");

      Result := Mint_Success;
   end Mint_NFT;

   function Get_Display_Name (Token : NFT_Record) return String is
   begin
      if Token.Name_Length = 0 then
         return "";
      else
         return Token.Display_Name (1 .. Token.Name_Length);
      end if;
   end Get_Display_Name;

   procedure Set_Display_Name
     (Token   : in out NFT_Record;
      Name    : in     String;
      Success :    out Boolean)
   is
   begin
      -- Kontrakt Pre zajistí: Is_Minted, 0 < Length <= 128
      -- Display name je nezávislý na wallet adrese
      if Name'Length > 0 and Name'Length <= 128 then
         Token.Display_Name (1 .. Name'Length) := Name;
         Token.Name_Length := Name'Length;
         Success := True;

         -- Logování změny
         Put_Line ("{""event"":""display_name_set"","
                   & """wallet"":""" & Token.Wallet & ""","
                   & """name"":""" & Name & """}");
      else
         Success := False;
      end if;
   end Set_Display_Name;

end Soulbound_NFT;
