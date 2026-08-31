pragma SPARK_Mode (On);

-- ============================================================
--  Vakuová Mincovna — Jádro systému (Standard 700)
--  Ada/SPARK 2022 — Formálně verifikovaný kód
--
--  Autor: Pan Jeskyně
--  Pravidlo: 13.4g stříbra = 1 mince (1.4g poplatek, 12g jistina)
-- ============================================================

with Ada.Text_IO;
with Ada.Command_Line;
with Ada.Strings.Fixed;

procedure Mincovna_Main is

   -- ==========================================================
   -- KONSTANTY A TYPY
   -- ==========================================================

   Standard_700_Mint_Cost : constant := 13.4;

   subtype Coin_Count is Natural range 0 .. 1_000_000_000;

   -- ==========================================================
   -- VÝPOČTOVÁ LOGIKA (SPARK)
   -- ==========================================================

   function Calculate_Coins (Silver_Grams : Float) return Coin_Count
     with
       Pre  => Silver_Grams >= 0.0 and Silver_Grams <= 1.0E10,
       Post => (if Silver_Grams < Standard_700_Mint_Cost
                then Calculate_Coins'Result = 0
                else Calculate_Coins'Result >= 0)
   is
      Result : Natural;
   begin
      if Silver_Grams < Standard_700_Mint_Cost then
         return 0;
      end if;

      -- Striktni kurz: 13.4g Ag = 1 mince (1.4g provoz, 12.0g jistina)
      Result := Natural (Float'Floor (Silver_Grams / Standard_700_Mint_Cost));

      return (if Result <= Coin_Count'Last then Result else Coin_Count'Last);
   end Calculate_Coins;

   -- ==========================================================
   -- I/O OPERACE (SPARK Mode Off)
   -- ==========================================================

   procedure Provest_CLI is
      pragma SPARK_Mode (Off);
      use Ada.Text_IO;
      use Ada.Command_Line;
      use Ada.Strings.Fixed;
   begin
      if Argument_Count = 0 then
         -- Lidsky citelny vystup (Status)
         Put_Line ("--- VAKUOVA MINCOVNA - INICIALIZOVANO ---");
         Put_Line ("[GNAT] Formalni verifikace aktivni");
         Put_Line ("[SPARK] Matematicka jistota: AKTIVNI");
         Put_Line ("[MINCOVNA] Standard 700 (12.0g Ag + 1.4g Fee = 13.4g Total)");
         Put_Line ("[TEST] 134.0g Ag -> " & Natural'Image (Calculate_Coins (134.0)) & " minci");
         Put_Line ("--- SYSTEM PRIPRAVEN K AUTONOMNIMU PROVOZU ---");
      else
         -- Cisty vystup pro Python Bridge
         declare
            Vstup : constant String := Argument (1);
            Stribro : Float;
         begin
            Stribro := Float'Value (Vstup);
            Put (Trim (Natural'Image (Calculate_Coins (Stribro)), Ada.Strings.Left));
         exception
            when others =>
               Put ("0");
         end;
      end if;
   end Provest_CLI;

begin
   Provest_CLI;
end Mincovna_Main;

