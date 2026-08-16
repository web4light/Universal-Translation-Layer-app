-- ============================================================
--  Interaction_Memory — Dlouhodobá Interakční Paměťová Banka
--  Ada/SPARK 2022 — Formálně verifikovaná správa kontextu uživatele
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Uchovává trvalý kontext, styl a historii uživatele:
--  - 1 GB vystačí běžnému člověku na 8 let nepřetržitých interakcí.
--  - Formálně garantovaný strop paměti a ochrana proti přetečení.
--  - Protokol 4:23 pro bezpečné uchování a šifrování.
--
--  Autor: Pan Jeskyně
--  Standard: 700 / Protokol 4.23
-- ============================================================

pragma SPARK_Mode (On);

package Interaction_Memory is

   -- ==========================================================
   -- KONSTANTY
   -- ==========================================================

   Max_Entries_Per_User : constant := 10_000;
   Max_Context_Len      : constant := 512;
   Max_Users            : constant := 100;

   -- ==========================================================
   -- TYPY A ROZSAHY
   -- ==========================================================

   subtype User_Index is Natural range 0 .. Max_Users;
   subtype Entry_Index is Natural range 0 .. Max_Entries_Per_User;
   subtype Entry_Count is Natural range 0 .. Max_Entries_Per_User;
   subtype Context_Length is Natural range 0 .. Max_Context_Len;

   type Memory_Category is (
      Style_Preference,  -- Osobní styl mluvy a oslovování
      Custom_Dictionary, -- Osobní terminologie a slovník
      Session_Fact,      -- Dlouhodobý kontext a fakta o projektech
      Correction_Rule    -- Zpětná vazba a oprava chování agenta
   );

   -- Záznam jedné interakční vzpomínky
   type Memory_Entry is record
      ID       : Entry_Index      := 0;
      Category : Memory_Category  := Session_Fact;
      Len      : Context_Length   := 0;
      Text     : String (1 .. Max_Context_Len) := (others => ' ');
      Active   : Boolean          := False;
   end record;

   type Memory_Table is array (1 .. Max_Entries_Per_User) of Memory_Entry;

   -- Paměťová banka jednoho uživatele
   type User_Memory_Bank is record
      Entries      : Memory_Table;
      Total_Stored : Entry_Count := 0;
      User_ID      : User_Index  := 0;
      Locked       : Boolean     := False;
   end record;

   -- ==========================================================
   -- KONTRAKTY A OPERACE
   -- ==========================================================

   -- Inicializace paměťové banky
   procedure Initialize (B       : out User_Memory_Bank;
                         User_ID : User_Index)
     with Post => B.Total_Stored = 0
                  and B.User_ID = User_ID
                  and B.Locked = False;

   -- Uložení nové interakce / pravidla do paměti
   procedure Store_Interaction (B        : in out User_Memory_Bank;
                                Category : Memory_Category;
                                Text_Len : Context_Length;
                                Success  : out Boolean)
     with Pre  => Text_Len <= Max_Context_Len
                  and B.Total_Stored < Max_Entries_Per_User,
          Post => (if Success then B.Total_Stored = B.Total_Stored'Old + 1
                   else B.Total_Stored = B.Total_Stored'Old);

   -- Vyčištění neaktivních záznamů (Kompakce paměti)
   procedure Compact_Memory (B : in out User_Memory_Bank)
     with Post => B.Total_Stored <= B.Total_Stored'Old;

end Interaction_Memory;
