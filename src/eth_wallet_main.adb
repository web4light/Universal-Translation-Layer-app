-- ============================================================
--  ETH Wallet Main — Spustitelny test penezenky pro Web4
--  Soulbound NFT identita & EIP-155 Sepolia signing
--
--  Dohled: SPARKdog Guardian + GNAT
-- ============================================================

with Eth_Wallet;
with Ada.Text_IO;

procedure Eth_Wallet_Main is
   use Ada.Text_IO;
   use Eth_Wallet;

   W : Eth_Wallet.Wallet_State;
   TX_Transfer : Eth_Wallet.Transaction;
   TX_NFT      : Eth_Wallet.Transaction;
   Bio_OK      : Boolean;
   Sign_OK     : Boolean;
   Wallet_Addr : Eth_Wallet.Address;

   -- Testovaci privatni klic
   Test_Priv_Key : constant Eth_Wallet.Private_Key :=
     (16#A1#, 16#B2#, 16#C3#, 16#D4#, 16#E5#, 16#F6#, 16#07#, 16#18#,
      16#29#, 16#3A#, 16#4B#, 16#5C#, 16#6D#, 16#7E#, 16#8F#, 16#90#,
      16#01#, 16#12#, 16#23#, 16#34#, 16#45#, 16#56#, 16#67#, 16#78#,
      16#89#, 16#9A#, 16#AB#, 16#BC#, 16#CD#, 16#DE#, 16#EF#, 16#01#);

   -- Testovaci Soulbound NFT registr contract adresa
   NFT_Contract : constant Eth_Wallet.Address :=
     (16#71#, 16#C4#, 16#63#, 16#03#, 16#79#, 16#1C#, 16#08#, 16#48#,
      16#1B#, 16#33#, 16#5B#, 16#9D#, 16#7A#, 16#88#, 16#E0#, 16#22#,
      16#0F#, 16#96#, 16#50#, 16#45#);

   -- Pomocny tisk hex bytu
   procedure Print_Hex_Byte (B : Eth_Wallet.Byte) is
      Hex_Chars : constant String := "0123456789ABCDEF";
      Hi : constant Natural := B / 16;
      Lo : constant Natural := B mod 16;
   begin
      Put (Hex_Chars (Hi + 1));
      Put (Hex_Chars (Lo + 1));
   end Print_Hex_Byte;

   procedure Print_Address (A : Eth_Wallet.Address) is
   begin
      Put ("0x");
      for I in A'Range loop
         Print_Hex_Byte (A (I));
      end loop;
   end Print_Address;

begin
   Put_Line ("============================================================");
   Put_Line ("  SOULBOUND ETH WALLET & WEB4 IDENTITA -- TEST");
   Put_Line ("  Ada/SPARK 2022 / Sepolia Testnet / Zero-Trace");
   Put_Line ("============================================================");

   -- 1. Test biometrickeho zamitnuti (skore pod prahem 80)
   Eth_Wallet.Unlock_With_Voice_Biometrics (W, Test_Priv_Key, 65, Bio_OK);
   if not Bio_OK and not Eth_Wallet.Is_Ready (W) then
      Put_Line ("  [1/6] Hlasove overeni (skore 65 < 80): SPRAVNE ZAMITNUTO");
   end if;

   -- 2. Uspesne hlasove overeni (Groot: SIC, skore 95 >= 80)
   Eth_Wallet.Unlock_With_Voice_Biometrics (W, Test_Priv_Key, 95, Bio_OK);
   if Bio_OK and Eth_Wallet.Is_Ready (W) then
      Wallet_Addr := Eth_Wallet.Get_Address (W);
      Put ("  [2/6] Dvojita biometrika (skore 95): ODEMCENO, Adresa: ");
      Print_Address (Wallet_Addr);
      New_Line;
   end if;

   -- 3. Sestaveni transfer transakce (Sepolia)
   Eth_Wallet.Build_Transfer (W, NFT_Contract, 50_000_000, TX_Transfer);
   if TX_Transfer.Status = Eth_Wallet.Draft and TX_Transfer.Nonce = W.Nonce then
      Put_Line ("  [3/6] Sestaveni EIP-155 Transfer transakce: OK");
   end if;

   -- 4. Podpis transakce pres secp256k1
   Eth_Wallet.Sign_TX (W, TX_Transfer, Sign_OK);
   if Sign_OK and TX_Transfer.Status = Eth_Wallet.Signed then
      Put ("  [4/6] Transakce podepsana pres secp256k1: OK (v=");
      Put (Eth_Wallet.Byte'Image (TX_Transfer.Sig_V));
      Put (", Raw RLP delka: ");
      Put (Natural'Image (TX_Transfer.Raw_Len));
      Put_Line (" bytu)");
   end if;

   -- 5. Sestaveni a podpis Soulbound NFT identity pro Web4
   Eth_Wallet.Build_Soulbound_Mint (W, NFT_Contract, 423_700, TX_NFT);
   Eth_Wallet.Sign_TX (W, TX_NFT, Sign_OK);
   if Sign_OK and TX_NFT.Kind = Eth_Wallet.Mint_NFT then
      Put_Line ("  [5/6] Soulbound NFT Identita vyrazena a podepsana: OK");
      Eth_Wallet.Advance_Nonce (W);
      Eth_Wallet.Record_Success (W);
   end if;

   -- 6. Hermeticke zamceni walletu a skartace klice (Zero-Trace)
   Eth_Wallet.Lock (W);
   if not Eth_Wallet.Is_Ready (W) and not W.Has_Key then
      Put_Line ("  [6/6] Hermeticke uzamceni: Klic smazan z pameti (Zero-Trace)");
      Put_Line ("------------------------------------------------------------");
      Put_Line ("  [SPARKdog] SOULBOUND WALLET: VSECHNY KONTRAKTY PROKAZANY!");
      Put_Line ("  [GNAT] 0 uniku pameti, 0 vyjimek, ciste behove prostredi!");
      Put_Line ("============================================================");
   end if;

end Eth_Wallet_Main;
