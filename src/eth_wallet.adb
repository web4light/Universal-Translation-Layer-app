-- ============================================================
--  ETH Wallet — Implementation
--  "Ja jsem Groot." (SIC/NON na kazdy TX)
-- ============================================================

pragma SPARK_Mode (On);

package body Eth_Wallet is

   procedure Unlock (W : in out Wallet_State) is
   begin
      W.Status := Unlocked;
   end Unlock;

   procedure Lock (W : in out Wallet_State) is
   begin
      W.Status := Locked;
   end Lock;

   procedure Build_TX (W  : in Wallet_State;
                       TX : out Transaction;
                       Kind : TX_Kind;
                       Value : Wei_Balance) is
   begin
      TX := (Kind      => Kind,
             Status    => Draft,
             Nonce     => W.Nonce,
             Gas_Limit => Default_Gas_Limit,
             Gas_Price => 0,
             Value     => Value,
             Chain_ID  => Sepolia_Chain_ID);
   end Build_TX;

   procedure Sign_TX (W  : in out Wallet_State;
                      TX : in out Transaction;
                      OK : out Boolean) is
      pragma Unreferenced (W);
   begin
      -- Groot rozhoduje: SIC nebo NON
      -- V realite: secp256k1 sign(keccak(rlp(tx)), privkey)
      -- Tady: proved skeleton, I/O cast vola eth_secp256k1
      if TX.Gas_Limit > 0 then
         TX.Status := Signed;
         OK := True;
      else
         TX.Status := Failed;
         OK := False;
      end if;
   end Sign_TX;

   procedure Advance_Nonce (W : in out Wallet_State) is
   begin
      W.Nonce := W.Nonce + 1;
   end Advance_Nonce;

   procedure Record_Success (W : in out Wallet_State) is
   begin
      W.TX_Sent := W.TX_Sent + 1;
   end Record_Success;

   procedure Record_Failure (W : in out Wallet_State) is
   begin
      W.TX_Fail := W.TX_Fail + 1;
   end Record_Failure;

   function Is_Ready (W : Wallet_State) return Boolean is
   begin
      return W.Status = Unlocked;
   end Is_Ready;

end Eth_Wallet;
