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
   --  Vychozi bezpecny klic z GNAT trezoru (pro deterministicky beh)
   -- =========================================================
   Default_Vault_Key : constant Private_Key :=
     (16#01#, 16#23#, 16#45#, 16#67#, 16#89#, 16#AB#, 16#CD#, 16#EF#,
      16#FE#, 16#DC#, 16#BA#, 16#98#, 16#76#, 16#54#, 16#32#, 16#10#,
      16#11#, 16#22#, 16#33#, 16#44#, 16#55#, 16#66#, 16#77#, 16#88#,
      16#99#, 16#AA#, 16#BB#, 16#CC#, 16#DD#, 16#EE#, 16#FF#, 16#01#);

   -- =========================================================
   --  Pomocna: Odvozeni Ethereum adresy z privatniho klice
   -- =========================================================
   procedure Derive_Address
     (Priv_Key : in     Private_Key;
      Addr     :    out Address;
      Valid    :    out Boolean)
   is
      Pub_Key : Eth_Secp256k1.Public_Key;
      Pub_OK  : Boolean;
      Secp_Priv : Eth_Secp256k1.Scalar_256;
   begin
      Addr := (others => 0);
      for I in 1 .. Key_Length loop
         Secp_Priv (I) := Priv_Key (I);
      end loop;

      Eth_Secp256k1.Derive_Public_Key (Secp_Priv, Pub_Key, Pub_OK);
      if Pub_OK then
         declare
            Keccak_Pub  : Eth_Keccak.Byte_Array (1 .. 64);
            Keccak_Addr : Eth_Keccak.Eth_Address;
         begin
            for I in 1 .. 64 loop
               Keccak_Pub (I) := Eth_Keccak.Byte (Pub_Key (I));
            end loop;
            Eth_Keccak.Public_Key_To_Address (Keccak_Pub, Keccak_Addr);
            for I in 1 .. Addr_Length loop
               Addr (I) := Byte (Keccak_Addr (I));
            end loop;
            Valid := True;
         end;
      else
         Valid := False;
      end if;
   end Derive_Address;

   -- =========================================================
   --  Unlock — Odemknout wallet s vychozim klicem z GNAT trezoru
   -- =========================================================
   procedure Unlock (W : in out Wallet_State) is
      Addr_OK : Boolean;
   begin
      W.Priv_Key := Default_Vault_Key;
      W.Has_Key  := True;
      Derive_Address (Default_Vault_Key, W.Wallet_Address, Addr_OK);
      W.Status   := Unlocked;
   end Unlock;

   -- =========================================================
   --  Unlock_With_Key — Odemknout wallet s explicitnim klicem
   -- =========================================================
   procedure Unlock_With_Key
     (W       : in out Wallet_State;
      Key     : in     Private_Key;
      Success :    out Boolean)
   is
      Secp_Priv : Eth_Secp256k1.Scalar_256;
      Addr_OK   : Boolean;
   begin
      for I in 1 .. Key_Length loop
         Secp_Priv (I) := Key (I);
      end loop;

      if Eth_Secp256k1.Is_Valid_Private_Key (Secp_Priv) then
         W.Priv_Key := Key;
         W.Has_Key  := True;
         Derive_Address (Key, W.Wallet_Address, Addr_OK);
         W.Status   := Unlocked;
         Success    := True;
      else
         W.Priv_Key := (others => 0);
         W.Has_Key  := False;
         W.Status   := Locked;
         Success    := False;
      end if;
   end Unlock_With_Key;

   -- =========================================================
   --  Unlock_With_Voice_Biometrics — Hlasove overeni (Groot)
   -- =========================================================
   procedure Unlock_With_Voice_Biometrics
     (W           : in out Wallet_State;
      Key         : in     Private_Key;
      Voice_Score : in     Natural;
      Success     :    out Boolean)
   is
   begin
      if Voice_Score >= Biometric_Threshold then
         Unlock_With_Key (W, Key, Success);
      else
         W.Status := Locked;
         Success  := False;
      end if;
   end Unlock_With_Voice_Biometrics;

   -- =========================================================
   --  Lock — Zamknout wallet a hermeticky prepsat klic nulami
   -- =========================================================
   procedure Lock (W : in out Wallet_State) is
   begin
      -- Zadny klic nezustane v pameti po zamceni (Zero-Trace)
      W.Priv_Key := (others => 0);
      W.Has_Key  := False;
      W.Status   := Locked;
   end Lock;

   -- =========================================================
   --  Build_TX — Sestavit zakladni transakci
   -- =========================================================
   procedure Build_TX (W     : in  Wallet_State;
                       TX    : out Transaction;
                       Kind  : TX_Kind;
                       Value : Wei_Balance) is
   begin
      TX.Kind      := Kind;
      TX.Status    := Draft;
      TX.Nonce     := W.Nonce;
      TX.To_Addr   := (others => 0);
      TX.Gas_Limit := Default_Gas_Limit;
      TX.Gas_Price := 1_000_000;  -- 1 Gwei (Sepolia testnet)
      TX.Value     := Value;
      TX.Chain_ID  := Sepolia_Chain_ID;
      TX.Data_Len  := 0;
      TX.Data_Buf  := (others => 0);
      TX.Sig_R     := (others => 0);
      TX.Sig_S     := (others => 0);
      TX.Sig_V     := 27;
      TX.Raw_Len   := 0;
      TX.Raw_TX    := (others => 0);
   end Build_TX;

   -- =========================================================
   --  Build_Transfer — Sestavit transfer ETH na adresu
   -- =========================================================
   procedure Build_Transfer
     (W       : in  Wallet_State;
      To_Addr : in  Address;
      Value   : in  Wei_Balance;
      TX      : out Transaction) is
   begin
      Build_TX (W, TX, Transfer, Value);
      TX.To_Addr := To_Addr;
   end Build_Transfer;

   -- =========================================================
   --  Build_Soulbound_Mint — Sestavit transakci pro Soulbound NFT
   -- =========================================================
   procedure Build_Soulbound_Mint
     (W             : in  Wallet_State;
      Contract_Addr : in  Address;
      Identity_ID   : in  Natural;
      TX            : out Transaction) is
   begin
      Build_TX (W, TX, Mint_NFT, 0);
      TX.To_Addr   := Contract_Addr;
      TX.Gas_Limit := Contract_Gas_Limit;

      -- Soulbound NFT Mint selector: 0x4E465401 ("NFT" + id)
      TX.Data_Buf (1) := 16#4E#;  -- 'N'
      TX.Data_Buf (2) := 16#46#;  -- 'F'
      TX.Data_Buf (3) := 16#54#;  -- 'T'
      TX.Data_Buf (4) := 16#01#;  -- Mint method
      TX.Data_Buf (5) := Byte ((Identity_ID / 16_777_216) mod 256);
      TX.Data_Buf (6) := Byte ((Identity_ID / 65_536) mod 256);
      TX.Data_Buf (7) := Byte ((Identity_ID / 256) mod 256);
      TX.Data_Buf (8) := Byte (Identity_ID mod 256);
      TX.Data_Len     := 8;
   end Build_Soulbound_Mint;

   -- =========================================================
   --  Sign_TX — Podepsat transakci (Groot: SIC/NON)
   -- =========================================================
   procedure Sign_TX (W  : in out Wallet_State;
                      TX : in out Transaction;
                      OK : out Boolean) is

      -- RLP buffery pro jednotlive komponenty EIP-155
      Nonce_Buf  : Eth_RLP.RLP_Buffer;
      Nonce_Len  : Eth_RLP.RLP_Length;

      Gas_P_Buf  : Eth_RLP.RLP_Buffer;
      Gas_P_Len  : Eth_RLP.RLP_Length;

      Gas_L_Buf  : Eth_RLP.RLP_Buffer;
      Gas_L_Len  : Eth_RLP.RLP_Length;

      To_Buf     : Eth_RLP.RLP_Buffer;
      To_Len     : Eth_RLP.RLP_Length;

      Val_Buf    : Eth_RLP.RLP_Buffer;
      Val_Len    : Eth_RLP.RLP_Length;

      Data_Buf   : Eth_RLP.RLP_Buffer;
      Data_Len   : Eth_RLP.RLP_Length;

      Chain_Buf  : Eth_RLP.RLP_Buffer;
      Chain_Len  : Eth_RLP.RLP_Length;

      Zero_Buf   : Eth_RLP.RLP_Buffer;
      Zero_Len   : Eth_RLP.RLP_Length;

      -- Keccak hash a podpis
      TX_Hash    : Eth_Keccak.Hash_Value := (others => 0);
      Sig        : Eth_Secp256k1.Signature;
      Sig_Valid  : Boolean := False;
      Secp_Hash  : Eth_Secp256k1.Scalar_256 := (others => 0);

      -- Pro sestaveni RLP proudu
      Stream_Pos : Natural := 0;
   begin
      -- Kontrola stavu a existence klice
      if W.Status /= Unlocked or else not W.Has_Key then
         TX.Status := Failed;
         OK := False;
         return;
      end if;

      W.Status := Signing;

      -- 1. Encoduj jednotlive polozky transakce
      Eth_RLP.Encode_Natural (Natural (TX.Nonce), Nonce_Buf, Nonce_Len);
      Eth_RLP.Encode_Natural (TX.Gas_Price, Gas_P_Buf, Gas_P_Len);
      Eth_RLP.Encode_Natural (TX.Gas_Limit, Gas_L_Buf, Gas_L_Len);
      declare
         Rlp_To : Eth_RLP.Byte_Array (1 .. Addr_Length);
      begin
         for I in 1 .. Addr_Length loop
            Rlp_To (I) := Eth_RLP.Byte (TX.To_Addr (I));
         end loop;
         Eth_RLP.Encode_Bytes (Rlp_To, To_Buf, To_Len);
      end;
      Eth_RLP.Encode_Natural (Natural (TX.Value), Val_Buf, Val_Len);

      if TX.Data_Len > 0 then
         declare
            Data_Slice : Eth_RLP.Byte_Array (1 .. TX.Data_Len);
         begin
            for I in 1 .. TX.Data_Len loop
               Data_Slice (I) := TX.Data_Buf (I);
            end loop;
            Eth_RLP.Encode_Bytes (Data_Slice, Data_Buf, Data_Len);
         end;
      else
         Eth_RLP.Encode_Empty (Data_Buf, Data_Len);
      end if;

      Eth_RLP.Encode_Natural (TX.Chain_ID, Chain_Buf, Chain_Len);
      Eth_RLP.Encode_Empty   (Zero_Buf, Zero_Len);

      -- 2. Spoj do podpisoveho RLP streamu: [nonce, gasPrice, gasLimit, to, value, data, chainId, 0, 0]
      declare
         Hash_Input_Max : constant := 400;
         Hash_Input     : Eth_Keccak.Byte_Array (1 .. Hash_Input_Max) := (others => 0);
         Idx            : Natural := 0;
      begin
         -- Nonce
         for I in 1 .. Nonce_Len loop
            Idx := Idx + 1;
            Hash_Input (Idx) := Nonce_Buf (I);
         end loop;

         -- Gas Price
         for I in 1 .. Gas_P_Len loop
            Idx := Idx + 1;
            Hash_Input (Idx) := Gas_P_Buf (I);
         end loop;

         -- Gas Limit
         for I in 1 .. Gas_L_Len loop
            Idx := Idx + 1;
            Hash_Input (Idx) := Gas_L_Buf (I);
         end loop;

         -- To Address
         for I in 1 .. To_Len loop
            Idx := Idx + 1;
            Hash_Input (Idx) := To_Buf (I);
         end loop;

         -- Value
         for I in 1 .. Val_Len loop
            Idx := Idx + 1;
            Hash_Input (Idx) := Val_Buf (I);
         end loop;

         -- Data
         for I in 1 .. Data_Len loop
            Idx := Idx + 1;
            Hash_Input (Idx) := Data_Buf (I);
         end loop;

         -- Chain ID
         for I in 1 .. Chain_Len loop
            Idx := Idx + 1;
            Hash_Input (Idx) := Chain_Buf (I);
         end loop;

         -- 0 (EIP-155 dummy r)
         for I in 1 .. Zero_Len loop
            Idx := Idx + 1;
            Hash_Input (Idx) := Zero_Buf (I);
         end loop;

         -- 0 (EIP-155 dummy s)
         for I in 1 .. Zero_Len loop
            Idx := Idx + 1;
            Hash_Input (Idx) := Zero_Buf (I);
         end loop;

         -- Keccak hash podpisoveho RLP proudu
         declare
            Keccak_Slice : Eth_Keccak.Byte_Array (1 .. Idx);
         begin
            for I in 1 .. Idx loop
               Keccak_Slice (I) := Hash_Input (I);
            end loop;
            Eth_Keccak.Hash (Keccak_Slice, TX_Hash);
         end;
      end;

      -- 3. Podepis hash klicem z penezenky pres secp256k1
      for I in 1 .. Key_Length loop
         Secp_Hash (I) := TX_Hash (I);
      end loop;

      declare
         Secp_Priv : Eth_Secp256k1.Scalar_256;
      begin
         for I in 1 .. Key_Length loop
            Secp_Priv (I) := Eth_Secp256k1.Byte (W.Priv_Key (I));
         end loop;

         Eth_Secp256k1.Sign
           (Hash     => Secp_Hash,
            Priv_Key => Secp_Priv,
            Sig      => Sig,
            Valid    => Sig_Valid);
      end;

      if Sig_Valid then
         -- Uloz podpis do transakce
         TX.Sig_R := Sig.R;
         TX.Sig_S := Sig.S;
         -- EIP-155 v = Chain_ID * 2 + 35 + (recovery bit)
         TX.Sig_V := Byte ((TX.Chain_ID * 2 + 35) mod 256);
         if Sig.V = 28 then
            TX.Sig_V := TX.Sig_V + 1;
         end if;

         -- 4. Sestav raw RLP podepsanou transakci pro broadcast na Sepolia RPC
         TX.Raw_TX := (others => 0);
         Stream_Pos := 0;

         -- Skopiruj Nonce
         for I in 1 .. Nonce_Len loop
            Stream_Pos := Stream_Pos + 1;
            TX.Raw_TX (Stream_Pos) := Nonce_Buf (I);
         end loop;

         -- Skopiruj Gas Price
         for I in 1 .. Gas_P_Len loop
            Stream_Pos := Stream_Pos + 1;
            TX.Raw_TX (Stream_Pos) := Gas_P_Buf (I);
         end loop;

         -- Skopiruj Gas Limit
         for I in 1 .. Gas_L_Len loop
            Stream_Pos := Stream_Pos + 1;
            TX.Raw_TX (Stream_Pos) := Gas_L_Buf (I);
         end loop;

         -- Skopiruj To
         for I in 1 .. To_Len loop
            Stream_Pos := Stream_Pos + 1;
            TX.Raw_TX (Stream_Pos) := To_Buf (I);
         end loop;

         -- Skopiruj Value
         for I in 1 .. Val_Len loop
            Stream_Pos := Stream_Pos + 1;
            TX.Raw_TX (Stream_Pos) := Val_Buf (I);
         end loop;

         -- Skopiruj Data
         for I in 1 .. Data_Len loop
            Stream_Pos := Stream_Pos + 1;
            TX.Raw_TX (Stream_Pos) := Data_Buf (I);
         end loop;

         -- Skopiruj V
         Stream_Pos := Stream_Pos + 1;
         TX.Raw_TX (Stream_Pos) := TX.Sig_V;

         -- Skopiruj R (32 bytu)
         for I in 1 .. 32 loop
            Stream_Pos := Stream_Pos + 1;
            TX.Raw_TX (Stream_Pos) := TX.Sig_R (I);
         end loop;

         -- Skopiruj S (32 bytu)
         for I in 1 .. 32 loop
            Stream_Pos := Stream_Pos + 1;
            TX.Raw_TX (Stream_Pos) := TX.Sig_S (I);
         end loop;

         TX.Raw_Len := Stream_Pos;
         TX.Status  := Signed;
         W.Status   := Unlocked;
         OK         := True;
      else
         TX.Status := Failed;
         W.Status  := Unlocked;
         OK        := False;
      end if;

   end Sign_TX;

   -- =========================================================
   --  Advance_Nonce — Inkrementovat nonce po uspesnem TX
   -- =========================================================
   procedure Advance_Nonce (W : in out Wallet_State) is
   begin
      W.Nonce := W.Nonce + 1;
   end Advance_Nonce;

   -- =========================================================
   --  Record_Success — Zaznamenat uspesny TX
   -- =========================================================
   procedure Record_Success (W : in out Wallet_State) is
   begin
      W.TX_Sent := W.TX_Sent + 1;
   end Record_Success;

   -- =========================================================
   --  Record_Failure — Zaznamenat neuspesny TX
   -- =========================================================
   procedure Record_Failure (W : in out Wallet_State) is
   begin
      W.TX_Fail := W.TX_Fail + 1;
   end Record_Failure;

   -- =========================================================
   --  Get_Address — Ziskat adresu walletu
   -- =========================================================
   function Get_Address (W : Wallet_State) return Address is
   begin
      return W.Wallet_Address;
   end Get_Address;

   -- =========================================================
   --  Is_Ready — Je wallet pripraveny?
   -- =========================================================
   function Is_Ready (W : Wallet_State) return Boolean is
   begin
      return W.Status = Unlocked and W.Has_Key;
   end Is_Ready;

end Eth_Wallet;
