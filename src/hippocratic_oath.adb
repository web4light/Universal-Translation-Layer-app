-- ============================================================
--  Hippocratic_Oath — Implementace Digitální Hippokratovy Přísahy
--  Ada/SPARK 2022 — Formálně verifikovaný etický kodex
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (On);

package body Hippocratic_Oath is

   function Check_Data_Access (Client_Consent : Boolean;
                               Life_Emergency : Boolean) return Ethics_Decision is
   begin
      if Life_Emergency then
         return Allowed_Emergency;
      elsif Client_Consent then
         return Allowed;
      else
         return Denied_No_Consent;
      end if;
   end Check_Data_Access;

   function Check_Voice_Recording (Is_Own_Voice      : Boolean;
                                   Third_Party_Agree : Boolean) return Ethics_Decision is
   begin
      if Is_Own_Voice or Third_Party_Agree then
         return Allowed;
      else
         return Denied_Voice_Violation;
      end if;
   end Check_Voice_Recording;

   function Is_Permitted (Decision : Ethics_Decision) return Boolean is
   begin
      return Decision = Allowed or Decision = Allowed_Emergency;
   end Is_Permitted;

end Hippocratic_Oath;
