-- ================================================================
-- GEALL — Transkomunikátor
-- Brána do Web4.23 VR systému
-- ================================================================
--
-- GEALL = GE(mini) + ALL = Gemini pro všechny
-- Zkráceně GAL — jediná výška vzdorující Římu.
-- Jako Galie u Asterixe: malá pevnost, která odolává celému impériu.
--
-- Architektura:
--   Uživatel → Geall (Ada) → Gemini CLI → odpověď
--                ↓
--           Mincovna.Verify(KYC) → Granted/Denied
--
-- Geall NENÍ vidět jako n8n — uživatel vidí jediného agenta.
-- ================================================================

with Mincovna;

package Geall is
   pragma SPARK_Mode (On);

   -- Maximální délka zprávy
   subtype Message_String is String (1 .. 4096);

   -- Výsledek zpracování
   type Response_Status is (Success, Auth_Failed, Error);

   type Response is record
      Status  : Response_Status;
      Message : Message_String;
      Length  : Natural;  -- skutečná délka odpovědi
   end record;

   -- ============================================================
   -- HLAVNÍ ROZHRANÍ GEALL
   -- Přijme zprávu od uživatele, ověří KYC, zavolá Gemini
   -- ============================================================
   procedure Process_Message
     (User_Token : in     Mincovna.Token_String;
      Input      : in     String;
      Output     :    out Response)
     with Pre => Input'Length > 0 and Input'Length <= 4096;

end Geall;
