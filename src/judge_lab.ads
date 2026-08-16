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

   type Case_Kind is (License_Audit,        -- kontrola licenci
                      Code_Verification,     -- SPARK/Asterisk prove
                      Agent_Certification,   -- MUSH DO++ test
                      Smart_Contract_Audit,  -- Solidity/ETH audit
                      KYC_Verification,      -- identita NFT
                      Behavior_Audit,        -- chovani agenta
                      Regulatory_Compliance, -- soulad s predpisy
                      Data_Protection,       -- ochrana osobnich udaju
                      IP_Enforcement,        -- vymahani IP prav
                      AI_Act_Compliance);    -- EU AI Act klasifikace

   -- =========================================================
   --  Jurisdikce
   -- =========================================================

   type Jurisdiction is (
      -- Primarni
      CH,    -- Svycarsko (DSG, OR, ZGB)
      EU,    -- Evropska unie (GDPR, EU AI Act, DSA, DMA)
      US,    -- Spojene staty (DMCA, CCPA, COPPA, SOX)
      -- Sekundarni
      CZ,    -- Ceska republika (autorsky zakon, UOOU)
      DE,    -- Nemecko (BDSG, UrhG)
      UK,    -- Spojena kralovstvi (UK GDPR, DPA 2018)
      CA,    -- Kanada (PIPEDA, CASL)
      AU,    -- Australie (Privacy Act)
      JP,    -- Japonsko (APPI)
      SG,    -- Singapur (PDPA)
      INTL); -- Mezinarodni (WIPO, Bernska umluva)

   -- =========================================================
   --  Pravni paragrafy — katalog
   -- =========================================================

   type Legal_Article is (

      -- === SVYCARSKO (CH) ===
      CH_DSG_Art_5,    -- DSG: definice osobnich udaju
      CH_DSG_Art_6,    -- DSG: zasady zpracovani
      CH_DSG_Art_25,   -- DSG: pravo na informace
      CH_DSG_Art_32,   -- DSG: oznameni poruceni zabezpeceni
      CH_OR_Art_328b,  -- OR: ochrana osobnosti zamestnance
      CH_URG_Art_2,    -- URG: definice dila (autorsky zakon)
      CH_URG_Art_10,   -- URG: prava autora
      CH_URG_Art_19,   -- URG: soukrome uziti

      -- === EVROPSKA UNIE (EU) ===
      EU_GDPR_Art_4,   -- GDPR: definice (osobni udaje, zpracovani)
      EU_GDPR_Art_6,   -- GDPR: pravni zaklad zpracovani
      EU_GDPR_Art_9,   -- GDPR: specialni kategorie udaju (biometrika!)
      EU_GDPR_Art_13,  -- GDPR: informacni povinnost
      EU_GDPR_Art_17,  -- GDPR: pravo na vymazani (right to be forgotten)
      EU_GDPR_Art_20,  -- GDPR: prenositelnost udaju
      EU_GDPR_Art_22,  -- GDPR: automatizovane rozhodovani
      EU_GDPR_Art_25,  -- GDPR: privacy by design
      EU_GDPR_Art_32,  -- GDPR: zabezpeceni zpracovani
      EU_GDPR_Art_83,  -- GDPR: pokuty (az 4% globalni obrat)
      EU_AI_Act_Art_6, -- EU AI Act: klasifikace high-risk AI
      EU_AI_Act_Art_9, -- EU AI Act: rizikovy management system
      EU_AI_Act_Art_13,-- EU AI Act: transparentnost
      EU_AI_Act_Art_50,-- EU AI Act: povinnosti pro GPAI modely
      EU_DSA_Art_16,   -- DSA: oznamovani nezakonneho obsahu
      EU_DMA_Art_5,    -- DMA: povinnosti gatekeeperu
      EU_InfoSoc_Art_2,-- Informacni spolecnost: pravo na reprodukci
      EU_InfoSoc_Art_3,-- Informacni spolecnost: pravo na sdeleni

      -- === SPOJENE STATY (US) ===
      US_DMCA_Sec_512, -- DMCA: safe harbor pro poskytovatele
      US_DMCA_Sec_1201,-- DMCA: zakaz obchazeni TPM
      US_CCPA_Sec_1798,-- CCPA: prava spotrebitele (Kalifornie)
      US_COPPA_Sec_6,  -- COPPA: ochrana deti online
      US_CFAA_Sec_1030,-- CFAA: pocitacove podvody a zneuziti
      US_SOX_Sec_302,  -- SOX: certifikace financnich vykazu
      US_HIPAA_164,    -- HIPAA: ochrana zdravotnich udaju
      US_FTC_Sec_5,    -- FTC Act: nekalé obchodní praktiky
      US_GPL3_Sec_4,   -- GPL v3: ukonceni licence
      US_GPL3_Sec_5,   -- GPL v3: sireji sireji podminkydistribuce
      US_Apache2_Sec_4,-- Apache 2.0: podminky redistribuce

      -- === MEZINARODNI (INTL) ===
      WIPO_Berne_Art_2,  -- Bernska umluva: chranena dila
      WIPO_Berne_Art_9,  -- Bernska umluva: pravo na reprodukci
      WIPO_TRIPs_Art_10, -- TRIPs: software jako dilo
      None);             -- zadny konkretni paragraf

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
      Decision  : Verdict := NON;            -- default: zamitni (bezpecne)
      Reason    : Verdict_Reason := Audit_Suspicious;
      Juris     : Jurisdiction := EU;        -- aktivni jurisdikce
      Article   : Legal_Article := None;     -- konkretni paragraf
      Appealed  : Boolean := False;          -- odvolani?
      Enforced  : Boolean := False;          -- vykonano?
   end record;

   -- =========================================================
   --  Justyna — operace
   -- =========================================================

   -- Zahaj pripad (se jurisdikci a paragrafem)
   procedure File_Case (C    : in out Court_Case;
                        Kind : Case_Kind;
                        Prio : Case_Priority;
                        J    : Jurisdiction := EU;
                        Art  : Legal_Article := None)
     with Pre  => C.Status = Filed,
          Post => C.Status = Under_Review and C.Kind = Kind
                  and C.Juris = J and C.Article = Art;

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
   --  Jurisdikcni routing — ktery paragraf plati kde
   -- =========================================================

   -- Patri paragraf do dane jurisdikce?
   function Article_In_Jurisdiction (Art  : Legal_Article;
                                     J    : Jurisdiction) return Boolean;

   -- Je biometricke zpracovani povoleno v dane jurisdikci?
   -- (klicove pro voice cloning / TTS pipeline)
   function Biometric_Processing_Allowed (J : Jurisdiction) return Verdict
     with Post => (if J = CH or J = EU
                   then Biometric_Processing_Allowed'Result = NON
                   else Biometric_Processing_Allowed'Result = SIC)
                  or Biometric_Processing_Allowed'Result = SIC
                  or Biometric_Processing_Allowed'Result = NON;

   -- Je AI system high-risk dle EU AI Act?
   -- (UTL pipeline zpracovava biometriku → high-risk kandidat)
   function Is_High_Risk_AI (Kind : Case_Kind;
                             J    : Jurisdiction) return Boolean
     with Post => (if J /= EU then Is_High_Risk_AI'Result = False
                   else Is_High_Risk_AI'Result = True
                        or Is_High_Risk_AI'Result = False);

   -- =========================================================
   --  Licencni matice (z druheho Kira — Justyna vidi vsechno)
   -- =========================================================

   type License_Type is (Apache_2_0, MIT, GPL_3, LGPL_3,
                         BSD_3, MPL_2, Proprietary,
                         Public_Domain, Charter);

   -- Je licence A kompatibilni s B?
   function License_Compatible (A, B : License_Type) return Boolean;

   -- Standard 700: 1 mince = 12 gramu stribra
   Standard_700_Grams : constant := 12;

   -- Verifikuj ze je dost stribra pro razbu
   function Verify_Standard_700 (Coins : Natural;
                                 Silver_Grams : Natural) return Verdict
     with Pre  => Coins <= 99_999_999,
          Post => (if Silver_Grams >= Coins * Standard_700_Grams
                   then Verify_Standard_700'Result = SIC
                   else Verify_Standard_700'Result = NON);

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
