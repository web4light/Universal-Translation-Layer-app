-- ============================================================
--  ETH Wallet — Ethereum penezhenka (Ada/Asterisk)
--
--  Vlastni wallet pro Sepolia testnet.
--  Zadny MetaMask, zadny Go, zadna GNU.
--
--  Schopnosti:
--    - Sprava privatnich klicu (bounded, proved)
--    - Sestaveni transakce (RLP encoding)
--    - Podpis (secp256k1)
--    - Balance tracking (proved overflow safe)
--    - Nonce management (monotonni, nikdy se nevrati)
--
--  Groot resi: "Ja jsem Groot." (SIC/NON na kazdy TX)
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0 (Rebirth Phoenix Foundation Charter)
-- ============================================================

pragma SPARK_Mode (On);

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

   -- =========================================================
   --  Stav walletu
   -- =========================================================

   type Wallet_Status is (Locked,      -- klic neni nacten
                          Unlocked,    -- pripraveny k pouziti
                          Signing,     -- prave podepisuje TX
                          Error);      -- chyba

   type Wallet_State is record
      Status  : Wallet_Status := Locked;
      Balance : Wei_Balance := 0;
      Nonce   : Nonce_Value := 0;
      TX_Sent : Natural range 0 .. 999_999 := 0;
      TX_Fail : Natural range 0 .. 999_999 := 0;
   end record;

   -- =========================================================
   --  Transakce
   -- =========================================================

   -- Typ transakce
   type TX_Kind is (Transfer,        -- poslat ETH
                    Contract_Call,    -- zavolat smart contract
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
      Gas_Limit : Natural range 0 .. 999_999 := Default_Gas_Limit;
      Gas_Price : Natural range 0 .. 999_999_999 := 0;  -- Wei
      Value     : Wei_Balance := 0;
      Chain_ID  : Natural := Sepolia_Chain_ID;
   end record;

   -- =========================================================
   --  Operace
   -- =========================================================

   -- Odemknout wallet (nacist klic)
   procedure Unlock (W : in out Wallet_State)
     with Pre  => W.Status = Locked,
          Post => W.Status = Unlocked;

   -- Zamknout wallet
   procedure Lock (W : in out Wallet_State)
     with Post => W.Status = Locked;

   -- Sestavit transakci
   procedure Build_TX (W  : in Wallet_State;
                       TX : out Transaction;
                       Kind : TX_Kind;
                       Value : Wei_Balance)
     with Pre  => W.Status = Unlocked,
          Post => TX.Status = Draft and TX.Nonce = W.Nonce;

   -- Podepsat transakci (Groot: SIC/NON)
   procedure Sign_TX (W  : in out Wallet_State;
                      TX : in out Transaction;
                      OK : out Boolean)
     with Pre  => W.Status = Unlocked and TX.Status = Draft,
          Post => (if OK then TX.Status = Signed
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

   -- Je wallet ready?
   function Is_Ready (W : Wallet_State) return Boolean
     with Post => Is_Ready'Result = (W.Status = Unlocked);

end Eth_Wallet;
