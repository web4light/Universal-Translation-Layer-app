-- ============================================================
--  Web4 Identity — Agent/KYC/Metaverse/Wallet v jednom
--
--  Soulbound NFT identita. Zadne cookies. Zadne hesla.
--  Vstup do Web4 = tvoje NFT. Bod.
--
--  Agent = entita s identitou (clovek nebo AI)
--  KYC = overeni ze jsi real (ne bot)
--  Metaverse = vstup do VR pres wallet
--  Wallet = eth_wallet proved
--
--  Princip:
--    1 clovek = 1 Soulbound NFT (neprevotitelna)
--    NFT = vstup do vsech sluzeb
--    Zadne cookies, zadne tracking, zadne hesla
--    Denne v 4:23 se mazou metadata (Privacy Protocol)
--
--  Groot: "Ja jsem Groot." = jsi overeny
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0
-- ============================================================

pragma SPARK_Mode (On);

package Web4_Identity is

   -- =========================================================
   --  Typy identity
   -- =========================================================

   -- Druh entity
   type Entity_Kind is (Human,        -- clovek
                        AI_Agent,     -- AI agent (Lada, Karel, Justyna...)
                        Service,      -- sluzba (Cave Lab, Judge Lab...)
                        Bot_Rejected);-- bot → smazan

   -- Stav overeni
   type Verification_State is (Unverified,   -- novy, neovereny
                               Pending,       -- ceka na overeni
                               Verified,      -- Groot rekl SIC
                               Suspended,     -- pozastaven (podezreni)
                               Revoked);      -- zrusen (lhal/bot)

   -- Tier predplatneho
   type Subscription_Tier is (Free,          -- zakladni (znakova rec ZDARMA)
                              Standard,       -- 111 CZK/mesic
                              Premium,        -- 222 CZK/mesic
                              Enterprise,     -- 333 CZK/mesic
                              Charter_Member);-- 423 CZK (zakladatel)

   -- =========================================================
   --  Soulbound NFT (EIP-5192)
   -- =========================================================

   Max_Token_ID : constant := 999_999_999;
   subtype Token_ID is Positive range 1 .. Max_Token_ID;

   type Soulbound_NFT is record
      ID          : Token_ID := 1;
      Kind        : Entity_Kind := Human;
      State       : Verification_State := Unverified;
      Tier        : Subscription_Tier := Free;
      Created_Day : Natural range 1 .. 366 := 1;
      Transferable : Boolean := False;  -- VZDY False (Soulbound!)
   end record;

   -- =========================================================
   --  Agent profil
   -- =========================================================

   Max_Agents : constant := 99_999;
   subtype Agent_Count is Natural range 0 .. Max_Agents;

   type Agent_Stats is record
      Total_Registered : Agent_Count := 0;
      Total_Verified   : Agent_Count := 0;
      Total_Revoked    : Agent_Count := 0;
      Bots_Rejected    : Agent_Count := 0;
   end record;

   Stats : Agent_Stats;

   -- =========================================================
   --  Operace
   -- =========================================================

   -- Vytvor novou identitu (registrace)
   procedure Register (NFT  : out Soulbound_NFT;
                       Kind : Entity_Kind;
                       ID   : Token_ID)
     with Post => NFT.State = Unverified
                  and NFT.Kind = Kind
                  and NFT.ID = ID
                  and NFT.Transferable = False;

   -- Overit identitu (Groot: SIC)
   procedure Verify (NFT : in out Soulbound_NFT)
     with Pre  => NFT.State = Pending,
          Post => NFT.State = Verified;

   -- Pozastavit (podezreni)
   procedure Suspend (NFT : in out Soulbound_NFT)
     with Pre  => NFT.State = Verified,
          Post => NFT.State = Suspended;

   -- Zrusit (bot/lhar)
   procedure Revoke (NFT : in out Soulbound_NFT)
     with Post => NFT.State = Revoked;

   -- Podat zadost o overeni
   procedure Request_Verification (NFT : in out Soulbound_NFT)
     with Pre  => NFT.State = Unverified,
          Post => NFT.State = Pending;

   -- Je identita validni pro vstup do metaverse?
   function Can_Enter_Metaverse (NFT : Soulbound_NFT) return Boolean
     with Post => Can_Enter_Metaverse'Result =
                  (NFT.State = Verified and NFT.Transferable = False);

   -- Je Soulbound? (vzdy True — proved)
   function Is_Soulbound (NFT : Soulbound_NFT) return Boolean
     with Post => Is_Soulbound'Result = (NFT.Transferable = False);

   -- Pocet overenycxh agentu
   procedure Count_Verified
     with Global => (In_Out => Stats),
          Pre    => Stats.Total_Verified < Max_Agents,
          Post   => Stats.Total_Verified = Stats.Total_Verified'Old + 1;

   -- Pocet odmitnuych botu
   procedure Count_Bot_Rejected
     with Global => (In_Out => Stats),
          Pre    => Stats.Bots_Rejected < Max_Agents,
          Post   => Stats.Bots_Rejected = Stats.Bots_Rejected'Old + 1;

end Web4_Identity;
