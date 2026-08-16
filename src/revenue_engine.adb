pragma SPARK_Mode (On);

-- ============================================================
--  Revenue_Engine — Body
--  AI co samo platí. Formálně verifikované finance.
-- ============================================================

package body Revenue_Engine is

   -- ==========================================================
   -- Initialize
   -- ==========================================================

   procedure Initialize (T : out Treasury) is
   begin
      T := (Total_Income    => 0,
            Total_Expenses  => 0,
            Current_Balance => 0,
            Reserve         => 0,
            Available       => 0,
            Reinvested      => 0);
   end Initialize;

   -- ==========================================================
   -- Receive_Payment — zákazník zaplatil
   -- ==========================================================

   procedure Receive_Payment (T      : in out Treasury;
                              Amount : in     Balance) is
   begin
      T.Current_Balance := T.Current_Balance + Amount;
      T.Total_Income    := T.Total_Income + Amount;
      -- Přepočítat rezervu a dostupné
      T.Reserve   := T.Current_Balance / (100 / Reserve_Percent);
      T.Available := T.Current_Balance - T.Reserve;
   end Receive_Payment;

   -- ==========================================================
   -- Get_Available — kolik může utratit (bez rezervy)
   -- ==========================================================

   function Get_Available (T : Treasury) return Balance is
      Res : constant Balance := T.Current_Balance / (100 / Reserve_Percent);
   begin
      if Res >= T.Current_Balance then
         return 0;
      end if;
      return T.Current_Balance - Res;
   end Get_Available;

   -- ==========================================================
   -- Can_Pay — stačí prostředky?
   -- ==========================================================

   function Can_Pay (T : Treasury; Amount : Expense) return Boolean is
   begin
      return Amount <= Get_Available (T);
   end Can_Pay;

   -- ==========================================================
   -- Pay_Expense — zaplatit náklad autonomně
   -- ==========================================================

   procedure Pay_Expense (T      : in out Treasury;
                          Amount : in     Expense;
                          Result : out    Payment_Result) is
   begin
      if Amount > T.Current_Balance then
         Result := Insufficient_Funds;
         return;
      end if;

      if Amount > Get_Available (T) then
         Result := Reserve_Protected;
         return;
      end if;

      -- Zaplatit
      T.Current_Balance := T.Current_Balance - Amount;
      T.Total_Expenses  := T.Total_Expenses + Amount;
      -- Přepočítat
      T.Reserve   := T.Current_Balance / (100 / Reserve_Percent);
      T.Available := T.Current_Balance - T.Reserve;
      Result      := Paid;
   end Pay_Expense;

   -- ==========================================================
   -- Reinvest — reinvestovat z volných prostředků
   -- ==========================================================

   procedure Reinvest (T      : in out Treasury;
                       Amount : in     Expense;
                       Result : out    Payment_Result) is
   begin
      if Amount > Get_Available (T) then
         Result := Reserve_Protected;
         return;
      end if;

      if Amount > T.Current_Balance then
         Result := Insufficient_Funds;
         return;
      end if;

      T.Current_Balance := T.Current_Balance - Amount;
      T.Total_Expenses  := T.Total_Expenses + Amount;
      T.Reinvested      := T.Reinvested + Amount;
      -- Přepočítat
      T.Reserve   := T.Current_Balance / (100 / Reserve_Percent);
      T.Available := T.Current_Balance - T.Reserve;
      Result      := Paid;
   end Reinvest;

   -- ==========================================================
   -- Net_Profit — čistý zisk
   -- ==========================================================

   function Net_Profit (T : Treasury) return Natural is
   begin
      if T.Total_Income >= T.Total_Expenses then
         return T.Total_Income - T.Total_Expenses;
      else
         return 0;
      end if;
   end Net_Profit;

end Revenue_Engine;
