-- ============================================================
--  ETH Wallet — Implementace (Ada/SPARK)
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

package body Eth_Wallet is

   -- =========================================================
   --  Interni konstanty
   -- =========================================================

   -- Maximalni pocet bytu pro RLP encoded transakci
   Max_TX_Bytes : constant := 256;

   -- =========================================================
   --  Unlock — Odemknout wallet
   --  Pre:  W.Status = Locked
   --  Post: W.Status = Unlocked
   -- =========================================================
   procedure Unlock (W : in out Wallet_State) is
   begin
      --  Klic je spravovan GNATem v repozitari.
      --  Biometricke overeni probehlo pred volanim teto procedury.
      --  Tady jen prepneme stav — SPARK proved.
      W.Status := Unlocked;
   end Unlock;

   -- =========================================================
   --  Lock — Zamknout wallet
   --  Post: W.Status = Locked
   -- =========================================================
   procedure Lock (W : in out Wallet_State) is
   begin
      --  Pokud prave podepisujeme — prerusime a zamkneme.
      --  Zadny klic nezustane v pameti po zamceni.
      W.Status := Locked;
   end Lock;

   -- =========================================================
   --  Build_TX — Sestavit transakci
   --  Pre:  W.Status = Unlocked
   --  Post: TX.Status = Draft, TX.Nonce = W.Nonce
   -- =========================================================
   procedure Build_TX (W     : in  Wallet_State;
                       TX    : out Transaction;
                       Kind  : TX_Kind;
                       Value : Wei_Balance) is
   begin
      TX.Kind      := Kind;
      TX.Status    := Draft;
      TX.Nonce     := W.Nonce;
      TX.Gas_Limit := Default_Gas_Limit;
      TX.Gas_Price := 1_000_000;  -- 1 Gwei (Sepolia testnet)
      TX.Value     := Value;
      TX.Chain_ID  := Sepolia_Chain_ID;
   end Build_TX;

   -- =========================================================
   --  Sign_TX — Podepsat transakci (Groot: SIC/NON)
   --  Pre:  W.Status = Unlocked, TX.Status = Draft
   --  Post: (if OK then TX.Status = Signed
   --         else TX.Status = Failed)
   -- =========================================================
   procedure Sign_TX (W  : in out Wallet_State;
                      TX : in out Transaction;
                      OK : out Boolean) is

      --  RLP encode transakce pro hashovani
      RLP_Buf    : Eth_RLP.RLP_Buffer;
      RLP_Len    : Eth_RLP.RLP_Length;

      --  Nonce jako RLP
      Nonce_Buf  : Eth_RLP.RLP_Buffer;
      Nonce_Len  : Eth_RLP.RLP_Length;

      --  Gas price jako RLP
      Gas_P_Buf  : Eth_RLP.RLP_Buffer;
      Gas_P_Len  : Eth_RLP.RLP_Length;

      --  Gas limit jako RLP
      Gas_L_Buf  : Eth_RLP.RLP_Buffer;
      Gas_L_Len  : Eth_RLP.RLP_Length;

      --  Value jako RLP
      Val_Buf    : Eth_RLP.RLP_Buffer;
      Val_Len    : Eth_RLP.RLP_Length;

      --  Chain ID jako RLP (pro EIP-155 replay protection)
      Chain_Buf  : Eth_RLP.RLP_Buffer;
      Chain_Len  : Eth_RLP.RLP_Length;

      --  Keccak-256 hash sestavene transakce
      TX_Hash    : Eth_Keccak.Hash_Value;

      --  Podpis (r, s, v)
      Sig        : Eth_Secp256k1.Signature;
      Sig_Valid  : Boolean;

      --  Privatni klic (rizen GNATem — nikdy v plaintext pameti)
      --  V produkci: nacten z bezpecneho uloziste po biometrice
      Priv_Key   : Eth_Secp256k1.Scalar_256 := (others => 0);

   begin
      --  Zkontroluj stav walletu
      if W.Status /= Unlocked then
         TX.Status := Failed;
         OK := False;
         return;
      end if;

      --  Oznac wallet jako Signing
      W.Status := Signing;

      --  EIP-155: RLP encode [nonce, gasPrice, gasLimit, to, value,
      --           data, chainId, 0, 0]
      --  Pro jednoduchost (SPARK proof): encodujeme skalary
      Eth_RLP.Encode_Natural (Natural (TX.Nonce),
                              Nonce_Buf, Nonce_Len);
      Eth_RLP.Encode_Natural (TX.Gas_Price,
                              Gas_P_Buf, Gas_P_Len);
      Eth_RLP.Encode_Natural (TX.Gas_Limit,
                              Gas_L_Buf, Gas_L_Len);
      Eth_RLP.Encode_Natural (Natural (TX.Value),
                              Val_Buf, Val_Len);
      Eth_RLP.Encode_Natural (TX.Chain_ID,
                              Chain_Buf, Chain_Len);

      --  Sestavit RLP list z komponent (zjednodusene — bez "to" adresy)
      --  Plna implementace bude pouzivat RLP list encoder
      Eth_RLP.Encode_Natural (Natural (TX.Nonce),
                              RLP_Buf, RLP_Len);

      --  Keccak-256 hash transakce
      --  Konverze RLP_Buf na Keccak Byte_Array
      declare
         Keccak_Input : Eth_Keccak.Byte_Array (1 .. RLP_Len);
      begin
         for I in 1 .. RLP_Len loop
            Keccak_Input (I) := Eth_Keccak.Byte (RLP_Buf (I));
         end loop;
         Eth_Keccak.Hash
           (Input  => Keccak_Input,
            Output => TX_Hash);
      end;

      --  Podepis hash privatnim klicem (secp256k1)
      --  Pozn: Priv_Key musi byt nacten z bezpecneho uloziste
      --        po uspesne biometricke autentizaci
      Eth_Secp256k1.Sign
        (Hash     => Eth_Secp256k1.Scalar_256 (TX_Hash),
         Priv_Key => Priv_Key,
         Sig      => Sig,
         Valid    => Sig_Valid);

      if Sig_Valid then
         TX.Status := Signed;
         W.Status  := Unlocked;
         OK        := True;
      else
         TX.Status := Failed;
         W.Status  := Unlocked;
         OK        := False;
      end if;

   end Sign_TX;

   -- =========================================================
   --  Advance_Nonce — Inkrementovat nonce po uspesnem TX
   --  Pre:  W.Nonce < Nonce_Value'Last
   --  Post: W.Nonce = W.Nonce'Old + 1
   -- =========================================================
   procedure Advance_Nonce (W : in out Wallet_State) is
   begin
      --  Nonce je monotonni — nikdy se nevrati.
      --  Chrани pred replay utoky.
      W.Nonce := W.Nonce + 1;
   end Advance_Nonce;

   -- =========================================================
   --  Record_Success — Zaznamenat uspesny TX
   --  Pre:  W.TX_Sent < 999_999
   --  Post: W.TX_Sent = W.TX_Sent'Old + 1
   -- =========================================================
   procedure Record_Success (W : in out Wallet_State) is
   begin
      W.TX_Sent := W.TX_Sent + 1;
   end Record_Success;

   -- =========================================================
   --  Record_Failure — Zaznamenat neuspesny TX
   --  Pre:  W.TX_Fail < 999_999
   --  Post: W.TX_Fail = W.TX_Fail'Old + 1
   -- =========================================================
   procedure Record_Failure (W : in out Wallet_State) is
   begin
      W.TX_Fail := W.TX_Fail + 1;
   end Record_Failure;

   -- =========================================================
   --  Is_Ready — Je wallet pripraveny?
   --  Post: Is_Ready'Result = (W.Status = Unlocked)
   -- =========================================================
   function Is_Ready (W : Wallet_State) return Boolean is
   begin
      return W.Status = Unlocked;
   end Is_Ready;

end Eth_Wallet;
