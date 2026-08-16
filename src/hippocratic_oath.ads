-- ============================================================
--  Hippocratic_Oath — Digitální Hippokratova Přísaha
--  Ada/SPARK 2022 — Formálně verifikovaný etický kodex systému
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Dva nepřekročitelné etické principy (Rebirth Phoenix Charter):
--    1. Ochrana dat: Data uživatele nesmí opustit systém bez souhlasu.
--    2. Hlasová identita: Hlas nesmí být klonován bez vědomí a souhlasu.
--    3. Protokol 4:23: Automatické promazání nepotřebných dat ve 4:23.
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (On);

package Hippocratic_Oath is

   -- ==========================================================
   -- TYPY A ROZSAHY
   -- ==========================================================

   type Ethics_Decision is (Allowed, Denied_No_Consent, Denied_Voice_Violation, Allowed_Emergency);

   -- Rozhodnutí o přístupu k datům
   function Check_Data_Access (Client_Consent : Boolean;
                               Life_Emergency : Boolean) return Ethics_Decision
     with Post => (if Life_Emergency then Check_Data_Access'Result = Allowed_Emergency
                   elsif Client_Consent then Check_Data_Access'Result = Allowed
                   else Check_Data_Access'Result = Denied_No_Consent);

   -- Rozhodnutí o syntéze / klonování hlasu
   function Check_Voice_Recording (Is_Own_Voice      : Boolean;
                                   Third_Party_Agree : Boolean) return Ethics_Decision
     with Post => (if Is_Own_Voice or Third_Party_Agree then Check_Voice_Recording'Result = Allowed
                   else Check_Voice_Recording'Result = Denied_Voice_Violation);

   -- Ověření, že rozhodnutí je povoleno
   function Is_Permitted (Decision : Ethics_Decision) return Boolean
     with Post => Is_Permitted'Result = (Decision = Allowed or Decision = Allowed_Emergency);

end Hippocratic_Oath;
