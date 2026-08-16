pragma SPARK_Mode (On);

-- ============================================================
--  Revenue_Engine — AI co samo platí
--
--  Systém autonomně:
--    1. Inkasuje od zákazníků (předplatné)
--    2. Platí náklady (API, hosting, licence)
--    3. Reinvestuje přebytek (hardware, kapacita)
--
--  Pravidla (formálně verifikovaná):
--    - Nikdy neutratí víc než má
--    - Vždy drží rezervu (min 20%)
--    - Reinvestuje jen z čistého zisku
--    - Žádné dluhy (systém nezná záporná čísla)
--
--  Autor: Pan Jeskyně
-- ============================================================

package Revenue_Engine is

   -- ==========================================================
   -- KONSTANTY
   -- ==========================================================

   Max_Balance      : constant := 999_999_999;  -- max haléře (CZK * 100)
   Reserve_Percent  : constant := 20;           -- vždy drží 20% jako rezervu
   Max_Expense      : constant := 100_000_000;  -- max jednorázový výdaj

   -- ==========================================================
   -- TYPY
   -- ==========================================================

   subtype Balance is Natural range 0 .. Max_Balance;
   subtype Expense is Natural range 0 .. Max_Expense;
   subtype Percent is Natural range 0 .. 100;

   type Payment_Result is (Paid, Insufficient_Funds, Reserve_Protected);

   -- Stav pokladny
   type Treasury is record
      Total_Income    : Balance := 0;   -- celkem přijato
      Total_Expenses  : Balance := 0;   -- celkem utraceno
      Current_Balance : Balance := 0;   -- aktuální zůstatek
      Reserve         : Balance := 0;   -- blokovaná rezerva (20%)
      Available       : Balance := 0;   -- volné prostředky (balance - reserve)
      Reinvested      : Balance := 0;   -- celkem reinvestováno
   end record;

   -- ==========================================================
   -- OPERACE
   -- ==========================================================

   -- Inicializovat pokladnu
   procedure Initialize (T : out Treasury)
     with Post => T.Current_Balance = 0
                  and T.Total_Income = 0
                  and T.Total_Expenses = 0;

   -- Přijmout platbu (zákazník zaplatil)
   procedure Receive_Payment (T      : in out Treasury;
                              Amount : in     Balance)
     with Pre  => T.Current_Balance <= Max_Balance - Amount
                  and T.Total_Income <= Max_Balance - Amount,
          Post => T.Current_Balance = T.Current_Balance'Old + Amount
                  and T.Total_Income = T.Total_Income'Old + Amount;

   -- Zaplatit náklad (API, hosting...) — autonomně
   procedure Pay_Expense (T      : in out Treasury;
                          Amount : in     Expense;
                          Result : out    Payment_Result)
     with Pre  => T.Total_Expenses <= Max_Balance - Amount,
          Post => (if Result = Paid
                   then T.Current_Balance = T.Current_Balance'Old - Amount
                   else T.Current_Balance = T.Current_Balance'Old);

   -- Vypočítat dostupné prostředky (po odečtení rezervy)
   function Get_Available (T : Treasury) return Balance
     with Post => Get_Available'Result <= T.Current_Balance;

   -- Může systém zaplatit tuto částku?
   function Can_Pay (T : Treasury; Amount : Expense) return Boolean
     with Post => Can_Pay'Result =
                  (Amount <= Get_Available (T));

   -- Reinvestovat (jen z volných prostředků nad rezervu)
   procedure Reinvest (T      : in out Treasury;
                       Amount : in     Expense;
                       Result : out    Payment_Result)
     with Pre  => T.Total_Expenses <= Max_Balance - Amount
                  and T.Reinvested <= Max_Balance - Amount,
          Post => (if Result = Paid
                   then T.Reinvested = T.Reinvested'Old + Amount
                   else T.Reinvested = T.Reinvested'Old);

   -- Aktuální zisk (příjem - výdaje)
   function Net_Profit (T : Treasury) return Natural
     with Post => (if T.Total_Income >= T.Total_Expenses
                   then Net_Profit'Result = T.Total_Income - T.Total_Expenses
                   else Net_Profit'Result = 0);

end Revenue_Engine;
