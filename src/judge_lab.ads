-- ============================================================
--  Judge Lab — Pravni AI Studio (Asgard)
--
--  Posuzuje, soudí, audituje. Zadny kompromis.
--  Verdikt je SIC nebo NON. Zadna seda zona.
--
--  Agent: Justyna — soudkyne AI
--
--  Schopnosti:
--    - Posouzeni smart contractu (Solidity audit)
--    - Validace licenci (GPL/Apache/MIT compliance)
--    - KYC verifikace (je agent legitimni?)
--    - Verdikt nad kodem (proved/unproved)
--    - Audit agentu (kdo lze = smazan)
--    - MUSH DO++ certifikace
--
--  SPARK proved — verdikt je matematicky jisty.
--  GPL-free. Apache 2.0.
--
--  Autor: Pan Jeskyne
--  Organizace: Rebirth Phoenix Foundation Charter
-- ============================================================

pragma SPARK_Mode (On);

package Judge_Lab is

   -- =========================================================
   --  Verdikt — SIC nebo NON. Zadna nula.
   -- =========================================================

   type Verdict is (SIC, NON);
   -- SIC = schvaleno, proved, legitimni
   -- NON = zamitnuto, unproved, podezrele

   -- Duvod verdiktu
   type Verdict_Reason is (License_OK,         -- licence je cista
                           License_Violation,   -- GPL contamination
                           Code_Proved,         -- SPARK proved
                           Code_Unproved,       -- neverifikovano
                           Agent_Certified,     -- agent prosel MUSH DO++
                           Agent_Rejected,      -- agent lhal → smazat
                           Contract_Safe,       -- smart contract OK
                           Contract_Vuln,       -- zranitelnost nalezena
                           KYC_Passed,          -- identita overena
                           KYC_Failed,          -- identita neprukazna
                           Audit_Clean,         -- audit cisty
                           Audit_Suspicious);   -- podezrele chovani

   -- =========================================================
   --  Typy pripadu
   -- =========================================================

   type Case_Kind is (License_Audit,      -- kontrola licenci
                      Code_Verification,   -- SPARK/Asterisk prove
                      Agent_Certification, -- MUSH DO++ test
                      Smart_Contract_Audit,-- Solidity/ETH audit
                      KYC_Verification,    -- identita NFT
                      Behavior_Audit);     -- chovani agenta

   -- Priorita pripadu
   type Case_Priority is (Critical,   -- okamzite (bezpecnost)
                          High,       -- do 1 hodiny
                          Normal,     -- do 24 hodin
                          Low);       -- kdyz bude cas

   -- Stav pripadu
   type Case_Status is (Filed,        -- podano
                        Under_Review, -- Justyna zkouma
                        Verdict_Made, -- rozhodnuto
                        Enforced,     -- vykonano
                        Archived);    -- archivovano

   -- =========================================================
   --  Pripad (Case)
   -- =========================================================

   Max_Case_ID : constant := 999_999;
   subtype Case_ID is Positive range 1 .. Max_Case_ID;

   type Court_Case is record
      ID        : Case_ID := 1;
      Kind      : Case_Kind := License_Audit;
      Priority  : Case_Priority := Normal;
      Status    : Case_Status := Filed;
      Decision  : Verdict := NON;       -- default: zamitni (bezpecne)
      Reason    : Verdict_Reason := Audit_Suspicious;
      Appealed  : Boolean := False;     -- odvolani?
      Enforced  : Boolean := False;     -- vykonano?
   end record;

   -- =========================================================
   --  Justyna — operace
   -- =========================================================

   -- Zahaj pripad
   procedure File_Case (C    : in out Court_Case;
                        Kind : Case_Kind;
                        Prio : Case_Priority)
     with Pre  => C.Status = Filed,
          Post => C.Status = Under_Review and C.Kind = Kind;

   -- Vynest verdikt
   procedure Render_Verdict (C      : in out Court_Case;
                             Result : Verdict;
                             Reason : Verdict_Reason)
     with Pre  => C.Status = Under_Review,
          Post => C.Status = Verdict_Made and
                  C.Decision = Result and C.Reason = Reason;

   -- Vykonat verdikt (smazat agenta, zablokovat contract, atd)
   procedure Enforce (C : in out Court_Case)
     with Pre  => C.Status = Verdict_Made,
          Post => C.Status = Enforced and C.Enforced = True;

   -- Odvolani (jednou — zadne nekonecne smycky)
   procedure Appeal (C : in out Court_Case)
     with Pre  => C.Status = Verdict_Made and C.Appealed = False,
          Post => C.Status = Under_Review and C.Appealed = True;

   -- Archivovat
   procedure Archive (C : in out Court_Case)
     with Pre  => C.Status = Enforced,
          Post => C.Status = Archived;

   -- =========================================================
   --  Statistiky
   -- =========================================================

   type Case_Counter is new Natural range 0 .. Max_Case_ID;

   procedure Count_Case (Counter : in out Case_Counter)
     with Pre  => Counter < Case_Counter'Last,
          Post => Counter = Counter'Old + 1;

   -- Kolik SIC vs NON
   function Conviction_Rate (SIC_Count : Case_Counter;
                             Total     : Case_Counter) return Natural
     with Pre  => Total > 0,
          Post => Conviction_Rate'Result <= 100;

end Judge_Lab;
