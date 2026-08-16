-- ============================================================
--  Interaction_Memory — Implementace Paměťové Banky
--  Ada/SPARK 2022 — Formálně verifikovaná správa paměti
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (On);

package body Interaction_Memory is

   -- ==========================================================
   -- INICIALIZACE
   -- ==========================================================

   procedure Initialize (B       : out User_Memory_Bank;
                         User_ID : User_Index) is
   begin
      B.Total_Stored := 0;
      B.User_ID      := User_ID;
      B.Locked       := False;

      for I in 1 .. Max_Entries_Per_User loop
         B.Entries (I) := (ID       => 0,
                           Category => Session_Fact,
                           Len      => 0,
                           Text     => (others => ' '),
                           Active   => False);
      end loop;
   end Initialize;

   -- ==========================================================
   -- ULOŽENÍ INTERAKCE
   -- ==========================================================

   procedure Store_Interaction (B        : in out User_Memory_Bank;
                                Category : Memory_Category;
                                Text_Len : Context_Length;
                                Success  : out Boolean) is
   begin
      if B.Total_Stored < Max_Entries_Per_User and then not B.Locked then
         B.Total_Stored := B.Total_Stored + 1;
         B.Entries (B.Total_Stored) :=
           (ID       => B.Total_Stored,
            Category => Category,
            Len      => Text_Len,
            Text     => (others => ' '),
            Active   => True);
         Success := True;
      else
         Success := False;
      end if;
   end Store_Interaction;

   -- ==========================================================
   -- KOMPAKCE PAMĚTI
   -- ==========================================================

   procedure Compact_Memory (B : in out User_Memory_Bank) is
   begin
      -- Kontrola integrity a udržení invariantu velikosti
      if B.Total_Stored > Max_Entries_Per_User then
         B.Total_Stored := Max_Entries_Per_User;
      end if;
   end Compact_Memory;

end Interaction_Memory;
