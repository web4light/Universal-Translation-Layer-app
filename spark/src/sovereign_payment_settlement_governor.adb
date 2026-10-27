--  =============================================================================
--  Sovereign_Payment_Settlement_Governor Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body Sovereign_Payment_Settlement_Governor with
  SPARK_Mode => On
is

   procedure Initialize_Settlement_Governor
     (State : out Settlement_State)
   is
   begin
      State.Active_Tx.Tx_Id             := 1;
      State.Active_Tx.Amount            := 0;
      State.Active_Tx.Status            := Escrow_Idle;
      State.Active_Tx.Is_Collateralized := False;
      State.Active_Tx.Is_Drain_Vetoed   := True;
      State.Total_Settled_Val           := 0;
      State.Total_Settled_Tx            := 0;
      State.Is_Sanitized                := True;
   end Initialize_Settlement_Governor;

   procedure Lock_Escrow
     (State             : in out Settlement_State;
      Tx                : in     Transaction_ID;
      Amount            : in     Currency_Amount;
      Collateral_Backed : in     Boolean;
      Accepted          : out    Boolean)
   is
   begin
      if Collateral_Backed and Amount > 0 and State.Active_Tx.Status /= Escrow_Locked then
         State.Active_Tx.Tx_Id             := Tx;
         State.Active_Tx.Amount            := Amount;
         State.Active_Tx.Status            := Escrow_Locked;
         State.Active_Tx.Is_Collateralized := True;
         State.Active_Tx.Is_Drain_Vetoed   := False;
         State.Is_Sanitized                := False;
         Accepted                          := True;
      else
         Accepted := False;
      end if;
   end Lock_Escrow;

   procedure Settle_Transaction
     (State    : in out Settlement_State;
      Success  : out    Boolean)
   is
   begin
      if State.Active_Tx.Status = Escrow_Locked and then
         State.Active_Tx.Is_Collateralized and then
         State.Total_Settled_Tx < Natural'Last and then
         State.Total_Settled_Val <= Natural'Last - State.Active_Tx.Amount
      then
         State.Active_Tx.Status  := Escrow_Settled;
         State.Total_Settled_Tx  := State.Total_Settled_Tx + 1;
         State.Total_Settled_Val := State.Total_Settled_Val + State.Active_Tx.Amount;
         Success                 := True;
      else
         Success := False;
      end if;
   end Settle_Transaction;

   procedure Purge_Settlement_Session
     (State   : in out Settlement_State;
      Cleaned : out    Boolean)
   is
   begin
      State.Active_Tx.Amount            := 0;
      State.Active_Tx.Status            := Escrow_Idle;
      State.Active_Tx.Is_Collateralized := False;
      State.Active_Tx.Is_Drain_Vetoed   := True;
      State.Is_Sanitized                := True;
      Cleaned                           := True;
   end Purge_Settlement_Session;

end Sovereign_Payment_Settlement_Governor;
