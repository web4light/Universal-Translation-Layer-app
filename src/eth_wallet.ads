-- ============================================================
--  ETH Wallet — Ethereum penezenka (Ada/Asterisk)
--
--  Soulbound NFT identita pro Web4.
--  Jeden clovek = jedna penezenka = jeden osobni AI agent.
--  Zadna seed fraze. Klic drzi GNAT v repozitari.
--  Dvojita biometrika = hlasove overeni.
--
--  SPARK proved. GPL-free. Zadna GNU zavislost.
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0 (Rebirth Phoenix Foundation Charter)
-- ============================================================

pragma SPARK_Mode (On);

with Eth_Secp256k1;
with Eth_Keccak;
with Eth_RLP;

package Eth_Wallet is

   -- =========================================================
   --  Typy
   -- =========================================================

   subtype Byte is Natural range 0 .. 255;
   type Byte_Array is array (Positive range <>) of Byte;

   -- 256-bit privatni klic
   Key_Length : constant := 32;
   subtype Private_Key is Byte_Array (1 .. Key_Length);

   -- Ethereum adresa (20 bytu)
   Addr_Length : constant := 20;
   subtype Address is Byte_Array (1 .. Addr_Length);

   -- Balance v Wei (max ~115 ETH pri Natural, staci pro testnet)
   type Wei_Balance is new Natural range 0 .. Natural'Last;

   -- Nonce — monotonni, nikdy se nevrati
   type Nonce_Value is new Natural range 0 .. 999_999_999;

   -- Chain ID (Sepolia = 11155111)
   Sepolia_Chain_ID : constant := 11_155_111;

   -- Gas limit (standardni transfer)
   Default_Gas_Limit : constant := 21_000;
   Contract_Gas_Limit: constant := 100_000;

   -- Data payload konstanty
   Max_Data_Bytes : constant := 128;
   subtype Data_Length is Natural range 0 .. Max_Data_Bytes;
   subtype Data_Buffer is Byte_Array (1 .. Max_Data_Bytes);

   -- Maximalni delka pro raw podepsanou transakci
   Max_Raw_TX_Bytes : constant := 512;
   subtype Raw_TX_Length is Natural range 0 .. Max_Raw_TX_Bytes;
   subtype Raw_TX_Buffer is Byte_Array (1 .. Max_Raw_TX_Bytes);

   -- Prah hlasove biometrie (0..100)
   Biometric_Threshold : constant := 80;

   -- =========================================================
   --  Stav walletu
   -- =========================================================

   type Wallet_Status is (Locked,      -- klic neni nacten
                          Unlocked,    -- pripraveny k pouziti
                          Signing,     -- prave podepisuje TX
                          Error);      -- chyba

   type Wallet_State is record
      Status         : Wallet_Status := Locked;
      Balance        : Wei_Balance   := 0;
      Nonce          : Nonce_Value   := 0;
      TX_Sent        : Natural range 0 .. 999_999 := 0;
      TX_Fail        : Natural range 0 .. 999_999 := 0;
      Wallet_Address : Address       := (others => 0);
      Priv_Key       : Private_Key   := (others => 0);
      Has_Key        : Boolean       := False;
   end record;

   -- =========================================================
   --  Transakce
   -- =========================================================

   -- Typ transakce
   type TX_Kind is (Transfer,        -- poslat ETH
                    Contract_Call,   -- zavolat smart contract
                    Mint_NFT);       -- razit Soulbound NFT

   -- Stav transakce
   type TX_Status is (Draft,         -- pripravena
                      Signed,        -- podepsana
                      Submitted,     -- odeslana
                      Confirmed,     -- potvrzena on-chain
                      Failed);       -- selhala

   -- Jedna transakce
   type Transaction is record
      Kind      : TX_Kind := Transfer;
      Status    : TX_Status := Draft;
      Nonce     : Nonce_Value := 0;
      To_Addr   : Address := (others => 0);
      Gas_Limit : Natural range 0 .. 999_999 := Default_Gas_Limit;
      Gas_Price : Natural range 1 .. 999_999_999 := 1_000_000;  -- Wei (min 1 Gwei)
      Value     : Wei_Balance := 0;
      Chain_ID  : Natural := Sepolia_Chain_ID;
      Data_Len  : Data_Length := 0;
      Data_Buf  : Data_Buffer := (others => 0);
      Sig_R     : Eth_Secp256k1.Scalar_256 := (others => 0);
      Sig_S     : Eth_Secp256k1.Scalar_256 := (others => 0);
      Sig_V     : Byte := 27;
      Raw_Len   : Raw_TX_Length := 0;
      Raw_TX    : Raw_TX_Buffer := (others => 0);
   end record;

   -- =========================================================
   --  Operace
   -- =========================================================

   -- Odemknout wallet (vychozi klic z GNAT trezoru)
   procedure Unlock (W : in out Wallet_State)
     with Pre  => W.Status = Locked,
          Post => W.Status = Unlocked and W.Has_Key;

   -- Odemknout wallet s explicitnim klicem
   procedure Unlock_With_Key
     (W       : in out Wallet_State;
      Key     : in     Private_Key;
      Success :    out Boolean)
     with Pre  => W.Status = Locked,
          Post => (if Success then W.Status = Unlocked and W.Has_Key
                   else W.Status = Locked);

   -- Dvojita biometrika: hlasove overeni pred odemknutim
   procedure Unlock_With_Voice_Biometrics
     (W           : in out Wallet_State;
      Key         : in     Private_Key;
      Voice_Score : in     Natural;
      Success     :    out Boolean)
     with Pre  => W.Status = Locked,
          Post => (if Success then W.Status = Unlocked and W.Has_Key
                   else W.Status = Locked);

   -- Zamknout wallet (hermeticky prepise klic v RAM nulami)
   procedure Lock (W : in out Wallet_State)
     with Post => W.Status = Locked and not W.Has_Key;

   -- Sestavit zakladni transakci
   procedure Build_TX (W     : in  Wallet_State;
                       TX    : out Transaction;
                       Kind  : TX_Kind;
                       Value : Wei_Balance)
     with Pre  => W.Status = Unlocked,
          Post => TX.Status = Draft and TX.Nonce = W.Nonce;

   -- Sestavit transfer ETH na adresu
   procedure Build_Transfer
     (W       : in  Wallet_State;
      To_Addr : in  Address;
      Value   : in  Wei_Balance;
      TX      : out Transaction)
     with Pre  => W.Status = Unlocked,
          Post => TX.Status = Draft and TX.Nonce = W.Nonce and TX.Kind = Transfer;

   -- Sestavit transakci pro Soulbound NFT identitu
   procedure Build_Soulbound_Mint
     (W             : in  Wallet_State;
      Contract_Addr : in  Address;
      Identity_ID   : in  Natural;
      TX            : out Transaction)
     with Pre  => W.Status = Unlocked,
          Post => TX.Status = Draft and TX.Nonce = W.Nonce and TX.Kind = Mint_NFT;

   -- Podepsat transakci (Groot: SIC/NON)
   procedure Sign_TX (W  : in out Wallet_State;
                      TX : in out Transaction;
                      OK : out Boolean)
     with Pre  => W.Status = Unlocked and TX.Status = Draft,
          Post => (if OK then TX.Status = Signed and TX.Raw_Len > 0
                   else TX.Status = Failed);

   -- Inkrementovat nonce po uspesnem odeslani
   procedure Advance_Nonce (W : in out Wallet_State)
     with Pre  => W.Nonce < Nonce_Value'Last,
          Post => W.Nonce = W.Nonce'Old + 1;

   -- Zaznamenat uspesny TX
   procedure Record_Success (W : in out Wallet_State)
     with Pre  => W.TX_Sent < 999_999,
          Post => W.TX_Sent = W.TX_Sent'Old + 1;

   -- Zaznamenat neuspesny TX
   procedure Record_Failure (W : in out Wallet_State)
     with Pre  => W.TX_Fail < 999_999,
          Post => W.TX_Fail = W.TX_Fail'Old + 1;

   -- Ziskat Ethereum adresu penezenky
   function Get_Address (W : Wallet_State) return Address;

   -- Je wallet ready?
   function Is_Ready (W : Wallet_State) return Boolean
     with Post => Is_Ready'Result = (W.Status = Unlocked);

end Eth_Wallet;
